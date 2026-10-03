import sys
from abc import ABC, abstractmethod
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from rag.repository import LanceDBAdapter


class FileHandler(ABC):
    def __init__(self, repository: LanceDBAdapter) -> None:
        self.repository = repository

    @abstractmethod
    def process(self, pdf_path: str, table_name: str) -> None:
        pass


class PDFFileHandler(FileHandler):
    def __init__(self, repository: LanceDBAdapter) -> None:
        super().__init__(repository)

    def process(self, pdf_path: str, table_name: str) -> None:
        filename = Path(pdf_path).name
        if self.repository.exists(pdf_path=pdf_path, table_name=table_name):
            print(
                f"[Ingest] Skipping {filename}: already exists in table '{table_name}'.",
                file=sys.stderr,
            )
            return

        print(f"[Ingest] Processing file: {pdf_path}", file=sys.stderr)
        reader = PdfReader(pdf_path)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

        chunks = []
        page_numbers = []

        for page_idx, page in enumerate(reader.pages, 1):
            page_text = page.extract_text() or ""
            if not page_text.strip():
                continue

            # Split text for this page
            page_chunks = text_splitter.split_text(page_text)
            for chunk in page_chunks:
                chunks.append(chunk)
                page_numbers.append(page_idx)

        self.repository.save(
            chunks=chunks,
            page_numbers=page_numbers,
            table_name=table_name,
            pdf_path=pdf_path,
        )
