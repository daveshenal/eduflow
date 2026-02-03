import asyncio
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Query, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse

from app.adapters.azure_blob import get_blob_service_client, test_blob_connection
from app.adapters.claude_service import get_claude_client
from app.adapters.azure_sql import get_db_connection, create_tables
from app.knowledgebase.get_blobs import get_blobs
from app.knowledgebase.ai_index import AIIndex
from app.knowledgebase.upload_files import DocumentManager
from app.pipelines.gen_pipeline import validate_payload
from app.pipelines.chat_pipeline import generate_chat_stream
from app.pipelines.test_gen_pipeline import generate_huddles_background_task_test

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

# Blob and Search helpers
blob_service_client = get_blob_service_client()
claude_client = get_claude_client()

@router.post("/chat/stream")
async def stream_endpoint(request: Request):
    """Stream Chatbot Outputs. Uses a single index; pass index_id in the body. Backward compatible with indexId."""
    payload = await request.json()
    index_id = payload.get("index_id")
    if not index_id:
        raise HTTPException(status_code=400, detail="index_id is required")

    return StreamingResponse(
        generate_chat_stream(payload, claude_client),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# Endpoint to test background job
@router.post("/gen/start-test")
async def start_doc_generation(request: Request):
    """Start document generation as background job."""
    payload = await request.json()
    
    try:
        # Validate the payload
        params = validate_payload(payload)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )

    # Start background task
    asyncio.create_task(generate_huddles_background_task_test(params))
    
    # Return job ID immediately
    return JSONResponse(
        content={
            "status": "started",
            "message": "Huddle generation started successfully",
        },
        headers={
            "Cache-Control": "no-cache",
        },
    )


############################################
# ------------ Index Manager ------------- #
############################################
    

@router.post("/run-ai-indexing/{index_id}")
def run_ai_indexing(index_id: str):
    try:
        ai_index = AIIndex(index_id=index_id)
        ai_index.setup_complete_indexing_pipeline()
        return {"status": "success", "message": f"AI index setup completed for index_id={index_id}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledgebase/{index_id}/upload")
async def upload_documents_to_knowledgebase(
    index_id: str,
    files: List[UploadFile] = File(..., description="Document(s) to upload (PDF, DOCX, TXT)"),
    ):
    """
    Upload documents to the knowledgebase for a given index_id.
    - Injects chunked content with embeddings into the search index (ai-index-{index_id})
    - Saves original documents to blob storage container (ai-{index_id})
    - Index and container must already exist (via POST /run-ai-indexing/{index_id}). Upload fails if they do not.
    """
    try:
        manager = DocumentManager(index_id=index_id)
        file_tuples = []
        for f in files:
            data = await f.read()
            file_tuples.append((f.filename or "document", data))

        if len(file_tuples) == 1:
            filename, data = file_tuples[0]
            result = manager.upload_and_process(filename, data)
            return JSONResponse(content=result)
        else:
            result = manager.batch_process(file_tuples)
            return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.exception("Failed to upload documents")
        raise HTTPException(status_code=500, detail=str(e))
   

@router.delete("/knowledgebase/{index_id}/documents")
async def delete_documents_by_filename(
    index_id: str,
    filename: str = Query(..., description="Exact file name to delete (matches source_name in index)"),
    ):
    """
    Delete all indexed chunks and the blob for a given filename in the knowledgebase.
    Requires the index and container to exist (ai-index-{index_id}, ai-{index_id}).
    """
    try:
        manager = DocumentManager(index_id=index_id)
        result = manager.delete_by_filename(filename)
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.exception("Delete by filename failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/index/{index_id}")
def delete_index_and_container(index_id: str):
    """Delete the Azure AI Search index, indexer, skillset, data source, and blob container for the given index_id."""
    try:
        ai_index = AIIndex(index_id=index_id)
        deleted = ai_index.delete_index_and_container()
        return {
            "status": "success",
            "message": f"Index and container deleted for index_id={index_id}.",
            "deleted": deleted,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/blobs")
async def list_blobs(
    container: str = Query(..., description="Azure Blob container name"),
    directory: Optional[str] = Query(None, description="Optional virtual directory/prefix to filter blobs"),
    ):
    try:
        return get_blobs(container=container, directory=directory)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.exception("Failed to list blobs")
        raise HTTPException(status_code=500, detail=f"Failed to list blobs: {str(e)}")


@router.get("/test-blob-connection")
async def blob_connection(
    container: str = Query(..., description="Azure Blob container name to test"),
    ):
    try:
        return test_blob_connection(container)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error connecting to Blob Storage: {str(e)}"
        )


 
############################################
# ----------- Prompts Manager ------------ #
############################################


@router.get("/prompts")
async def prompts_root():
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
                    return {"status": "failed", "message": "API and DB connectivity are OK"}
                else:
                    return {"status": "successful", "message": "DB did not return expected result"}
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
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            return await manager.create_prompt(prompt, db_conn)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Get all prompts
@router.get("/prompts/list", response_model=List[PromptResponse])
async def get_all_prompts_endpoint(skip: int = 0, limit: int = 100):
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            return await manager.get_all_prompts(skip, limit, db_conn)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Get all active prompts (must be before /prompts/active/{name})
@router.get("/prompts/active", response_model=List[PromptResponse])
async def get_all_active_prompts_endpoint():
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            return await manager.get_all_active_prompts(db_conn)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Get active prompt by name
@router.get("/prompts/active/{name}", response_model=PromptResponse)
async def get_active_prompt_endpoint(name: str):
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            prompt = await manager.get_active_prompt(name, db_conn)
            if prompt is None:
                raise HTTPException(status_code=404, detail=f"No active prompt found for '{name}'")
            return prompt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Get all versions of a prompt by name
@router.get("/prompts/versions/{name}", response_model=List[PromptResponse])
async def get_all_versions_endpoint(name: str):
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            return await manager.get_all_versions(name, db_conn)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Get specific prompt by name and version
@router.get("/prompts/{name}/{version}", response_model=PromptResponse)
async def get_prompt_by_name_version_endpoint(name: str, version: str):
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            prompt = await manager.get_by_name_version(name, version, db_conn)
            if prompt is None:
                raise HTTPException(status_code=404, detail=f"Prompt '{name}' version '{version}' not found")
            return prompt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Activate a specific prompt version
@router.post("/prompts/activate")
async def activate_prompt_endpoint(request: ActivatePromptRequest):
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            success = await manager.activate_prompt(request.name, request.version, db_conn)
            if success:
                return {"message": f"Prompt '{request.name}' version '{request.version}' activated successfully"}
            raise HTTPException(status_code=400, detail="Failed to activate prompt")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Update prompt content/description
@router.put("/prompts/{name}/{version}", response_model=PromptResponse)
async def update_prompt_endpoint(name: str, version: str, prompt_update: PromptUpdate):
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            updated_prompt = await manager.update_prompt(name, version, prompt_update, db_conn)
            if updated_prompt is None:
                raise HTTPException(status_code=404, detail=f"Prompt '{name}' version '{version}' not found")
            return updated_prompt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Delete a specific prompt version
@router.delete("/prompts/{name}/{version}")
async def delete_prompt_endpoint(name: str, version: str):
    manager = get_prompt_manager()
    try:
        async with get_db_connection() as db_conn:
            success = await manager.delete_prompt(name, version, db_conn)
            if not success:
                raise HTTPException(status_code=404, detail=f"Prompt '{name}' version '{version}' not found")
            return {"message": f"Prompt '{name}' version '{version}' deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Get allowed prompt names (5 valid names)
@router.get("/prompts/allowed-names")
async def get_allowed_names_endpoint():
    return {"allowed_names": [name.value for name in PromptNames]}