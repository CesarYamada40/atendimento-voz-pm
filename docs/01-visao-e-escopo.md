# 01 · Visão e Escopo

## Objetivo
Oferecer à Polícia Militar um **canal de atendimento por voz automatizado** que
recepção chamadas da população, registra a ocorrência **em tempo real** enquanto
o cidadão fala, identifica o **local correto** (CEP, rua ou referência) e define a
**gravidade** e o **órgão/viatura responsável**, entregando o despacho ao
despachante humano ou diretamente à guarnição.

## Problema
- Linhas de emergência sobrecarregadas com chamadas de baixa complexidade.
- Registro manual (digitado) durante a ligação gera atraso e erro.
- Localização imprecisa atrasa a chegada da viatura.

## Escopo do piloto (Fase 1)
- Atendimento por voz via navegador (simula a chamada por telefone).
- Transcrição em tempo real (pt-BR) e diálogo guiado.
- Resolução de local por CEP / rua / referência.
- Classificação de gravidade G1..G5 e roteamento do responsável.
- Painel de ocorrências ao vivo e persistência.

## Fora de escopo (Fase 1) — planejado depois
- Telefonia real (PABX/SIP/190).
- Integração efetiva com o CAD/despacho da PM.
- Login/autenticação de operadores, auditoria e trilha de custódia.
- Conformidade LGPD formal e hardening on-premise.

## Requisitos funcionais (RF)
| Cód. | Requisito |
|------|-----------|
| RF1 | Atender a chamada por voz e responder por voz |
| RF2 | Transcrever a fala em tempo real (parcial + final) |
| RF3 | Conduzir roteiro fixo: nome, ocorrência, PF/PJ, endereço, telefone, referência, fatos |
| RF4 | Resolver CEP (todo o Brasil) em endereço + coordenadas |
| RF5 | Geocodificar rua/referência em coordenadas |
| RF6 | Classificar gravidade G1..G5 de forma auditável |
| RF7 | Definir órgão/viatura responsável |
| RF8 | Registrar a ocorrência com transcrição completa |
| RF9 | Encaminhar casos críticos a despachante humano (handoff) |
| RF10 | Exibir ocorrências em painel ao vivo |
| RF11 | Gerar número da ocorrência (protocolo) e permitir repetir/consultar os dados |

## Requisitos não funcionais (RNF)
| Cód. | Requisito | Meta |
|------|-----------|------|
| RNF1 | Latência de resposta do bot | < 2 s (LLM ligado) / < 300 ms (heurística) |
| RNF2 | Resolução de CEP | < 1,5 s |
| RNF3 | Disponibilidade | 24×7 (fase 3) |
| RNF4 | Tolerância a falhas | funciona sem LLM; nunca perde o registro |
| RNF5 | Privacidade | dados sensíveis; áudio e fala não logados |

## Parâmetros operacionais (configuráveis por `.env`)
| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `VOZ_HOST` / `VOZ_PORT` | bind do servidor | 127.0.0.1 / 8088 |
| `VOZ_DB_PATH` | banco SQLite | `./data/ocorrencias.db` |
| `VOZ_LLM_ENABLED` | usar LLM (OpenRouter) | `true` |
| `VOZ_LLM_MODEL` | modelo do agente | `openai/gpt-4o-mini` |
| `VOZ_LLM_TIMEOUT` | timeout do LLM (s) | `20` |
| `VOZ_MAX_CALL_SECONDS` | duração máxima da chamada | `600` |
| `VOZ_AUDIO_RETENTION_DAYS` | retenção de áudio (fase 3) | `90` |
| `VOZ_RECORDING_ENABLED` | gravar áudio (fase 3) | `true` |

## Fonte dos dados de localização
| Função | Serviço | Cobertura | Chave |
|--------|---------|-----------|-------|
| CEP → endereço + coords | BrasilAPI v2 | Brasil | não |
| CEP → endereço (fallback) | ViaCEP | Brasil | não |
| Rua/referência → coords | Nominatim/OSM | Brasil | não (uso justo) |
