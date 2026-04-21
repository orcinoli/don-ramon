FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY don_ramon/ ./don_ramon/

RUN pip install --no-cache-dir -e .

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

VOLUME ["/root/.don-ramon"]

ENTRYPOINT ["dr"]
CMD ["--help"]
