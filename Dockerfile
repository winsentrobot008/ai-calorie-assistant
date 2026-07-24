# ============================================
# AI Calorie Assistant — Multi-stage Dockerfile
# ============================================

# ─── Stage 1: Build Frontend ───
FROM node:20-alpine AS frontend-builder

WORKDIR /app/webapp
COPY webapp/package.json webapp/package-lock.json* ./
RUN npm ci

COPY webapp/ .
RUN npm run build

# ─── Stage 2: Backend + Serve ───
FROM python:3.12-slim

WORKDIR /app

# Install ffmpeg (for image processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy backend source
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/webapp/dist /app/webapp/dist

# Expose port
EXPOSE 8000

# Environment variables (override at runtime)
ENV AI_API_BASE_URL=https://api.lk888.ai/api
ENV AI_API_KEY=""
ENV VITE_API_URL=http://localhost:8000

# Start backend (FastAPI)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
