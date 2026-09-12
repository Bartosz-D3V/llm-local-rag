import requests
from config.config import OLLAMA_HOST


def get_local_embedding(text: str) -> list[float]:
    response = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": text,
            "options": {"num_ctx": 8192, "num_batch": 4096},
        },
    )
    return response.json()["embedding"]
