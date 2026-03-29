"""
Memory-based generation pipeline: no curriculum plan.
Uses user-provided prompts; each prompt is the retrieval query for that doc.
Maintains a running summary (memory) of previous docs and injects it when
generating the next doc.
"""

import logging

from config.settings import settings
from app.retrievers.index_data_retriver import PrioritizedRetriever
from app.adapters.azure_sql import get_db_connection
from app.core.content_upload import upload_artifacts
from app.core.curriculem_plan_service import get_word_targets
from app.core.content_service import (
    MemoryDocParams,
    fetch_pdf_prompts,
    process_single_doc_memory,
    update_memory_summary,
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


async def generate_content_memory_background_task(params: dict, claude_client):
    """Background task for memory-based generation (prompt-per-doc + memory summary)."""
    await run_prompt_style_background_task(
        params,
        claude_client,
        generate_content_memory,
        queued_message="Memory-based generation started...",
        failed_message="Memory-based generation failed",
        completed_message="Memory-based generation completed",
        log_label="Memory-based",
    )


async def generate_content_memory(params: dict, claude_client):
    """
    Generate docs from user prompts; each prompt is the retrieval query for that doc.
    Maintains a running memory summary of previous docs for subsequent prompts.
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
                claude_client,
                MemoryDocParams(
                    user_prompt=user_prompt,
                    doc_id=doc_id,
                    retriever=retriever,
                    prompts=pdf_prompts,
                    min_words=min_words,
                    max_words=max_words,
                    duration=params["duration"],
                    memory_summary=memory_summary,
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

        generated_docs = build_prompt_based_generated_docs(
            prompts_list, upload_result)

        memory_plan = {
            "baseline": False,
            "memory_based": True,
            "num_docs": len(prompts_list),
        }

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
        try:
            clean_local_directories(params["job_id"])
        except Exception:
            logging.exception(
                "Failed to clean up memory job directory for %s",
                params.get("job_id"),
            )
        return {
            "success": False,
            "error": str(e),
        }
