"""Exporta ocorrências e relatórios de log para docs/relatorios/.

Uso:  .venv/bin/python scripts/exportar.py
Gera:
  docs/relatorios/ocorrencias-AAAA-MM-DD.json   (dados completos + relatórios)
  docs/relatorios/relatorio-AAAA-MM-DD.txt       (relatório legível de cada uma)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import report, storage  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "relatorios")


def main() -> None:
    storage.init_db()
    os.makedirs(OUT, exist_ok=True)
    today = date.today().isoformat()
    occs = storage.list_occurrences(1000)

    # JSON completo
    data = []
    for o in occs:
        rep = report.build_report(o.call_id)
        data.append(rep)
    json_path = os.path.join(OUT, f"ocorrencias-{today}.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, default=str)

    # Texto legível
    txt_path = os.path.join(OUT, f"relatorio-{today}.txt")
    with open(txt_path, "w", encoding="utf-8") as fh:
        fh.write(f"RELATÓRIO DE OCORRÊNCIAS — {today} — total: {len(occs)}\n\n")
        for rep in data:
            o = rep["occurrence"]
            fh.write(f"Ocorrência {o.get('occurrence_number')} | sev={o.get('severity')} "
                     f"| status={o.get('status')} | call_id={rep['call_id']}\n")
            falhas = [k for k, v in rep["checks"].items() if not v]
            fh.write(f"  checagens: {'tudo OK' if not falhas else 'falta ' + ', '.join(falhas)}\n")
            for s in rep["steps"]:
                mark = "OK " if s["entendeu"] else "-- "
                fh.write(f"  [{mark}] {s['pergunta'] or '(comando)':11} "
                         f"falou={s['falou']!r} -> {s['campo']}={s['valor']!r}\n")
            fh.write("\n")

    print(f"Salvo: {json_path}")
    print(f"Salvo: {txt_path}")


if __name__ == "__main__":
    main()
