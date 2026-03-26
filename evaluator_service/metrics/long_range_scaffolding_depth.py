"""
Long-Range Scaffolding Depth (LSD).

What it measures:
  For each later document D>1 and each of its ASSUMES concepts, it finds the
  earliest INTRODUCES occurrence (by semantic hybrid matching) in the curriculum,
  and counts how far back that introduction is.

High value means:
  Later prerequisites are supported by concepts introduced many documents earlier,
  indicating deep multi-document scaffolding.
"""

from __future__ import annotations

from typing import Any

from evaluator_service.metrics.concept_docs import ConceptDoc
from evaluator_service.utils.hybrid_concept_matching import find_best_match, normalize


def calculate_lsd(docs: list[ConceptDoc], *, threshold: float = 0.75) -> dict[str, Any]:
    """
    Calculate Long-Range Scaffolding Depth (LSD).

    Returns:
      {
        "total_depth": int,
        "average_depth": float,
        "long_range_links": int,
        "total_matched_assumptions": int,
        "unmatched_assumptions": int,
        "per_doc": [
          {
            "doc_id": int,
            "matched_assumptions": int,
            "depth_sum": int,
            "links": [
              {"concept": str, "introduced_in_doc": int, "depth": int}, ...
            ]
          }, ...
        ]
      }
    """

    introduction_index: dict[str, int] = {}

    # Earliest introduction index for each normalized introduced concept.
    for doc_index in range(len(docs)):
        for concept in docs[doc_index].INTRODUCES:
            norm = normalize(concept)
            if norm and norm not in introduction_index:
                introduction_index[norm] = doc_index

    introduction_keys = list(introduction_index.keys())

    total_depth = 0
    total_matched = 0
    unmatched = 0
    long_range = 0

    per_doc: list[dict[str, Any]] = []

    for doc_index in range(1, len(docs)):
        doc_depth = 0
        doc_matched = 0
        links: list[dict[str, Any]] = []

        for concept in docs[doc_index].ASSUMES:
            match = find_best_match(concept, introduction_keys, threshold=threshold)
            if match is not None:
                intro_idx = introduction_index[match]
                depth = doc_index - intro_idx

                if depth > 0:
                    total_depth += depth
                    doc_depth += depth
                    total_matched += 1
                    doc_matched += 1

                    if depth >= 2:
                        long_range += 1

                    links.append(
                        {
                            "concept": concept,
                            "introduced_in_doc": intro_idx + 1,
                            "depth": depth,
                        }
                    )
            else:
                unmatched += 1

        per_doc.append(
            {
                "doc_id": doc_index + 1,
                "matched_assumptions": doc_matched,
                "depth_sum": doc_depth,
                "links": links,
            }
        )

    avg_depth = (total_depth / total_matched) if total_matched > 0 else 0.0

    return {
        "total_depth": total_depth,
        "average_depth": round(avg_depth, 4),
        "long_range_links": long_range,
        "total_matched_assumptions": total_matched,
        "unmatched_assumptions": unmatched,
        "per_doc": per_doc,
    }

