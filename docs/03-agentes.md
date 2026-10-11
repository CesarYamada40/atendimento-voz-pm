# 03 · Agentes (papéis do sistema)

O piloto usa **um orquestrador com agentes especializados** (funções/módulos com
responsabilidade única). Cada agente tem interface clara e pode ser testado
isoladamente. Só dois usam LLM; o resto é determinístico.

| # | Agente | Módulo | LLM? | Responsabilidade |
|---|--------|--------|------|------------------|
| 1 | Orquestrador / Triagem | `agent.py` | não | conduz o diálogo, decide o próximo passo |
| 2 | Extração (NLU) | `agent.py` + `llm.py` | sim | converte fala → campos estruturados |
| 3 | Localização | `location.py` | não | CEP/rua → endereço + coordenadas |
| 4 | Gravidade | `severity.py` | não | matriz G1..G5 auditável |
| 5 | Roteamento/Despacho | `location.py` | não | define órgão/viatura responsável |
| 6 | Registro | `storage.py` | não | persiste ocorrência + transcrição |
| 7 | Handoff humano | `agent.py` | não | escala casos G1/G2 ao despachante |

## 1. Orquestrador / Triagem (`agent.py`)
- **Entrada**: `TurnRequest {call_id, text}`.
- **Saída**: `TurnResponse {state, reply, occurrence, question, classification, human_handoff}`.
- **Faz**: conduz o **roteiro fixo** (`QUESTIONS`) — escolhe a próxima pergunta não
  respondida (`_next_question`), entende a resposta, preenche o campo, trata
  comandos ("repetir os dados", "não entendi", "não sei", "corrigir") e decide
  quando gerar a ocorrência (ver `04-processos-fluxo.md`).
- **Fala**: perguntas do roteiro (`Question.prompt`).

## 2. Extração / NLU (`llm.extract_answer` + parsers locais)
- **Por pergunta**: `llm.extract_answer(label, fala)` devolve só o valor pedido
  (ou `null`). Ex.: pedido "nome" + fala "meu nome é João" → "João".
- **Fallback determinístico**: parsers locais por campo (`_parse_name`,
  `_parse_phone`, `_parse_pf_pj`, `_parse_org`, regex de endereço/CEP) e
  `severity.detect_nature`. Nunca quebra a chamada.
- **Números falados** (`nlu.spoken_to_digits`): converte "sete zero zero quatro"
  → `70040010`, "vinte e cinco" → `25`, "cento e cinquenta" → `150`. Aplicado só
  onde dígitos fazem sentido (telefone, CEP, número do endereço) — nunca em
  natureza/fatos, para não corromper o texto livre.

## 3. Localização (`location.resolve`)
- Se houver **CEP** (regex `\d{5}-?\d{3}`): BrasilAPI v2 → endereço + lat/lng; fallback ViaCEP.
- Senão, se houver **rua/referência**: Nominatim (Brasil).
- **Confiança**: `alta` (CEP + coords), `media` (geocode/fallback), `baixa` (não resolvido).
- **Regra**: não inventar; se não resolver → confiança baixa + validação humana.

## 4. Gravidade (`severity.classify`)
- Determinística: `score = base(natureza) + modificadores`.
- Modificadores: risco de vida +25, arma +20, em andamento +15, feridos +15.
- Mapeamento: ≥80 G1 · 60–79 G2 · 40–59 G3 · 20–39 G4 · <20 G5.
- LLM só **redige a justificativa** (`llm.justify`), nunca muda o score.

## 5. Roteamento/Despacho (`location.responsible_agency`)
- Base: Polícia Militar da área (mapa `data/batalhoes.json`, opcional).
- Apoio por natureza: acidente/feridos → SAMU 192; incêndio → Bombeiros 193.
- Gravidade G1/G2 → "solicitar apoio da guarnição mais próxima".

## 6. Registro (`storage.py`)
- Grava ocorrência (JSON + colunas indexadas `severity`/`status`) e cada turno.
- Encerra com transcrição completa e duração.

## 7. Handoff humano (`human_handoff`)
- Disparado quando `recommend_human` (G1/G2 ou natureza indefinida).
- Fase 1: sinaliza na resposta e no painel. Fase 3: transfere a chamada ao ramal
  do despachante (telefonia) mantendo transcrição e localização na tela.
