"""
Scaffolding Connectivity Score (SCS).

What it measures:
  For each document D>1, it checks whether each concept in D.ASSUMES was introduced
  by any earlier document in the sequence.

High value means:
  Later documents' prerequisites are largely supported by earlier introductions,
  indicating strong conceptual scaffolding connectivity across the curriculum.
"""

from __future__ import annotations

from typing import Any

from evaluator_service.metrics.concept_docs import ConceptDoc
from evaluator_service.utils.llm_concept_matching import llm_match_concepts


def calculate_scs(
    docs: list[ConceptDoc],
    *,
    threshold: float = 0.7,
    concept_embeddings: dict[str, list[float]] | None = None,
) -> dict[str, Any]:
    """
    Calculate Scaffolding Connectivity Score (SCS).

    Returns:
      {
        "overall": float,
        "per_doc": [
          {
            "doc_id": int,
            "assumptions_count": int,
            "satisfied_count": int,
            "unsatisfied_concepts": list[str]
          }, ...
        ]
      }
    """

    total_assumptions = 0
    satisfied_assumptions = 0

    # LLM is used for matching (deterministic temperature=0). Embeddings are no longer used here.
    all_introduced_so_far: list[str] = []
    per_doc_results: list[dict[str, Any]] = []

    for doc_index in range(len(docs)):
        current_doc = docs[doc_index]
        current_assumes = current_doc.ASSUMES
        current_introduces = current_doc.INTRODUCES

        if doc_index == 0:
            all_introduced_so_far.extend(current_introduces)
            continue

        doc_total = 0
        doc_satisfied = 0
        unsatisfied: list[str] = []

        matches, details = llm_match_concepts(
            queries=current_assumes,
            candidates=all_introduced_so_far,
            temperature=0.0,
        )

        for concept in current_assumes:
            total_assumptions += 1
            doc_total += 1

            mapped = matches.get(concept)
            if mapped is not None:
                satisfied_assumptions += 1
                doc_satisfied += 1
            else:
                # Temporary debug logging for unmatched concepts.
                d = details.get(concept, {})
                print("UNMATCHED QUERY:", concept)
                print("BEST CANDIDATE:", d.get("suggested"))
                print("SIMILARITY SCORE:", d.get("confidence"))
                unsatisfied.append(concept)

        per_doc_results.append(
            {
                "doc_id": doc_index + 1,
                "assumptions_count": doc_total,
                "satisfied_count": doc_satisfied,
                "unsatisfied_concepts": unsatisfied,
            }
        )
        all_introduced_so_far.extend(current_introduces)

    if total_assumptions == 0:
        overall = 0.0
    else:
        overall = satisfied_assumptions / total_assumptions

    return {"overall": round(overall, 4), "per_doc": per_doc_results}

