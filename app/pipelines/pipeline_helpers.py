"""Shared helpers for baseline- and memory-style prompt pipelines (upload + notifications)."""

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.adapters.azure_sql import create_bg_job, update_bg_job
from app.core.content_upload import GenerationLogUpload, upload_generation_logs

from app.pipelines.gen_pipeline import send_job_completion_notification


def build_prompt_based_generated_docs(prompts_list: list, upload_result: dict) -> list[dict]:
    """
    Build the docs list from upload results for prompt-per-doc pipelines
    (baseline and memory): PDF paths plus placeholder audio/voicescript names.
    """
    generated_docs = []
    for i in range(len(prompts_list)):
        doc_id = i + 1
        pdf_filename = f"doc-{doc_id}.pdf"
        pdf_path = next(
            (path for path in upload_result["pdf"] if pdf_filename in path),
            None,
        )
        if not pdf_path:
            raise ValueError(f"Uploaded artifact missing for doc {doc_id}")
        generated_docs.append({
            "doc_index": i + 1,
            "title": f"Document {doc_id}",
            "pdf_path": pdf_path,
            "audio_path": f"voiceover-{doc_id}.mp3",
            "voicescript_path": f"voicescript-{doc_id}.txt",
        })
    return generated_docs


async def run_prompt_style_background_task(
    params: dict,
    claude_client: Any,
    generate_fn: Callable[[dict, Any], Awaitable[dict]],
    *,
    queued_message: str,
    failed_message: str,
    completed_message: str,
    log_label: str,
) -> None:
    """
    Common background flow: create job, run generate_fn, update DB, notify, upload logs.
    Used by baseline and memory pipelines.
    """
    job_id = params.get("job_id")
    try:
        callback_url = (params.get("callback_url") or "").strip()
        await create_bg_job(
            job_id=job_id,
            index_id=params.get("index_id"),
            callback_url=callback_url,
            status="queued",
            message=queued_message,
        )
        result = await generate_fn(params, claude_client)

        if result.get("success") is False:
            await update_bg_job(
                job_id=job_id,
                status="Failed",
                message=failed_message,
                result_text=json.dumps(result.get(
                    "error")) if result else None,
            )
            await send_job_completion_notification(
                params, result=None, error=result.get("error"),
            )
            return

        await update_bg_job(
            job_id=job_id,
            status="completed",
            message=completed_message,
            result_text=json.dumps(result.get("returns")) if result else None,
        )
        await send_job_completion_notification(
            params, result=result.get("returns"), error=None,
        )

        logs = result.get("logs", {})
        upload_generation_logs(
            GenerationLogUpload(
                job_id=job_id,
                index_id=params.get("index_id"),
                params=params,
                plan=logs.get("plan"),
                response=result.get("returns"),
                usage=logs.get("token_usage"),
            )
        )
        logging.info("%s job %s completed", log_label, job_id)
    except Exception as exc:
        logging.exception("%s job %s failed", log_label, job_id)
        await send_job_completion_notification(params, result=None, error=str(exc))
