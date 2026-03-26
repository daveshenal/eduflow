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
from evaluator_service.utils.hybrid_concept_matching import hybrid_match


def calculate_scs(docs: list[ConceptDoc], *, threshold: float = 0.75) -> dict[str, Any]:
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

        for concept in current_assumes:
            total_assumptions += 1
            doc_total += 1

            matched, _ = hybrid_match(concept, all_introduced_so_far, threshold=threshold)
            if matched:
                satisfied_assumptions += 1
                doc_satisfied += 1
            else:
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

