from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from prometheus_fastapi_instrumentator import Instrumentator
import httpx
import os
import time


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    embedding: list[float] = Field(default_factory=lambda: [0.0] * 384)


app = FastAPI(title="AI Platform API Gateway")
Instrumentator().instrument(app).expose(app)  # Integration 9: Prometheus

VLLM_URL = os.environ.get("VLLM_URL") or os.environ.get("VLLM_NGROK_URL", "")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4")


async def search_context(embedding: list[float]) -> list[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.post(
                f"{QDRANT_URL}/collections/documents/points/search",
                json={"vector": embedding, "limit": 3},
            )
            response.raise_for_status()
            return response.json().get("result", [])
    except Exception:
        return []


async def call_vllm(prompt: str) -> dict[str, Any] | None:
    if not VLLM_URL:
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{VLLM_URL.rstrip('/')}/v1/chat/completions",
                json={
                    "model": MODEL_NAME,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            return response.json()
    except Exception:
        return None


def local_fallback_answer(query: str, context: list[dict[str, Any]]) -> str:
    context_count = len(context)
    return (
        "Local fallback answer: the platform uses Kafka for event ingestion, "
        "Prefect for orchestration, Qdrant and Redis for retrieval/features, "
        f"and the API gateway handled the query '{query}' with {context_count} "
        "retrieved context items."
    )


@app.post("/api/v1/chat")
async def chat(body: ChatRequest):
    start = time.time()

    if len(body.embedding) != 384:
        raise HTTPException(status_code=422, detail="embedding must contain 384 floats")

    context = await search_context(body.embedding)
    prompt = f"Context: {context}\n\nQuery: {body.query}"
    result = await call_vllm(prompt)
    latency = round((time.time() - start) * 1000, 2)

    if result:
        choice = result["choices"][0]["message"]["content"]
        model = result.get("model", MODEL_NAME)
    else:
        choice = local_fallback_answer(body.query, context)
        model = "local-fallback"

    return {
        "answer": choice,
        "latency_ms": latency,
        "model": model,
        "context_count": len(context),
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "vllm_configured": bool(VLLM_URL),
        "qdrant_url": QDRANT_URL,
    }
