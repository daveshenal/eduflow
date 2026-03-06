# Document Evaluation Microservice

Evaluates PDF documents using metrics such as coherence. Accepts up to 10 PDFs via API.

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
cd evaluator-service
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or:

```bash
cd evaluator-service
python main.py
```

## API

- `GET /` — Health check
- `POST /evaluate` — Upload PDFs (max 10), returns `{"document_count": N, "metrics": {"coherence": 0.82}}`

Example with curl:

```bash
curl -X POST "http://localhost:8000/evaluate" -F "files=@doc1.pdf" -F "files=@doc2.pdf"
```
