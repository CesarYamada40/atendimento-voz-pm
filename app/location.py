"""Resolução de local (CEP/rua/referência) e roteamento do órgão responsável.

Fontes gratuitas, sem chave:
  - CEP        -> BrasilAPI v2 (endereço + coordenadas + IBGE)
  - Rua/nome   -> Nominatim / OpenStreetMap (geocodificação)
  - CEP fallback -> ViaCEP (endereço sem coordenadas)

O objetivo: transformar "meu CEP é 70040-010" ou "na Avenida Paulista 1578"
em um endereço estruturado + coordenadas + órgão/viatura responsável.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, asdict
from typing import Optional
from urllib.parse import quote

import httpx

log = logging.getLogger("voz.location")

UA = {"User-Agent": "atendimento-voz-pm/0.1 (piloto PM; contato: operador@local)"}
CEP_RE = re.compile(r"\b(\d{5})-?(\d{3})\b")

# Mapa configurável de batalhões por município/UF (opcional).
_BATALHOES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               "data", "batalhoes.json")


@dataclass
class GeoResult:
    raw: str
    resolved: bool = False
    cep: Optional[str] = None
    street: Optional[str] = None
    number: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    ibge: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    display: Optional[str] = None
    source: Optional[str] = None
    confidence: str = "baixa"   # alta | media | baixa


def find_cep(text: str) -> Optional[str]:
    """Encontra um CEP mesmo com separadores (08.526-060, 08526 060, 08526-060)."""
    t = text or ""
    t2 = re.sub(r"(?<=\d)[.\s]+(?=\d)", "", t)   # remove pontos/espaços entre dígitos
    t2 = re.sub(r"(?<=\d)-(?=\d)", "", t2)       # remove hífen entre dígitos
    m = re.search(r"\b(\d{8})\b", t2)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d{5})-?(\d{3})\b", t)
    return f"{m.group(1)}{m.group(2)}" if m else None


def _load_batalhoes() -> dict:
    if os.path.exists(_BATALHOES_PATH):
        try:
            with open(_BATALHOES_PATH, encoding="utf-8") as fh:
                return json.load(fh)
        except (ValueError, OSError):
            log.warning("batalhoes.json inválido; ignorado")
    return {}


async def _brasilapi_cep(cep: str) -> Optional[GeoResult]:
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"https://brasilapi.com.br/api/cep/v2/{cep}", headers=UA)
            if r.status_code != 200:
                return None
            d = r.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("BrasilAPI falhou (%s)", exc)
        return None
    loc = (d.get("location") or {}).get("coordinates") or {}
    return GeoResult(
        raw=cep, resolved=True, cep=d.get("cep"), street=d.get("street"),
        neighborhood=d.get("neighborhood"), city=d.get("city"), state=d.get("state"),
        ibge=(d.get("ibge") or {}).get("city"),
        lat=float(loc["latitude"]) if loc.get("latitude") else None,
        lng=float(loc["longitude"]) if loc.get("longitude") else None,
        display=f"{d.get('street','')}, {d.get('neighborhood','')}, "
                f"{d.get('city','')}/{d.get('state','')}".strip(", "),
        source="brasilapi", confidence="alta",
    )


async def _viacep(cep: str) -> Optional[GeoResult]:
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"https://viacep.com.br/ws/{cep}/json/", headers=UA)
            if r.status_code != 200:
                return None
            d = r.json()
            if d.get("erro"):
                return None
    except Exception as exc:  # noqa: BLE001
        log.warning("ViaCEP falhou (%s)", exc)
        return None
    return GeoResult(
        raw=cep, resolved=True, cep=d.get("cep", "").replace("-", ""),
        street=d.get("logradouro"), neighborhood=d.get("bairro"),
        city=d.get("localidade"), state=d.get("uf"), ibge=d.get("ibge"),
        display=f"{d.get('logradouro','')}, {d.get('bairro','')}, "
                f"{d.get('localidade','')}/{d.get('uf','')}".strip(", "),
        source="viacep", confidence="media",
    )


async def _nominatim(query: str) -> Optional[GeoResult]:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "jsonv2", "countrycodes": "br",
                        "addressdetails": 1, "limit": 1},
                headers=UA,
            )
            if r.status_code != 200:
                return None
            data = r.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("Nominatim falhou (%s)", exc)
        return None
    if not data:
        return None
    hit = data[0]
    addr = hit.get("address", {})
    return GeoResult(
        raw=query, resolved=True, cep=(addr.get("postcode") or "").replace("-", "") or None,
        street=addr.get("road"), number=addr.get("house_number"),
        neighborhood=addr.get("suburb") or addr.get("neighbourhood"),
        city=addr.get("city") or addr.get("town") or addr.get("municipality"),
        state=addr.get("state"), lat=float(hit["lat"]), lng=float(hit["lon"]),
        display=hit.get("display_name"), source="nominatim", confidence="media",
    )


async def _viacep_busca(uf: str, city: str, street: str) -> list:
    """Busca CEP(s) por UF/cidade/logradouro (ViaCEP) — endereço -> CEP."""
    url = f"https://viacep.com.br/ws/{quote(uf)}/{quote(city)}/{quote(street)}/json/"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, headers=UA)
            if r.status_code != 200:
                return []
            data = r.json()
            return data if isinstance(data, list) else []
    except Exception as exc:  # noqa: BLE001
        log.warning("ViaCEP busca falhou (%s)", exc)
        return []


async def resolve_address(uf: Optional[str], city: Optional[str], street: Optional[str],
                          bairro: Optional[str] = None) -> GeoResult:
    """Descobre rua canônica + CEP a partir de rua/bairro/cidade/UF (ViaCEP)."""
    raw = ", ".join(x for x in [street, bairro, city, uf] if x)
    uf = parse_uf(uf) or uf
    if not (uf and city and street) or len(uf) != 2 or len(city) < 3 or len(street) < 3:
        return GeoResult(raw=raw, resolved=False, source="nao_resolvido", confidence="baixa")

    items = await _viacep_busca(uf, city, street)
    if not items:
        return GeoResult(raw=raw, resolved=False, display=raw, source="nao_resolvido",
                         confidence="baixa")

    def score(it: dict) -> int:
        s = 0
        if bairro and _norm_uf(bairro) and _norm_uf(bairro) in _norm_uf(it.get("bairro", "")):
            s += 2
        if _norm_uf(street) and _norm_uf(street) in _norm_uf(it.get("logradouro", "")):
            s += 1
        return s

    best = max(items, key=score)
    return GeoResult(
        raw=raw, resolved=True,
        cep=(best.get("cep") or "").replace("-", "") or None,
        street=best.get("logradouro"), neighborhood=best.get("bairro"),
        city=best.get("localidade"), state=best.get("uf"),
        display=f"{best.get('logradouro','')}, {best.get('bairro','')}, "
                f"{best.get('localidade','')}/{best.get('uf','')}".strip(", "),
        source="viacep-busca", confidence="media",
    )


async def resolve(query: str, cep_hint: Optional[str] = None) -> GeoResult:
    """Resolve uma referência textual (CEP, rua, ponto) em endereço estruturado."""
    query = (query or "").strip()
    cep = cep_hint or find_cep(query)

    if cep:
        result = await _brasilapi_cep(cep) or await _viacep(cep)
        if result:
            return result

    if query:
        result = await _nominatim(query)
        if result:
            return result

    return GeoResult(raw=query, resolved=False, display=query or None,
                     source="nao_resolvido", confidence="baixa")


def responsible_agency(geo: GeoResult, nature: Optional[str], severity: Optional[str]) -> str:
    """Define a viatura/órgão responsável a partir do local e da natureza."""
    uf = geo.state or "??"
    mun = geo.city or "município não identificado"

    batalhoes = _load_batalhoes()
    unit = batalhoes.get(f"{mun}/{uf}") or batalhoes.get(uf)
    pm_unit = unit or f"Batalhão da área de {mun}/{uf}"

    base = f"Polícia Militar — {pm_unit}"
    apoio = []
    n = (nature or "").lower()
    if any(k in n for k in ["acidente", "ferido", "vitima", "queda", "atropel"]):
        apoio.append("SAMU 192")
    if any(k in n for k in ["incendio", "fogo", "explosao"]):
        apoio.append("Corpo de Bombeiros 193")
    if severity in ("G1", "G2"):
        apoio.append("solicitar apoio da guarnição mais próxima")

    if apoio:
        return base + " + " + " + ".join(apoio)
    return base


def geo_to_dict(geo: GeoResult) -> dict:
    return asdict(geo)


# --- Estados (UF) --------------------------------------------------------------
UF_BY_NAME = {
    "acre": "AC", "alagoas": "AL", "amapa": "AP", "amazonas": "AM", "bahia": "BA",
    "ceara": "CE", "distrito federal": "DF", "espirito santo": "ES", "goias": "GO",
    "maranhao": "MA", "mato grosso do sul": "MS", "mato grosso": "MT",
    "minas gerais": "MG", "paraiba": "PB", "parana": "PR", "pernambuco": "PE",
    "piaui": "PI", "rio grande do norte": "RN", "rio grande do sul": "RS",
    "rio de janeiro": "RJ", "rondonia": "RO", "roraima": "RR", "santa catarina": "SC",
    "sao paulo": "SP", "sergipe": "SE", "tocantins": "TO", "para": "PA",
}
_UF_SET = set(UF_BY_NAME.values())


def _norm_uf(text: str) -> str:
    t = (text or "").lower()
    for a, b in (("á", "a"), ("ã", "a"), ("â", "a"), ("à", "a"), ("é", "e"),
                 ("ê", "e"), ("í", "i"), ("ó", "o"), ("ô", "o"), ("õ", "o"),
                 ("ú", "u"), ("ç", "c")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def parse_uf(text: str) -> Optional[str]:
    """Extrai a UF de 'são paulo', 'sergipe', 'SP' ou 'estado de SP'."""
    t = _norm_uf(text)
    for name in sorted(UF_BY_NAME, key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", t):
            return UF_BY_NAME[name]
    m = re.search(r"\b([A-Z]{2})\b", text or "")
    if m and m.group(1) in _UF_SET:
        return m.group(1)
    return None
