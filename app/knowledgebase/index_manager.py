"""Standalone FastAPI app for AI index management."""

from fastapi import FastAPI, HTTPException
from app.knowledgebase.ai_index import AIIndex

app = FastAPI()

@app.post("/run-ai-indexing/{provider_id}")
def run_ai_indexing(provider_id: str):
    """Set up AI indexing pipeline for the given provider."""
    try:
        ai_index = AIIndex(index_id=provider_id)
        ai_index.setup_complete_indexing_pipeline()
        return {"status": "success", "message": f"AI index setup completed for provider_id={provider_id}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
