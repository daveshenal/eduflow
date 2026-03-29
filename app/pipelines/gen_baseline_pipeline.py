"""
Baseline generation pipeline: no curriculum plan.
Uses user-provided prompts; each prompt is the retrieval query for that doc.
Flow: input validation → for each doc: minimal system prompt + user prompt +
retrieval (by that prompt) → PDF → upload.
"""

import logging

from config.settings import settings
from app.retrievers.index_data_retriver import PrioritizedRetriever
from app.adapters.azure_sql import get_db_connection
from app.core.content_upload import upload_artifacts
from app.core.curriculem_plan_service import get_word_targets
from app.core.content_service import (
    BaselineDocParams,
    fetch_pdf_prompts,
    process_single_doc_baseline,
)
from app.core.pdf_generator import create_pdf

from app.pipelines.gen_pipeline import (
    setup_output_directories,
    clean_local_directories,
)
from app.pipelines.pipeline_helpers import (
    build_prompt_based_generated_docs,
    run_prompt_style_background_task,
)


def validate_baseline_payload(payload: dict) -> dict:
    """Validate baseline payload: job_id, callback_url, index_id, prompts (list), duration."""
    required = ["job_id", "index_id", "prompts", "duration"]
    missing = [f for f in required if f not in payload]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    prompts = payload.get("prompts")
    if not isinstance(prompts, (list, tuple)):
        raise ValueError("'prompts' must be a list of strings")
    prompts = [str(p).strip() for p in prompts if p]
    if not prompts:
        raise ValueError(
            "'prompts' must contain at least one non-empty string")

    return {
        "job_id": payload.get("job_id"),
        "callback_url": payload.get("callback_url"),
        "index_id": payload.get("index_id"),
        "prompts": prompts,
        "duration": int(payload.get("duration")),
    }


async def generate_content_baseline_background_task(params: dict, claude_client):
    """Background task for baseline generation (prompt-per-doc + retrieval by that prompt)."""
    await run_prompt_style_background_task(
        params,
        claude_client,
        generate_content_baseline,
        queued_message="Baseline generation started...",
        failed_message="Baseline generation failed",
        completed_message="Baseline generation completed",
        log_label="Baseline",
    )


async def generate_content_baseline(params: dict, claude_client):
    """Generate docs from user prompts; each prompt is the retrieval query for that doc."""
    total_input_tokens = 0
    total_output_tokens = 0
    try:
        dirs = setup_output_directories(params["job_id"])
        min_words, max_words = get_word_targets(params["duration"])
        prompts_list = params["prompts"]

        retriever = PrioritizedRetriever(
            index_id=params["index_id"],
            k=settings.INDEX_TOP_K,
            min_score=settings.MIN_SCORE,
        )

        async with get_db_connection() as db_conn:
            pdf_prompts = await fetch_pdf_prompts(db_conn)

        for i, user_prompt in enumerate(prompts_list):
            doc_id = i + 1
            result = await process_single_doc_baseline(
                claude_client,
                BaselineDocParams(
                    user_prompt=user_prompt,
                    doc_id=doc_id,
                    retriever=retriever,
                    prompts=pdf_prompts,
                    min_words=min_words,
                    max_words=max_words,
                    duration=params["duration"],
                ),
            )
            total_input_tokens += result["tokens"]["input"]
            total_output_tokens += result["tokens"]["output"]
            content_html = result.get("content_html")
            try:
                await create_pdf(doc_id, content_html, dirs["pdfs"])
            except Exception as pdf_error:
                logging.error(
                    "Failed to create PDF for doc %s: %s", doc_id, pdf_error)
                raise

        token_usage = {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
        }

        upload_result = upload_artifacts(
            job_id=params["job_id"],
            index_id=params["index_id"],
            pdfs_dir=dirs["pdfs"],
            audio_dir=dirs["audio"],
            voicescripts_dir=dirs["voiceovers"],
        )

        generated_docs = build_prompt_based_generated_docs(
            prompts_list, upload_result)

        baseline_plan = {"baseline": True, "num_docs": len(prompts_list)}

        clean_local_directories(params["job_id"])

        return {
            "success": True,
            "returns": {
                "title": "Baseline generation",
                "doc_duration": params["duration"],
                "docs": generated_docs,
            },
            "logs": {
                "token_usage": token_usage,
                "plan": baseline_plan,
            },
        }
    except Exception as e:
        try:
            clean_local_directories(params["job_id"])
        except Exception:
            logging.exception(
                "Failed to clean up baseline job directory for %s",
                params.get("job_id"),
            )
        return {
            "success": False,
            "error": str(e),
        }
