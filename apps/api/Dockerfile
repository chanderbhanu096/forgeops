# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry and configure it to export requirements
RUN pip install --no-cache-dir poetry==1.8.3
COPY pyproject.toml ./
# Generate a lockfile if one does not exist, then export to requirements.txt
# so the final image does not need Poetry at runtime.
RUN poetry lock --no-update 2>/dev/null || poetry lock && \
    poetry export --only main --without-hashes -f requirements.txt -o requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Runtime system deps (no compiler needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages from the exported requirements
COPY --from=builder /app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Health check uses stdlib only — no curl required
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

EXPOSE 8000

# Run database migrations then start
CMD ["sh", "-c", "alembic upgrade head && uvicorn forgeops.app:app --host 0.0.0.0 --port 8000 --workers 2"]
