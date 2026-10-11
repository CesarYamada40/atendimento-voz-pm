"""Testes da resolução de local (CEP/rua) e do órgão responsável.

A rede é mockada no conftest (fixture autouse). Aqui testamos a lógica.
"""
import asyncio

from app import location

GEO_SP = location.GeoResult(
    raw="", resolved=True, cep="01310100", street="Avenida Paulista",
    neighborhood="Bela Vista", city="São Paulo", state="SP",
    lat=-23.5475, lng=-46.63611, display="Avenida Paulista, Bela Vista, São Paulo/SP",
    source="brasilapi", confidence="alta")


def test_find_cep_variacoes():
    assert location.find_cep("meu cep é 01310-100") == "01310100"
    assert location.find_cep("CEP 70040010") == "70040010"
    assert location.find_cep("sem cep aqui") is None


def test_find_cep_com_separadores_irregulares():
    assert location.find_cep("meu cep 08.526-060") == "08526060"
    assert location.find_cep("08526 060") == "08526060"
    assert location.find_cep("08526-060") == "08526060"


def test_telefone_nao_vira_cep():
    assert location.find_cep("meu telefone 11 91234-5678") is None


def test_resolve_cep_valido():
    geo = asyncio.run(location.resolve("01310-100"))
    assert geo.resolved
    assert geo.cep == "01310100"
    assert geo.city == "São Paulo"
    assert geo.state == "SP"
    assert geo.source == "brasilapi"
    assert geo.confidence == "alta"
    assert geo.lat is not None and geo.lng is not None


def test_resolve_cep_inexistente_nao_inventa():
    geo = asyncio.run(location.resolve("99999999"))
    assert geo.resolved is False
    assert geo.source == "nao_resolvido"
    assert geo.confidence == "baixa"


def test_resolve_rua_via_nominatim(monkeypatch):
    async def fake_nominatim(query):
        return location.GeoResult(
            raw=query, resolved=True, street="Avenida Paulista", number="1578",
            city="São Paulo", state="SP", lat=-23.56, lng=-46.65,
            display="Avenida Paulista 1578", source="nominatim", confidence="media")

    monkeypatch.setattr(location, "_nominatim", fake_nominatim)
    geo = asyncio.run(location.resolve("Avenida Paulista 1578"))
    assert geo.resolved
    assert geo.source == "nominatim"
    assert geo.city == "São Paulo"


def test_orgao_responsavel_pm():
    agency = location.responsible_agency(GEO_SP, "crime_em_andamento", "G1")
    assert "Polícia Militar" in agency
    assert "apoio" in agency  # G1/G2 pede apoio


def test_orgao_responsavel_aciona_samu():
    agency = location.responsible_agency(GEO_SP, "acidente com feridos", "G2")
    assert "SAMU" in agency
