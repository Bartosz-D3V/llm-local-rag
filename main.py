import sys

from watchdog.observers.polling import PollingObserver

from config.config import INBOX_DIR
from file.handler import PDFFileHandler
from file.watcher import FileWatcher
from models.vectorizer import LLAMAProcessor
from rag.repository import LanceDBAdapter
from server.controller import MCPController

if __name__ == "__main__":
    print("Starting PDF watcher...", file=sys.stderr)
    print(f"[*] Watching {INBOX_DIR} for new PDFs...", file=sys.stderr)
    embedding_processor = LLAMAProcessor()
    repository = LanceDBAdapter(embedding_processor)
    pdf_file_handler = PDFFileHandler(repository)

    event_handler = FileWatcher(pdf_file_handler)
    observer = PollingObserver()
    observer.schedule(event_handler, INBOX_DIR, recursive=True)
    observer.start()

    mcp_controller = MCPController(pdf_file_handler, repository)
    mcp_controller.start()
