# Document Evaluation Microservice

Evaluates ordered PDF document sequences using scaffolding + progression metrics. Accepts up to 10 PDFs via API.

## Install Required Packages

```bash
pip install -r requirements.txt
```

## Configuration

Ensure `.env` is configured (in project root or evaluator-service directory):

- **Azure OpenAI** (default): `AZURE_OPENAI_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`
- **OpenAI**: `OPENAI_API_KEY` (falls back if Azure not configured)

## Run Locally

```bash
cd evaluator_service
uvicorn main:app --reload --host 0.0.0.0 --port 8002
```

Or:

```bash
cd evaluator_service
python main.py
```

## API

- `GET /` — Health check
- `POST /evaluate` — Upload PDFs (max 10), returns:
  - `{"document_count": N, "metrics": {"scaffolding_connectivity_score": {...}, "concept_progression_velocity": {...}, "long_range_scaffolding_depth": {...}}}`

Example with curl:

```bash
curl -X POST "http://localhost:8002/evaluate" -F "files=@doc1.pdf" -F "files=@doc2.pdf"
```

## Docker

Build from the repo root (so `config/` is included):

```bash
docker build -f evaluator_service/Dockerfile -t eduflow-evaluator .
docker run --rm -p 8002:8002 --env-file evaluator_service/.env eduflow-evaluator
```
