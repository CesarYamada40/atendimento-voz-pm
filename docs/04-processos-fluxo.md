# 04 · Processos e fluxo do atendimento

## Roteiro fixo de perguntas

O atendimento segue **sempre as mesmas perguntas**, na ordem abaixo. Cada resposta é
entendida (LLM + heurística) e guardada no campo correspondente. Perguntas já
respondidas são **puladas**; várias informações numa só fala também são capturadas.

| Ordem | Pergunta | Campo | Obrigatória |
|-------|----------|-------|-------------|
| 1 | Qual é o seu nome? | `caller_name` | sim |
| 2 | Qual é a ocorrência? O que está acontecendo? | `nature` | sim |
| 3 | A ocorrência é para pessoa física ou empresa? | `caller_type` (+ `org_name`) | sim |
| 4 | Qual o endereço da ocorrência? (rua/nº/bairro ou CEP) | `location_address` (+ CEP/geo) | sim |
| 5 | Qual o número do endereço? (ou aproximado) | `location_number` | não |
| 6 | Qual o estado, a UF? | `location_state` | sim |
| 7 | Qual a cidade? | `city` | sim |
| 8 | Qual o bairro? | `location_neighborhood` | sim |
| 9 | Qual é um telefone para contato? | `caller_phone` | sim |
| 10 | Tem algum ponto de referência? | `location_reference` | não |
| 11 | Agora descreva os fatos. | `description` | sim |

> **Localização:** quando o CEP é informado, ele resolve endereço + bairro + cidade + UF
> (BrasilAPI/ViaCEP) e as perguntas 6–8 são **puladas automaticamente**; o **número**
> (pergunta 5) continua sendo pedido.

Ao final, a IA dá um **resumo curto**: **número do registro** e **nome da rua** —
*"Ocorrência AAAA-NNNNNN registrada. Rua …. Repassando para a equipe tática. Aguarde."*
Quem quiser ouvir todos os dados diz **"repetir os dados"**.

## Repetição de fala (corrigido)
O reconhecedor (a) emite finais **cumulativos** ("meu" → "meu nome" → "meu nome é
João") e (b) repete trechos. O frontend **mescla** os finais sobrepostos
(`appendFinal`) e o backend **colapsa repetições** (`nlu.collapse_repeats`),
**preservando sequências numéricas** faladas (para não corromper CEP/telefone).
O autofill **não** captura endereço/telefone de falas soltas — só sinais de risco.

## Controle da fala (navegador)
O reconhecedor de voz só fecha um trecho a cada pausa curta; para **não cortar a
frase do cidadão**, o frontend **acumula** o texto e só registra após **~2,2 s de
silêncio**. Também há o botão **"Já falei — avançar"** para confirmar na hora, e o
campo **"Digitar resposta"** como alternativa ao microfone (tablet/celular).

## Estados (`DialogState`)
`GREETING → COLLECTING → GENERATED → CLOSED`
- **COLLECTING**: conduz o roteiro; `current_qid` aponta a pergunta atual.
- **GENERATED**: ocorrência gerada com número; aceita "repetir os dados"/"número".
- **CLOSED**: ligação encerrada.

## Comandos que o cidadão pode dar a qualquer momento
| Fala | Efeito |
|------|--------|
| "repetir os dados" / "resumo" | bot lê todos os dados coletados |
| "não entendi" / "repete" | bot repete a pergunta atual |
| "não sei" (pergunta opcional) | pula a pergunta |
| "corrigir nome/endereço/…" | volta para aquele campo |
| "número" / "protocolo" (após gerar) | informa o número da ocorrência |
| "sim, pode encerrar" / "obrigado" | encerra a ligação |

## Procedimento por chamada
1. **Saudação** (com aviso de gravação) + 1ª pergunta (nome).
2. **Coleta** das 7 perguntas; a cada turno: entende → preenche → resolve local → próxima.
3. **Geração**: protocolo + gravidade (G1..G5) + órgão responsável; lê o resumo.
4. **Encerramento**: grava transcrição e duração; marca G1/G2 para handoff humano.

## Tratamento de erro
| Falha | Comportamento |
|-------|---------------|
| LLM indisponível | segue com heurística local (mesmo roteiro) |
| Resposta não entendida | repete a pergunta; após 2 tentativas aceita a fala crua |
| BrasilAPI/ViaCEP fora | cai para Nominatim; senão confiança baixa |
| CEP confundível com telefone | CEP é removido antes de interpretar o telefone |
| Cidadão não confirma nada | o roteiro garante progresso (fallback por campo) |

## Fase 2/3 (telefonia)
`telephony.py` (SIP/190) → STT servidor (`faster-whisper`) → mesmo
`agent.process_turn` → TTS servidor. Integração com o CAD da PM para despacho real.
