#!/usr/bin/env bash
# Teste ponta a ponta do atendimento via HTTP (simula a fala do cidadão).
# Requer o servidor no ar:  scripts/run.sh   (ou uvicorn em :8088)
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8088}"
PY="$(dirname "$0")/../.venv/bin/python"

FALAS=(
  "Bom dia, meu nome é João da Silva"
  "Estou sendo assaltado agora, tem um homem armado"
  "É pessoa física"
  "Avenida Paulista, CEP 01310-100, São Paulo"
  "Pode anotar 11 91234-5678"
  "Perto do MASP"
  "O homem está de camiseta preta, de moto, apontando a arma agora"
  "repetir os dados"
  "sim, pode encerrar"
)

CID=$(curl -s -X POST "$BASE/api/call/start" -H 'Content-Type: application/json' \
  -d '{"channel":"web"}' | "$PY" -c "import sys,json;print(json.load(sys.stdin)['call_id'])")
echo "call_id = $CID"
echo

for T in "${FALAS[@]}"; do
  echo "CIDADÃO: $T"
  curl -s -X POST "$BASE/api/call/turn" -H 'Content-Type: application/json' \
    -d "{\"call_id\":\"$CID\",\"text\":\"$T\"}" \
  | "$PY" -c "import sys,json;d=json.load(sys.stdin);print('   BOT:',d['reply'])"
done

echo
echo "=== Ocorrência final ==="
curl -s "$BASE/api/occurrences/$CID" | "$PY" -c "
import sys,json
o=json.load(sys.stdin)
for k in ('occurrence_number','caller_name','caller_type','nature','location_address','cep','city','location_state','caller_phone','location_reference','severity','responsible_agency','status'):
    print(f'  {k:20} {o.get(k)}')
"
