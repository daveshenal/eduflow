"""
Synchronous faithfulness scoring: reload plan + PDFs, re-retrieve, LLM score per session.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

from langchain.schema import Document

from app.retrievers.index_data_retriver import PrioritizedRetriever
from config.settings import settings
from evaluator_service.adapters.azure_openai import chat_json
from evaluator_service.utils.pdf_extractor import extract_text_from_pdf

FAITHFULNESS_SCORING_SYSTEM = "You are a strict JSON evaluator. Output JSON only."

FAITHFULNESS_SCORING_USER_TEMPLATE = """You are an expert evaluator of RAG-generated educational documents.

You are given:
1) DOCUMENT TEXT — the generated learner-facing document extracted from a PDF.
2) RETRIEVED CONTEXT — chunks retrieved from the knowledge base for this session (the only sources the generator was expected to use).

Score FAITHFULNESS from 1 to 5:
- Are substantive claims in the document grounded in the retrieved context?
- Are there assertions, facts, or specific recommendations with no support in the context?
- Are citations/endnote references (if any) used accurately relative to the retrieved sources?

Scale:
1 = Severe hallucination or contradiction; most claims unsupported.
2 = Frequent unsupported claims or misuse of context.
3 = Mixed: core points mostly supported but notable gaps or weak citations.
4 = Strong grounding; minor omissions or phrasing stretch only.
5 = Excellent: claims align with context; citations accurate.

DOCUMENT TEXT:
{document_text}

RETRIEVED CONTEXT:
{retrieved_context}

Also count substantive claims in the DOCUMENT TEXT (for comparing architectures such as EduFlow vs baselines):
- A "claim" is a factual assertion, specific recommendation, regulatory/clinical statement, or causal link that could be checked against the retrieved context. Do not count pure formatting, empty headings, signposts, or generic pleasantries unless they state a specific fact.
- claim_count: total number of distinct substantive claims you identified.
- supported_claim_count: how many of those claims are clearly supported by (or paraphrased from) the RETRIEVED CONTEXT. Must be <= claim_count.

Respond in this exact JSON format:
{{
  "faithfulness_score": <integer 1-5>,
  "reasoning": "<concise explanation referencing support or gaps>",
  "claim_count": <integer >= 0>,
  "supported_claim_count": <integer >= 0, <= claim_count>
}}
"""

_DEFAULT_REASONING = "Scorer response could not be parsed reliably."


def _load_input_params_prompts(job_dir: Path) -> list[str]:
    path = job_dir / "logs" / "input_params.json"
    if not path.is_file():
        raise ValueError(f"input_params.json not found (required for this architecture): {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    prompts = data.get("prompts")
    if not isinstance(prompts, (list, tuple)):
        raise ValueError("input_params.json must contain a 'prompts' list")

    out = [str(p).strip() for p in prompts if str(p).strip()]
    if not out:
        raise ValueError("input_params.json 'prompts' must contain at least one non-empty string")

    return out


def _title_for_prompt_session(prompt: str, session_index: int) -> str:
    label = (prompt or "").strip().replace("\n", " ")
    if len(label) > 160:
        label = label[:157] + "..."
    return label or f"Document {session_index}"


def _evaluator_service_root() -> Path:
    # This module lives at evaluator_service/evaluators/faithfulness_evaluator.py
    return Path(__file__).resolve().parent.parent


def downloaded_jobs_root() -> Path:
    return _evaluator_service_root() / "evaluation" / "downloaded_jobs"


def normalize_job_id(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        raise ValueError("job_id is required")
    if not s.startswith("job-"):
        s = f"job-{s}"
    return s


def build_retrieval_query(doc: dict) -> str:
    """Match gen_pipeline / process_single_doc composite query."""
    title = doc.get("title")
    main_focus = doc.get("main_focus")
    return (
        (doc.get("retrieval_query") or "")
        + " "
        + " ".join([p for p in [title, main_focus] if p])
    ).strip()


def _chunks_used_from_documents(docs: list[Document]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for d in docs:
        md = d.metadata or {}
        name = md.get("source_name") or ""
        out.append({"source_name": str(name), "text": d.page_content or ""})
    return out


def _safe_int_score_1_5(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and 1 <= value <= 5:
        return value
    if isinstance(value, float) and value.is_integer():
        iv = int(value)
        if 1 <= iv <= 5:
            return iv
    return None


def _safe_non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, float) and not math.isnan(value) and not math.isinf(value):
        if value < 0:
            return None
        iv = int(round(value))
        if abs(value - iv) < 1e-6:
            return iv
    return None


def _normalize_claim_counts(total: int, supported: int) -> tuple[int, int]:
    if supported > total:
        supported = total
    if total < 0:
        total = 0
    if supported < 0:
        supported = 0
    return total, supported


def _parse_claim_counts_from_response(data: dict[str, Any]) -> tuple[int, int] | None:
    """Returns (claim_count, supported_claim_count) or None if fields missing/invalid."""
    t = _safe_non_negative_int(data.get("claim_count"))
    s = _safe_non_negative_int(data.get("supported_claim_count"))
    if t is None or s is None:
        return None
    return _normalize_claim_counts(t, s)


def _score_one_session(
    *,
    document_text: str,
    retrieved_context: str,
) -> dict[str, Any]:
    user = FAITHFULNESS_SCORING_USER_TEMPLATE.format(
        document_text=document_text.strip() or "(empty)",
        retrieved_context=retrieved_context.strip() or "(no context retrieved)",
    )
    attempts = 0
    max_attempts = 3
    last_reasoning = _DEFAULT_REASONING

    while attempts < max_attempts:
        attempts += 1
        try:
            data = chat_json(
                system=FAITHFULNESS_SCORING_SYSTEM,
                user=user,
                model=settings.GPT4O_DEPLOYMENT,
                temperature=0,
                max_output_tokens=1200,
            )
        except Exception:
            if attempts < max_attempts:
                time.sleep(10 * attempts)
            continue

        reasoning = data.get("reasoning")
        if isinstance(reasoning, str) and reasoning.strip():
            last_reasoning = reasoning.strip()

        score = _safe_int_score_1_5(data.get("faithfulness_score"))
        if score is None:
            if attempts < max_attempts:
                time.sleep(10 * attempts)
            continue

        parsed_counts = _parse_claim_counts_from_response(data)
        if parsed_counts is None:
            if attempts < max_attempts:
                time.sleep(10 * attempts)
            continue

        claim_count, supported_claim_count = parsed_counts
        return {
            "faithfulness_score": score,
            "reasoning": last_reasoning,
            "claim_count": claim_count,
            "supported_claim_count": supported_claim_count,
        }

    return {
        "faithfulness_score": 3,
        "reasoning": last_reasoning,
        "claim_count": 0,
        "supported_claim_count": 0,
    }


def compute_faithfulness(
    job_id: str,
    index_id: str,
    *,
    use_input_param_queries: bool = False,
) -> dict[str, Any]:
    """
    use_input_param_queries:
      False — EduFlow: composite query per plan doc (process_single_doc).
      True  — Baseline / memory: each logs/input_params.json prompts[i] is the query
              for doc i+1 (process_single_doc_baseline / process_single_doc_memory).
    """
    jid = normalize_job_id(job_id)
    idx = (index_id or "").strip()
    if not idx:
        raise ValueError("index_id is required")

    job_dir = downloaded_jobs_root() / jid
    if not job_dir.is_dir():
        raise ValueError(f"Job directory not found: {job_dir}")

    plan_path = job_dir / "logs" / "plan.json"
    if not plan_path.is_file():
        raise ValueError(f"Plan not found: {plan_path}")

    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    retriever = PrioritizedRetriever(
        index_id=idx,
        k=settings.INDEX_TOP_K,
        min_score=settings.MIN_SCORE,
    )

    session_payloads: list[dict[str, Any]] = []
    scores: list[int] = []

    if not use_input_param_queries:
        docs = (plan or {}).get("docs") or []
        if not docs:
            raise ValueError("Plan contains no docs (eduflow architecture requires plan.docs)")

        for session_index, doc in enumerate(docs, start=1):
            doc_id_raw = doc.get("id")
            try:
                doc_id = int(doc_id_raw)
            except (TypeError, ValueError):
                raise ValueError(f"Invalid doc id in plan: {doc_id_raw!r}") from None

            pdf_path = job_dir / "pdf" / f"doc-{doc_id}.pdf"
            if not pdf_path.is_file():
                raise ValueError(f"PDF not found for session {session_index}: {pdf_path}")

            title = (doc.get("title") or "").strip() or f"Session {session_index}"
            query = build_retrieval_query(doc)
            retrieved = retriever.get_relevant_documents(query=query)
            retrieved_context = retriever.format_context_with_sources(retrieved)
            chunks_used = _chunks_used_from_documents(retrieved)

            document_text = extract_text_from_pdf(str(pdf_path))
            llm_out = _score_one_session(
                document_text=document_text,
                retrieved_context=retrieved_context,
            )
            score = int(llm_out["faithfulness_score"])
            scores.append(score)

            session_payloads.append(
                {
                    "session_index": session_index,
                    "title": title,
                    "faithfulness_score": score,
                    "reasoning": llm_out["reasoning"],
                    "claim_count": int(llm_out["claim_count"]),
                    "supported_claim_count": int(llm_out["supported_claim_count"]),
                    "chunks_used": chunks_used,
                    "low_faithfulness": score < 3,
                }
            )
    else:
        # Same retrieval query construction as process_single_doc_baseline / memory.
        prompts = _load_input_params_prompts(job_dir)
        for session_index, user_prompt in enumerate(prompts, start=1):
            pdf_path = job_dir / "pdf" / f"doc-{session_index}.pdf"
            if not pdf_path.is_file():
                raise ValueError(f"PDF not found for session {session_index}: {pdf_path}")

            title = _title_for_prompt_session(user_prompt, session_index)
            query = user_prompt.strip()
            retrieved = retriever.get_relevant_documents(query=query)
            retrieved_context = retriever.format_context_with_sources(retrieved)
            chunks_used = _chunks_used_from_documents(retrieved)

            document_text = extract_text_from_pdf(str(pdf_path))
            llm_out = _score_one_session(
                document_text=document_text,
                retrieved_context=retrieved_context,
            )
            score = int(llm_out["faithfulness_score"])
            scores.append(score)

            session_payloads.append(
                {
                    "session_index": session_index,
                    "title": title,
                    "faithfulness_score": score,
                    "reasoning": llm_out["reasoning"],
                    "claim_count": int(llm_out["claim_count"]),
                    "supported_claim_count": int(llm_out["supported_claim_count"]),
                    "chunks_used": chunks_used,
                    "low_faithfulness": score < 3,
                }
            )

    overall = round(sum(scores) / len(scores), 2) if scores else 0.0
    total_claims = sum(s["claim_count"] for s in session_payloads)
    total_supported_claims = sum(s["supported_claim_count"] for s in session_payloads)
    overall_supported_claim_ratio = (
        round(total_supported_claims / total_claims, 4) if total_claims > 0 else None
    )

    return {
        "job_id": jid,
        "index_id": idx,
        "use_input_param_queries": use_input_param_queries,
        "overall_faithfulness_score": overall,
        "total_claims": total_claims,
        "total_supported_claims": total_supported_claims,
        "overall_supported_claim_ratio": overall_supported_claim_ratio,
        "sessions": session_payloads,
    }
