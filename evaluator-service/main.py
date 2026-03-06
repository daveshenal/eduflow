"""
Start FastAPI application
Import FastAPI and evaluation router
Create FastAPI app
Register router
Run application
"""

# Import FastAPI
from fastapi import FastAPI

# Import evaluation router from routes.evaluate
from routes.evaluate import router as evaluate_router

# Create FastAPI app
app = FastAPI(
    title="Document Evaluation Service",
    description="Evaluate PDF documents using coherence and other metrics.",
    version="1.0.0",
)

# Register router with app
app.include_router(evaluate_router)


@app.get("/")
def root():
    """Health check / root endpoint."""
    return {"status": "ok", "service": "document-evaluation"}


@app.get("/health")
def health():
    """Health check for deployment."""
    return {"status": "healthy"}


if __name__ == "__main__":
    # Run application
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
