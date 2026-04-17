# EduFlow RAG System

AI-powered retrieval and content generation platform for micro-learning workflows.

## What EduFlow Does

- Ingests and indexes knowledgebase documents
- Retrieves relevant context for generation tasks
- Generates learning content in multiple formats (for example PDF and voice assets)
- Supports chatbot streaming, background generation jobs, and prompt versioning

## Tech Stack

- Backend: FastAPI
- AI/Orchestration: OpenAI + Anthropic integrations, LangChain
- Storage/Search: Azure Blob Storage + Azure AI Search
- Data layer: Azure SQL (background jobs + prompt management)
- Frontend: `dummy-ui` (served separately)

## Project Structure

```text
eduflow/
├── app/                    # FastAPI application core
│   ├── adapters/           # External service adapters (Azure, model clients, etc.)
│   ├── core/               # Shared application logic
│   ├── knowledgebase/      # Indexing and document processing logic
│   ├── pipelines/          # Generation and chat workflow pipelines
│   ├── prompts/            # Prompt models and management services
│   ├── retrievers/         # Retrieval helpers
│   ├── routers/            # API route definitions
│   └── main.py             # API entrypoint
├── config/                 # Configuration and logging setup
├── docs/                   # Architecture diagrams and documentation
├── dummy-ui/               # Frontend app
├── evaluator_service/      # Evaluator microservice
├── tests/                  # Test suite
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.10+ (recommended)
- Docker Desktop (optional, for containerized run)
- Azure resources configured for Blob/Search/SQL
- A populated `.env` file in the project root

### Option 1: Run with Docker Compose

```bash
docker compose up --build
```

- Backend API: `http://localhost:8000`
- Frontend UI: `http://localhost:3000`

### Option 2: Run backend locally

```bash
python -m venv .venv
```

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Overview

### Generation and Chat

- `POST /chat/stream` - stream chatbot responses using a selected index
- `POST /gen/start` - start background content generation
- `POST /gen/start-baseline` - start baseline generation flow
- `POST /gen/start-memory` - start memory-based generation flow
- `POST /gen/start-test` - trigger test generation flow

### Knowledgebase

- `POST /run-ai-indexing/{index_id}` - provision indexing pipeline artifacts
- `POST /knowledgebase/{index_id}/upload` - upload and index documents
- `DELETE /knowledgebase/{index_id}/documents` - delete indexed docs by filename
- `DELETE /index/{index_id}` - remove index artifacts and related container
- `GET /blobs` - list blobs by container/prefix
- `GET /test-blob-connection` - test Blob connectivity

### Background Jobs and Prompt Management

- `GET /bg_jobs` and `GET /bg_jobs/{job_id}` - inspect generation job state/results
- `DELETE /bg_jobs/clear` - clear background jobs
- `POST /init-tables` - initialize prompt tables
- `GET /prompts/*`, `POST /prompts/new`, `POST /prompts/activate`, `PUT/DELETE /prompts/...` - prompt lifecycle APIs

## Development Notes

- CORS is currently open (`allow_origins=["*"]`) in `app/main.py` for development flexibility.
- `requirements.txt` includes `weasyprint`; on Windows, if install issues occur, reinstall `cffi` and `fonttools` as noted in the file.
