import sys
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler

from local_mcp.file.factory import FileHandlerFactory


def folder_name_to_table(folder_name: str) -> str:
    return folder_name.lower().replace(" ", "_").replace("-", "_")


class FileWatcher(FileSystemEventHandler):
    def __init__(self, file_handler: FileHandlerFactory) -> None:
        self.file_handler = file_handler

    def on_created(self, event: FileSystemEvent) -> None:
        print(f"[Watcher] Detected new file: {event.src_path}", file=sys.stderr)
        src_path = (
            event.src_path.decode("utf-8")
            if isinstance(event.src_path, bytes)
            else event.src_path
        )
        if event.is_directory:
            return

        file_path = Path(src_path)
        folder = file_path.parent
        description_file = folder / "description.md"

        if not description_file.exists():
            print(
                f"[Watcher] Skipping {file_path.name}: no description.md in {folder.name}",
                file=sys.stderr,
            )
            return

        table_name = folder_name_to_table(folder.name)
        file_handler = self.file_handler.get_handler(src_path)
        file_handler.process(str(file_path), table_name)
