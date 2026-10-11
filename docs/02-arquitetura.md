# 02 · Arquitetura

## Visão de componentes

```
┌───────────────────────── Navegador (Chrome) ─────────────────────────┐
│  index.html        Web Speech API (STT pt-BR)  +  SpeechSynthesis(TTS)│
│  dashboard.html    WebSocket (ocorrências ao vivo)                    │
└───────────────▲───────────────────────────────┬──────────────────────┘
                │ HTTP/JSON                     │ WS
┌───────────────┴───────────────────────────────▼──────────────────────┐
│                          FastAPI  (app/main.py)                        │
│  /api/call/start  /api/call/turn  /api/occurrences  /api/gravidade     │
└───────┬───────────────────────┬──────────────────────┬────────────────┘
        │                       │                      │
┌───────▼────────┐   ┌──────────▼─────────┐  ┌─────────▼──────────┐
│ agent.py       │   │ severity.py        │  │ location.py        │
│ diálogo/estado │   │ matriz G1..G5      │  │ CEP + geocode      │
│ extração       │   │                    │  │ órgão responsável  │
└───┬────────┬───┘   └────────────────────┘  └─────────┬──────────┘
    │        │                                          │
┌───▼───┐ ┌──▼─────────┐                    ┌───────────▼──────────┐
│llm.py │ │storage.py  │                    │ BrasilAPI / ViaCEP   │
│OpenRt │ │SQLite      │                    │ Nominatim (internet) │
└───────┘ └────────────┘                    └──────────────────────┘
```

## Princípio central
O **núcleo é determinístico** (máquina de estados + matriz de gravidade) e funciona
sem internet e sem LLM. O LLM é um **enriquecedor opcional**: extrai campos em
linguagem natural e redige a justificativa. Se o LLM falhar, a chamada continua.

## Fluxo de dados (uma fala do cidadão)
1. Navegador transcreve (STT) → `POST /api/call/turn {call_id, text}`.
2. `agent.process_turn`:
   - heurística local (`_heuristic_fields`) + LLM (`llm.extract_fields`);
   - aplica campos na ocorrência (`_apply`);
   - detecta natureza (`severity.detect_nature`);
   - resolve local (`_maybe_resolve` → `location.resolve`);
   - avança a máquina de estados e gera a próxima pergunta;
   - no estado CONFIRM: classifica (`severity.classify`), define responsável
     (`location.responsible_agency`) e grava.
3. `main` faz broadcast no WebSocket para o painel.
4. Navegador fala a resposta (TTS) e volta a escutar.

## Endpoints
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | interface de atendimento |
| GET | `/dashboard` | painel de ocorrências |
| GET | `/api/health` | saúde + se o LLM está ativo |
| POST | `/api/call/start` | inicia ligação, devolve saudação |
| POST | `/api/call/turn` | processa uma fala do cidadão |
| GET | `/api/occurrences` | lista ocorrências |
| GET | `/api/occurrences/{call_id}` | uma ocorrência |
| GET | `/api/occurrences/{call_id}/relatorio` | relatório de log (passo a passo) |
| GET | `/api/gravidade` | matriz de gravidade |
| WS | `/ws` | eventos ao vivo |

## Modelo de dados (ocorrência)
Chave da tabela `occurrences`: `call_id`. Campos principais: natureza, descrição,
transcrição, flags (risco de vida, arma, em andamento), local (endereço, CEP,
bairro, cidade, UF, lat/lng, fonte, confiança), órgão responsável, gravidade
(G1..G5), status, duração. Tabela `turns` guarda cada fala (papel, estado, texto).
Tabela `events` guarda, por turno, o que foi entendido (campos preenchidos) e o
próximo passo — base do **relatório de log** (`app/report.py`).

## Deploy (fase 3, alvo)
- Processo único FastAPI atrás de Nginx (já existente na VPS), HTTPS via cloudflared.
- Banco SQLite → migrar para PostgreSQL em produção multiusuário.
- Integração futura: SIP/190 (`app/telephony.py`), STT servidor (`faster-whisper`),
  integração CAD da PM para despacho real.
