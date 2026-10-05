from pathlib import Path

from local_mcp.file.handler import FileHandler, PDFFileHandler, URLHandler


class FileHandlerFactory:
    def __init__(self, pdf_handler: PDFFileHandler, url_handler: URLHandler):
        self.url_handler = url_handler
        self._extension_handlers = {
            ".pdf": pdf_handler,
            ".url": url_handler,
            ".webloc": url_handler,
        }

    def get_handler(self, src_path: str) -> FileHandler:
        ext = Path(src_path).suffix.lower()

        if handler := self._extension_handlers.get(ext):
            return handler

        raise ValueError(f"Unsupported file extension or format: {src_path}")
