# HOP RAG System

**AI-powered retrieval and generation for micro-education in healthcare compliance**

## Overview
A Retrieval-Augmented Generation (RAG) system designed to:
- Transform regulatory guidelines, medical knowledge, and performance data into targeted micro-learning content
- Deliver personalized training for home health clinicians
- Address compliance risks through AI-driven education

## Key Components
1. **Data Pipeline**
   - Ingests regulatory documents (CMS, Medicare standards)
   - Processes clinical protocols and agency-specific performance data

2. **Retrieval System**
   - Semantic search across compliance documents
   - Role/discipline-specific content filtering

3. **Generation System**
   - General Chatbot
   - Creates micro-learning modules (Huddles)
   - Supports multiple output formats (PDF+voice, assessments)

## First-Time Setup
### Prerequisites:
- Docker and Docker Compose installed  
- Azure Services credentials (for embedding, search, storage access)

```bash
git clone https://github.com/HOP-Into-Homecare/hop-phoenix-ml.git
```
```bash
cd hop-phoenix-ml
```
```bash
docker-compose up --build
```

## How To RUN
From inside hop-phoenix-ml, run
```bash
docker-compose up
```
Open the local URL
```bash
http://localhost:3000
```

## Project Structure
```text
hop-phoenix-ml/
├── app/                  # FastAPI application core
│   ├── main.py           # API entrypoint
│   ├── core/             # Application-wide core logic
│   ├── prompts/          # Multiple prompts
│   ├── routes/           # API route definitions
│   ├── services/         # Embedding, retrieval, LLM logic
│   └── utils/            # Helper functions and utilities
├── config/               # Configuration files
├── docs/                 # Architecture diagrams and documentation
├── dummy-ui/             # Frontend placeholder (HTML, CSS, JS)
├── notebooks/            # Jupyter notebooks
├── scripts/              # Project automation scripts
├── tests/                # Test cases for services and APIs
├── .env.sample           # Example env vars for setup
├── .gitignore
├── create_req_txt.py
├── docker-compose.yml
├── Dockerfile
├── README.md
└── requirements.txt
```

## Contact
Dave Perera: dave@silverlineit.co
