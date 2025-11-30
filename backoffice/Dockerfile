FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Docker CLI
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    lsb-release \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    docker-ce-cli \
    docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY backoffice/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backoffice/backend/ ./

# Copy frontend
COPY backoffice/frontend/ ./frontend/

# Create directory structure for runtime data
RUN mkdir -p /app/runtime/agents \
    /app/runtime/agent-definitions \
    /app/runtime/compose \
    /app/runtime/workflows \
    /app/examples/agents \
    /app/examples/agent-definitions \
    /app/examples/compose \
    /app/examples/workflows

# Copy example files into the image
COPY examples/ /app/examples/

# Copy base agent template
COPY agents/ /app/base-agents/

# Copy docker-compose files (required for DeploymentManager)
COPY docker-compose*.yml ./

# Set project root to /app (inside container)
ENV PROJECT_ROOT=/app
ENV HOST_PROJECT_ROOT=/app
ENV STANDALONE_MODE=true

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

# Run the application
CMD ["python", "app.py"]
