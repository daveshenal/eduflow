import asyncio
import socket
import os
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Set
from fastapi import APIRouter, HTTPException, UploadFile, Request, File, Form, Body, Query
from fastapi.responses import StreamingResponse, JSONResponse
from azure.core.exceptions import ResourceExistsError
from azure.core.exceptions import HttpResponseError
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

from app.adapters.azure_blob import get_blob_service_client, generate_sas_token
from app.knowledgebase.get_blobs import get_blobs as kb_get_blobs
from app.adapters.claude_service import get_claude_client
from app.adapters.azure_sql import create_tables, get_db_connection
from app.knowledgebase.upload_files import DocumentProcessor
from app.knowledgebase.global_index import GlobalIndex
from app.knowledgebase.provider_index import ProviderIndex
from app.pipelines.huddle_pipeline import generate_huddles_background_task, validate_payload
from app.pipelines.test_huddle_pipeline import generate_huddles_background_task_test
from app.pipelines.chat_pipeline import generate_chat_stream
from app.retrievers.index_data_retriver  import PrioritizedRetriever
from config.settings import settings
from app.core.scope_val_service import scope_validation

# Prompt management imports
from app.prompts.prompt_management import (
    get_manager as get_prompt_manager,
    PromptCreate as PMPromptCreate,
    PromptUpdate as PMPromptUpdate,
    PromptResponse as PMPromptResponse,
    ActivatePromptRequest as PMActivatePromptRequest,
    managers as pm_managers,
    MainPromptNames,
    UseCasePromptNames,
    RolePromptNames,
    DisciplinePromptNames,
)

router = APIRouter()

# Blob and Search helpers
blob_service_client = get_blob_service_client()
claude_client = get_claude_client()

# Configure a processor aligned with new index chunking expectations
_processor = DocumentProcessor(
    embedding_deployment=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    chunk_size=500,
    chunk_overlap=100,
)

def _build_search_client(index_name: str) -> SearchClient:
    return SearchClient(
        endpoint=settings.AZURE_SEARCH_ENDPOINT,
        index_name=index_name,
        credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY),
    )

def _split_embed_build_global_docs(
    filename: str,
    file_bytes: bytes,
    blob_path: str,
    level: str,
    state: Optional[str],
    category: Optional[str],
) -> tuple[List[dict], Optional[str]]:
    """
    Process document and return chunks along with any error message.
    Returns (chunks, error_message)
    """
    try:
        documents = _processor._load_document_from_bytes(filename, file_bytes)
        if not documents:
            return [], "No content could be extracted from the file"
        
        chunks = _processor.text_splitter.split_documents(documents)
        if not chunks:
            return [], "No chunks could be created from the document"
        
        texts = [doc.page_content for doc in chunks]
        embeddings = _processor.embeddings.embed_documents(texts)
        parent_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        results: List[dict] = []
        
        for chunk, vector in zip(chunks, embeddings):
            results.append(
                {
                    "chunk_id": str(uuid.uuid4()),
                    "parent_id": parent_id,
                    "level": (level or "").lower(),
                    "state": (state or "").lower(),
                    "category": (category or "").lower(),
                    "source_name": filename,
                    "source_path": blob_path,
                    "created_at": created_at,
                    "title": None,
                    "content": chunk.page_content,
                    "content_vector": vector,
                }
            )
        return results, None
        
    except Exception as e:
        error_msg = f"Failed to process document {filename}: {str(e)}"
        logging.error(error_msg)
        return [], error_msg

def _split_embed_build_provider_docs(
    filename: str,
    file_bytes: bytes,
    blob_path: str,
    category: str,
) -> tuple[List[dict], Optional[str]]:
    """
    Process document and return chunks along with any error message.
    Returns (chunks, error_message)
    """
    try:
        documents = _processor._load_document_from_bytes(filename, file_bytes)
        if not documents:
            return [], "No content could be extracted from the file"
        
        chunks = _processor.text_splitter.split_documents(documents)
        if not chunks:
            return [], "No chunks could be created from the document"
        
        texts = [doc.page_content for doc in chunks]
        embeddings = _processor.embeddings.embed_documents(texts)
        parent_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        results: List[dict] = []
        
        for chunk, vector in zip(chunks, embeddings):
            results.append(
                {
                    "chunk_id": str(uuid.uuid4()),
                    "parent_id": parent_id,
                    "category": (category or "").lower(),
                    "source_name": filename,
                    "source_path": blob_path,
                    "created_at": created_at,
                    "title": None,
                    "content": chunk.page_content,
                    "content_vector": vector,
                }
            )
        return results, None
        
    except Exception as e:
        error_msg = f"Failed to process document {filename}: {str(e)}"
        logging.error(error_msg)
        return [], error_msg

def _batch_upload_documents(search_client, documents, batch_size=50):
    results = []
    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        res = search_client.upload_documents(documents=batch)
        results.extend(res)
    return results


############################################
# ----------- GEN API ENDPOINTS ---------- #
############################################


@router.post("/chat/stream")
async def stream_endpoint(request: Request):
    """Stream Chatbot Outputs."""
    payload = await request.json()
    provider_id = payload.get("provider_id") or payload.get("providerId")
    if not provider_id:
        raise HTTPException(status_code=400, detail="provider_id is required")

    return StreamingResponse(
        generate_chat_stream(payload, claude_client),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
    

# Endpoint to start background job
@router.post("/huddles/start")
async def start_huddle_generation(request: Request):
    """Start Huddle PDF generation as background job."""
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
    asyncio.create_task(generate_huddles_background_task(params, claude_client))
    
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
    
# Endpoint to test background job
@router.post("/huddles/start-test")
async def start_huddle_generation(request: Request):
    """Start Huddle PDF generation as background job."""
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

@router.post("/scope/validate-test")
async def test_scope_validation(request: Request):
    """Test endpoint to run scope validation against Claude using active prompt."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    try:
        last_result = None
        async for result in scope_validation(payload, claude_client):
            last_result = result
        if last_result is None:
            raise HTTPException(status_code=500, detail="No response from scope validation")
        return JSONResponse(status_code=200, content=last_result)
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Scope validation failed")
        raise HTTPException(status_code=500, detail=f"Scope validation failed: {str(e)}")

@router.get("/huddles/status/{job_id}")
async def get_huddle_job_status(job_id: str):
    """Get the status of a huddle generation job from DB."""
    try:
        from app.adapters.azure_sql import get_huddle_job
        row = await get_huddle_job(job_id)
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")

        # Only expose the fields we currently use
        response_data = {
            "job_id": row.get("job_id"),
            "status": row.get("status"),
            "message": row.get("message"),
            "result": row.get("result"),
            "error": row.get("error"),
            "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
            "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
        }

        return JSONResponse(
            content=response_data,
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Failed to fetch huddle job status")
        raise HTTPException(status_code=500, detail=f"Failed to fetch job status: {str(e)}")



############################################
# ------------ Index Manager ------------- #
############################################


@router.post("/upload-documents")
async def upload_documents(
    files: List[UploadFile] = File(...),
    index_type: str = Form(..., description="global | provider"),
    global_category: Optional[str] = Form(None),
    global_accreditation: Optional[str] = Form(None),
    global_federal: Optional[str] = Form(None),
    global_state: Optional[str] = Form(None),
    provider_category: Optional[str] = Form(None),
    provider_id: Optional[str] = Form(None),
):
    """Batch upload endpoint to support the dummy-ui uploader. Dispatches to global or provider flows per file."""
    try:
        results = []
        if index_type not in {"global", "provider"}:
            raise HTTPException(status_code=400, detail="index_type must be 'global' or 'provider'")

        if index_type == "global":
            # Determine mapping to level/state/category
            if not global_category:
                raise HTTPException(status_code=400, detail="global_category is required for global uploads")

            if global_category == "accreditations":
                level = "accreditations"
                state_val = None
                category_val = global_accreditation
                if not category_val:
                    raise HTTPException(status_code=400, detail="global_accreditation is required when category is 'accreditations'")
            elif global_category == "federal":
                level = "federal"
                state_val = None
                category_val = global_federal
                if not category_val:
                    raise HTTPException(status_code=400, detail="global_federal is required when category is 'federal'")
            elif global_category == "state":
                level = "state"
                state_val = global_state
                category_val = None
                if not state_val:
                    raise HTTPException(status_code=400, detail="global_state is required when category is 'state'")
            else:
                # default: treat as level with category
                level = global_category
                state_val = None
                category_val = None

            container_name = "global-knowledgebase"
            container_client = blob_service_client.get_container_client(container_name)
            if not container_client.exists():
                raise HTTPException(status_code=404, detail=f"Container '{container_name}' not found")

            index_name = settings.AZURE_GLOBAL_INDEX_NAME
            search_client = _build_search_client(index_name)

            for upload in files:
                # Blob path
                parts = [level]
                if state_val:
                    parts.append(state_val)
                if category_val:
                    parts.append(category_val)
                directory_path = "/".join(part.strip("/") for part in parts if part)
                blob_path = f"{directory_path}/{upload.filename}"

                # Metadata
                metadata = {
                    "level": (level or "").lower(),
                    "state": (state_val or "").lower() if state_val else "",
                    "category": (category_val or "").lower() if category_val else "",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }

                # Upload to blob
                blob_client = container_client.get_blob_client(blob_path)
                with upload.file as stream:
                    blob_client.upload_blob(stream, overwrite=True, metadata=metadata)

                # Get bytes
                try:
                    upload.file.seek(0)
                    file_bytes = upload.file.read()
                    if not file_bytes:
                        file_bytes = blob_client.download_blob().readall()
                except Exception:
                    file_bytes = blob_client.download_blob().readall()

                # Build chunks and upload
                chunk_docs, processing_error = _split_embed_build_global_docs(
                    filename=upload.filename,
                    file_bytes=file_bytes,
                    blob_path=blob_path,
                    level=level,
                    state=state_val,
                    category=category_val,
                )
                if not chunk_docs:
                    results.append({
                        "filename": upload.filename,
                        "blob_path": blob_path,
                        "index": index_name,
                        "chunks_uploaded": 0,
                        "error": processing_error or "No content could be extracted or embedded from the file",
                        "metadata": metadata,
                        "success": False
                    })
                    continue

                upload_result = _batch_upload_documents(search_client, chunk_docs, batch_size=50)
                results.append({
                    "filename": upload.filename,
                    "blob_path": blob_path,
                    "index": index_name,
                    "chunks_uploaded": len(chunk_docs),
                    "upload_status": [r.succeeded for r in upload_result],
                    "metadata": metadata,
                    "success": True
                })

            # Check if any uploads failed
            failed_uploads = [r for r in results if not r.get("success", True)]
            if failed_uploads:
                return JSONResponse(
                    status_code=207,  # Multi-Status for partial failures
                    content={
                        "success": False, 
                        "message": f"{len(failed_uploads)} of {len(results)} uploads failed",
                        "results": results
                    }
                )
            else:
                return JSONResponse(status_code=200, content={"success": True, "results": results})

        # Provider flow
        if not provider_id:
            raise HTTPException(status_code=400, detail="provider_id is required for provider uploads")
        if not provider_category:
            raise HTTPException(status_code=400, detail="provider_category is required for provider uploads")

        container_name = f"provider-{provider_id}"
        container_client = blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            raise HTTPException(status_code=404, detail=f"Container '{container_name}' not found")

        index_name = f"provider-index-{provider_id}"
        search_client = _build_search_client(index_name)

        for upload in files:
            directory_path = (provider_category or "").strip("/")
            blob_path = f"{directory_path}/{upload.filename}"
            metadata = {
                "category": (provider_category or "").lower(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            blob_client = container_client.get_blob_client(blob_path)
            with upload.file as stream:
                blob_client.upload_blob(stream, overwrite=True, metadata=metadata)

            try:
                upload.file.seek(0)
                file_bytes = upload.file.read()
                if not file_bytes:
                    file_bytes = blob_client.download_blob().readall()
            except Exception:
                file_bytes = blob_client.download_blob().readall()

            chunk_docs, processing_error = _split_embed_build_provider_docs(
                filename=upload.filename,
                file_bytes=file_bytes,
                blob_path=blob_path,
                category=provider_category,
            )
            if not chunk_docs:
                results.append({
                    "filename": upload.filename,
                    "blob_path": blob_path,
                    "index": index_name,
                    "chunks_uploaded": 0,
                    "error": processing_error or "No content could be extracted or embedded from the file",
                    "metadata": metadata,
                    "success": False
                })
                continue

            upload_result = _batch_upload_documents(search_client, chunk_docs, batch_size=50)
            results.append({
                "filename": upload.filename,
                "blob_path": blob_path,
                "index": index_name,
                "chunks_uploaded": len(chunk_docs),
                "upload_status": [r.succeeded for r in upload_result],
                "metadata": metadata,
                "success": True
            })

        # Check if any uploads failed
        failed_uploads = [r for r in results if not r.get("success", True)]
        if failed_uploads:
            return JSONResponse(
                status_code=207,  # Multi-Status for partial failures
                content={
                    "success": False, 
                    "message": f"{len(failed_uploads)} of {len(results)} uploads failed",
                    "results": results
                }
            )
        else:
            return JSONResponse(status_code=200, content={"success": True, "results": results})
    except HTTPException:
        raise
    except ResourceExistsError:
        raise HTTPException(status_code=409, detail="Blob already exists.")
    except HttpResponseError as e:
        raise HTTPException(status_code=400, detail=f"Azure error: {str(e)}")
    except Exception as e:
        logging.exception("Batch upload failed")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.delete("/documents/delete-by-filename")
async def delete_documents_by_filename(
    filename: str = Query(..., description="Exact file name to delete (matches source_name in index)"),
    index_type: str = Query(..., description="global | provider"),
    provider_id: Optional[str] = Query(None, description="Required when index_type=provider"),
):
    """
    Delete all indexed chunks and the underlying blob(s) for a given filename.
    - For global: searches `settings.AZURE_GLOBAL_INDEX` and deletes from container `global-knowledgebase`.
    - For provider: searches `provider-index-{provider_id}` and deletes from container `provider-{provider_id}`.
    """
    try:
        if index_type not in {"global", "provider"}:
            raise HTTPException(status_code=400, detail="index_type must be 'global' or 'provider'")
        if index_type == "provider" and not provider_id:
            raise HTTPException(status_code=400, detail="provider_id is required when index_type is 'provider'")

        # Determine index and container
        if index_type == "global":
            index_name = settings.AZURE_GLOBAL_INDEX_NAME
            container_name = "global-knowledgebase"
        else:
            index_name = f"provider-index-{provider_id}"
            container_name = f"provider-{provider_id}"

        search_client = _build_search_client(index_name)
        container_client = blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            raise HTTPException(status_code=404, detail=f"Container '{container_name}' not found")

        # Find all chunks for the filename
        filter_expr = f"source_name eq '{filename}'"
        results_iter = search_client.search(
            search_text="*",
            filter=filter_expr,
            select=["chunk_id", "source_path", "source_name", "parent_id"],
            include_total_count=True,
        )

        chunk_ids: List[str] = []
        blob_paths: Set[str] = set()
        total = 0
        for item in results_iter:
            total += 1
            chunk_id = item.get("chunk_id") or item.get("id")
            source_path = item.get("source_path")
            if chunk_id:
                chunk_ids.append(chunk_id)
            if source_path:
                blob_paths.add(source_path)

        if total == 0:
            return JSONResponse(status_code=200, content={
                "message": "No documents found for filename",
                "filename": filename,
                "index": index_name,
                "deleted_chunks": 0,
                "deleted_blobs": 0,
            })

        # Delete blobs (best-effort)
        deleted_blobs = 0
        for blob_path in blob_paths:
            try:
                container_client.delete_blob(blob_path)
                deleted_blobs += 1
            except Exception:
                # Ignore missing blobs or transient errors for deletion
                pass

        # Delete indexed chunks
        to_delete = [{"chunk_id": cid} for cid in chunk_ids]
        delete_result = search_client.delete_documents(documents=to_delete)
        deleted_chunks = sum(1 for r in delete_result if getattr(r, "succeeded", False))

        return JSONResponse(status_code=200, content={
            "message": "Deletion attempted",
            "filename": filename,
            "index": index_name,
            "matched_chunks": len(chunk_ids),
            "deleted_chunks": deleted_chunks,
            "matched_blobs": len(blob_paths),
            "deleted_blobs": deleted_blobs,
        })
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Delete by filename failed")
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

 

############################################
# ----------- Prompts Manager ------------ #
############################################


@router.get("/prompts")
async def prompts_root():
    return {
        "message": "Prompt Management API v2.0",
        "tables": list(pm_managers.keys()),
        "allowed_names": {
            "main_prompts": [name.value for name in MainPromptNames],
            "use_case_prompts": [name.value for name in UseCasePromptNames],
            "role_prompts": [name.value for name in RolePromptNames],
            "discipline_prompts": [name.value for name in DisciplinePromptNames],
        },
    }

@router.get("/prompts/health")
async def prompts_health_check():
    return {"status": "healthy", "message": "API is running"}

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
@router.post("/prompts/{table_name}/", response_model=PMPromptResponse)
async def create_prompt_endpoint(table_name: str, prompt: PMPromptCreate):
    manager = get_prompt_manager(table_name)
    try:
        async with get_db_connection() as db_conn:
            return await manager.create_prompt(prompt, db_conn)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Get all prompts in a table
@router.get("/prompts/{table_name}/", response_model=List[PMPromptResponse])
async def get_all_prompts_endpoint(table_name: str, skip: int = 0, limit: int = 100):
    manager = get_prompt_manager(table_name)
    try:
        async with get_db_connection() as db_conn:
            return await manager.get_all_prompts(skip, limit, db_conn)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Get active prompt by name
@router.get("/prompts/{table_name}/active/{name}", response_model=PMPromptResponse)
async def get_active_prompt_endpoint(table_name: str, name: str):
    manager = get_prompt_manager(table_name)
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
@router.get("/prompts/{table_name}/versions/{name}", response_model=List[PMPromptResponse])
async def get_all_versions_endpoint(table_name: str, name: str):
    manager = get_prompt_manager(table_name)
    try:
        async with get_db_connection() as db_conn:
            return await manager.get_all_versions(name, db_conn)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Get specific prompt by name and version
@router.get("/prompts/{table_name}/{name}/{version}", response_model=PMPromptResponse)
async def get_prompt_by_name_version_endpoint(table_name: str, name: str, version: str):
    manager = get_prompt_manager(table_name)
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
@router.post("/prompts/{table_name}/activate")
async def activate_prompt_endpoint(table_name: str, request: PMActivatePromptRequest):
    manager = get_prompt_manager(table_name)
    try:
        async with get_db_connection() as db_conn:
            success = await manager.activate_prompt(request.name, request.version, db_conn)
            if success:
                return {"message": f"Prompt '{request.name}' version '{request.version}' activated successfully"}
            else:
                raise HTTPException(status_code=400, detail="Failed to activate prompt")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Update prompt content/description
@router.put("/prompts/{table_name}/{name}/{version}", response_model=PMPromptResponse)
async def update_prompt_endpoint(table_name: str, name: str, version: str, prompt_update: PMPromptUpdate):
    manager = get_prompt_manager(table_name)
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
@router.delete("/prompts/{table_name}/{name}/{version}")
async def delete_prompt_endpoint(table_name: str, name: str, version: str):
    manager = get_prompt_manager(table_name)
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

# Get allowed names for a specific table
@router.get("/prompts/{table_name}/allowed-names")
async def get_allowed_names_endpoint(table_name: str):
    manager = get_prompt_manager(table_name)
    return {
        "table_name": table_name,
        "allowed_names": [name.value for name in manager.allowed_names],
    }

# Get all active prompts in a table
@router.get("/prompts/{table_name}/active", response_model=List[PMPromptResponse])
async def get_all_active_prompts_endpoint(table_name: str):
    manager = get_prompt_manager(table_name)
    try:
        async with get_db_connection() as db_conn:
            return await manager.get_all_active_prompts(db_conn)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


############################################
# ------------ Index Manager ------------- #
############################################
    

@router.post("/run-provider-indexing/{provider_id}")
def run_provider_indexing(provider_id: str):
    try:
        provider_index = ProviderIndex(provider_id=provider_id)
        provider_index.setup_complete_indexing_pipeline()
        return {"status": "success", "message": f"Provider index setup completed for provider_id={provider_id}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-global-indexing")
def run_global_indexing():
    try:
        global_index = GlobalIndex()
        
        global_index.setup_complete_indexing_pipeline()
        return {"status": "success", "message": "Global index setup completed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/blobs")
async def list_blobs(
    container: str = Query(..., description="Azure Blob container name"),
    directory: Optional[str] = Query(None, description="Optional virtual directory/prefix to filter blobs"),
):
    try:
        return kb_get_blobs(container=container, directory=directory)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.exception("Failed to list blobs")
        raise HTTPException(status_code=500, detail=f"Failed to list blobs: {str(e)}")


@router.get("/test-blob-connection")
async def test_blob_connection():
    from azure.core.exceptions import ResourceNotFoundError
    try:
        # Connect to the blob container
        container_client = blob_service_client.get_container_client(settings.AZURE_GLOBAL_CONTAINER_NAME)

        # List blobs in the container
        blobs = list(container_client.list_blobs())
        
        if not blobs:
            raise HTTPException(status_code=404, detail="No blobs found in the container.")
        
        # Return blob names as a simple response
        blob_names = [blob.name for blob in blobs]
        return {"status": "success", "blobs": blob_names}
    
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Container not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to Blob Storage: {str(e)}")


@router.get("/test-sql-connection")
async def test_sql_connection(verbose: bool = Query(False)):
    diagnostics = None
    
    # Always collect diagnostics first if verbose=True
    if verbose:
        host = settings.MYSQL_HOST
        port = settings.MYSQL_PORT
        dns_resolution = None
        tcp_connect_ok = None
        tcp_error = None
        ca_path = "certs/DigiCertGlobalRootCA.crt.pem"
        ca_exists = os.path.exists(ca_path)

        # DNS resolution
        try:
            infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
            dns_resolution = list({info[4][0] for info in infos})
        except Exception as e:
            dns_resolution = f"DNS error: {str(e)}"

        # Raw TCP connectivity
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=3.0)
            tcp_connect_ok = True
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
        except Exception as e:
            tcp_connect_ok = False
            tcp_error = str(e)
            
        diagnostics = {
            "host": host,
            "port": port,
            "dns_resolution": dns_resolution,
            "tcp_connect_ok": tcp_connect_ok,
            "tcp_error": tcp_error,
            "ssl_ca_exists": ca_exists,
            "ssl_ca_path": ca_path,
        }
    
    # Now try the database connection
    try:
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT 1 AS ok")
                ok_row = await cursor.fetchone()
                await cursor.execute("SELECT VERSION()")
                version_row = await cursor.fetchone()

        response = {
            "status": "success",
            "ok": bool(ok_row[0] == 1 if ok_row is not None else False),
            "server_version": version_row[0] if version_row else None,
        }
        if diagnostics is not None:
            response["diagnostics"] = diagnostics
        return response
        
    except Exception as e:
        if verbose and diagnostics:
            return JSONResponse(status_code=500, content={
                "status": "error",
                "message": f"Error connecting to MySQL: {str(e)}",
                "diagnostics": diagnostics,
            })
        raise HTTPException(status_code=500, detail=f"Error connecting to MySQL: {str(e)}")


@router.get("/test-sql-connection-mode")
async def test_sql_connection_mode(
    mode: str = Query("ssl_verify_ca", description="no_ssl | ssl_true | ssl_verify_ca | ssl_no_verify"),
    host: Optional[str] = Query(None),
    port: Optional[int] = Query(None),
    verbose: bool = Query(False),
    ca_path: Optional[str] = Query(None, description="Path to CA file for verify mode"),
):
    import aiomysql
    import ssl as ssl_lib

    used_host = host or settings.MYSQL_HOST
    used_port = port or settings.MYSQL_PORT
    used_user = settings.MYSQL_USER
    used_password = settings.MYSQL_PASSWORD
    used_db = settings.MYSQL_DB

    # Configure SSL parameter based on mode
    ssl_param = None
    resolved_ca = ca_path or "certs/DigiCertGlobalRootCA.crt.pem"
    if mode == "no_ssl":
        ssl_param = None
    elif mode == "ssl_true":
        ssl_param = ssl_lib.create_default_context()
    elif mode == "ssl_verify_ca":
        ssl_param = ssl_lib.create_default_context(cafile=resolved_ca)
    elif mode == "ssl_no_verify":
        ctx = ssl_lib.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl_lib.CERT_NONE
        ssl_param = ctx
    else:
        raise HTTPException(status_code=400, detail="Invalid mode. Use: no_ssl, ssl_true, ssl_verify_ca, ssl_no_verify")

    diagnostics = None
    if verbose:
        dns_resolution = None
        tcp_connect_ok = None
        tcp_error = None
        try:
            infos = socket.getaddrinfo(used_host, used_port, proto=socket.IPPROTO_TCP)
            dns_resolution = list({info[4][0] for info in infos})
        except Exception as e:
            dns_resolution = f"DNS error: {str(e)}"
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(used_host, used_port), timeout=3.0)
            tcp_connect_ok = True
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
        except Exception as e:
            tcp_connect_ok = False
            tcp_error = str(e)
        diagnostics = {
            "host": used_host,
            "port": used_port,
            "dns_resolution": dns_resolution,
            "tcp_connect_ok": tcp_connect_ok,
            "tcp_error": tcp_error,
            "ssl_mode": mode,
            "ssl_ca_path": resolved_ca if mode == "ssl_verify_ca" else None,
            "ssl_ca_exists": (os.path.exists(resolved_ca) if mode == "ssl_verify_ca" else None),
        }

    try:
        conn = await aiomysql.connect(
            host=used_host,
            port=used_port,
            user=used_user,
            password=used_password,
            db=used_db,
            autocommit=True,
            ssl=ssl_param,
        )
        try:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT 1")
                one = await cursor.fetchone()
                await cursor.execute("SELECT VERSION()")
                version_row = await cursor.fetchone()
        finally:
            conn.close()

        resp = {
            "status": "success",
            "mode": mode,
            "ok": bool(one and one[0] == 1),
            "server_version": version_row[0] if version_row else None,
        }
        if diagnostics is not None:
            resp["diagnostics"] = diagnostics
        return resp
    except Exception as e:
        if verbose:
            return JSONResponse(status_code=500, content={
                "status": "error",
                "mode": mode,
                "message": f"Connect/query failed: {str(e)}",
                "details": diagnostics or {},
            })
        raise HTTPException(status_code=500, detail=f"Connect/query failed: {str(e)}")