from abc import ABC, abstractmethod

import requests

from local_mcp.config.config import OLLAMA_HOST


class EmbeddingProcessor(ABC):
    @abstractmethod
    def process(self, text: str) -> list[float | int]:
        pass

    @abstractmethod
    def process_batch(self, texts: list[str]) -> list[list[float | int]]:
        pass


class LLAMAProcessor(EmbeddingProcessor):
    def process(self, text: str) -> list[float | int]:
        return self.process_batch([text])[0]

    def process_batch(
        self, texts: list[str], batch_size: int = 64
    ) -> list[list[float | int]]:
        if not texts:
            return []

        all_embeddings: list[list[float | int]] = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            response = requests.post(
                f"{OLLAMA_HOST}/api/embed",
                json={
                    "model": "nomic-embed-text",
                    "input": chunk,
                },
            )
            response.raise_for_status()
            all_embeddings.extend(response.json()["embeddings"])
        return all_embeddings
