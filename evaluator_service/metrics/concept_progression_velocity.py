"""
Concept Progression Velocity (CPV).

What it measures:
  It summarizes how quickly new INTRODUCES concepts appear across the curriculum.

Low value means:
  Many introductions are repeats of earlier concepts.

High value means:
  INTRODUCES lists contain a high ratio of unique concepts, and more documents
  contribute their first-time concepts.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from evaluator_service.metrics.concept_docs import ConceptDoc
from evaluator_service.utils.llm_concept_matching import llm_match_concepts


def calculate_cpv(docs: list[ConceptDoc]) -> dict[str, Any]:
    """
    Calculate Concept Progression Velocity (CPV).

    Returns:
      {
        "cpv": float,
        "total_unique_concepts": int,
        "total_concept_mentions": int,
        "repeated_concepts": list[str],
        "per_doc_new_concepts": list[int]
      }
    """

    # LLM is used for semantic "already seen?" checks (deterministic temperature=0).
    all_concepts: list[str] = []
    unique_concepts: set[str] = set()
    seen_so_far: set[str] = set()
    per_doc_new: list[int] = []

    for doc in docs:
        new_count = 0
        current_introduces = [c.strip() for c in doc.INTRODUCES if isinstance(c, str) and c.strip()]

        # Determine which of the current INTRODUCES are genuinely new vs any prior INTRODUCES.
        # We match "current -> prior" and treat a null match as new.
        prior_list = list(seen_so_far)
        matches, _details = llm_match_concepts(
            queries=current_introduces,
            candidates=prior_list,
            temperature=0.0,
        )

        for concept in current_introduces:
            all_concepts.append(concept)

            # Unique is tracked on raw strings, but "newness" is decided semantically via LLM.
            if concept not in unique_concepts:
                unique_concepts.add(concept)

            mapped = matches.get(concept)
            if mapped is None:
                new_count += 1
                seen_so_far.add(concept)

        per_doc_new.append(new_count)

    total_mentions = len(all_concepts)
    total_unique = len(unique_concepts)

    cpv = (total_unique / total_mentions) if total_mentions > 0 else 0.0

    counts = Counter(all_concepts)
    repeated = [c for c in unique_concepts if counts.get(c, 0) > 1]

    return {
        "cpv": round(cpv, 4),
        "total_unique_concepts": total_unique,
        "total_concept_mentions": total_mentions,
        "repeated_concepts": repeated,
        "per_doc_new_concepts": per_doc_new,
    }

