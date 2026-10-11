# AGENTS — Central de Atendimento por Voz (PM)

Convenções para agentes que editarem este projeto.

## Fonte de verdade
- Código em `/root/projects/atendimento-voz-pm/` é a fonte de verdade.
- Documentação de projeto: `/root/vault/Projetos/atendimento-voz-pm/`.

## Regras
- **Núcleo determinístico primeiro**: a classificação de gravidade e o roteamento
  nunca podem depender só do LLM. O LLM enriquece (`app/llm.py`); se falhar o
  sistema continua (heurística em `agent.py` e `severity.py`).
- **Não inventar dados de local**: se o CEP/rua não resolver, marcar
  `location_confidence = "baixa"` e recomendar validação humana.
- **LGPD/sigilo**: dados de ocorrência e áudio são sensíveis. Não logar conteúdo
  de fala nem telefone. Não enviar áudio a terceiros sem decisão explícita.
- Rodar `.venv/bin/python scripts/demo_fluxo.py` antes de considerar pronto.

## Comandos
```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8088   # servidor
.venv/bin/python scripts/demo_fluxo.py                        # teste backend (texto)
bash scripts/teste_http.sh                                    # teste ponta a ponta via API
.venv/bin/python -m pytest                                    # suíte automatizada (tests/)
.venv/bin/python scripts/relatorio.py                         # relatório de log (última ocorrência)
curl -s localhost:8088/api/health                             # saúde
curl -s localhost:8088/api/gravidade                          # matriz
```

## Testes
- `tests/test_severity.py` — matriz de gravidade (G1..G5, limites, indefinida).
- `tests/test_location.py` — CEP válido/inexistente, geocode, órgão responsável.
- `tests/test_agent_flow.py` — fluxo completo, "não sei", correção, repetir dados, nº.
- `tests/test_nlu.py` — números falados por extenso ("sete zero zero", "vinte e cinco").
- Rede (CEP/geocode) e LLM são **mockados/desligados** no `tests/conftest.py`:
  os testes são rápidos, offline e determinísticos.
- Rodar antes de considerar qualquer alteração pronta: `.venv/bin/python -m pytest`.

## Pendências conhecidas
- Telefonia real (SIP/190) e STT no servidor (fase 2).
- Integração com o CAD/despacho da PM para despacho efetivo da viatura.
- Gravação de áudio (flag `VOZ_RECORDING_ENABLED` existe; upload ainda não).
