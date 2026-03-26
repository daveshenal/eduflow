"""
Unified metric wrapper for EduFlow evaluator.

This module preserves the existing LLM-based concept extraction logic for:
  - ASSUMES (prerequisite concepts a later document expects the reader to know)
  - INTRODUCES (concepts explicitly introduced/defined for later use)

It then computes the three new embedding-based metrics in the required order:
  1) Scaffolding Connectivity Score (SCS)
  2) Concept Progression Velocity (CPV)
  3) Long-Range Scaffolding Depth (LSD)
"""

from __future__ import annotations

from typing import Any

from evaluator_service.adapters.azure_openai import chat_json
from evaluator_service.metrics.concept_docs import ConceptDoc
from evaluator_service.metrics.concept_progression_velocity import calculate_cpv
from evaluator_service.metrics.long_range_scaffolding_depth import calculate_lsd
from evaluator_service.metrics.scaffolding_connectivity_score import calculate_scs


def _extract_assumed_concepts(doc_text: str) -> list[str]:
    # NOTE: Prompt and cleaning logic copied from the prior dependency metric.
    system = (
        "You are extracting prerequisite concepts from training documents.\n"
        "Be strict and conservative. Return JSON only."
    )

    user = (
        "Given the document below, list ONLY the key concepts that the document CLEARLY ASSUMES "
        "the reader already knows.\n\n"
        "A concept is ASSUMED only if:\n"
        "- It is used directly without explanation\n"
        "- It is NOT defined, described, or introduced in the document\n"
        "- The reader would need prior knowledge to understand it\n\n"
        "Do NOT include:\n"
        "- Concepts that are explained even briefly\n"
        "- Generic domain terms (e.g., 'patient care', 'assessment')\n"
        "- Concepts that are only loosely implied\n\n"
        "Be conservative:\n"
        "- If unsure, DO NOT include the concept\n"
        "- Prefer fewer, high-confidence concepts\n\n"
        "Rules:\n"
        "- Return 3-15 concise concepts\n"
        "- Concepts must be specific (avoid generic phrases)\n"
        "- Use short noun phrases (2-6 words)\n\n"
        'Return JSON as: {"concepts": ["..."]}\n\n'
        f"DOCUMENT:\n{doc_text}"
    )

    data = chat_json(system=system, user=user)
    concepts = data.get("concepts", [])
    if not isinstance(concepts, list):
        return []

    cleaned: list[str] = []
    for c in concepts:
        if isinstance(c, str) and c.strip():
            cleaned.append(c.strip())

    # de-dupe while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for c in cleaned:
        key = c.lower()
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def _extract_introduced_concepts(doc_text: str) -> list[str]:
    # NOTE: Prompt and cleaning logic copied from the prior dependency metric.
    system = (
        "You are extracting introduced concepts from training documents.\n"
        "Be strict and evidence-based. Return JSON only."
    )

    user = (
        "Given the document below, list ONLY the key concepts that the document EXPLICITLY INTRODUCES "
        "or DEFINES (new terms, methods, frameworks, definitions).\n\n"
        "Rules:\n"
        "- Return 3-20 concise concepts\n"
        "- Use short noun phrases (2-6 words)\n"
        "- Do NOT include concepts that are merely mentioned without explanation\n\n"
        'Return JSON as: {"concepts": ["..."]}\n\n'
        f"DOCUMENT:\n{doc_text}"
    )

    data = chat_json(system=system, user=user)
    concepts = data.get("concepts", [])
    if not isinstance(concepts, list):
        return []

    cleaned: list[str] = []
    for c in concepts:
        if isinstance(c, str) and c.strip():
            cleaned.append(c.strip())

    seen: set[str] = set()
    out: list[str] = []
    for c in cleaned:
        key = c.lower()
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def extract_concepts(docs_text: list[str]) -> list[ConceptDoc]:
    """
    Extract ASSUMES and INTRODUCES concept lists for each input document.

    This function preserves the existing LLM prompts used by the previous metrics.
    """

    assumed_docs: list[list[str]] = []
    introduces_docs: list[list[str]] = []

    for doc_text in docs_text:
        assumed_docs.append(_extract_assumed_concepts(doc_text))
        introduces_docs.append(_extract_introduced_concepts(doc_text))

    return [
        ConceptDoc(ASSUMES=assumed, INTRODUCES=introduces)
        for assumed, introduces in zip(assumed_docs, introduces_docs)
    ]


def calculate_all_metrics(docs: list[ConceptDoc]) -> dict[str, Any]:
    """
    Compute all three metrics from concept-annotated documents.

    Returns:
      {
        "scaffolding_connectivity_score": ...,
        "concept_progression_velocity": ...,
        "long_range_scaffolding_depth": ...,
      }
    """

    return {
        "scaffolding_connectivity_score": calculate_scs(docs),
        "concept_progression_velocity": calculate_cpv(docs),
        "long_range_scaffolding_depth": calculate_lsd(docs),
    }

