# 05 · Matriz de gravidade

Classificação **determinística e auditável**. `score = base(natureza) + modificadores`,
limitado a 0–100. O LLM não altera o score; apenas redige a justificativa.

## Mapeamento score → gravidade
| Faixa | Gravidade | Significado | SLA (min) | Humano? |
|-------|-----------|-------------|-----------|---------|
| ≥ 80 | **G1** | Crítica — risco de vida iminente | 0 (imediato) | sim |
| 60–79 | **G2** | Alta | 5 | sim |
| 40–59 | **G3** | Média | 15 | — |
| 20–39 | **G4** | Baixa | 60 | — |
| < 20 | **G5** | Não policial / informativo | — | — |

## Naturezas (score base)
| Natureza | Score base | Despacho sugerido |
|----------|-----------|-------------------|
| Crime em andamento com risco | 85 | Despacho imediato, prioridade máxima |
| Violência / agressão em curso | 78 | Urgente — viatura + apoio (Maria da Penha) |
| Acidente com vítimas | 70 | Urgente — viatura + SAMU |
| Pessoa desaparecida | 64 | Prioritário — protocolo de desaparecidos |
| Ameaça / perseguição | 62 | Urgente |
| Acidente sem vítimas | 46 | Normal |
| Atitude suspeita | 42 | Normal — verificação preventiva |
| Dano ao patrimônio | 40 | Normal |
| Perturbação do sossego | 26 | Não emergencial |
| Orientação / informação | 12 | Encaminhamento não policial |
| Indefinida | 30 → G3 | Revisão humana |

## Modificadores
| Condição | Delta |
|----------|-------|
| Risco de vida declarado | +25 |
| Presença de arma | +20 |
| Ocorrência em andamento | +15 |
| Há feridos | +15 |

## Exemplo (validado)
Fala: *"estou sendo assaltado na Avenida Paulista, CEP 01310-100, está acontecendo
agora e ele está armado"* →
natureza `crime_em_andamento` (85) + em andamento (+15) + arma (+20) = **120 → 100 = G1**.
Responsável: *Polícia Militar — Batalhão da área de São Paulo/SP + solicitar apoio
da guarnição mais próxima*.

## Detecção de natureza
Correspondência por palavras-chave (lista em `severity.NATURE_MATRIX`). Natureza com
mais gatilhos vence. `severity.detect_nature` é determinística e testável; o LLM
pode contribuir com `nature` na extração, mas a matriz prevalece no score.

> A matriz vive em `app/severity.py` (`NATURE_MATRIX` + `MODIFIERS`). Ajustá-la é a
> forma prevista de calibrar o comportamento com a PM, sem tocar no diálogo.
