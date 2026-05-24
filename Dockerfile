# ── Stage 1: Build Next.js frontend ──────────────────────────────────────────
# node:20-slim = Debian Bookworm slim — same libc as python:3.11-slim below
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./

# Empty string = relative URLs → nginx routes them to FastAPI on same host
ENV NEXT_PUBLIC_API_URL=""
RUN npm run build

# ── Stage 2: Combined runtime ─────────────────────────────────────────────────
FROM python:3.11-slim

# System packages: nginx + supervisor only (Node comes from build stage below)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy Node.js binary from build stage (both Debian Bookworm — compatible glibc)
COPY --from=frontend-builder /usr/local/bin/node /usr/local/bin/node

# ── Python backend ─────────────────────────────────────────────────────────────
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .

# ── Next.js standalone ─────────────────────────────────────────────────────────
WORKDIR /app/frontend
COPY --from=frontend-builder /app/frontend/.next/standalone ./
COPY --from=frontend-builder /app/frontend/.next/static  ./.next/static
COPY --from=frontend-builder /app/frontend/public        ./public

# ── Config files ───────────────────────────────────────────────────────────────
COPY nginx.conf       /etc/nginx/sites-available/default
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# HuggingFace Spaces requires port 7860
EXPOSE 7860

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
