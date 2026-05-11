# [CERTIFICATION GRADE]: Standardized Industrial Environment
FROM python:3.11-slim

# Install system dependencies for Spacy, PDF processing (fitz), and Redis client
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libmupdf-dev \
    swig \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# [LAYER CACHING]: Install dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# [LINGUISTIC MODELS]: Download Spacy model for PII analysis
RUN python -m spacy download en_core_web_lg

# Copy application source
COPY . .

# [EXPOSURE]: Standard API port
EXPOSE 8000

# Entrypoint is handled by docker-compose (uvicorn vs celery)
