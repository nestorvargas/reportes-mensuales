#!/usr/bin/env bash
# start.sh — Levanta el entorno completo de Complemento 360
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# ── 1. Base de datos ──────────────────────────────────────────────────────
echo "▶ Levantando PostgreSQL..."
docker compose -f "$ROOT/docker-compose.yml" up -d
echo "  Esperando que la BD esté lista..."
until docker compose -f "$ROOT/docker-compose.yml" exec -T db pg_isready -U c360 -d complemento360 &>/dev/null; do
  sleep 1
done
echo "  BD lista."

# ── 2. Backend ────────────────────────────────────────────────────────────
echo "▶ Iniciando backend (puerto 8007)..."
if [ ! -f "$BACKEND/.venv/bin/uvicorn" ]; then
  echo "  Creando virtualenv..."
  python3 -m venv "$BACKEND/.venv"
  "$BACKEND/.venv/bin/pip" install -q -r "$BACKEND/requirements.txt"
fi
"$BACKEND/.venv/bin/uvicorn" main:app --reload --port 8007 --app-dir "$BACKEND" &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

# ── 3. Frontend ───────────────────────────────────────────────────────────
echo "▶ Iniciando frontend (puerto 5179)..."
if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "  Instalando dependencias npm..."
  npm --prefix "$FRONTEND" install
fi
npm --prefix "$FRONTEND" run dev &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"

# ── 4. URLs ───────────────────────────────────────────────────────────────
echo ""
echo "  App:     http://localhost:5179"
echo "  API:     http://localhost:8007/docs"
echo ""
echo "  Presiona Ctrl+C para detener todo."

# Esperar y propagar señal de parada a los procesos hijos
trap "echo ''; echo 'Deteniendo...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait $BACKEND_PID $FRONTEND_PID
