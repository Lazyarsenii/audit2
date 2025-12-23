# Repo Auditor Backend Dockerfile
# Full-featured image with ALL analysis tools
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    ca-certificates \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libcairo2 \
    libcairo2-dev \
    pkg-config \
    nodejs \
    npm \
    gcc \
    clang \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install hadolint (Dockerfile linter)
RUN wget -O /usr/local/bin/hadolint \
    https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-x86_64 \
    && chmod +x /usr/local/bin/hadolint

# Install jscpd (code duplication detector)
RUN npm install -g jscpd

# Install Python analysis tools globally
RUN pip install --no-cache-dir \
    semgrep \
    bandit \
    safety \
    radon \
    vulture \
    pip-licenses \
    pipdeptree

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create temp directory for cloning repos
RUN mkdir -p /tmp/repo-auditor-clones

# Create non-root user
RUN useradd --create-home appuser \
    && chown -R appuser:appuser /app \
    && chown -R appuser:appuser /tmp/repo-auditor-clones
USER appuser

# Expose port (Railway assigns dynamic PORT)
EXPOSE 8000

# Run application - uses PORT env var from Railway
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
