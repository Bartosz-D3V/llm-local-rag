import time

from watchdog.events import FileSystemEvent, FileSystemEventHandler

from local_rag.vectorization.main import process_pdf


class PDFHandler(FileSystemEventHandler):
    def on_created(self, event: FileSystemEvent) -> None:
        src_path = (
            event.src_path.decode("utf-8")
            if isinstance(event.src_path, bytes)
            else event.src_path
        )
        if not event.is_directory and src_path.endswith(".pdf"):
            time.sleep(1)  # Brief pause for write completion
            process_pdf(src_path)
