"""Demo do fluxo completo sem navegador (útil para testar o backend).

Uso:  .venv/bin/python scripts/demo_fluxo.py

Simula a fala do cidadão turno a turno, mostra a resposta do bot, a
resolução de local (CEP/rua) e a classificação de gravidade.
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("VOZ_LLM_ENABLED", "false")

from app import agent, storage  # noqa: E402
from app.schemas import CallStartRequest, TurnRequest  # noqa: E402

FALAS = [
    "Bom dia, meu nome é João da Silva",
    "Estou sendo assaltado agora, tem um homem armado",
    "É pessoa física mesmo",
    "Avenida Paulista, CEP 01310-100, São Paulo",
    "Pode anotar 11 91234-5678",
    "Perto do MASP",
    "O homem está de camiseta preta, de moto, e está apontando a arma para as pessoas agora",
    "repetir os dados",
    "sim, pode encerrar",
]


async def main() -> None:
    storage.init_db()
    start = agent.start_call(CallStartRequest(channel="web"))
    print(f"[BOT ] {start.greeting}\n")
    call_id = start.call_id
    for fala in FALAS:
        print(f"[CID ] {fala}")
        resp = await agent.process_turn(TurnRequest(call_id=call_id, text=fala))
        print(f"[BOT ] {resp.reply}")
        o = resp.occurrence
        if o.location_source:
            print(f"      -> local resolvido via {o.location_source}: {o.location_address} "
                  f"| CEP {o.cep} | {o.city}/{o.location_state} "
                  f"| ({o.location_lat},{o.location_lng})")
        if resp.classification:
            print(f"      -> GRAVIDADE {resp.classification.severity.value} "
                  f"({resp.classification.label}) score={resp.classification.score}")
            print(f"      -> {o.responsible_agency}")
        if resp.human_handoff:
            print("      -> HANDOFF para despachante humano")
        print()
        if resp.finished:
            break


if __name__ == "__main__":
    asyncio.run(main())
