FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required by WeasyPrint, cairo, gobject, etc.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libglib2.0-0 \
        libffi-dev \
        shared-mime-info \
        ffmpeg \
        wget \
    && rm -rf /var/lib/apt/lists/*

# Download MySQL SSL certificate
RUN mkdir -q /app/certs && \
    wget -q https://www.digicert.com/CACerts/DigiCertGlobalRootCA.crt.pem -O /app/certs/DigiCertGlobalRootCA.crt.pem

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8000

# Runs Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]