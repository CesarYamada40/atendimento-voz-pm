"""Cliente LLM (OpenRouter / OpenAI-compatível) com degradação graciosa.

O agente funciona sem LLM (heurística local). O LLM só enriquece:
extração da resposta de cada pergunta e justificativa da gravidade.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from .config import settings

log = logging.getLogger("voz.llm")


async def _chat(messages: list[dict], temperature: float = 0.2,
                max_tokens: int = 700) -> Optional[str]:
    if not (settings.llm_enabled and settings.llm_api_key):
        return None
    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001 - degradar silenciosamente
        log.warning("LLM indisponível (%s); usando heurística local", exc)
        return None


async def extract_answer(field_label: str, utterance: str) -> Optional[str]:
    """Extrai a resposta a UMA pergunta do formulário de atendimento.

    Retorna o valor em texto curto, ou None se não houver resposta útil.
    """
    out = await _chat(
        [
            {"role": "system",
             "content": "Você atende ligações de emergência da Polícia Militar. "
                        "Recebe a fala do cidadão e a informação que o atendente "
                        "precisa obter. Responda APENAS com o valor pedido, curto e "
                        "direto, em português, sem frases. Se a fala não contiver a "
                        "informação, responda exatamente: null"},
            {"role": "user",
             "content": f"Informação pedida: {field_label}\nFala do cidadão: {utterance}"},
        ],
        temperature=0.0,
        max_tokens=60,
    )
    if not out:
        return None
    clean = out.strip().strip('"').strip()
    if not clean or clean.lower() in {"null", "nenhum", "n/a", "nao informado",
                                      "não informado", "nao", "não"}:
        return None
    return clean


async def justify(occurrence_summary: str, severity_label: str) -> Optional[str]:
    """Gera uma justificativa curta e profissional para o despachante."""
    return await _chat(
        [
            {"role": "system",
             "content": "Resuma em 1 frase objetiva, em português, por que esta "
                        "ocorrência tem esta prioridade, para o despachante da PM."},
            {"role": "user", "content": f"Ocorrência: {occurrence_summary}\n"
                                        f"Prioridade atribuída: {severity_label}"},
        ],
        temperature=0.3,
        max_tokens=120,
    )
