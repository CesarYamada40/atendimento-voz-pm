"""Configuração central do projeto (lida de variáveis de ambiente)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _load_env_file(path: str = "/root/.env") -> None:
    """Carrega .env simples sem sobrescrever variáveis já definidas."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()


@dataclass(frozen=True)
class Settings:
    app_name: str = "Central de Atendimento por Voz - PM"
    host: str = os.getenv("VOZ_HOST", "127.0.0.1")
    port: int = int(os.getenv("VOZ_PORT", "8088"))

    db_path: str = os.getenv(
        "VOZ_DB_PATH",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ocorrencias.db"),
    )

    # LLM (opcional). Se ausente/indisponível, o agente usa a heurística local.
    llm_enabled: bool = os.getenv("VOZ_LLM_ENABLED", "true").lower() in {"1", "true", "yes"}
    llm_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    llm_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    llm_model: str = os.getenv("VOZ_LLM_MODEL", "openai/gpt-4o-mini")
    llm_timeout: float = float(os.getenv("VOZ_LLM_TIMEOUT", "20"))

    # Parâmetros de atendimento
    max_call_seconds: int = int(os.getenv("VOZ_MAX_CALL_SECONDS", "600"))
    audio_retention_days: int = int(os.getenv("VOZ_AUDIO_RETENTION_DAYS", "90"))
    recording_enabled: bool = os.getenv("VOZ_RECORDING_ENABLED", "true").lower() in {"1", "true", "yes"}


settings = Settings()
