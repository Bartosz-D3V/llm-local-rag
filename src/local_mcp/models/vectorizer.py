from abc import ABC, abstractmethod

import requests
from local_mcp.config.config import OLLAMA_HOST


class EmbeddingProcessor(ABC):
    @abstractmethod
    def process(self, text: str) -> list[float | int]:
        pass


class LLAMAProcessor(EmbeddingProcessor):
    def process(self, text: str) -> list[float | int]:
        response = requests.post(
            f"{OLLAMA_HOST}/api/embeddings",
            json={
                "model": "nomic-embed-text",
                "prompt": text,
                "options": {"num_ctx": 8192, "num_batch": 4096},
            },
        )
        return response.json()["embedding"]
