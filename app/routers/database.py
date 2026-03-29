"""API router for database operations, background jobs, and prompt management."""

from typing import List, Optional, Any
from datetime import datetime, timedelta
import json

from fastapi import APIRouter, HTTPException

from app.adapters.azure_sql import (
    get_db_connection,
    create_tables,
    clear_all_bg_jobs,
    get_all_bg_jobs,
    get_bg_job,
)
from app.adapters.azure_blob import get_blob_service_client, generate_sas_token

# Prompt management imports
from app.prompts.prompt_management import (
    get_prompt_manager,
    PromptNames,
    PromptCreate,
    PromptResponse,
    PromptUpdate,
    ActivatePromptRequest,
)

router = APIRouter()


############################################
# ------------ BG Job Manager ------------ #
############################################


@router.delete("/bg_jobs/clear", summary="Clear all background jobs")
async def api_clear_all_bg_jobs():
    """Clear all background jobs from the database."""
    try:
        deleted_count = await clear_all_bg_jobs()
        return {"success": True, "deleted_jobs": deleted_count}
    except Exception as e:
        # Optional: log the error here
        raise HTTPException(
            status_code=500, detail=f"Failed to clear jobs: {str(e)}")


@router.get("/bg_jobs", summary="List all background jobs with summary")
async def api_list_all_bg_jobs():
    """
    Return a summary plus the full list of all background_jobs.

    Summary includes total count and counts per status.
    """
    try:
        jobs = await get_all_bg_jobs()
        total = len(jobs)
        by_status = {}
        for job in jobs:
            status = job.get("status") or "unknown"
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "summary": {
                "total": total,
                "by_status": by_status,
            },
            "jobs": jobs,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch background jobs: {str(e)}")


@router.get("/bg_jobs/{job_id}", summary="Get background job status")
async def api_get_bg_job_status(job_id: str):
    """
    Poll-friendly endpoint.
    - Returns `status`/`message` for any job state.
    - When `status` is `completed`, returns `result` with per-doc SAS URLs for downloads.
    """
    try:
        job = await get_bg_job(job_id)
        if not job:
            raise HTTPException(
                status_code=404, detail=f"No background job found for job_id={job_id}")

        status = job.get("status") or "unknown"
        message = job.get("message")
        error = job.get("error")

        # `result` is stored as TEXT in the DB.
        result: Optional[Any] = None
        raw_result = job.get("result")
        if raw_result:
            if isinstance(raw_result, (dict, list)):
                result = raw_result
            else:
                try:
                    result = json.loads(raw_result)
                except Exception:
                    result = raw_result

        # Enrich docs with blob SAS URLs after completion.
        if isinstance(status, str) and status.lower() == "completed" and isinstance(result, dict):
            docs = result.get("docs") or []
            if isinstance(docs, list) and docs:
                blob_service_client = get_blob_service_client()
                container_name = "ai-saves"
                expiry_time = datetime.utcnow() + timedelta(hours=2)

                index_id = str(job.get("index_id") or "")

                def to_blob_name(blob_path: Any, kind: str) -> Optional[str]:
                    if not blob_path:
                        return None
                    blob_path_str = str(blob_path).strip()
                    if not blob_path_str:
                        return None

                    # If the path already contains a virtual directory
                    # (e.g. `index-.../.../file.ext`), use it as-is.
                    # Otherwise infer it using the known artifact layout.
                    if "/" in blob_path_str or blob_path_str.startswith("index-"):
                        return blob_path_str

                    if kind == "pdf":
                        return f"index-{index_id}/{job_id}/pdf/{blob_path_str}"
                    if kind == "audio_mp3":
                        return f"index-{index_id}/{job_id}/audio_mp3/{blob_path_str}"
                    if kind == "voicescripts":
                        return f"index-{index_id}/{job_id}/voicescripts/{blob_path_str}"
                    return blob_path_str

                def to_sas_url(blob_path: Any, kind: str) -> Optional[str]:
                    blob_name = to_blob_name(blob_path, kind=kind)
                    if not blob_name:
                        return None
                    try:
                        sas_token = generate_sas_token(
                            container_name=container_name,
                            blob_name=blob_name,
                            expiry_time=expiry_time,
                        )
                        return (
                            f"https://{blob_service_client.account_name}.blob.core.windows.net/"
                            f"{container_name}/{blob_name}?{sas_token}"
                        )
                    except Exception:
                        return None

                enriched_docs: list[dict[str, Any]] = []
                for doc in docs:
                    if not isinstance(doc, dict):
                        continue

                    doc = dict(doc)  # shallow copy for safety
                    doc["pdf_url"] = to_sas_url(
                        doc.get("pdf_path"), kind="pdf")
                    doc["audio_url"] = to_sas_url(
                        doc.get("audio_path"), kind="audio_mp3")
                    doc["voicescript_url"] = to_sas_url(
                        doc.get("voicescript_path"), kind="voicescripts")
                    enriched_docs.append(doc)

                result["docs"] = enriched_docs

        return {
            "job_id": job.get("job_id"),
            "index_id": job.get("index_id"),
            "status": status,
            "message": message,
            "error": error,
            "result": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}")



############################################
# ----------- Prompts Manager ------------ #
############################################


@router.get("/prompts")
async def prompts_root():
    """Return API information and available prompt types."""
    return {
        "message": "Prompt Management API v1.0",
        "prompt_types": [name.value for name in PromptNames],
    }

@router.get("/prompts/health")
async def prompts_health_check():
    """Check API + MySQL connectivity"""
    try:
        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                result = await cur.fetchone()
                if result and result[0] == 1:
                    return {"status": "success", "message": "API and DB connectivity are OK"}
                else:
                    return {"status": "failed", "message": "DB did not return expected result"}
    except Exception as e:
        return {"status": "failed", "message": f"DB connection failed: {str(e)}"}

@router.post("/init-tables")
async def init_tables():
    """
    Initialize the prompt tables in the database.
    """
    try:
        await create_tables()
        return {"status": "success", "message": "Tables created or verified."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Create a new prompt (inactive by default)
@router.post("/prompts/new", response_model=PromptResponse)
async def create_prompt_endpoint(prompt: PromptCreate):
    """Create a new prompt version."""
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            return await manager.create_prompt(prompt, db_conn)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}")

# Get all prompts
@router.get("/prompts/list", response_model=List[PromptResponse])
async def get_all_prompts_endpoint(skip: int = 0, limit: int = 100):
    """Retrieve all prompts with pagination."""
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            return await manager.get_all_prompts(skip, limit, db_conn)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}")

# Get all active prompts (must be before /prompts/active/{name})
@router.get("/prompts/active", response_model=List[PromptResponse])
async def get_all_active_prompts_endpoint():
    """Retrieve all currently active prompts."""
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            return await manager.get_all_active_prompts(db_conn)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}")

# Get active prompt by name
@router.get("/prompts/active/{name}", response_model=PromptResponse)
async def get_active_prompt_endpoint(name: str):
    """Retrieve the active prompt by name."""
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            prompt = await manager.get_active_prompt(name, db_conn)
            if prompt is None:
                raise HTTPException(
                    status_code=404, detail=f"No active prompt found for '{name}'")
            return prompt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}")

# Get all versions of a prompt by name
@router.get("/prompts/versions/{name}", response_model=List[PromptResponse])
async def get_all_versions_endpoint(name: str):
    """Retrieve all versions of a prompt by name."""
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            return await manager.get_all_versions(name, db_conn)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}")

# Get specific prompt by name and version
@router.get("/prompts/{name}/{version}", response_model=PromptResponse)
async def get_prompt_by_name_version_endpoint(name: str, version: str):
    """Retrieve a specific prompt by name and version."""
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            prompt = await manager.get_by_name_version(name, version, db_conn)
            if prompt is None:
                raise HTTPException(
                    status_code=404, detail=f"Prompt '{name}' version '{version}' not found")
            return prompt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}")

# Activate a specific prompt version
@router.post("/prompts/activate")
async def activate_prompt_endpoint(request: ActivatePromptRequest):
    """Activate a specific prompt version."""
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            success = await manager.activate_prompt(request.name, request.version, db_conn)
            if success:
                return {
                    "message": (
                        f"Prompt '{request.name}' version '{request.version}' "
                        "activated successfully"
                    )
                }
            raise HTTPException(
                status_code=400, detail="Failed to activate prompt")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}")

# Update prompt content/description
@router.put("/prompts/{name}/{version}", response_model=PromptResponse)
async def update_prompt_endpoint(name: str, version: str, prompt_update: PromptUpdate):
    """Update a prompt's content or description."""
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            updated_prompt = await manager.update_prompt(name, version, prompt_update, db_conn)
            if updated_prompt is None:
                raise HTTPException(
                    status_code=404, detail=f"Prompt '{name}' version '{version}' not found")
            return updated_prompt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}")

# Delete a specific prompt version
@router.delete("/prompts/{name}/{version}")
async def delete_prompt_endpoint(name: str, version: str):
    """Delete a specific prompt version."""
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            success = await manager.delete_prompt(name, version, db_conn)
            if not success:
                raise HTTPException(
                    status_code=404, detail=f"Prompt '{name}' version '{version}' not found")
            return {"message": f"Prompt '{name}' version '{version}' deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}")

# Get allowed prompt names (5 valid names)
@router.get("/prompts/allowed-names")
async def get_allowed_names_endpoint():
    """Return the list of allowed prompt names."""
    return {"allowed_names": [name.value for name in PromptNames]}
