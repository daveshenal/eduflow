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

from evaluator_service.metrics.all_metrics import calculate_all_metrics, extract_concepts


def _write_llm_concepts_artifact(
    *,
    documents: list[str],
    assumed_concepts: list[list[str] | None],
    introduces_concepts: list[list[str] | None],
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

    lines.append("INTRODUCES (for later scaffolding)")
    for i in range(len(documents)):
        concepts = introduces_concepts[i] if i < len(
            introduces_concepts) else None
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

    Documents are processed in the order given. Returns the new scaffolding + progression
    metrics with per-document breakdowns for interpretability.
    """
    documents: list[str] = []

    for pdf_path in pdf_file_paths:
        text = extract_text_from_pdf(pdf_path)
        if not (text or "").strip():
            raise ValueError(f"PDF contains no extractable text: {pdf_path}")
        documents.append(text.strip())

    concept_docs = extract_concepts(documents)
    metrics = calculate_all_metrics(concept_docs)

    _write_llm_concepts_artifact(
        documents=documents,
        assumed_concepts=[d.ASSUMES for d in concept_docs],
        introduces_concepts=[d.INTRODUCES for d in concept_docs],
    )

    return {
        "document_count": len(documents),
        "metrics": {
            **metrics,
        },
    }
