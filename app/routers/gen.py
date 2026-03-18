import asyncio
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse

from app.adapters.claude_service import get_claude_client

from app.pipelines.gen_pipeline import validate_payload, generate_content_background_task
from app.pipelines.gen_baseline_pipeline import (
    validate_baseline_payload,
    generate_content_baseline_background_task,
)
from app.pipelines.gen_memory_pipeline import generate_content_memory_background_task
from app.pipelines.test_gen_pipeline import generate_content_background_task_test
from app.pipelines.chat_pipeline import generate_chat_stream


router = APIRouter()

# Blob and Search helpers
claude_client = get_claude_client()


# Endpoint to chatbot
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
async def start_docs_generation(request: Request):
    """Start Doc generation as background job."""
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
    asyncio.create_task(generate_content_background_task_test(params))
    
    # Return job ID immediately
    return JSONResponse(
        content={
            "status": "started",
            "message": "Docs generation started successfully",
        },
        headers={
            "Cache-Control": "no-cache",
        },
    )
    
# Endpoint to start background job
@router.post("/gen/start")
async def start_content_generation(request: Request):
    """Start content generation as background job."""
    payload = await request.json()
    
    try:
        # Validate the payload
        params = validate_payload(payload)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )

    # await generate_content_background_task(params, claude_client)
    asyncio.create_task(generate_content_background_task(params, claude_client))
    
    return JSONResponse(
        content={
            "status": "started",
            "message": "Docs generation started successfully",
        },
        headers={
            "Cache-Control": "no-cache",
        },
    )

# Endpoint to start baseline without memory
@router.post("/gen/start-baseline")
async def start_baseline_generation(request: Request):
    """
    Baseline generation: no curriculum plan.
    Body: job_id, callback_url, index_id, prompts (list of strings), duration, voice.
    Each prompt is used as the retrieval query for that doc; docs are generated with
    minimal system prompt + user prompt + retrieved context.
    """
    payload = await request.json()
    try:
        params = validate_baseline_payload(payload)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    # await generate_content_baseline_background_task(params, claude_client)
    asyncio.create_task(generate_content_baseline_background_task(params, claude_client))
    return JSONResponse(
        content={
            "status": "started",
            "message": "Baseline generation started successfully",
        },
        headers={"Cache-Control": "no-cache"},
    )

# Endpoint to start baseline with memory unit
@router.post("/gen/start-memory")
async def start_memory_generation(request: Request):
    """
    Memory-based generation workflow.
    Body: job_id, callback_url, index_id, prompts (list of strings), duration, voice.
    Each prompt is used as the retrieval query for that doc; a running summary of previous
    docs is added as memory when generating each subsequent doc.
    """
    payload = await request.json()
    try:
        params = validate_baseline_payload(payload)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    # await generate_content_memory_background_task(params, claude_client)
    asyncio.create_task(generate_content_memory_background_task(params, claude_client))
    return JSONResponse(
        content={
            "status": "started",
            "message": "Memory-based generation started successfully",
        },
        headers={"Cache-Control": "no-cache"},
    )
