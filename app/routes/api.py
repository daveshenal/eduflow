import asyncio
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Query, UploadFile, File
from fastapi.responses import JSONResponse

from app.adapters.azure_blob import get_blob_service_client
from app.knowledgebase.get_blobs import get_blobs
from app.knowledgebase.ai_index import AIIndex
from app.knowledgebase.upload_files import DocumentManager
from app.pipelines.gen_pipeline import validate_payload
from app.pipelines.test_gen_pipeline import generate_huddles_background_task_test

router = APIRouter()

# Blob and Search helpers
blob_service_client = get_blob_service_client()


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
async def test_blob_connection(
    container: str = Query(..., description="Azure Blob container name to test"),
    ):
    from azure.core.exceptions import ResourceNotFoundError
    try:
        container_client = blob_service_client.get_container_client(container)
        blobs = list(container_client.list_blobs())
        if not blobs:
            raise HTTPException(status_code=404, detail="No blobs found in the container.")
        blob_names = [blob.name for blob in blobs]
        return {"status": "success", "blobs": blob_names}
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Container not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to Blob Storage: {str(e)}")