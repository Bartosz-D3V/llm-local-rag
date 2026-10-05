import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DB_DIR = str(PROJECT_ROOT / "lancedb_data")
INBOX_DIR = str(PROJECT_ROOT / "pdf_inbox")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
