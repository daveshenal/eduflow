"""
Concept-to-concept semantic matching utilities.

We intentionally match short concept strings (2-6 words) against other short concept
strings, rather than raw document text. This avoids embedding dilution from long
paragraphs and makes matching more robust.
"""

from __future__ import annotations

from typing import Iterable

from evaluator_service.adapters.azure_openai import cosine_similarity, embed_texts

_embedding_cache: dict[str, list[float]] = {}


def _normalize(concept: str) -> str:
    return " ".join((concept or "").strip().lower().split())


def _get_embeddings(concepts: list[str]) -> list[list[float]]:
    """
    Embed concepts with a simple in-memory cache.

    This is process-local and resets when the server restarts.
    """
    missing: list[str] = []
    for c in concepts:
        key = _normalize(c)
        if key and key not in _embedding_cache:
            missing.append(c)

    if missing:
        embs = embed_texts(missing)
        for c, e in zip(missing, embs):
            key = _normalize(c)
            if key:
                _embedding_cache[key] = e

    out: list[list[float]] = []
    for c in concepts:
        key = _normalize(c)
        if not key:
            continue
        emb = _embedding_cache.get(key)
        if emb is not None:
            out.append(emb)
    return out


def is_concept_covered(
    concept: str,
    previous_concepts: list[str],
    *,
    similarity_threshold: float = 0.85,
) -> bool:
    """
    Return True if `concept` is semantically covered by any item in `previous_concepts`.

    Matching is embedding cosine similarity with a conservative default threshold.
    """
    concept = (concept or "").strip()
    if not concept:
        return False
    prev = [c.strip() for c in previous_concepts if (c or "").strip()]
    if not prev:
        return False

    concept_embs = _get_embeddings([concept])
    if not concept_embs:
        return False
    concept_emb = concept_embs[0]

    prev_embs = _get_embeddings(prev)
    if not prev_embs:
        return False

    best = max(cosine_similarity(concept_emb, e) for e in prev_embs)
    return best >= similarity_threshold


def flatten_concepts(concepts_per_doc: Iterable[list[str] | None]) -> list[str]:
    """Flatten per-doc concept lists into a single list (skipping None/empties)."""
    out: list[str] = []
    for items in concepts_per_doc:
        if not items:
            continue
        for c in items:
            if isinstance(c, str) and c.strip():
                out.append(c.strip())
    return out

