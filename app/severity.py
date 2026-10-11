"""Matriz de gravidade de ocorrências (classificação G1..G5).

Regra central do bot: transformar a fala do cidadão numa prioridade de despacho.
A classificação é determinística (base + modificadores) para ser auditável e
reproduzível. O LLM pode justificar/refinar, mas nunca substitui a matriz.
"""
from __future__ import annotations

import re
from typing import List, Tuple

from .schemas import Occurrence, Severity, SeverityResult

# --- Tabela de naturezas: (chave, gatilhos, score_base, label, despacho) -------
NATURE_MATRIX: List[Tuple[str, List[str], int, str, str]] = [
    (
        "crime_em_andamento",
        ["assalto", "roubo", "roubando", "assaltando", "tiro", "tiroteio", "disparo",
         "baleado", "sequestro", "arrastao", "arrastao", "invasao", "invasor",
         "estao assaltando", "estao roubando", "arma", "armado", "faca", "refem"],
        85,
        "Crime em andamento com risco",
        "Despacho imediato - viatura mais próxima, prioridade máxima",
    ),
    (
        "violencia_domestica",
        ["violencia domestica", "marido batendo", "companheiro", "agressao", "agredindo",
         "espancando", "briga de casal", "ameaca de morte", "estupro", "abuso sexual",
         "violencia sexual"],
        78,
        "Violência / agressão em curso",
        "Despacho urgente - viatura + apoio (Lei Maria da Penha)",
    ),
    (
        "briga",
        ["briga", "brigando", "vias de fato", "confusao", "tumulto",
         "desentendimento", "socos", "empurrao"],
        55,
        "Briga / vias de fato",
        "Atendimento prioritário",
    ),
    (
        "ameaca",
        ["ameaca", "ameacando", "vai me matar", "ameacou", "perseguindo", "perseguicao",
         "stalking", "importunacao"],
        62,
        "Ameaça / perseguição",
        "Despacho urgente",
    ),
    (
        "acidente_com_feridos",
        ["acidente com ferido", "ferido", "feridos", "atropelamento", "colisao com vitima",
         "capotou", "queda de moto", "sangrando"],
        70,
        "Acidente com vítimas",
        "Despacho urgente - viatura + SAMU",
    ),
    (
        "desaparecimento",
        ["desapareceu", "desaparecido", "sumiu", "nao voltou", "sequestraram"],
        64,
        "Pessoa desaparecida",
        "Despacho prioritário - verificar protocolo de desaparecidos",
    ),
    (
        "acidente_sem_feridos",
        ["acidente", "colisao", "batida", "abalroamento", "choque"],
        46,
        "Acidente sem vítimas",
        "Atendimento normal",
    ),
    (
        "dano_patrimonio",
        ["depredacao", "vandalismo", "danificou", "quebrou", "pichacao", "dano ao patrimonio"],
        40,
        "Dano ao patrimônio",
        "Atendimento normal",
    ),
    (
        "furto",
        ["furto", "furtaram", "furtaram meu", "levaram minha", "levaram meu",
         "subtrairam", "roubaram minha bicicleta", "roubaram o celular"],
        52,
        "Furto / subtração de bem",
        "Atendimento normal - registro e orientação de boletim",
    ),
    (
        "atitude_suspeita",
        ["suspeito", "atitude suspeita", "olhando carros", "rondando", "tentando abrir",
         "individuo estranho", "homem armado"],
        42,
        "Atitude suspeita",
        "Atendimento normal - verificação preventiva",
    ),
    (
        "perturbacao",
        ["som alto", "barulho", "festa", "perturbacao", "sossego", "vizinho"],
        26,
        "Perturbação do sossego",
        "Atendimento não emergencial",
    ),
    (
        "orientacao",
        ["informacao", "orientacao", "informar", "duvida", "como faco", "denuncia anonima",
         "informacao sobre"],
        12,
        "Orientação / informação",
        "Encaminhamento não policial / registro posterior",
    ),
]

# --- Modificadores de risco ----------------------------------------------------
MODIFIERS: List[Tuple[str, int, str]] = [
    ("life_risk", 25, "risco de vida declarado"),
    ("weapon", 20, "presença de arma"),
    ("ongoing", 15, "ocorrência em andamento"),
    ("injuries", 15, "há feridos"),
]


def _norm(text: str) -> str:
    text = text.lower()
    for src, dst in (("á", "a"), ("à", "a"), ("ã", "a"), ("â", "a"), ("é", "e"),
                     ("ê", "e"), ("í", "i"), ("ó", "o"), ("ô", "o"), ("õ", "o"),
                     ("ú", "u"), ("ç", "c")):
        text = text.replace(src, dst)
    return re.sub(r"\s+", " ", text).strip()


def detect_nature(text: str) -> Tuple[str, int, str, str]:
    """Retorna (chave, score_base, label, despacho) da natureza mais provável."""
    t = _norm(text)
    best = ("indefinido", 30, "Ocorrência não classificada", "Avaliação humana necessária")
    best_hits = 0
    for key, triggers, score, label, dispatch in NATURE_MATRIX:
        hits = sum(1 for trig in triggers if _norm(trig) in t)
        if hits > best_hits:
            best_hits = hits
            best = (key, score, label, dispatch)
    return best


def _score_to_severity(score: int) -> Severity:
    if score >= 80:
        return Severity.G1
    if score >= 60:
        return Severity.G2
    if score >= 40:
        return Severity.G3
    if score >= 20:
        return Severity.G4
    return Severity.G5


_SEV_LABEL = {
    Severity.G1: "Crítica (risco de vida iminente)",
    Severity.G2: "Alta",
    Severity.G3: "Média",
    Severity.G4: "Baixa",
    Severity.G5: "Não policial / informativo",
}

_SLA = {Severity.G1: 0, Severity.G2: 5, Severity.G3: 15, Severity.G4: 60, Severity.G5: None}


def classify(occ: Occurrence, free_text: str = "") -> SeverityResult:
    """Classifica a ocorrência combinando natureza + modificadores."""
    text = " ".join(filter(None, [free_text, occ.description or "", occ.nature or ""]))
    key, base, label, dispatch = detect_nature(text)

    score = base
    reasons = [f"natureza: {label} (base {base})"]

    flags = {
        "life_risk": occ.life_risk,
        "weapon": occ.weapon,
        "ongoing": occ.ongoing,
        "injuries": bool(occ.injuries),
    }
    for name, delta, why in MODIFIERS:
        if flags.get(name):
            score += delta
            reasons.append(f"+{delta} {why}")

    if key == "indefinido":
        return SeverityResult(
            severity=Severity.G3,
            label=_SEV_LABEL[Severity.G3],
            score=score,
            reason="Natureza indefinida; encaminhado para avaliação humana. " + "; ".join(reasons),
            sla_minutes=_SLA[Severity.G3],
            recommend_human=True,
            recommended_dispatch="Despachante humano decide o encaminhamento",
        )

    score = max(0, min(100, score))
    sev = _score_to_severity(score)
    return SeverityResult(
        severity=sev,
        label=_SEV_LABEL[sev],
        score=score,
        reason="; ".join(reasons),
        sla_minutes=_SLA[sev],
        recommend_human=sev in (Severity.G1, Severity.G2),
        recommended_dispatch=dispatch,
    )


def matrix_summary() -> List[dict]:
    """Exporta a matriz (para documentação / endpoint /gravidade)."""
    return [
        {"natureza": key, "score_base": score, "label": label, "despacho": dispatch,
         "gatilhos": triggers}
        for key, triggers, score, label, dispatch in NATURE_MATRIX
    ]
