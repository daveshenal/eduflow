import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse

from app.adapters.azure_blob import get_blob_service_client
from app.knowledgebase.get_blobs import get_blobs
from app.knowledgebase.ai_index import AIIndex
from app.pipelines.huddle_pipeline import validate_payload
from app.pipelines.test_huddle_pipeline import generate_huddles_background_task_test

router = APIRouter()

# Blob and Search helpers
blob_service_client = get_blob_service_client()

    
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