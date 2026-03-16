"""
Azure OpenAI helpers for the evaluator service.

This module provides:
- A cached Azure OpenAI client
- A small JSON-oriented GPT-4o chat helper
- An embeddings helper used for semantic concept matching
"""

from __future__ import annotations

import json
import math
from typing import Any, Iterable
from openai import AzureOpenAI

from config.settings import settings

_client: AzureOpenAI | None = None

def get_llm_client() -> AzureOpenAI:
    """Return a cached Azure OpenAI client."""
    global _client
    if _client is None:
        _client = AzureOpenAI(
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_KEY,
        )
    return _client


def chat_json(
    *,
    system: str,
    user: str,
    model: str = settings.GPT4O_DEPLOYMENT,
    temperature: float = 0.2,
    max_output_tokens: int = 800,
) -> dict[str, Any]:
    """
    Ask GPT-4o for a JSON object and parse it.

    The prompt should instruct the model to output JSON only.
    """
    client = get_llm_client()
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_output_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
    )
    content = (resp.choices[0].message.content or "").strip()
    if not content:
        return {}
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Defensive: if the SDK ever returns non-JSON despite response_format.
        return {}


def embed_texts(
    texts: Iterable[str],
    *,
    deployment: str | None = None,
) -> list[list[float]]:
    """Embed texts using Azure OpenAI embeddings."""
    dep = deployment or settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
    items = [t.strip() for t in texts if (t or "").strip()]
    if not items:
        return []

    client = get_llm_client()
    resp = client.embeddings.create(model=dep, input=items)
    return [d.embedding for d in resp.data]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity for two same-length vectors."""
    if len(a) != len(b):
        raise ValueError("Vectors must have same dimension")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)