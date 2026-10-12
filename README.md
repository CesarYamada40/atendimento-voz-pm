# Central de Atendimento por Voz — Polícia Militar (piloto)

Chatbot que atende a população **por voz**, registra a ocorrência **em tempo real**
enquanto o cidadão fala, resolve o **local** (CEP / rua / referência → endereço +
coordenadas) e define a **gravidade** e o **órgão/viatura responsável** a despachar.

> Documentação de projeto (vault): `/root/vault/Projetos/atendimento-voz-pm/`

## O que já funciona (Fase 1 — PoC web)

- Atendimento por voz no navegador (Web Speech API, pt-BR): transcrição parcial em tempo real.
- Bot fala as perguntas (TTS do navegador).
- Agente de diálogo guiado (máquina de estados) que preenche a ocorrência.
- Resolução de local:
  - **CEP** → BrasilAPI v2 (endereço + coordenadas) com fallback ViaCEP.
  - **Rua / referência** → Nominatim / OpenStreetMap.
- Matriz de gravidade **G1..G5** auditável + roteamento do órgão responsável
  (PM da área, SAMU, Bombeiros conforme a natureza).
- Perguntas de **estado (UF), cidade e bairro** e do **número do local (ou aproximado)**
  (estado/cidade/bairro pulados quando o CEP já resolve) — garante que a **viatura/
  equipe tática certa** vá ao local.
- Perguntas de local na ordem **estado → cidade → bairro → rua → número → CEP**
  (do geral ao específico) — garante que a **viatura/equipe tática certa** vá ao local.
- A IA **confirma o local identificado** antes de prosseguir ("Localizei o endereço:
  … Está correto?") e, se o cidadão **não tiver o CEP**, **descobre o CEP** pela
  rua/bairro/cidade/UF (ViaCEP por logradouro — SP e todo o Brasil). Se não estiver
  certo, volta a perguntar o endereço.
- Ao gerar, dá um **resumo curto** (número do registro + **nome da rua**).
- **Sem repetição**: mescla finais cumulativos do reconhecedor e colapsa repetições
  (preservando números falados). Autofill não captura endereço de falas soltas.
- **Voz masculina** pt-BR (seleção automática, com seletor para trocar).
- **NLU de voz**: números falados por extenso ("rua dez", "CEP sete zero zero
  quatro", "nove um dois...") convertidos para dígitos em telefone/CEP/endereço.
- **Controle de fala**: só registra a resposta após ~2,2 s de silêncio; botão
  "Já falei — avançar"; e campo "Digitar resposta" para tablet/celular.
- **Limpeza de fala**: colapsa repetições do STT e reconhece CEP com separadores
  irregulares ("08.526-060").
- **Relatório de log por ocorrência**: mostra passo a passo o que foi entendido,
  computado e registrado, com checklist e pendências.
- Painel de ocorrências ao vivo (WebSocket).
- Persistência em SQLite + transcrição por turno.

## Como rodar

```bash
cd /root/projects/atendimento-voz-pm
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# opcional: copie .env.example e configure OPENROUTER_API_KEY
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8088
```

Abra:

- Atendimento (use **Google Chrome** para o microfono): `http://127.0.0.1:8088/`
- Painel de ocorrências: `http://127.0.0.1:8088/dashboard`

Acesso remoto (HTTPS é obrigatório para microfone fora de localhost): use o
`cloudflared` já disponível na VPS.

Teste do backend sem navegador:

```bash
.venv/bin/python scripts/demo_fluxo.py   # simula a fala turno a turno
bash scripts/teste_http.sh               # chamada completa via API HTTP
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest               # suíte automatizada (46 testes)
```

Relatório de log de uma ocorrência (auditoria ponta a ponta):

```bash
.venv/bin/python scripts/relatorio.py            # última ocorrência
.venv/bin/python scripts/relatorio.py <call_id>  # uma específica
.venv/bin/python scripts/relatorio.py --all      # resumo de todas
# ou via API:  GET /api/occurrences/<call_id>/relatorio
```

## Estrutura

```
app/
  main.py       FastAPI: rotas, WebSocket, estáticos
  agent.py      máquina de estados do diálogo + extração + registro
  severity.py   matriz de gravidade G1..G5
  location.py   CEP (BrasilAPI/ViaCEP) + geocodificação (Nominatim) + órgão responsável
  llm.py        cliente OpenRouter (opcional; degrada para heurística)
  storage.py    SQLite (ocorrências + turnos)
  schemas.py    modelos de dados
  static/       index.html (atendimento) · dashboard.html (painel)
scripts/
  demo_fluxo.py demonstração do fluxo completo sem navegador
docs/           especificação, arquitetura, agentes, processos, roadmap
```

## Estado das fases

| Fase | Escopo | Estado |
|------|--------|--------|
| 1 | PoC web por voz + CEP/geo + gravidade | **funcional** |
| 2 | Telefonia real (SIP/190), STT servidor, gravação de áudio | planejada |
| 3 | Integração CAD/despacho da PM, login, auditoria | planejada |
| 4 | Segurança/LGPD, on-premise, hardening | planejada |

## Privacidade e LGPD

- Este repositório é **público** e **não contém dados reais** de atendimento.
  Ficam fora do versionamento: banco (`data/*.db`), `logs/`, `.env` e os
  relatórios com dados reais (`docs/relatorios/`).
- O relatório de exemplo em `docs/exemplo-relatorio.md` usa dados **fictícios**.
- Dados de ocorrência (nome, telefone, endereço, fala) são **sensíveis**: em
  produção devem ficar **on-premise**, criptografados, com retenção mínima e
  trilha de auditoria. Áudio e fala **não** são registrados em log.
- A saudação já inclui o **aviso de gravação**; a gravação de áudio é opcional
  (`VOZ_RECORDING_ENABLED`) e ainda não implementada.

## Licença

MIT — ver `LICENSE`.
