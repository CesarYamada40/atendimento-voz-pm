"""Relatório de log por ocorrência: o que foi entendido, computado e registrado."""
from __future__ import annotations

from typing import Optional

from . import storage

# pergunta -> campo da ocorrência (para verificar se foi entendida)
QUESTION_FIELD = {
    "nome": "caller_name", "ocorrencia": "nature", "tipo": "caller_type",
    "endereco": "location_address", "numero": "location_number",
    "estado": "location_state", "cidade": "city",
    "bairro": "location_neighborhood", "telefone": "caller_phone",
    "referencia": "location_reference", "fatos": "description",
}
REQUIRED = ["nome", "ocorrencia", "tipo", "endereco", "telefone", "fatos"]
LABEL = {
    "caller_name": "Nome", "nature": "Ocorrência", "caller_type": "Tipo",
    "location_address": "Endereço", "location_number": "Número", "cep": "CEP",
    "location_neighborhood": "Bairro", "city": "Cidade", "location_state": "UF",
    "caller_phone": "Telefone", "location_reference": "Referência",
    "description": "Fatos",
}


def build_report(call_id: str) -> Optional[dict]:
    occ = storage.get_occurrence(call_id)
    if not occ:
        return None
    d = occ.model_dump()
    events = storage.get_events(call_id)
    turns = storage.get_turns(call_id)

    steps = []
    for ev in events:
        snap = ev.get("snapshot") or {}
        ans = snap.get("answered")
        fld = QUESTION_FIELD.get(ans) if ans else None
        fields = snap.get("fields") or {}
        steps.append({
            "pergunta": ans,
            "campo": fld,
            "falou": ev.get("text"),
            "entendeu": bool(fld and fields.get(fld)),
            "valor": fields.get(fld) if fld else None,
            "proximo": snap.get("next_question"),
            "gravidade": snap.get("severity"),
        })

    missing = [q for q in REQUIRED if not d.get(QUESTION_FIELD[q])]
    checks = {
        "campos_obrigatorios_ok": not missing,
        "local_resolvido": bool(d.get("location_source")),
        "cep_identificado": bool(d.get("cep")),
        "gravidade_calculada": bool(d.get("severity")),
        "orgao_definido": bool(d.get("responsible_agency")),
        "numero_gerado": bool(d.get("occurrence_number")),
        "registrada": d.get("status") in ("registrada", "encerrada"),
    }

    issues = []
    if missing:
        issues.append("Campos obrigatórios sem resposta: " +
                      ", ".join(LABEL.get(QUESTION_FIELD[q], q) for q in missing))
    if not d.get("cep"):
        issues.append("CEP não identificado — local pode estar impreciso")
    if d.get("location_confidence") == "baixa" or d.get("location_source") == "nao_resolvido":
        issues.append("Localização com baixa confiança — validar com o solicitante")
    if not d.get("severity"):
        issues.append("Gravidade não calculada (ocorrência não gerada)")
    if not d.get("responsible_agency"):
        issues.append("Órgão/viatura responsável não definido")

    return {
        "call_id": call_id,
        "occurrence": d,
        "checks": checks,
        "issues": issues,
        "steps": steps,
        "turns": turns,
    }
