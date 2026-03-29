"""
Hybrid concept matching for RAG research metrics.

Matching is performed on short concept strings using:
1) Exact match (after lower+strip)
2) Substring match
3) Semantic similarity using sentence-transformers embeddings + cosine similarity

The embedding threshold defaults to 0.75.
"""

from __future__ import annotations

from typing import Dict, Iterable, Tuple

import re

from evaluator_service.embedding.similarity import cosine_similarity, get_embedding


def normalize(text: str) -> str:
    """
    Strong normalization for concept strings.

    - Lowercase
    - Remove parenthesized content
    - Strip punctuation
    - Collapse whitespace
    """
    text = text or ""
    text = text.lower()
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def semantic_match(
    query: str,
    candidates: Iterable[str],
    threshold: float = 0.7,
    *,
    embedding_index: Dict[str, list[float]] | None = None,
) -> Tuple[bool, str | None, float]:
    """
    Primary semantic matcher used by metrics.

    Matching order:
      1) Exact match on normalized strings
      2) Substring match on normalized strings
      3) Embedding cosine similarity over normalized strings
    """
    candidate_list = [c for c in candidates if isinstance(
        c, str) and (c or "").strip()]
    query_norm = normalize(query)
    if not query_norm or not candidate_list:
        return False, None, 0.0

    # 1. Exact + substring safety layer (on normalized strings)
    best_candidate_norm: str | None = None
    for candidate in candidate_list:
        cand_norm = normalize(candidate)
        if not cand_norm:
            continue
        if query_norm == cand_norm:
            return True, candidate, 1.0
        if query_norm in cand_norm or cand_norm in query_norm:
            return True, candidate, 1.0

    # 2. Embedding-based semantic similarity
    store = embedding_index if embedding_index is not None else {}

    if query_norm in store:
        query_emb = store[query_norm]
    else:
        query_emb = get_embedding(query_norm)
        store[query_norm] = query_emb

    best_score = 0.0
    best_candidate: str | None = None

    for candidate in candidate_list:
        cand_norm = normalize(candidate)
        if not cand_norm:
            continue
        if cand_norm in store:
            cand_emb = store[cand_norm]
        else:
            cand_emb = get_embedding(cand_norm)
            store[cand_norm] = cand_emb

        score = cosine_similarity(query_emb, cand_emb)
        if score > best_score:
            best_score = score
            best_candidate = candidate
            best_candidate_norm = cand_norm

    if best_score >= threshold and best_candidate is not None:
        return True, best_candidate, best_score

    return False, best_candidate if best_candidate is not None else best_candidate_norm, best_score


def hybrid_match(
    query: str,
    candidate_list: Iterable[str],
    threshold: float = 0.7,
) -> Tuple[bool, str | None]:
    """
    Backwards-compatible wrapper around `semantic_match` returning only (matched, candidate).
    """
    matched, candidate, _ = semantic_match(
        query, candidate_list, threshold=threshold)
    return matched, candidate


def find_best_match(
    query: str,
    candidate_keys: Iterable[str],
    threshold: float = 0.7,
) -> str | None:
    """Find the best-matching candidate key using the shared matcher."""
    _, candidate, _ = semantic_match(
        query, candidate_keys, threshold=threshold)
    return candidate

