"""
Memory-based generation pipeline: no curriculum plan.
Uses user-provided prompts; each prompt is the retrieval query for that doc.
Maintains a running summary (memory) of previous docs and injects it when generating the next doc.
"""

import json
import logging

from config.settings import settings
from app.retrievers.index_data_retriver import PrioritizedRetriever
from app.adapters.azure_sql import get_db_connection
from app.core.content_upload import upload_artifacts, upload_generation_logs
from app.core.curriculem_plan_service import get_word_targets
from app.core.content_service import (
    fetch_pdf_prompts,
    process_single_doc_memory,
    update_memory_summary,
)
from app.core.pdf_generator import create_pdf

from app.pipelines.gen_pipeline import setup_output_directories, send_job_completion_notification, clean_local_directories


async def generate_content_memory_background_task(params: dict, claude_client):
    """Background task for memory-based generation (prompt-per-doc + retrieval + running summary)."""
    from app.adapters.azure_sql import create_bg_job, update_bg_job

    job_id = params.get("job_id")
    try:
        await create_bg_job(
            job_id=job_id,
            index_id=params.get("index_id"),
            callback_url=params.get("callback_url"),
            status="queued",
            message="Memory-based generation started...",
        )
        result = await generate_content_memory(params, claude_client)

        if result.get("success") is False:
            await update_bg_job(
                job_id=job_id,
                status="Failed",
                message="Memory-based generation failed",
                result_text=json.dumps(result.get("error")) if result else None,
            )
            await send_job_completion_notification(params, result=None, error=result.get("error"))
            return

        await update_bg_job(
            job_id=job_id,
            status="completed",
            message="Memory-based generation completed",
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
        logging.info("Memory-based job %s completed", job_id)
    except Exception as e:
        logging.exception("Memory-based job %s failed", job_id)
        await send_job_completion_notification(params, result=None, error=str(e))


async def generate_content_memory(params: dict, claude_client):
    """
    Generate docs from user prompts; each prompt is used as retrieval query for that doc.
    Additionally maintains a running memory summary of previous docs, added into the prompt
    for each subsequent doc.
    """
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

        memory_summary = ""
        for i, user_prompt in enumerate(prompts_list):
            doc_id = i + 1
            result = await process_single_doc_memory(
                claude_client=claude_client,
                user_prompt=user_prompt,
                doc_id=doc_id,
                retriever=retriever,
                prompts=pdf_prompts,
                min_words=min_words,
                max_words=max_words,
                duration=params["duration"],
                memory_summary=memory_summary,
            )
            total_input_tokens += result["tokens"]["input"]
            total_output_tokens += result["tokens"]["output"]

            content_html = result.get("content_html")
            try:
                await create_pdf(doc_id, content_html, dirs["pdfs"])
            except Exception as pdf_error:
                logging.error("Failed to create PDF for doc %s: %s", doc_id, pdf_error)
                raise

            # Update memory with this doc's content
            memory_update = await update_memory_summary(
                claude_client,
                previous_summary=memory_summary,
                new_doc_html=content_html,
            )
            memory_summary = memory_update["summary"]
            total_input_tokens += memory_update["tokens"]["input"]
            total_output_tokens += memory_update["tokens"]["output"]

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
            generated_docs.append(
                {
                    "doc_index": i + 1,
                    "title": f"Document {doc_id}",
                    "pdf_path": pdf_path,
                    "audio_path": f"voiceover-{doc_id}.mp3",
                    "voicescript_path": f"voicescript-{doc_id}.txt",
                }
            )

        memory_plan = {
            "baseline": False,
            "memory_based": True,
            "num_docs": len(prompts_list),
        }

        # Ensure we don't leave local generation traces after upload.
        clean_local_directories(params["job_id"])

        return {
            "success": True,
            "returns": {
                "title": "Memory-based generation",
                "doc_duration": params["duration"],
                "docs": generated_docs,
            },
            "logs": {
                "token_usage": token_usage,
                "plan": memory_plan,
            },
        }
    except Exception as e:
        # Best-effort cleanup on error.
        try:
            clean_local_directories(params["job_id"])
        except Exception:
            logging.exception("Failed to clean up memory job directory for %s", params.get("job_id"))
        return {
            "success": False,
            "error": str(e),
        }
