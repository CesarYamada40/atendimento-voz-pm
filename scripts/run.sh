#!/usr/bin/env bash
# Sobe a Central de Atendimento por Voz em background (persistente).
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${VOZ_PORT:-8088}"
mkdir -p logs
setsid .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$PORT" \
  >logs/servidor.log 2>&1 </dev/null &
echo "PID $! — logs em logs/servidor.log — http://127.0.0.1:$PORT/"
