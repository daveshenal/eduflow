FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy requirements first for better layer caching.
# IMPORTANT: Build with repo root as context:
#   docker build -f evaluator_service/Dockerfile -t eduflow-evaluator .
COPY evaluator_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the evaluator service and shared config it imports.
COPY evaluator_service ./evaluator_service
COPY config ./config

EXPOSE 8002

CMD ["uvicorn", "evaluator_service.main:app", "--host", "0.0.0.0", "--port", "8002"]
