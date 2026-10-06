import sys

from watchdog.observers.polling import PollingObserver

from local_mcp.config.config import INBOX_DIR
from local_mcp.file.factory import FileHandlerFactory
from local_mcp.file.handler import PDFFileHandler, URLHandler
from local_mcp.file.watcher import FileWatcher
from local_mcp.models.vectorizer import LLAMAProcessor
from local_mcp.rag.repository import LanceDBAdapter
from local_mcp.server.controller import MCPController


def main():
    print("Starting PDF watcher...", file=sys.stderr)
    print(f"[*] Watching {INBOX_DIR} for new PDFs...", file=sys.stderr)
    embedding_processor = LLAMAProcessor()
    repository = LanceDBAdapter(embedding_processor)
    pdf_file_handler = PDFFileHandler(repository)
    url_handler = URLHandler(repository)

    file_handler = FileHandlerFactory(pdf_file_handler, url_handler)
    event_handler = FileWatcher(file_handler)
    observer = PollingObserver()
    observer.schedule(event_handler, INBOX_DIR, recursive=True)
    observer.start()

    mcp_controller = MCPController(pdf_file_handler, repository)
    mcp_controller.start()
