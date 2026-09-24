import sys
from abc import ABC, abstractmethod
from pathlib import Path

from file.processor import PDFFileProcessorAdapter
from rag.repository import LanceDBAdapter


class FileHandler(ABC):
    def __init__(
        self, repository: LanceDBAdapter, pdf_processor: PDFFileProcessorAdapter
    ) -> None:
        self.repository = repository
        self.pdf_processor = pdf_processor

    @abstractmethod
    def process(self, pdf_path: str, table_name: str) -> None:
        pass


class PDFFileHandler(FileHandler):
    def __init__(
        self, repository: LanceDBAdapter, pdf_processor: PDFFileProcessorAdapter
    ) -> None:
        super().__init__(repository, pdf_processor)

    def process(self, pdf_path: str, table_name: str) -> None:
        filename = Path(pdf_path).name
        if self.repository.exists(pdf_path=pdf_path, table_name=table_name):
            print(
                f"[Ingest] Skipping {filename}: already exists in table '{table_name}'.",
                file=sys.stderr,
            )
            return

        file_data = self.pdf_processor.process(pdf_path=pdf_path)

        self.repository.save(
            chunks=file_data.chunks,
            page_numbers=file_data.page_numbers,
            table_name=table_name,
            pdf_path=pdf_path,
        )
