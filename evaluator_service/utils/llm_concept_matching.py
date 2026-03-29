"""
LLM-based concept matching utilities (deterministic).

This module replaces embedding-based semantic similarity for metric matching.

Why LLM + temperature=0:
  - We want a one-time, deterministic mapping from query concepts to candidate concepts.
  - Temperature=0 reduces nondeterminism so the same inputs produce stable outputs.

Output contract:
  The LLM is instructed to choose ONLY from the provided candidate strings, or null.
  We parse a structured JSON response and return:
    - matches: dict[query -> candidate_or_None]
    - details: dict[query -> {"confidence": float, "suggested": str|None}]
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

from evaluator_service.adapters.azure_openai import chat_json


@dataclass(frozen=True)
class LLMMatchBatchResult:
    matches: dict[str, str | None]
    details: dict[str, dict[str, Any]]


def _dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if not isinstance(x, str):
            continue
        s = x.strip()
        if not s:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _chunk(items: list[str], chunk_size: int) -> list[list[str]]:
    if chunk_size <= 0:
        return [items]
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def _parse_llm_payload(payload: dict[str, Any], *, queries: list[str]) -> LLMMatchBatchResult:
    """
    Defensive parsing: tolerate missing keys, enforce query coverage, and type-check.
    """
    matches_raw = payload.get("matches", {})
    details_raw = payload.get("details", {})

    matches: dict[str, str | None] = {}
    if isinstance(matches_raw, dict):
        for k, v in matches_raw.items():
            if not isinstance(k, str):
                continue
            if v is None:
                matches[k] = None
            elif isinstance(v, str) and v.strip():
                matches[k] = v.strip()

    details: dict[str, dict[str, Any]] = {}
    if isinstance(details_raw, dict):
        for k, v in details_raw.items():
            if not isinstance(k, str) or not isinstance(v, dict):
                continue
            details[k] = v

    # Ensure every query has an entry.
    for q in queries:
        matches.setdefault(q, None)
        details.setdefault(q, {})

    return LLMMatchBatchResult(matches=matches, details=details)


def llm_match_concepts(
    *,
    queries: list[str],
    candidates: list[str],
    temperature: float = 0.0,
    query_chunk_size: int = 20,
    max_candidates: int = 250,
) -> Tuple[dict[str, str | None], dict[str, dict[str, Any]]]:
    """
    Match each query concept to the single best candidate concept (or None) using an LLM.

    This function handles batching (query chunking) to reduce token limit risk.

    Returns:
      (matches, details)
        - matches: dict mapping each query to a candidate string from `candidates` or None
        - details: per-query debug info, if provided by LLM (confidence, suggested)
    """
    q_list = _dedupe_preserve_order(queries)
    c_list = _dedupe_preserve_order(candidates)

    if not q_list:
        return {}, {}
    if not c_list:
        return {q: None for q in q_list}, {q: {"confidence": 0.0, "suggested": None} for q in q_list}

    # If candidate list is huge, keep the most recent / relevant slice.
    # (Efficiency is not a concern, but this avoids extreme prompt sizes.)
    if len(c_list) > max_candidates:
        c_list = c_list[-max_candidates:]

    system = "You are a strict JSON-only matcher. Output JSON only."

    all_matches: dict[str, str | None] = {}
    all_details: dict[str, dict[str, Any]] = {}

    for q_chunk in _chunk(q_list, query_chunk_size):
        # The prompt enforces that outputs are either EXACTLY one of the candidates, or null.
        user = (
            "You are matching curriculum concept strings.\n"
            "For each QUERY concept, choose the SINGLE BEST matching concept from CANDIDATES, or null if no good match.\n\n"
            "Matching must be semantic (rephrased, partial overlap, equivalent concepts are matches).\n"
            "However, you MUST NOT invent new strings.\n"
            "If you return a match, it MUST be exactly one of the strings in CANDIDATES.\n\n"
            "Return JSON in this format:\n"
            '{\n'
            '  "matches": { "QUERY_1": "CANDIDATE_STRING_OR_NULL", ... },\n'
            '  "details": {\n'
            '     "QUERY_1": {"confidence": 0.0-1.0, "suggested": "BEST_CANDIDATE_STRING_OR_NULL"}, ...\n'
            "  }\n"
            "}\n\n"
            "CANDIDATES:\n"
            f"{json.dumps(c_list, ensure_ascii=False)}\n\n"
            "QUERIES:\n"
            f"{json.dumps(q_chunk, ensure_ascii=False)}\n"
        )

        payload = chat_json(
            system=system,
            user=user,
            temperature=temperature,
            max_output_tokens=1500,
        )

        parsed = _parse_llm_payload(payload, queries=q_chunk)

        # Enforce candidate validity: if model returns a string not in candidates, treat as None.
        candidate_set = set(c_list)
        for q in q_chunk:
            v = parsed.matches.get(q)
            if v is not None and v not in candidate_set:
                v = None
            all_matches[q] = v

            d = parsed.details.get(q, {})
            # Normalize a couple expected fields if present.
            if not isinstance(d, dict):
                d = {}
            conf = d.get("confidence")
            suggested = d.get("suggested")
            if not isinstance(conf, (int, float)):
                conf = 0.0
            if suggested is not None and (not isinstance(suggested, str) or suggested not in candidate_set):
                suggested = None
            all_details[q] = {"confidence": float(
                conf), "suggested": suggested}

    # Fill any missing (can happen if duplicates were in original queries list).
    for q in q_list:
        all_matches.setdefault(q, None)
        all_details.setdefault(q, {"confidence": 0.0, "suggested": None})

    return all_matches, all_details

