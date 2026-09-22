from abc import abstractmethod, ABC
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

@dataclass
class FileData:
    chunks: list[str]
    page_numbers: list[int]


class FileHandler(ABC):
    @abstractmethod
    def process(self, pdf_path: str) -> FileData:
        pass

class PDFFileHandlerAdapter(FileHandler):
    def process(self, pdf_path: str) -> FileData:
        print(
            f"[Ingest] Processing file: {pdf_path} → table '{table_name}'", file=sys.stderr
        )
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

        return FileData(
            chunks=chunks,
            page_numbers=page_numbers
        )
