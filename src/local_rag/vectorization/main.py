import sys
from pathlib import Path

from file.handler import PDFFileHandlerAdapter
from local_rag.repository import LanceDBAdapter


def process_pdf(pdf_path: str, table_name: str):
    filename = Path(pdf_path).name
    repo = LanceDBAdapter()
    if repo.exists(pdf_path=pdf_path, table_name=table_name):
        print(
            f"[Ingest] Skipping {filename}: already exists in table '{table_name}'.",
            file=sys.stderr,
        )
        return

    handler = PDFFileHandlerAdapter()
    file_data = handler.process(pdf_path=pdf_path)

    repo = LanceDBAdapter()
    repo.save(chunks=file_data.chunks,
              page_numbers=file_data.page_numbers,
              table_name=table_name,
              pdf_path=pdf_path)
