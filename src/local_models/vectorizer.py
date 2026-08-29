import requests


def get_local_embedding(text: str) -> list[float]:
    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": text,
            "options": {"num_ctx": 8192, "num_batch": 4096},
        },
    )
    return response.json()["embedding"]
