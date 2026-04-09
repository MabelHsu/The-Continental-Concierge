# ============================================================
# Cloud Run: Custom World MCP Server + UI
# ============================================================
# Multi-stage build for the MCP server and optional frontend.

# ── Stage 1: Python MCP Server ────────────────────────────────
FROM python:3.12-slim AS mcp-server

WORKDIR /app

# Install dependencies
COPY requirements-mcp.txt .
RUN pip install --no-cache-dir -r requirements-mcp.txt

# Copy MCP server code
COPY mcp/custom_world_mcp/ ./mcp/custom_world_mcp/

# Expose SSE endpoint
EXPOSE 8080

ENV PORT=8080

CMD ["python", "-m", "mcp.custom_world_mcp.server"]


# ── Stage 2: Full stack (MCP + UI) ───────────────────────────
FROM python:3.12-slim AS full

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code
COPY app/ ./app/
COPY mcp/ ./mcp/
COPY ui/ ./ui/

# Build UI if present
RUN if [ -f ui/package.json ]; then \
        cd ui && npm install && npm run build; \
    fi

EXPOSE 8080

ENV PORT=8080

# Use gunicorn for production
CMD ["gunicorn", "app.server:app", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "120"]
