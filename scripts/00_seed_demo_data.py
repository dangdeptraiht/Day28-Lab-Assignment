import hashlib
import json
import time

import redis
import requests


QDRANT_URL = "http://localhost:6333"
COLLECTION = "documents"
SAMPLE_RECORDS = [
    {"id": "doc_001", "text": "AI platform integration test", "timestamp": time.time()},
    {"id": "doc_002", "text": "Kafka to Prefect pipeline", "timestamp": time.time()},
]


def local_embedding(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode()).digest()
    return [((digest[i % len(digest)] / 255.0) * 2) - 1 for i in range(384)]


def seed_qdrant() -> None:
    response = requests.put(
        f"{QDRANT_URL}/collections/{COLLECTION}",
        json={"vectors": {"size": 384, "distance": "Cosine"}},
        timeout=10,
    )
    if response.status_code != 409:
        response.raise_for_status()

    points = [
        {"id": index + 1, "vector": local_embedding(record["text"]), "payload": record}
        for index, record in enumerate(SAMPLE_RECORDS)
    ]
    requests.put(
        f"{QDRANT_URL}/collections/{COLLECTION}/points",
        json={"points": points},
        timeout=10,
    ).raise_for_status()
    print(f"Seeded {len(points)} vectors in Qdrant")


def seed_redis() -> None:
    client = redis.Redis(host="localhost", port=6379, decode_responses=True)
    for record in SAMPLE_RECORDS:
        client.set(
            f"feature:{record['id']}",
            json.dumps({"text": record["text"], "timestamp": record["timestamp"], "processed": True}),
        )
    print(f"Seeded {len(SAMPLE_RECORDS)} features in Redis")


if __name__ == "__main__":
    seed_qdrant()
    seed_redis()
    print("Demo data ready")
