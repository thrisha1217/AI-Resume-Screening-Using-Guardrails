#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh — Run this on the EC2 instance to deploy the application
# Usage: bash deploy.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

APP_DIR="/opt/resume-screening"
DOMAIN="${DOMAIN:-resume.yourdomain.com}"

echo "======================================================"
echo " Resume Screening System — Deployment Script"
echo "======================================================"

# ── 1. Pull latest code ────────────────────────────────────────────────────────
echo "[1/6] Pulling latest code..."
cd $APP_DIR
git pull origin main 2>/dev/null || echo "  (no git repo — using local files)"

# ── 2. Stop existing containers ────────────────────────────────────────────────
echo "[2/6] Stopping existing containers..."
docker compose down --remove-orphans 2>/dev/null || true

# ── 3. Build images ────────────────────────────────────────────────────────────
echo "[3/6] Building Docker images..."
docker compose build --no-cache

# ── 4. Start services ──────────────────────────────────────────────────────────
echo "[4/6] Starting services..."
docker compose up -d

# ── 5. Wait for Ollama and pull model ─────────────────────────────────────────
echo "[5/6] Waiting for Ollama to be ready..."
until docker compose exec -T ollama curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
    echo "  Waiting for Ollama..."
    sleep 5
done
echo "  Ollama ready. Pulling qwen2.5:3b model..."
docker compose exec -T ollama ollama pull qwen2.5:3b
echo "  Model pulled."

# ── 6. Health check ────────────────────────────────────────────────────────────
echo "[6/6] Running health checks..."
sleep 10

BACKEND_HEALTH=$(curl -sf http://localhost:8000/api/health 2>/dev/null || echo "FAIL")
FRONTEND_HEALTH=$(curl -sf http://localhost/health 2>/dev/null || echo "FAIL")

echo ""
echo "======================================================"
echo " Deployment Status"
echo "======================================================"
echo "  Backend  : $BACKEND_HEALTH"
echo "  Frontend : $FRONTEND_HEALTH"
echo "  App URL  : http://$DOMAIN"
echo "======================================================"

if [[ "$BACKEND_HEALTH" == *"ok"* ]] && [[ "$FRONTEND_HEALTH" == *"healthy"* ]]; then
    echo "  ✅ Deployment successful!"
else
    echo "  ❌ Health check failed. Check logs:"
    echo "     docker compose logs backend"
    echo "     docker compose logs frontend"
    exit 1
fi
