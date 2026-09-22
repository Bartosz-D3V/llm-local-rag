import sys
from abc import ABC, abstractmethod
from pathlib import Path

from local_models.vectorizer import get_local_embedding
from local_rag.db.lance import db


class VectorStoreRepository(ABC):
    @abstractmethod
    def save(
        self,
        chunks: list[str],
        page_numbers: list[int],
        pdf_path: str,
        table_name: str,
    ) -> None:
        """Save chunks and page numbers to the vector store."""

    @abstractmethod
    def exists(
        self,
        pdf_path: str,
        table_name: str,
    ) -> bool:
        """Check if a PDF already exists in the vector store."""


class LanceDBAdapter(VectorStoreRepository):
    def save(
        self,
        chunks: list[str],
        page_numbers: list[int],
        pdf_path: str,
        table_name: str,
    ) -> None:

        if not chunks:
            print(
                f"[Ingest] Warning: No text extracted from {pdf_path}", file=sys.stderr
            )
            return

        if not pdf_path or not table_name:
            raise ValueError("pdf_path and table_name must be provided.")

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

        # Write or append to the folder-specific LanceDB table
        if table_name in db.table_names():
            table = db.open_table(table_name)
            table.delete(f'source = "{Path(table_name).name}"')
            table.add(data)
        else:
            db.create_table(table_name, data=data)

        print(
            f"[Ingest] Successfully stored {len(data)} chunks into table '{table_name}'.",
            file=sys.stderr,
        )

    def exists(
        self,
        pdf_path: str,
        table_name: str,
    ) -> bool:
        if not pdf_path or not table_name:
            return False

        if table_name not in db.table_names():
            return False

        filename = Path(pdf_path).name
        table = db.open_table(table_name)
        existing = table.search().where(f'source = "{filename}"').limit(1).to_list()
        return bool(existing)
