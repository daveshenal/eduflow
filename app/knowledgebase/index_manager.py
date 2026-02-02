from fastapi import FastAPI, HTTPException
from app.knowledgebase.global_index import GlobalIndex
from app.knowledgebase.provider_index import ProviderIndex

app = FastAPI()

@app.post("/run-provider-indexing/{provider_id}")
def run_provider_indexing(provider_id: str):
    try:
        provider_index = ProviderIndex(provider_id=provider_id)
        provider_index.setup_complete_indexing_pipeline()
        return {"status": "success", "message": f"Provider index setup completed for provider_id={provider_id}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run-global-indexing")
def run_global_indexing():
    try:
        global_index = GlobalIndex()
        
        global_index.setup_complete_indexing_pipeline()
        return {"status": "success", "message": "Global index setup completed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)