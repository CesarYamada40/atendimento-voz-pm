# Histórico de erros e correções — Atendimento por Voz (PM)

Registro cronológico do que foi testado, os defeitos encontrados e as correções.
Cada item lista: **sintoma → causa → correção → teste**.

## 2026-10-11 — Sessão inicial do piloto

| # | Sintoma | Causa | Correção |
|---|---------|-------|----------|
| 1 | IA não deixava terminar de falar; avançava na 1ª pausa e partia a frase ("telefone" / "telefone é 11") | Web Speech finaliza um trecho a cada pausa curta; o frontend enviava o 1º final | Acumular a fala e só registrar após **~2,2 s de silêncio**; botão "Já falei — avançar"; campo "Digitar resposta" |
| 2 | CEP interpretado como telefone (`01310100`) | autofill pegava qualquer sequência de 8–11 dígitos | Remover o padrão de CEP antes de interpretar o telefone |
| 3 | Assalto com arma classificado como **G3** | classificador olhava só o campo "fatos" | Classificar usando a **transcrição completa** (G1 correto) |
| 4 | Diálogo genérico, não seguia o atendimento real | fluxo por "estado" | Reescrever como **roteiro fixo de perguntas** |
| 5 | Números falados não reconhecidos ("rua dez") | STT devolve por extenso | `nlu.spoken_to_digits` ("sete zero zero"→700; "vinte e cinco"→25) |
| 6 | Falta estado/cidade/bairro para a viatura certa | campos ausentes | Perguntas de **UF, cidade, bairro** (puladas quando o CEP resolve) |
| 7 | Bot não confirmava o local nem o despacho | texto ausente | **Anúncio do local** ("Você está em …") + **despacho** ("Repassando para a equipe tática … Aguarde") |
| 8 | Endereço redundante ("número dez, número 10") | texto cru + número extraído à parte | Normalizar endereço com `spoken_to_digits` + `collapse_repeats` |
| 9 | Transcrição/campos com muitas repetições do STT | reconhecedor repete trechos | `nlu.collapse_repeats` (colapsa palavras/frases repetidas) |
| 10 | CEP "08.526-060" não reconhecido | regex exigia `\d{5}-\d{3}` | `location.find_cep` aceita pontos/espaços/hífen |
| 11 | Natureza gravada como texto cru repetido | fallback sem limpeza | Colapsar fallback + reconhecer "briga/brigando" → *Briga / vias de fato* |
| 12 | Sem auditoria do que foi entendido | ausência de log | **Relatório de log** (`app/report.py`, `scripts/relatorio.py`, endpoint) + tabela `events` |
| 13 | Não pedia o número do imóvel | pergunta ausente | Pergunta **"número do endereço (ou aproximado)"** |
| 14 | Final longo e repetitivo | lia todos os dados | **Final curto: rua + nº do registro** (+ despacho) |
| 15 | Voz feminina | padrão do navegador | **Voz masculina pt-BR** (seleção automática + seletor + pitch grave) |
| 16 | Endereço errado ("rua tem 1 cara com uma arma…") e pergunta de endereço pulada | autofill capturava "rua" solto no meio da fala | Autofill só captura **sinais de risco**; endereço/telefone só pelas perguntas |
| 17 | Respostas ainda repetidas ("meu" → "meu nome" → "meu nome é") | reconhecedor emite finais **cumulativos** | Frontend mescla finais sobrepostos (`appendFinal`) |
| 18 | CEP/telefone corrompidos pelo colapso ("zero um três um zero um zero zero") | `collapse_repeats` colapsava dígitos falados | Colapso **preserva sequências numéricas** |
| 19 | Número do imóvel virava os dígitos do CEP ("01310") | `_parse_address_number` capturava o CEP | Remover CEP antes de extrair o número |

## Estado atual
- 49 testes automatizados (`pytest`), offline e determinísticos.
- Relatório de log por ocorrência com checklist e passo a passo.
- Erros conhecidos/pendências: telefonia real (SIP/190) e integração CAD ainda não existem (fases 2–3).
