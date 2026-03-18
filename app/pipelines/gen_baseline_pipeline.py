"""
Baseline generation pipeline: no curriculum plan.
Uses user-provided prompts; each prompt is the retrieval query for that doc.
Flow: input validation → for each doc: minimal system prompt + user prompt + retrieval (by that prompt) → PDF → upload.
"""

import json
import logging
from pathlib import Path

from config.settings import settings
from app.retrievers.index_data_retriver import PrioritizedRetriever
from app.adapters.azure_sql import get_db_connection
from app.core.content_upload import upload_artifacts, upload_generation_logs
from app.core.curriculem_plan_service import get_word_targets
from app.core.content_service import fetch_pdf_prompts, process_single_doc_baseline
from app.core.pdf_generator import create_pdf

from app.pipelines.gen_pipeline import setup_output_directories, send_job_completion_notification


def validate_baseline_payload(payload: dict) -> dict:
    """Validate and extract baseline payload: job_id, callback_url, index_id, prompts (list), duration, voice."""
    required = ["job_id", "callback_url", "index_id", "prompts", "duration", "voice"]
    missing = [f for f in required if f not in payload]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    prompts = payload.get("prompts")
    if not isinstance(prompts, (list, tuple)):
        raise ValueError("'prompts' must be a list of strings")
    prompts = [str(p).strip() for p in prompts if p]
    if not prompts:
        raise ValueError("'prompts' must contain at least one non-empty string")

    return {
        "job_id": payload.get("job_id"),
        "callback_url": payload.get("callback_url"),
        "index_id": payload.get("index_id"),
        "prompts": prompts,
        "duration": int(payload.get("duration")),
        "voice": payload.get("voice"),
    }


async def generate_content_baseline_background_task(params: dict, claude_client):
    """Background task for baseline generation (prompt-per-doc + retrieval by that prompt)."""
    from app.adapters.azure_sql import create_bg_job, update_bg_job

    job_id = params.get("job_id")
    try:
        await create_bg_job(
            job_id=job_id,
            index_id=params.get("index_id"),
            callback_url=params.get("callback_url"),
            status="queued",
            message="Baseline generation started...",
        )
        result = await generate_content_baseline(params, claude_client)

        if result.get("success") is False:
            await update_bg_job(
                job_id=job_id,
                status="Failed",
                message="Baseline generation failed",
                result_text=json.dumps(result.get("error")) if result else None,
            )
            await send_job_completion_notification(params, result=None, error=result.get("error"))
            return

        await update_bg_job(
            job_id=job_id,
            status="completed",
            message="Baseline generation completed",
            result_text=json.dumps(result.get("returns")) if result else None,
        )
        await send_job_completion_notification(params, result=result.get("returns"), error=None)

        logs = result.get("logs", {})
        upload_generation_logs(
            job_id=job_id,
            index_id=params.get("index_id"),
            params=params,
            plan=logs.get("plan"),
            response=result.get("returns"),
            usage=logs.get("token_usage"),
        )
        logging.info("Baseline job %s completed", job_id)
    except Exception as e:
        logging.exception("Baseline job %s failed", job_id)
        await send_job_completion_notification(params, result=None, error=str(e))


async def generate_content_baseline(params: dict, claude_client):
    """Generate docs from user prompts; each prompt is used as retrieval query for that doc. No plan."""
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
                claude_client=claude_client,
                user_prompt=user_prompt,
                doc_id=doc_id,
                retriever=retriever,
                prompts=pdf_prompts,
                min_words=min_words,
                max_words=max_words,
                duration=params["duration"],
            )
            total_input_tokens += result["tokens"]["input"]
            total_output_tokens += result["tokens"]["output"]
            content_html = result.get("content_html")
            try:
                await create_pdf(doc_id, content_html, dirs["pdfs"])
            except Exception as pdf_error:
                logging.error("Failed to create PDF for doc %s: %s", doc_id, pdf_error)
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

        generated_docs = []
        for i in range(len(prompts_list)):
            doc_id = i + 1
            pdf_filename = f"doc-{doc_id}.pdf"
            pdf_path = next((path for path in upload_result["pdf"] if pdf_filename in path), None)
            if not pdf_path:
                raise ValueError(f"Uploaded artifact missing for doc {doc_id}")
            generated_docs.append({
                "doc_index": i + 1,
                "title": f"Document {doc_id}",
                "pdf_path": pdf_path,
                "audio_path": f"voiceover-{doc_id}.mp3",
                "voicescript_path": f"voicescript-{doc_id}.txt",
            })

        baseline_plan = {"baseline": True, "num_docs": len(prompts_list)}

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
        return {
            "success": False,
            "error": str(e),
        }
