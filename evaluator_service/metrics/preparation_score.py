"""
Preparation Score metric.

We evaluate an ordered sequence of documents (training materials). For each adjacent
pair (N, N+1), we ask GPT-4o to extract the concepts that document N introduces or sets
up for future use. We then check whether those concepts actually appear in document N+1.

For each N from 1..K-1:
  Preparation_N = covered_in_next / total_set_up

Final preparation_score = average(Preparation_N) across N=1..K-1.

Semantic matching is performed via embeddings cosine similarity (Azure OpenAI embeddings).
"""

from __future__ import annotations

from dataclasses import dataclass

from evaluator_service.adapters.azure_openai import chat_json
from evaluator_service.utils.concept_matching import is_concept_covered


@dataclass(frozen=True)
class PreparationResult:
    score: float
    per_document: list[float | None]  # None for last document
    setup_concepts: list[list[str] | None]  # None for last document


def _chunk_text(text: str, *, max_chars: int = 2000, overlap: int = 200) -> list[str]:
    t = (text or "").strip()
    if not t:
        return []
    if len(t) <= max_chars:
        return [t]
    chunks: list[str] = []
    start = 0
    while start < len(t):
        end = min(len(t), start + max_chars)
        chunks.append(t[start:end])
        if end == len(t):
            break
        start = max(0, end - overlap)
    return chunks


def _extract_setup_concepts(doc_text: str) -> list[str]:
    system = (
        "You are extracting forward-looking concepts from training documents.\n"
        "Be precise and evidence-based. Return JSON only."
    )

    user = (
        "Given the document below, list ONLY the key concepts that the document EXPLICITLY INTRODUCES "
        "or CLEARLY PREPARES for future use.\n\n"

        "A concept should be included ONLY if:\n"
        "- It is clearly introduced, explained, or emphasized in this document\n"
        "- The document signals it will be important later (e.g., structured sections, emphasis, definitions)\n\n"

        "Do NOT include:\n"
        "- Concepts that are just mentioned casually\n"
        "- Concepts that are already well-known or repeated\n"
        "- Concepts that are guessed to be useful later\n\n"

        "Be strict:\n"
        "- If the document does not clearly prepare the concept, DO NOT include it\n"
        "- Prefer fewer, high-confidence concepts\n\n"

        "Rules:\n"
        "- Return 3-15 concise concepts\n"
        "- Concepts must be specific and meaningful\n"
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
    seen: set[str] = set()
    out: list[str] = []
    for c in cleaned:
        key = c.lower()
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def _extract_present_concepts(doc_text: str) -> list[str]:
    """
    Extract concepts that are clearly present/used in the document.

    We use this as a compact "target set" for concept-to-concept matching, avoiding
    matching against raw paragraphs.
    """
    system = (
        "You are extracting concepts present in a training document.\n"
        "Be strict and evidence-based. Return JSON only."
    )
    user = (
        "Given the document below, list the key concepts that are CLEARLY PRESENT in the document "
        "(used, discussed, or applied).\n\n"
        "Rules:\n"
        "- Return 5-25 concise concepts\n"
        "- Use short noun phrases (2-6 words)\n"
        "- Do NOT include generic filler concepts\n\n"
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


def calculate_preparation_score(documents: list[str]) -> PreparationResult:
    """
    Compute Preparation Score for an ordered document sequence.

    Returns:
      PreparationResult(score=<0..1>, per_document=[prep1, prep2, ..., None])
    """
    if not documents:
        return PreparationResult(score=0.0, per_document=[], setup_concepts=[])
    if len(documents) == 1:
        return PreparationResult(score=0.0, per_document=[None], setup_concepts=[None])

    per_doc: list[float | None] = []
    setup_per_doc: list[list[str] | None] = []
    prep_values: list[float] = []

    present_concepts_per_doc: list[list[str]] = []
    for d in documents:
        present_concepts_per_doc.append(_extract_present_concepts(d))

    for idx in range(0, len(documents) - 1):
        doc = documents[idx]
        setup = _extract_setup_concepts(doc)
        setup_per_doc.append(setup)
        if not setup:
            prep_n = 0.0
            per_doc.append(prep_n)
            prep_values.append(prep_n)
            continue

        next_concepts = present_concepts_per_doc[idx + 1]
        covered = 0
        for concept in setup:
            if is_concept_covered(concept, next_concepts, similarity_threshold=0.85):
                covered += 1
        prep_n = covered / max(1, len(setup))
        per_doc.append(round(prep_n, 4))
        prep_values.append(prep_n)

    per_doc.append(None)
    setup_per_doc.append(None)
    final = sum(prep_values) / max(1, len(prep_values))
    return PreparationResult(
        score=round(final, 4),
        per_document=per_doc,
        setup_concepts=setup_per_doc,
    )
