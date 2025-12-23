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
    # For hadolint (Dockerfile linter)
    ca-certificates \
    # For weasyprint PDF generation
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libcairo2 \
    libcairo2-dev \
    pkg-config \
    # For Node.js (jscpd)
    nodejs \
    npm \
    # For pycairo/xhtml2pdf build
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

# Install Python analysis tools globally (available for all analyses)
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

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
