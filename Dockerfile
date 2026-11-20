# syntax=docker/dockerfile:1
# Single-service image for SentinelGate AI: builds the React/Vite frontend, then
# serves it together with the FastAPI API from one Uvicorn process.

# ---- Stage 1: build the React + Vite production bundle ----
FROM node:20-slim AS frontend
WORKDIR /frontend
# Install dependencies first (cached unless the lockfile changes).
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
# Copy the rest of the frontend source and build. frontend/.env.production
# (VITE_API_BASE_URL=/) makes the bundle call the API with relative URLs.
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: FastAPI backend serving the built frontend ----
FROM python:3.12-slim AS backend
WORKDIR /app
# Install backend dependencies (cached unless requirements change).
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Backend application code.
COPY backend/app ./app
# Built frontend assets into the directory FastAPI serves (FRONTEND_DIST).
COPY --from=frontend /frontend/dist ./frontend/dist

ENV FRONTEND_DIST=/app/frontend/dist \
    DATABASE_PATH=/app/data/sentinelgate.db \
    ENABLE_HF_CLASSIFIER=false \
    PORT=8000
RUN mkdir -p /app/data
EXPOSE 8000
# Render provides $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
