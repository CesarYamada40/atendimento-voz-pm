# 06 · Ferramentas e stack

## Em uso na Fase 1 (funcional)
| Camada | Ferramenta | Papel | Custo |
|--------|-----------|-------|-------|
| Frontend | HTML/CSS/JS puro | UI de atendimento e painel | — |
| STT (voz→texto) | Web Speech API (Chrome, pt-BR) | transcrição em tempo real no navegador | grátis |
| TTS (texto→voz) | SpeechSynthesis (navegador) | bot fala as perguntas | grátis |
| Backend | FastAPI + Uvicorn | API, WebSocket, estáticos | grátis |
| HTTP | httpx (async) | chamadas a LLM e APIs de CEP | grátis |
| LLM (opcional) | OpenRouter (`OPENROUTER_API_KEY`) | extração NLU + justificativa | por uso |
| CEP | BrasilAPI v2 → ViaCEP | CEP→endereço+coords | grátis |
| Geocode | Nominatim/OSM | rua/referência→coords | grátis |
| Banco | SQLite | ocorrências + turnos | grátis |

## Fase 2 — telefonia e STT servidor (planejado)
| Necessidade | Opções | Observação |
|-------------|--------|------------|
| Telefonia | Asterisk/FreeSWITCH + SIP trunk (integração ao 190/PABX) | E1/SIP da central da PM |
| STT servidor | `faster-whisper` (local) ou Azure/Google STT | local exige GPU; CPU aceita modelo small |
| TTS servidor | Piper (local) ou Azure TTS | voz pt-BR |
| Streaming de áudio | WebSocket/WebRTC | transcrição parcial em tempo real |
| Gravação | armazenamento com retenção | `VOZ_AUDIO_RETENTION_DAYS` |

## Fase 3 — despacho e operação (planejado)
| Necessidade | Opções |
|-------------|--------|
| Integração CAD/despacho PM | API/webhook do sistema da corporação |
| Banco produção | PostgreSQL |
| Autenticação | login de despachantes (OIDC/SSO da PM) |
| Observabilidade | logs estruturados, métricas, alertas |
| Mapa | tiles OSM/Leaflet no painel com lat/lng |

## Fase 4 — segurança e LGPD (planejado)
| Necessidade | Ação |
|-------------|------|
| Soberania de dados | deploy on-premise na rede da PM |
| Criptografia | TLS em trânsito; repouso no banco e no áudio |
| Minimização | não logar fala/telefone; reter só o necessário |
| Trilha de auditoria | registro de acesso e alteração de ocorrência |
| Consentimento | aviso de gravação na saudação (já implementado) |

## Ferramentas de desenvolvimento
- Python 3.12 · venv em `.venv/`.
- Teste rápido do backend: `scripts/demo_fluxo.py`.
- Subir servidor: `scripts/run.sh` ou `uvicorn app.main:app`.
