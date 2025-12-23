# Stage 1: Build Next.js frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/ui

# Copy package files
COPY ui/package*.json ./

# Install dependencies
RUN npm ci --legacy-peer-deps

# Copy source code
COPY ui/ .

# Build static export
RUN npm run build

# Stage 2: Python backend with static files
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends git curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .
RUN mkdir -p /app/data

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/ui/out /app/static

# Test imports during build
RUN python -c "from app.main import app; print('Import OK!')"

EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
