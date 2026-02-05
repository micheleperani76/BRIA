#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Worker Trascrizione Audio
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-03
# Descrizione: Processo background che elabora la coda di trascrizione.
#              Gira come servizio systemd, elabora un file alla volta.
#
# Uso:     python3 scripts/worker_trascrizione.py
# Servizio: systemctl start trascrizione-worker
# ==============================================================================

import os
import sys
import time
import json
import shutil
import signal
import sqlite3
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# ==============================================================================
# SETUP PATH
# ==============================================================================

BASE_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(BASE_DIR))

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

# Importa configurazione da file conf
try:
    from app.config_trascrizione import (
        MODELLO, MODELLO_VELOCE, LINGUA_DEFAULT, DEVICE, COMPUTE_TYPE,
        ORARIO_INIZIO, ORARIO_STOP, SOGLIA_GRANDE_BYTES, SOGLIA_CODA_TURBO,
        RETENTION_AUDIO_GIORNI, RETENTION_CONSUMO_GIORNI,
        POLLING_SECONDI, AGGIORNAMENTO_PROGRESSO, NUM_THREADS,
        LD_PRELOAD, DB_FILE,
        DIR_ATTESA, DIR_LAVORAZIONE, DIR_COMPLETATI, DIR_TESTI, DIR_CONSUMO,
        TRASCRIZIONE_DIR,
        is_orario_elaborazione, stima_tempo_trascrizione,
        get_dir_consumo_data, inizializza_cartelle
    )
except ImportError:
    print("ERRORE: Impossibile importare config_trascrizione.")
    print("Verificare che app/config_trascrizione.py esista.")
    sys.exit(1)

# Importa config clienti per path
try:
    from app.config import get_cliente_base_path
except ImportError:
    def get_cliente_base_path(cliente):
        return None


# Importa connettore notifiche trascrizione
try:
    from app.connettori_notifiche.trascrizione import (
        notifica_trascrizione_completata,
        notifica_trascrizione_errore
    )
    NOTIFICHE_ATTIVE = True
except ImportError:
    NOTIFICHE_ATTIVE = False

# ==============================================================================
# LOGGING
# ==============================================================================

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "trascrizione.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(str(LOG_FILE), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('worker_trascrizione')


# ==============================================================================
# VARIABILI GLOBALI
# ==============================================================================

# Flag per shutdown graceful
_shutdown = False

# Modello whisper (caricato una volta sola)
_modello_corrente = None
_nome_modello_corrente = None


def _invia_notifica(func, job, **kwargs):
    """
    Wrapper sicuro per invio notifiche.
    Apre una connessione dedicata per non interferire col worker.
    """
    if not NOTIFICHE_ATTIVE:
        return
    try:
        conn_notif = sqlite3.connect(str(DB_FILE))
        func(conn_notif, job, **kwargs)
        conn_notif.close()
        logger.info("  Notifica inviata")
    except Exception as e:
        logger.warning(f"  Notifica non inviata: {e}")


def signal_handler(sig, frame):
    """Gestisce SIGTERM e SIGINT per shutdown graceful."""
    global _shutdown
    logger.info("Ricevuto segnale di stop, attendo fine elaborazione corrente...")
    _shutdown = True

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


# ==============================================================================
# FUNZIONI DATABASE
# ==============================================================================

def get_db():
    """Ritorna connessione database."""
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def secondi_a_stop():
    """
    Calcola quanti secondi mancano alla fine dell'orario di elaborazione (ORARIO_STOP).
    Gestisce il caso in cui ORARIO_STOP e' dopo mezzanotte (es. 4:00).
    
    Returns:
        int: secondi rimasti, o 0 se fuori orario
    """
    from datetime import datetime as dt, timedelta
    now = dt.now()
    ora = now.hour
    
    if ORARIO_INIZIO <= ORARIO_STOP:
        # Caso semplice (es. 7-20)
        stop_oggi = now.replace(hour=ORARIO_STOP, minute=0, second=0, microsecond=0)
        diff = (stop_oggi - now).total_seconds()
    else:
        # Caso overnight (es. 7-4 del giorno dopo)
        if ora >= ORARIO_INIZIO:
            # Siamo nella prima parte (es. dalle 7 a mezzanotte)
            stop_domani = (now + timedelta(days=1)).replace(hour=ORARIO_STOP, minute=0, second=0, microsecond=0)
            diff = (stop_domani - now).total_seconds()
        else:
            # Siamo nella seconda parte (es. da mezzanotte alle 4)
            stop_oggi = now.replace(hour=ORARIO_STOP, minute=0, second=0, microsecond=0)
            diff = (stop_oggi - now).total_seconds()
    
    return max(0, int(diff))


def job_entra_in_orario(job):
    """
    Verifica se un job puo' essere completato prima della fine dell'orario.
    Aggiunge un margine di sicurezza del 30% alla stima.
    
    Args:
        job: dict del job dalla coda
    
    Returns:
        bool: True se il job puo' essere completato in tempo
    """
    durata_audio = job.get('durata_secondi', 0)
    modello = job.get('modello', None)
    
    if durata_audio <= 0:
        # Durata sconosciuta, lascia passare
        return True
    
    tempo_stimato = stima_tempo_trascrizione(durata_audio, modello)
    # Margine sicurezza 30% + 5 minuti per conversione/salvataggio
    tempo_con_margine = int(tempo_stimato * 1.3) + 300
    
    rimasti = secondi_a_stop()
    
    if tempo_con_margine <= rimasti:
        return True
    
    logger.info(
        f"  Job #{job['id']} richiederebbe ~{tempo_con_margine//60}min, "
        f"rimangono {rimasti//60}min prima dello stop -> posticipato"
    )
    return False


def prossimo_job():
    """
    Prende il prossimo job dalla coda che puo' essere completato in orario.
    Ordine: priorita DESC (2=recovery, 1=normale, 0=bassa), poi data_inserimento ASC.
    Se un job non entra in orario, prova il successivo.
    
    Returns:
        dict o None
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM coda_trascrizioni
        WHERE stato = 'attesa'
        ORDER BY priorita DESC, data_inserimento ASC
        LIMIT 10
    ''')
    
    candidati = cursor.fetchall()
    conn.close()
    
    if not candidati:
        return None
    
    for job in candidati:
        job_dict = dict(job)
        if job_entra_in_orario(job_dict):
            return job_dict
    
    # Nessun job entra in orario - log una volta
    logger.info("Nessun job in coda entra nell'orario rimasto, attendo domani")
    return None


def conta_coda():
    """Conta file in attesa nella coda."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM coda_trascrizioni WHERE stato = 'attesa'")
    n = cursor.fetchone()[0]
    conn.close()
    return n


def aggiorna_stato(job_id, stato, **kwargs):
    """
    Aggiorna lo stato di un job.
    
    Args:
        job_id: ID del job
        stato: Nuovo stato
        **kwargs: Campi aggiuntivi da aggiornare
    """
    conn = get_db()
    cursor = conn.cursor()
    
    campi = ['stato = ?']
    valori = [stato]
    
    for chiave, valore in kwargs.items():
        campi.append(f'{chiave} = ?')
        valori.append(valore)
    
    valori.append(job_id)
    
    query = f"UPDATE coda_trascrizioni SET {', '.join(campi)} WHERE id = ?"
    cursor.execute(query, valori)
    conn.commit()
    conn.close()


def aggiorna_progresso(job_id, percentuale):
    """Aggiorna la percentuale di progresso."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE coda_trascrizioni SET progresso_percentuale = ? WHERE id = ?",
        (int(percentuale), job_id)
    )
    conn.commit()
    conn.close()


# ==============================================================================
# FUNZIONI AUDIO
# ==============================================================================

def get_durata_audio(file_path):
    """
    Ottiene la durata di un file audio con ffprobe.
    
    Args:
        file_path: Path al file audio
    
    Returns:
        float: Durata in secondi, o 0 se errore
    """
    try:
        result = subprocess.run(
            [
                'ffprobe', '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                str(file_path)
            ],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"Errore ffprobe: {e}")
    
    return 0.0


def converti_audio_wav(file_input, file_output):
    """
    Converte qualsiasi formato audio in WAV con ffmpeg.
    
    Args:
        file_input: Path file originale
        file_output: Path file WAV di output
    
    Returns:
        bool: True se conversione riuscita
    """
    try:
        result = subprocess.run(
            [
                'ffmpeg', '-y',             # Sovrascrivi
                '-i', str(file_input),       # Input
                '-ar', '16000',              # Sample rate 16kHz (ottimale per Whisper)
                '-ac', '1',                  # Mono
                '-acodec', 'pcm_s16le',      # PCM 16bit
                str(file_output)
            ],
            capture_output=True, text=True, timeout=300
        )
        
        if result.returncode != 0:
            logger.error(f"Errore ffmpeg: {result.stderr[:500]}")
            return False
        
        return file_output.exists()
        
    except subprocess.TimeoutExpired:
        logger.error("Timeout conversione ffmpeg (5 minuti)")
        return False
    except Exception as e:
        logger.error(f"Errore conversione: {e}")
        return False


# ==============================================================================
# FUNZIONI TRASCRIZIONE
# ==============================================================================

def carica_modello(nome_modello):
    """
    Carica il modello Whisper. Riusa il modello se gia caricato.
    
    Args:
        nome_modello: Nome modello (es. 'large-v3')
    
    Returns:
        WhisperModel
    """
    global _modello_corrente, _nome_modello_corrente
    
    if _modello_corrente is not None and _nome_modello_corrente == nome_modello:
        return _modello_corrente
    
    logger.info(f"Caricamento modello {nome_modello}...")
    
    from faster_whisper import WhisperModel
    _modello_corrente = WhisperModel(nome_modello, device=DEVICE, compute_type=COMPUTE_TYPE, cpu_threads=NUM_THREADS)
    _nome_modello_corrente = nome_modello
    
    logger.info(f"Modello {nome_modello} caricato")
    return _modello_corrente


def scegli_modello(job):
    """
    Sceglie quale modello usare in base a priorita e coda.
    
    Args:
        job: Dict del job corrente
    
    Returns:
        str: Nome modello da usare
    """
    # File a priorita bassa (>150MB) → sempre turbo
    if job.get('priorita', 1) == 0:
        return MODELLO_VELOCE
    
    # Coda lunga → turbo per smaltire
    n_coda = conta_coda()
    if n_coda >= SOGLIA_CODA_TURBO:
        logger.info(f"Coda con {n_coda} file, uso modello veloce")
        return MODELLO_VELOCE
    
    # Modello specificato nel job
    if job.get('modello') and job['modello'] != MODELLO:
        return job['modello']
    
    # Default: modello standard
    return MODELLO


def trascrivi_audio(file_wav, job_id, durata_totale, modello_nome):
    """
    Esegue la trascrizione con faster-whisper.
    Aggiorna il progresso nel DB durante l'elaborazione.
    
    Args:
        file_wav: Path al file WAV
        job_id: ID del job (per aggiornamento progresso)
        durata_totale: Durata audio in secondi
        modello_nome: Nome modello da usare
    
    Returns:
        str: Testo trascritto, o None se errore
    """
    try:
        model = carica_modello(modello_nome)
        
        segments, info = model.transcribe(
            str(file_wav),
            language=LINGUA_DEFAULT,
            vad_filter=True,            # Filtra silenzio
            vad_parameters=dict(
                min_silence_duration_ms=500,
            )
        )
        
        testo_completo = []
        ultimo_aggiornamento = time.time()
        
        for segment in segments:
            if _shutdown:
                logger.warning("Shutdown richiesto durante trascrizione")
                return None
            
            testo_completo.append(segment.text.strip())
            
            # Aggiorna progresso ogni N secondi
            if durata_totale > 0 and (time.time() - ultimo_aggiornamento) >= AGGIORNAMENTO_PROGRESSO:
                progresso = min(99, int((segment.end / durata_totale) * 100))
                aggiorna_progresso(job_id, progresso)
                ultimo_aggiornamento = time.time()
        
        return '\n'.join(testo_completo)
        
    except Exception as e:
        logger.error(f"Errore trascrizione: {e}")
        return None


# ==============================================================================
# FUNZIONI DESTINAZIONE FILE
# ==============================================================================

def get_destinazione_cliente(job):
    """
    Calcola i path di destinazione per trascrizione da cliente.
    
    Args:
        job: Dict del job
    
    Returns:
        tuple: (path_testo, path_audio) o (None, None) se errore
    """
    cliente_id = job.get('cliente_id')
    if not cliente_id:
        return None, None
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clienti WHERE id = ?", (cliente_id,))
    cliente = cursor.fetchone()
    conn.close()
    
    if not cliente:
        logger.error(f"Cliente ID {cliente_id} non trovato")
        return None, None
    
    try:
        base_path = get_cliente_base_path(dict(cliente))
        trascrizioni_dir = base_path / 'trascrizioni'
        trascrizioni_dir.mkdir(parents=True, exist_ok=True)
        
        # Nome file: timestamp + nome originale
        nome_orig = Path(job['nome_file_originale']).stem
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
        nome_base = f"{timestamp}_{nome_orig}"
        
        path_testo = trascrizioni_dir / f"{nome_base}.txt"
        path_audio = trascrizioni_dir / f"{nome_base}.{job.get('formato_originale', 'aac')}"
        
        return path_testo, path_audio
        
    except Exception as e:
        logger.error(f"Errore calcolo path cliente: {e}")
        return None, None


def get_destinazione_consumo(job):
    """
    Calcola i path di destinazione per trascrizione a consumo.
    
    Args:
        job: Dict del job
    
    Returns:
        tuple: (path_testo, None) - audio non viene conservato
    """
    codice_utente = job.get('codice_utente', '000000')
    data_dir = get_dir_consumo_data(codice_utente)
    
    nome_orig = Path(job['nome_file_originale']).stem
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
    nome_base = f"{timestamp}_{nome_orig}"
    
    path_testo = data_dir / f"{nome_base}.txt"
    
    return path_testo, None  # Audio non conservato


# ==============================================================================
# FUNZIONE PRINCIPALE ELABORAZIONE
# ==============================================================================

def elabora_job(job):
    """
    Elabora un singolo job di trascrizione.
    
    Flusso:
    1. Verifica che il job non sia stato eliminato
    2. Sposta file da attesa a lavorazione
    2. Converte in WAV con ffmpeg
    3. Calcola durata con ffprobe
    4. Trascrive con faster-whisper
    5. Salva testo nella destinazione corretta
    6. Sposta/elimina audio originale
    7. Aggiorna DB
    
    Args:
        job: Dict del job dalla tabella coda_trascrizioni
    
    Returns:
        bool: True se completato con successo
    """
    job_id = job['id']
    
    # Verifica che il job non sia stato eliminato nel frattempo
    conn_check = get_db()
    stato_db = conn_check.execute(
        "SELECT stato FROM coda_trascrizioni WHERE id = ?", (job_id,)
    ).fetchone()
    conn_check.close()
    if not stato_db or stato_db["stato"] == "eliminato":
        logger.info(f"  Job #{job_id} eliminato nel frattempo, salto")
        return False
    nome_sistema = job['nome_file_sistema']
    tipo = job['tipo']  # 'cliente' o 'dashboard'
    
    logger.info(f"--- Job #{job_id} - {job['nome_file_originale']} ({tipo}) ---")
    
    # 1. Sposta da attesa a lavorazione
    file_attesa = DIR_ATTESA / nome_sistema
    file_lavorazione = DIR_LAVORAZIONE / nome_sistema
    
    if not file_attesa.exists():
        logger.error(f"File non trovato in attesa: {file_attesa}")
        aggiorna_stato(job_id, 'errore', errore='File audio non trovato in coda')
        _invia_notifica(notifica_trascrizione_errore, job, errore_desc='File audio non trovato')
        return False
    
    shutil.move(str(file_attesa), str(file_lavorazione))
    aggiorna_stato(job_id, 'lavorazione',
        data_inizio_elaborazione=datetime.now().isoformat()
    )
    logger.info(f"  Spostato in lavorazione")
    
    # 2. Calcola durata
    durata = get_durata_audio(file_lavorazione)
    if durata > 0:
        aggiorna_stato(job_id, 'lavorazione', durata_secondi=durata)
        logger.info(f"  Durata audio: {int(durata//60)}m {int(durata%60)}s")
    
    # 3. Converti in WAV
    file_wav = DIR_LAVORAZIONE / f"{Path(nome_sistema).stem}.wav"
    
    logger.info(f"  Conversione in WAV...")
    if not converti_audio_wav(file_lavorazione, file_wav):
        logger.error("  Conversione WAV fallita")
        aggiorna_stato(job_id, 'errore', errore='Conversione audio fallita')
        _invia_notifica(notifica_trascrizione_errore, job, errore_desc='Conversione audio fallita')
        # Rimetti in attesa
        if file_lavorazione.exists():
            shutil.move(str(file_lavorazione), str(file_attesa))
        return False
    
    # 4. Scegli modello e trascrivi
    modello_nome = scegli_modello(job)
    tempo_stimato = stima_tempo_trascrizione(durata, modello_nome)
    logger.info(f"  Modello: {modello_nome}")
    logger.info(f"  Tempo stimato: {int(tempo_stimato//60)}m {int(tempo_stimato%60)}s")
    
    aggiorna_stato(job_id, 'lavorazione', modello=modello_nome)
    
    testo = trascrivi_audio(file_wav, job_id, durata, modello_nome)
    
    # Cleanup WAV temporaneo
    if file_wav.exists():
        file_wav.unlink()
    
    if testo is None:
        if _shutdown:
            # Shutdown richiesto: controlla se il job e' stato eliminato nel frattempo
            conn_check = get_db()
            stato_attuale = conn_check.execute(
                "SELECT stato FROM coda_trascrizioni WHERE id = ?", (job_id,)
            ).fetchone()
            conn_check.close()
            
            if stato_attuale and stato_attuale['stato'] == 'eliminato':
                logger.info("  Shutdown: job era stato eliminato, non rimesso in attesa")
                if file_lavorazione.exists():
                    file_lavorazione.unlink()
                return False
            
            logger.info("  Shutdown: job rimesso in attesa")
            aggiorna_stato(job_id, 'attesa',
                data_inizio_elaborazione=None,
                progresso_percentuale=0
            )
            if file_lavorazione.exists():
                shutil.move(str(file_lavorazione), str(file_attesa))
            return False
        
        logger.error("  Trascrizione fallita")
        aggiorna_stato(job_id, 'errore', errore='Trascrizione fallita')
        _invia_notifica(notifica_trascrizione_errore, job, errore_desc='Trascrizione fallita')
        if file_lavorazione.exists():
            shutil.move(str(file_lavorazione), str(file_attesa))
        return False
    
    # 5. Salva risultato nella destinazione corretta
    if tipo == 'cliente':
        path_testo, path_audio = get_destinazione_cliente(job)
    else:
        path_testo, path_audio = get_destinazione_consumo(job)
    
    if path_testo is None:
        logger.error("  Impossibile calcolare destinazione")
        aggiorna_stato(job_id, 'errore', errore='Destinazione non calcolabile')
        _invia_notifica(notifica_trascrizione_errore, job, errore_desc='Errore percorso destinazione')
        return False
    
    # Scrivi file testo
    try:
        path_testo.parent.mkdir(parents=True, exist_ok=True)
        with open(path_testo, 'w', encoding='utf-8') as f:
            f.write(testo)
        logger.info(f"  Testo salvato: {path_testo}")
    except Exception as e:
        logger.error(f"  Errore scrittura testo: {e}")
        aggiorna_stato(job_id, 'errore', errore=f'Errore scrittura: {e}')
        _invia_notifica(notifica_trascrizione_errore, job, errore_desc=f'Errore scrittura file')
        return False
    
    # 6. Gestisci audio originale
    now = datetime.now()
    data_scadenza_audio = None
    data_scadenza_testo = None
    percorso_audio_finale = None
    
    if tipo == 'cliente':
        # Audio → cartella cliente (retention 180gg)
        if path_audio and file_lavorazione.exists():
            shutil.move(str(file_lavorazione), str(path_audio))
            percorso_audio_finale = str(path_audio)
            data_scadenza_audio = (now + timedelta(days=RETENTION_AUDIO_GIORNI)).strftime('%Y-%m-%d')
            logger.info(f"  Audio spostato: {path_audio} (scade: {data_scadenza_audio})")
    else:
        # Dashboard: audio eliminato subito
        if file_lavorazione.exists():
            file_lavorazione.unlink()
            logger.info("  Audio eliminato (consumo)")
        data_scadenza_testo = (now + timedelta(days=RETENTION_CONSUMO_GIORNI)).strftime('%Y-%m-%d')
    
    # 7. Aggiorna DB
    aggiorna_stato(job_id, 'completato',
        progresso_percentuale=100,
        data_completamento=now.isoformat(),
        percorso_testo=str(path_testo),
        percorso_audio_finale=percorso_audio_finale,
        data_scadenza_audio=data_scadenza_audio,
        data_scadenza_testo=data_scadenza_testo
    )
    
    logger.info(f"  COMPLETATO")
    
    # 8. Notifica utente
    _invia_notifica(notifica_trascrizione_completata, job)
    logger.info(f"--- Fine Job #{job_id} ---")
    
    return True


# ==============================================================================
# PULIZIA RETENTION
# ==============================================================================

def pulizia_retention():
    """
    Elimina file audio e testo scaduti secondo la retention policy.
    Eseguita una volta al giorno (controllata dal worker).
    """
    conn = get_db()
    cursor = conn.cursor()
    oggi = datetime.now().strftime('%Y-%m-%d')
    
    # Audio scaduti (clienti, 180gg)
    cursor.execute('''
        SELECT id, percorso_audio_finale 
        FROM coda_trascrizioni 
        WHERE data_scadenza_audio IS NOT NULL 
        AND data_scadenza_audio <= ?
        AND percorso_audio_finale IS NOT NULL
    ''', (oggi,))
    
    for row in cursor.fetchall():
        path = Path(row[1])
        if path.exists():
            path.unlink()
            logger.info(f"Retention: eliminato audio {path}")
        cursor.execute(
            "UPDATE coda_trascrizioni SET percorso_audio_finale = NULL WHERE id = ?",
            (row[0],)
        )
    
    # Testi scaduti (consumo, 21gg)
    cursor.execute('''
        SELECT id, percorso_testo 
        FROM coda_trascrizioni 
        WHERE data_scadenza_testo IS NOT NULL 
        AND data_scadenza_testo <= ?
        AND percorso_testo IS NOT NULL
    ''', (oggi,))
    
    for row in cursor.fetchall():
        path = Path(row[1])
        if path.exists():
            path.unlink()
            logger.info(f"Retention: eliminato testo consumo {path}")
        cursor.execute(
            "UPDATE coda_trascrizioni SET percorso_testo = NULL WHERE id = ?",
            (row[0],)
        )
    
    conn.commit()
    conn.close()


# ==============================================================================
# LOOP PRINCIPALE
# ==============================================================================

# ==============================================================================
# RECOVERY: Ripristino job bloccati in lavorazione
# ==============================================================================

def recovery_job_bloccati():
    """
    All'avvio del worker, controlla se ci sono job rimasti in stato
    'lavorazione' (es. per crash o riavvio server).
    Li rimette in stato 'attesa' con priorita' alta cosi'
    vengono rielaborati per primi.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, nome_file_originale, nome_file_sistema
        FROM coda_trascrizioni
        WHERE stato = 'lavorazione'
    """)
    bloccati = cursor.fetchall()
    
    if not bloccati:
        logger.info("Recovery: nessun job bloccato trovato")
        conn.close()
        return
    
    logger.warning(f"Recovery: trovati {len(bloccati)} job bloccati in lavorazione")
    
    for job in bloccati:
        job_id = job['id']
        nome_orig = job['nome_file_originale']
        nome_sistema = job['nome_file_sistema']
        
        # Riporta il file da lavorazione ad attesa se esiste
        file_lavorazione = DIR_LAVORAZIONE / nome_sistema
        file_attesa = DIR_ATTESA / nome_sistema
        
        if file_lavorazione.exists():
            shutil.move(str(file_lavorazione), str(file_attesa))
            logger.info(f"  Job #{job_id} ({nome_orig}): file spostato da lavorazione ad attesa")
        elif file_attesa.exists():
            logger.info(f"  Job #{job_id} ({nome_orig}): file gia' in attesa")
        else:
            logger.error(f"  Job #{job_id} ({nome_orig}): file audio non trovato, segnato come errore")
            cursor.execute("""
                UPDATE coda_trascrizioni
                SET stato = 'errore', errore = 'File audio perso dopo crash'
                WHERE id = ?
            """, (job_id,))
            conn.commit()
            continue
        
        # Rimetti in attesa con priorita' 0 (massima) per essere elaborato per primo
        cursor.execute("""
            UPDATE coda_trascrizioni
            SET stato = 'attesa',
                priorita = 2,
                progresso_percentuale = 0,
                data_inizio_elaborazione = NULL,
                errore = NULL
            WHERE id = ?
        """, (job_id,))
        logger.warning(f"  Job #{job_id} ({nome_orig}): rimesso in coda con priorita' 2 (massima)")
    
    conn.commit()
    conn.close()
    logger.info("Recovery completato")


def main():
    """Loop principale del worker."""
    
    logger.info("=" * 60)
    logger.info("  WORKER TRASCRIZIONE - Avvio")
    logger.info("=" * 60)
    logger.info(f"  Modello standard:  {MODELLO}")
    logger.info(f"  Modello veloce:    {MODELLO_VELOCE}")
    logger.info(f"  Device:            {DEVICE}")
    logger.info(f"  Orario:            {ORARIO_INIZIO}:00 - {ORARIO_STOP}:00")
    logger.info(f"  Polling:           {POLLING_SECONDI}s")
    logger.info(f"  DB:                {DB_FILE}")
    logger.info("=" * 60)
    
    # Inizializza cartelle
    inizializza_cartelle()
    
    # Recovery job bloccati in lavorazione (crash/riavvio)
    recovery_job_bloccati()
    
    # Contatore per pulizia giornaliera
    ultima_pulizia = None
    
    while not _shutdown:
        try:
            # Pulizia retention (una volta al giorno)
            oggi = datetime.now().date()
            if ultima_pulizia != oggi:
                logger.info("Esecuzione pulizia retention giornaliera...")
                pulizia_retention()
                ultima_pulizia = oggi
            
            # Verifica orario elaborazione
            if not is_orario_elaborazione():
                ora = datetime.now().strftime('%H:%M')
                logger.debug(f"Fuori orario ({ora}), attendo...")
                time.sleep(POLLING_SECONDI)
                continue
            
            # Cerca prossimo job
            job = prossimo_job()
            
            if job is None:
                # Nessun job in coda, attendo
                time.sleep(POLLING_SECONDI)
                continue
            
            # Elabora il job
            inizio = time.time()
            successo = elabora_job(job)
            durata_elaborazione = time.time() - inizio
            
            if successo:
                logger.info(
                    f"Job #{job['id']} completato in "
                    f"{int(durata_elaborazione//60)}m {int(durata_elaborazione%60)}s"
                )
            
            # Breve pausa tra un job e l'altro
            time.sleep(2)
            
        except KeyboardInterrupt:
            logger.info("Interruzione tastiera, uscita...")
            break
        except Exception as e:
            logger.error(f"Errore nel loop principale: {e}", exc_info=True)
            time.sleep(POLLING_SECONDI)
    
    logger.info("Worker trascrizione arrestato")


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == '__main__':
    # Imposta LD_PRELOAD per faster-whisper
    if LD_PRELOAD and 'LD_PRELOAD' not in os.environ:
        os.environ['LD_PRELOAD'] = LD_PRELOAD
    
    main()
