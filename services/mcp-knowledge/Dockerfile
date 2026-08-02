FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" asyncpg "sqlalchemy[asyncio]" pgvector pydantic structlog rank-bm25
COPY main.py .
EXPOSE 8003
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
