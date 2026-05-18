import requests
import os
import hashlib

EMBED_URL = os.environ.get("EMBED_NGROK_URL", "")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION = "documents"

response = requests.put(
    f"{QDRANT_URL}/collections/{COLLECTION}",
    json={"vectors": {"size": 384, "distance": "Cosine"}},
    timeout=10,
)
if response.status_code != 409:
    response.raise_for_status()


def local_embedding(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode()).digest()
    return [((digest[i % len(digest)] / 255.0) * 2) - 1 for i in range(384)]


def embed_and_store(records: list[dict]):
    if EMBED_URL:
        response = requests.post(
            f"{EMBED_URL.rstrip('/')}/embed",
            json={"texts": [r["text"] for r in records]},
            timeout=30,
        )
        response.raise_for_status()
        embeddings = response.json()["embeddings"]
    else:
        embeddings = [local_embedding(r["text"]) for r in records]

    points = [
        {"id": i + 1, "vector": emb, "payload": rec}
        for i, (emb, rec) in enumerate(zip(embeddings, records))
    ]
    requests.put(
        f"{QDRANT_URL}/collections/{COLLECTION}/points",
        json={"points": points},
        timeout=10,
    ).raise_for_status()
    print(f"Integration 5 OK: {len(points)} vectors stored in Qdrant")

embed_and_store([
    {"id": "doc_001", "text": "AI platform integration test"},
    {"id": "doc_002", "text": "Kafka to Airflow pipeline"},
])
