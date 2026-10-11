"""Modelos de dados (schemas) do domínio de atendimento."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DialogState(str, Enum):
    """Estados do atendimento (formulário guiado)."""

    GREETING = "greeting"       # saudação inicial
    COLLECTING = "collecting"   # coletando as respostas do formulário
    GENERATED = "generated"     # ocorrência gerada (nº emitido)
    CLOSED = "closed"           # ligação encerrada


class Severity(str, Enum):
    G1 = "G1"  # Crítica / risco de vida iminente
    G2 = "G2"  # Alta
    G3 = "G3"  # Média
    G4 = "G4"  # Baixa
    G5 = "G5"  # Não policial / informativo


class SeverityResult(BaseModel):
    severity: Severity
    label: str
    score: int
    reason: str
    sla_minutes: Optional[int] = None
    recommend_human: bool = False
    recommended_dispatch: str = ""


class Occurrence(BaseModel):
    id: Optional[int] = None
    call_id: str
    occurrence_number: Optional[str] = None  # protocolo ex.: 2026-000123
    created_at: str = Field(default_factory=_now_iso)

    # --- dados do formulário ---
    caller_name: Optional[str] = None
    caller_phone: Optional[str] = None
    caller_type: Optional[str] = None        # PF | PJ
    org_name: Optional[str] = None           # nome da empresa, se PJ

    nature: Optional[str] = None
    description: Optional[str] = None        # "descreva os fatos"
    life_risk: bool = False
    weapon: bool = False
    ongoing: bool = False
    suspects: Optional[str] = None
    victims: Optional[str] = None
    injuries: Optional[str] = None

    location_address: Optional[str] = None
    location_reference: Optional[str] = None
    city: Optional[str] = None

    # --- localização resolvida (CEP / geocodificação) ---
    cep: Optional[str] = None
    location_number: Optional[str] = None
    location_neighborhood: Optional[str] = None
    location_state: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    location_source: Optional[str] = None      # brasilapi | viacep | nominatim | manual
    location_confidence: Optional[str] = None  # alta | media | baixa
    responsible_agency: Optional[str] = None

    # --- classificação ---
    severity: Optional[Severity] = None
    severity_label: Optional[str] = None
    severity_reason: Optional[str] = None

    recommended_dispatch: Optional[str] = None
    status: str = "em_atendimento"  # em_atendimento | registrada | encerrada
    transcript: Optional[str] = None
    audio_path: Optional[str] = None
    duration_seconds: Optional[float] = None


class TurnRequest(BaseModel):
    """Uma fala do cidadão já transcrita (vinda do STT do navegador)."""

    call_id: str
    text: str


class TurnResponse(BaseModel):
    call_id: str
    state: DialogState
    reply: str                              # o que o bot fala (TTS)
    occurrence: Occurrence
    question_id: Optional[str] = None       # pergunta atual
    question: Optional[str] = None          # texto da pergunta atual
    classification: Optional[SeverityResult] = None
    human_handoff: bool = False
    finished: bool = False


class CallStartRequest(BaseModel):
    caller_phone: Optional[str] = None
    channel: str = "web"             # web | telefone


class CallStartResponse(BaseModel):
    call_id: str
    greeting: str
    state: DialogState
    question_id: Optional[str] = None
    question: Optional[str] = None
    occurrence: Occurrence
