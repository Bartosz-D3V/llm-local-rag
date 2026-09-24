import sys
from abc import ABC, abstractmethod
from pathlib import Path

from models.vectorizer import LLAMAProcessor, EmbeddingProcessor
from rag.lance import db


class VectorStoreRepository(ABC):
    def __init__(self, embedding_processor: EmbeddingProcessor) -> None:
        self.embedding_processor = embedding_processor

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

    @abstractmethod
    def search(self, table_name: str, query: str, top_k: int) -> str:
        """Search the vector store for chunks and page numbers."""


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

        embeddings = [self.embedding_processor.process(chunk) for chunk in chunks]

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

    def search(self, table_name: str, query: str, top_k: int = 5) -> str:
        if table_name not in db.table_names():
            return f"No documents indexed for '{table_name}' yet."

        table = db.open_table(table_name)
        query_vector = self.embedding_processor.process(query)
        results = table.search(query_vector).limit(top_k).to_list()
        if not results:
            return "No relevant information found."

        formatted = []
        for r in results:
            score = 1 - r.get("_distance", 0)
            formatted.append(
                f"--- Source: {r['source']} (relevance: {score:.2f}) ---\n{r['text']}\n"
            )
        return "\n".join(formatted)
