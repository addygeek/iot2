"""
Configuration module for Meeting Recorder
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / "models"
SESSIONS_DIR = BASE_DIR / "sessions"

# Vosk configuration
VOSK_MODEL_PATH = Path.home() / "vosk-model-small-en-us-0.15"
VOSK_SAMPLE_RATE = 16000

# Server configuration
HOST = "0.0.0.0"
PORT = 8000
MAX_CLIENTS = 10

# Audio processing
CHUNK_DURATION = 3  # seconds
MAX_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB
SUPPORTED_FORMATS = [".webm", ".ogg", ".wav", ".mp3", ".m4a"]

# Summarization configuration
SUMMARY_WORD_THRESHOLD = 200  # Trigger summary after N words
SUMMARY_TIME_INTERVAL = 30  # Or after N seconds
SUMMARY_SENTENCE_COUNT = 3  # Number of sentences in summary

# Worker configuration
MAX_WORKER_THREADS = 2
CHUNK_PROCESS_TIMEOUT = 30  # seconds

# Storage configuration
MAX_SESSION_AGE_HOURS = 24  # Auto-cleanup old sessions

# Ensure directories exist
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
