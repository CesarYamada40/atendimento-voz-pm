"""Configuração dos testes: ambiente isolado, DB temporário, LLM desligado,
e rede (CEP/geocode) mockada para testes rápidos e determinísticos.
"""
from __future__ import annotations

import asyncio
import os
import tempfile

# Precisa vir ANTES de importar app.*
os.environ["VOZ_LLM_ENABLED"] = "false"
_TMP = tempfile.mkdtemp(prefix="voz-test-")
os.environ["VOZ_DB_PATH"] = os.path.join(_TMP, "test.db")

import pytest  # noqa: E402

from app import agent, location, storage  # noqa: E402

FAKE_GEO = location.GeoResult(
    raw="", resolved=True, cep="01310100", street="Avenida Paulista",
    neighborhood="Bela Vista", city="São Paulo", state="SP",
    lat=-23.5475, lng=-46.63611,
    display="Avenida Paulista, Bela Vista, São Paulo/SP",
    source="brasilapi", confidence="alta",
)


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    """DB limpo, sessões limpas e rede mockada em todos os testes."""
    storage.init_db()
    conn = storage._connect()
    conn.execute("DELETE FROM occurrences")
    conn.execute("DELETE FROM turns")
    conn.commit()
    agent._sessions.clear()

    async def fake_brasilapi(cep: str):
        return FAKE_GEO if cep == "01310100" else None

    async def fake_viacep(cep: str):
        return None

    async def fake_nominatim(query: str):
        return None

    async def fake_viacep_busca(uf: str, city: str, street: str):
        if "flores" in street.lower():
            return [{"cep": "49015-110", "logradouro": "Rua das Flores",
                     "bairro": "Centro", "localidade": "Aracaju", "uf": "SE"}]
        return []

    monkeypatch.setattr(location, "_brasilapi_cep", fake_brasilapi)
    monkeypatch.setattr(location, "_viacep", fake_viacep)
    monkeypatch.setattr(location, "_nominatim", fake_nominatim)
    monkeypatch.setattr(location, "_viacep_busca", fake_viacep_busca)
    yield


def run_call(falas):
    """Executa uma ligação completa (lista de falas) e devolve (start, último)."""
    start = agent.start_call(agent.CallStartRequest(channel="web"))
    last = None
    for fala in falas:
        last = asyncio.run(agent.process_turn(
            agent.TurnRequest(call_id=start.call_id, text=fala)))
    return start, last


@pytest.fixture
def run():
    return run_call


@pytest.fixture
def turn():
    """Envia uma fala avulsa para uma ligação existente."""
    def _turn(call_id: str, text: str):
        return asyncio.run(agent.process_turn(
            agent.TurnRequest(call_id=call_id, text=text)))
    return _turn
