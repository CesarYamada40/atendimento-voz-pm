#!/usr/bin/env bash
# Sobe um túnel HTTPS público para acessar o atendimento de qualquer dispositivo
# (tablet/celular). Imprime a URL no final. Requer o servidor em :8088.
set -euo pipefail
PORT="${VOZ_PORT:-8088}"
LOG="/tmp/cf-${PORT}.log"
pkill -f "cloudflared.*127.0.0.1:${PORT}" 2>/dev/null || true
setsid cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:${PORT}" \
  >"$LOG" 2>&1 </dev/null &
for _ in $(seq 1 15); do
  URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$LOG" | head -1 || true)
  [ -n "${URL:-}" ] && break
  sleep 1
done
echo "Atendimento: ${URL:-<não obtida, veja $LOG>}"
echo "Painel:      ${URL:-?}/dashboard"
