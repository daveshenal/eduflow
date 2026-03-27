# EduFlow RAG System

**AI-powered retrieval and generation for micro-education**

## Key Components

1. **Data Pipeline**
2. **Retrieval System**
3. **Generation System**
   - General Chatbot
   - Creates micro-learning modules
   - Supports multiple output formats (PDF+voice, assessments)

## Project Structure

```text
eduflow/
├── app/                  # FastAPI application core
│   ├── adapters          # External services
│   ├── core/             # Application wide core logic
│   ├── knowledgebase/    # Index management scripts
│   ├── pipelines/        # Main workflow pipelines
│   ├── prompts/          # Prompts management scripts
│   ├── retrievers/       # Data retrievers
│   ├── routers/          # API route definitions
│   └── main.py           # API entrypoint
├── config/               # Configuration files
├── docs/                 # Architecture diagrams and documentation
├── dummy-ui/             # User Interface
├── evaluator_service     # Evaluator micro service (Local API)
├── tests/                # Test cases
├── .gitignore
└── README.md
```
