# ---- Build stage ----
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build tools
RUN pip install --no-cache-dir hatchling

# Copy dependency manifest first for layer caching
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install \
    fastapi==0.115.6 \
    uvicorn[standard]==0.32.1 \
    pydantic==2.10.3 \
    pydantic-settings==2.7.0 \
    sqlalchemy==2.0.36 \
    aiosqlite==0.20.0 \
    httpx==0.28.1 \
    greenlet \
    python-json-logger>=2.0.7

# ---- Runtime stage ----
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create non-root user
RUN addgroup --system app && adduser --system --ingroup app app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/

# Set ownership
RUN chown -R app:app /app

USER app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL="sqlite+aiosqlite:///./data/intuitive.db"

# Create data directory for SQLite persistence
RUN mkdir -p data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
