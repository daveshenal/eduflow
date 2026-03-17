"""
Document evaluation entrypoint.

This service evaluates ordered sequences of training documents using metrics designed
for RAG research: whether later documents depend on earlier ones, and whether earlier
documents prepare the reader for what comes next.
"""

from __future__ import annotations

import os
from pathlib import Path

from evaluator_service.utils.pdf_extractor import extract_text_from_pdf

from evaluator_service.metrics.dependency_score import calculate_dependency_score
from evaluator_service.metrics.preparation_score import calculate_preparation_score


def _write_llm_concepts_artifact(
    *,
    documents: list[str],
    assumed_concepts: list[list[str] | None],
    setup_concepts: list[list[str] | None],
) -> str:
    """
    Persist the LLM-extracted concepts (ASSUMES / INTRODUCES) to a repo-local text file.

    File is overwritten on each run for easy inspection:
      evaluator_service/tmp/llm_concepts.txt
    """
    # Base directory = this file's parent package root (evaluator_service/)
    base_dir = Path(__file__).resolve().parents[1]
    out_dir = base_dir / "tmp"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "llm_concepts.txt"

    lines: list[str] = []
    lines.append("EduFlow evaluator - LLM extracted concepts")
    lines.append(f"document_count: {len(documents)}")
    lines.append("")

    lines.append("ASSUMES (dependency)")
    for i in range(len(documents)):
        if i == 0:
            lines.append("Doc 1: (n/a)")
            continue
        concepts = assumed_concepts[i] if i < len(assumed_concepts) else None
        lines.append(f"Doc {i+1}:")
        if not concepts:
            lines.append("  - (none)")
        else:
            for c in concepts:
                lines.append(f"  - {c}")
    lines.append("")

    lines.append("INTRODUCES/SETS UP (preparation)")
    for i in range(len(documents)):
        if i == len(documents) - 1:
            lines.append(f"Doc {i+1}: (n/a)")
            continue
        concepts = setup_concepts[i] if i < len(setup_concepts) else None
        lines.append(f"Doc {i+1}:")
        if not concepts:
            lines.append("  - (none)")
        else:
            for c in concepts:
                lines.append(f"  - {c}")

    tmp_path = out_dir / "llm_concepts.tmp"
    tmp_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp_path, out_path)
    return str(out_path)


def evaluate_documents(pdf_file_paths: list[str]) -> dict:
    """
    Evaluate documents from PDF file paths.

    Documents are processed in the order given. Returns dependency + preparation
    metrics with per-document breakdowns for interpretability.
    """
    documents: list[str] = []

    for pdf_path in pdf_file_paths:
        text = extract_text_from_pdf(pdf_path)
        if not (text or "").strip():
            raise ValueError(f"PDF contains no extractable text: {pdf_path}")
        documents.append(text.strip())

    dep = calculate_dependency_score(documents)
    prep = calculate_preparation_score(documents)

    _write_llm_concepts_artifact(
        documents=documents,
        assumed_concepts=dep.assumed_concepts,
        setup_concepts=prep.setup_concepts,
    )

    per_document: list[dict] = []
    for i in range(len(documents)):
        per_document.append(
            {
                "doc_index": i + 1,
                "dependency": dep.per_document[i] if i < len(dep.per_document) else None,
                "preparation": prep.per_document[i] if i < len(prep.per_document) else None,
            }
        )

    return {
        "document_count": len(documents),
        "metrics": {
            "dependency_score": dep.score,
            "preparation_score": prep.score,
            "per_document": per_document,
        },
    }
