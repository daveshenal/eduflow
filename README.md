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
hop-phoenix-ml/
├── app/                  # FastAPI application core
│   ├── adapters          # External services
│   ├── core/             # Application wide core logic
│   ├── evaluator/        # Evaluator service
│   ├── knowledgebase/    # Index management scripts
│   ├── pipeline/         # Main workflow pipelines
│   ├── prompts/          # Prompts management scripts
│   ├── retrievers/       # Data retrievers
│   ├── routes/           # API route definitions
│   └── main.py           # API entrypoint
├── config/               # Configuration files
├── docs/                 # Architecture diagrams and documentation
├── dummy-ui/             # User Interface
├── tests/                # Test cases
├── .gitignore
└── README.md
```
