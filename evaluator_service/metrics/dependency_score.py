"""
Dependency Score metric.

We evaluate an ordered sequence of documents (training materials). For each document N
(starting at 2), we ask GPT-4o to extract the concepts that the document assumes the
reader already knows (i.e., concepts used without introduction). We then check whether
each assumed concept was introduced earlier in the sequence (any document < N).

For each document N >= 2:
  Dependency_N = covered_assumed / total_assumed

Final dependency_score = average(Dependency_N) across N=2..K.

Semantic matching is performed via embeddings cosine similarity (Azure OpenAI embeddings).
"""

from __future__ import annotations

from dataclasses import dataclass

from evaluator_service.adapters.azure_openai import chat_json, cosine_similarity, embed_texts

@dataclass(frozen=True)
class DependencyResult:
    score: float
    per_document: list[float | None]  # None for first document
    assumed_concepts: list[list[str] | None]  # None for first document


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


def _extract_assumed_concepts(doc_text: str) -> list[str]:
    system = (
        "You are extracting prerequisite concepts from training documents.\n"
        "Return JSON only."
    )
    user = (
        "Given the document below, list the key concepts that the document ASSUMES the reader "
        "already knows (concepts used without introduction).\n\n"
        "Rules:\n"
        "- Return 3-25 concise concepts.\n"
        "- Concepts should be short noun phrases (2-6 words).\n"
        "- Do not include concepts that are introduced/defined in the document.\n\n"
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


def _is_concept_covered_in_previous_docs(
    concept: str,
    previous_docs: list[str],
    *,
    similarity_threshold: float = 0.78,
) -> bool:
    # Embed concept once
    concept_embs = embed_texts([concept])
    if not concept_embs:
        return False
    concept_emb = concept_embs[0]

    # Embed chunks from previous docs and take max similarity.
    chunks: list[str] = []
    for d in previous_docs:
        chunks.extend(_chunk_text(d))
    if not chunks:
        return False
    chunk_embs = embed_texts(chunks)
    if not chunk_embs:
        return False
    best = max(cosine_similarity(concept_emb, e) for e in chunk_embs)
    return best >= similarity_threshold


def calculate_dependency_score(documents: list[str]) -> DependencyResult:
    """
    Compute Dependency Score for an ordered document sequence.

    Returns:
      DependencyResult(score=<0..1>, per_document=[None, dep2, dep3, ...])
    """
    if not documents:
        return DependencyResult(score=0.0, per_document=[], assumed_concepts=[])
    if len(documents) == 1:
        return DependencyResult(score=0.0, per_document=[None], assumed_concepts=[None])

    per_doc: list[float | None] = [None]
    assumed_per_doc: list[list[str] | None] = [None]
    dep_values: list[float] = []

    for idx in range(1, len(documents)):
        doc = documents[idx]
        assumed = _extract_assumed_concepts(doc)
        assumed_per_doc.append(assumed)
        if not assumed:
            dep_n = 1.0
            per_doc.append(dep_n)
            dep_values.append(dep_n)
            continue

        prev_docs = documents[:idx]
        covered = 0
        for concept in assumed:
            if _is_concept_covered_in_previous_docs(concept, prev_docs):
                covered += 1
        dep_n = covered / max(1, len(assumed))
        per_doc.append(round(dep_n, 4))
        dep_values.append(dep_n)

    final = sum(dep_values) / max(1, len(dep_values))
    return DependencyResult(
        score=round(final, 4),
        per_document=per_doc,
        assumed_concepts=assumed_per_doc,
    )
