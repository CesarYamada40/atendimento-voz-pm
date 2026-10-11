"""Relatório de log de uma ocorrência (auditoria ponta a ponta).

Uso:
  .venv/bin/python scripts/relatorio.py            # última ocorrência
  .venv/bin/python scripts/relatorio.py <call_id>  # uma ocorrência específica
  .venv/bin/python scripts/relatorio.py --all       # resumo de todas
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import report, storage  # noqa: E402

MARK = {True: "OK ", False: "FALTA"}


def _print_report(rep: dict) -> None:
    o = rep["occurrence"]
    print("=" * 78)
    print(f"OCORRÊNCIA {o.get('occurrence_number') or '(não gerada)'}  "
          f"call_id={rep['call_id']}")
    print(f"  status={o.get('status')}  gravidade={o.get('severity')}  "
          f"criada={o.get('created_at', '')[:19]}")
    print("-" * 78)

    print("CHECKLIST")
    for k, v in rep["checks"].items():
        print(f"  [{MARK[v]}] {k}")

    if rep["issues"]:
        print("\nPENDÊNCIAS / ALERTAS")
        for it in rep["issues"]:
            print(f"  - {it}")

    print("\nPASSO A PASSO (entendimento por pergunta)")
    for s in rep["steps"]:
        q = s["pergunta"] or "(comando)"
        mark = "OK " if s["entendeu"] else "-- "
        val = s["valor"] if s["valor"] is not None else ""
        print(f"  [{mark}] {q:11} falou={s['falou']!r}")
        if s["entendeu"]:
            print(f"        -> {s['campo']} = {val!r}")
        if s["gravidade"]:
            print(f"        -> GRAVIDADE {s['gravidade']}")

    print("\nDADOS FINAIS")
    for k in ("caller_name", "caller_type", "org_name", "nature",
              "location_address", "location_number", "location_neighborhood",
              "city", "location_state", "cep", "location_source",
              "location_confidence", "caller_phone", "location_reference",
              "severity", "severity_label", "responsible_agency",
              "occurrence_number", "status"):
        print(f"  {k:22} {o.get(k)!r}")
    print(f"  {'description':22} {o.get('description')!r}")
    print(f"  {'transcript':22} {(o.get('transcript') or '')[:400]!r}")
    print("=" * 78)


def main() -> None:
    storage.init_db()
    args = sys.argv[1:]

    if args and args[0] == "--all":
        occs = storage.list_occurrences(100)
        if not occs:
            print("Nenhuma ocorrência registrada.")
            return
        print(f"{'call_id':14} {'nº':12} {'sev':4} {'status':12} checagens")
        for o in occs:
            rep = report.build_report(o.call_id)
            falhas = [k for k, v in rep["checks"].items() if not v]
            print(f"{o.call_id:14} {str(o.occurrence_number):12} "
                  f"{str(o.severity and o.severity.value):4} {o.status:12} "
                  f"{'tudo OK' if not falhas else 'falta: ' + ', '.join(falhas)}")
        return

    call_id = args[0] if args else None
    if not call_id:
        occs = storage.list_occurrences(1)
        if not occs:
            print("Nenhuma ocorrência registrada.")
            return
        call_id = occs[0].call_id

    rep = report.build_report(call_id)
    if not rep:
        print(f"Ocorrência {call_id} não encontrada.")
        return
    _print_report(rep)


if __name__ == "__main__":
    main()
