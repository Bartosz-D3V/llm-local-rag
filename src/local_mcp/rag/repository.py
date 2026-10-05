import sys
from abc import ABC, abstractmethod
from pathlib import Path

from lancedb.index import BTree
from lancedb.rerankers import RRFReranker

from local_mcp.models.vectorizer import EmbeddingProcessor
from local_mcp.rag.lance import db


class VectorStoreRepository(ABC):
    def __init__(self, embedding_processor: EmbeddingProcessor) -> None:
        self.embedding_processor = embedding_processor

    @abstractmethod
    def save(
        self,
        chunks: list[str],
        page_numbers: list[int],
        file_path: str,
        table_name: str,
    ) -> None:
        """Save chunks and page numbers to the vector store."""

    @abstractmethod
    def exists(
        self,
        file_path: str,
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
        file_path: str,
        table_name: str,
    ) -> None:

        if not chunks:
            print(
                f"[Ingest] Warning: No text extracted from {file_path}", file=sys.stderr
            )
            return

        if not file_path or not table_name:
            raise ValueError("file_path and table_name must be provided.")

        embeddings = self.embedding_processor.process_batch(chunks)

        data = [
            {
                "id": f"{Path(file_path).stem}_{idx}",
                "vector": vec,
                "text": chunk,
                "source": Path(file_path).name,
                "page": page_num,
            }
            for idx, (chunk, vec, page_num) in enumerate(
                zip(chunks, embeddings, page_numbers)
            )
        ]

        # Write or append to the folder-specific LanceDB table
        if table_name in db.table_names():
            table = db.open_table(table_name)
            table.delete(f'source = "{Path(file_path).name}"')
            table.add(data)
        else:
            table = db.create_table(table_name, data=data)

        try:
            table.create_index("source", config=BTree(), replace=True)
        except Exception as e:  # noqa: BLE001
            print(
                f"[Ingest] Warning: Failed to create scalar index on 'source' for table '{table_name}': {e}",
                file=sys.stderr,
            )

        try:
            table.create_fts_index("text", replace=True)
        except Exception as e:  # noqa: BLE001
            print(
                f"[Ingest] Warning: Failed to create FTS index for table '{table_name}': {e}",
                file=sys.stderr,
            )

        print(
            f"[Ingest] Successfully stored {len(data)} chunks into table '{table_name}'.",
            file=sys.stderr,
        )

    def exists(
        self,
        file_path: str,
        table_name: str,
    ) -> bool:
        if not file_path or not table_name:
            return False

        if table_name not in db.table_names():
            return False

        filename = Path(file_path).name
        table = db.open_table(table_name)
        existing = table.search().where(f'source = "{filename}"').limit(1).to_list()
        return bool(existing)

    def search(self, table_name: str, query: str, top_k: int = 5) -> str:
        if table_name not in db.table_names():
            return f"No documents indexed for '{table_name}' yet."

        table = db.open_table(table_name)
        query_vector = self.embedding_processor.process(query)
        reranker = RRFReranker()

        try:
            results = (
                table.search(query_type="hybrid")
                .vector(query_vector)
                .text(query)
                .rerank(reranker)
                .limit(top_k)
                .to_list()
            )
        except Exception:  # noqa: BLE001
            results = (
                table.search(query_vector)
                .metric("cosine")
                .select(["source", "text", "page", "_distance"])
                .limit(top_k)
                .to_list()
            )

        if not results:
            return "No relevant information found."

        formatted = []
        for r in results:
            if "_relevance_score" in r:
                score = r["_relevance_score"]
            elif "_distance" in r:
                score = max(0.0, 1.0 - r["_distance"])
            else:
                score = r.get("_score", 0.0)
            formatted.append(
                f"--- Source: {r['source']} (relevance: {score:.2f}) ---\n{r['text']}\n"
            )
        return "\n".join(formatted)
