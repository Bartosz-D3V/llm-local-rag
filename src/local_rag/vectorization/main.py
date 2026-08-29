import sys
from pathlib import Path

from local_models.vectorizer import get_local_embedding
from local_rag.db.lance import db
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


def process_pdf(pdf_path: str):
    print(f"[Ingest] Processing file: {pdf_path}", file=sys.stderr)
    reader = PdfReader(pdf_path)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,  # Increased from 600 for better context
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

    if not chunks:
        print(f"[Ingest] Warning: No text extracted from {pdf_path}", file=sys.stderr)
        return

    embeddings = [get_local_embedding(chunk) for chunk in chunks]

    data = [
        {
            "id": f"{Path(pdf_path).stem}_{idx}",
            "vector": vec,
            "text": chunk,
            "source": Path(pdf_path).name,
            "page": page_num,
        }
        for idx, (chunk, vec, page_num) in enumerate(
            zip(chunks, embeddings, page_numbers)
        )
    ]

    # Write or append to LanceDB table
    if "documents" in db.table_names():
        table = db.open_table("documents")
        table.delete(f'source = "{Path(pdf_path).name}"')
        table.add(data)
    else:
        table = db.create_table("documents", data=data)

    print(
        f"[Ingest] Successfully stored {len(data)} chunks into LanceDB.",
        file=sys.stderr,
    )
