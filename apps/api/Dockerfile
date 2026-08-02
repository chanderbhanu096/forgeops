FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.8.4 && poetry config virtualenvs.create false

# Install dependencies first (layer caching)
COPY pyproject.toml poetry.lock* ./
RUN poetry install --only main --no-root

# Copy source
COPY . .

# Run database migrations then start
CMD ["sh", "-c", "alembic upgrade head && uvicorn forgeops.app:app --host 0.0.0.0 --port 8000 --workers 2"]
