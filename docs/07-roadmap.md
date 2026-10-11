# 07 · Roadmap

## Fase 1 — PoC funcional (concluída)
- [x] Atendimento por voz no navegador (STT/TTS pt-BR)
- [x] Diálogo guiado (máquina de estados)
- [x] Resolução de CEP (BrasilAPI/ViaCEP) e rua (Nominatim)
- [x] Matriz de gravidade G1..G5 + órgão responsável
- [x] Painel de ocorrências ao vivo + SQLite
- [x] LLM opcional com fallback determinístico

## Fase 2 — Telefonia real e voz no servidor
- [ ] `app/telephony.py`: receber chamada via SIP (integração ao 190/PABX)
- [ ] STT servidor em streaming (`faster-whisper`) — sem depender do navegador
- [ ] TTS servidor (Piper/Azure) para as perguntas do bot
- [ ] Gravação de áudio com retenção
- [ ] Número de teste (DID) para homologação

## Fase 3 — Despacho e operação PM
- [ ] Integração com o CAD/despacho da corporação (despachar viatura de fato)
- [ ] Mapa no painel (lat/lng) e fila de despacho por gravidade/SLA
- [ ] Login de despachantes e transferência de chamada (handoff real)
- [ ] Migrar SQLite → PostgreSQL; métricas e alertas

## Fase 4 — Segurança e LGPD
- [ ] Deploy on-premise na rede da PM
- [ ] Criptografia em trânsito e repouso; minimização de dados
- [ ] Trilha de auditoria e controle de acesso
- [ ] Validação jurídica do uso de IA no atendimento de emergência

## Riscos e mitigação
| Risco | Mitigação |
|-------|-----------|
| STT erra endereço/número | confirmação obrigatória + resolução por CEP |
| Natureza ambígua | G3 + revisão humana (`recommend_human`) |
| API externa fora do ar | fallback em cadeia (BrasilAPI→ViaCEP→Nominatim→texto) |
| LLM fora do ar | núcleo determinístico assume |
| Dados sensíveis | fase 4: on-premise, criptografia, sem log de fala |
| Falsa gravidade baixa | G1/G2 sempre com handoff humano |

## Critérios de aceite do piloto (para apresentação à PM)
1. Uma ligação de teste completa registra a ocorrência com local e gravidade.
2. CEP de qualquer estado do Brasil resolve endereço + coordenadas.
3. Casos críticos marcam handoff para despachante.
4. O sistema continua funcional com o LLM desligado.
