from typing import List
from fastapi import APIRouter, HTTPException

from app.adapters.azure_sql import get_db_connection, create_tables, clear_all_huddle_jobs

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


@router.delete("/huddle_jobs/clear", summary="Clear all huddle jobs")
async def api_clear_all_huddle_jobs():
    try:
        deleted_count = await clear_all_huddle_jobs()
        return {"success": True, "deleted_jobs": deleted_count}
    except Exception as e:
        # Optional: log the error here
        raise HTTPException(status_code=500, detail=f"Failed to clear jobs: {str(e)}")


 
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