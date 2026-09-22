import sys
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler

from file.handler import PDFFileHandler


def folder_name_to_table(folder_name: str) -> str:
    return folder_name.lower().replace(" ", "_").replace("-", "_")


class PDFWatcher(FileSystemEventHandler):
    def on_created(self, event: FileSystemEvent) -> None:
        print(f"[Watcher] Detected new file: {event.src_path}", file=sys.stderr)
        src_path = (
            event.src_path.decode("utf-8")
            if isinstance(event.src_path, bytes)
            else event.src_path
        )
        if event.is_directory or not src_path.endswith(".pdf"):
            return

        pdf_path = Path(src_path)
        folder = pdf_path.parent
        description_file = folder / "description.md"

        if not description_file.exists():
            print(
                f"[Watcher] Skipping {pdf_path.name}: no description.md in {folder.name}",
                file=sys.stderr,
            )
            return

        table_name = folder_name_to_table(folder.name)
        pdf_handler = PDFFileHandler()
        pdf_handler.process(str(pdf_path), table_name)
