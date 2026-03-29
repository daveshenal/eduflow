"""FastAPI application entrypoint: CORS, routers, and optional uvicorn dev server."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.gen import router as gen_router
from app.routers.knowledgebase import router as kb_router
from app.routers.database import router as db_router
from config.log_config import configure_logging

configure_logging()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gen_router)
app.include_router(kb_router)
app.include_router(db_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
