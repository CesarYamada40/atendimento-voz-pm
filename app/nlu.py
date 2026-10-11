"""Utilitários de NLU para fala (pt-BR).

O STT costuma devolver números por extenso ("rua dez", "CEP sete zero zero
quatro zero zero um zero", "nove um dois três..."). Aqui convertemos fala em
dígitos para alimentar telefone, CEP e número do endereço.

Uso seletivo: só aplicamos onde dígitos fazem sentido (nunca em natureza/fatos,
para não estragar o texto livre).
"""
from __future__ import annotations

import re

_DIGITS = {"zero": "0", "um": "1", "dois": "2", "tres": "3", "quatro": "4",
           "cinco": "5", "seis": "6", "sete": "7", "oito": "8", "nove": "9"}
_TEENS = {"dez": 10, "onze": 11, "doze": 12, "treze": 13, "quatorze": 14,
          "catorze": 14, "quinze": 15, "dezesseis": 16, "dezessete": 17,
          "dezoito": 18, "dezenove": 19}
_TENS = {"vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50,
         "sessenta": 60, "setenta": 70, "oitenta": 80, "noventa": 90}
_HUNDREDS = {"cem": 100, "cento": 100, "duzentos": 200, "trezentos": 300,
             "quatrocentos": 400, "quinhentos": 500, "seiscentos": 600,
             "setecentos": 700, "oitocentos": 800, "novecentos": 900}

_ACCENT = (("á", "a"), ("ã", "a"), ("â", "a"), ("à", "a"), ("é", "e"), ("ê", "e"),
           ("í", "i"), ("ó", "o"), ("ô", "o"), ("õ", "o"), ("ú", "u"), ("ç", "c"))


def _norm(w: str) -> str:
    w = w.lower()
    for a, b in _ACCENT:
        w = w.replace(a, b)
    return w.strip(".,;:()!?")


def spoken_to_digits(text: str) -> str:
    """Converte palavras-número em dígitos. Ex.: 'sete zero zero' -> '700';
    'vinte e cinco' -> '25'; 'cento e cinquenta' -> '150'."""
    tokens = (text or "").split()
    out: list[str] = []
    i = 0
    n = len(tokens)
    while i < n:
        w = _norm(tokens[i])
        if w in _HUNDREDS:
            val = _HUNDREDS[w]
            j = i + 1
            if j < n and _norm(tokens[j]) == "e":
                j += 1
            if j < n and _norm(tokens[j]) in _TENS:
                val += _TENS[_norm(tokens[j])]
                j += 1
                if j < n and _norm(tokens[j]) == "e":
                    j += 1
                if j < n and _norm(tokens[j]) in _DIGITS and _norm(tokens[j]) != "zero":
                    val += int(_DIGITS[_norm(tokens[j])])
                    j += 1
            elif j < n and _norm(tokens[j]) in _TEENS:
                val += _TEENS[_norm(tokens[j])]
                j += 1
            elif j < n and _norm(tokens[j]) in _DIGITS and _norm(tokens[j]) != "zero":
                val += int(_DIGITS[_norm(tokens[j])])
                j += 1
            out.append(str(val))
            i = j
            continue
        if w in _TENS:
            val = _TENS[w]
            j = i + 1
            if j < n and _norm(tokens[j]) == "e":
                j += 1
            if j < n and _norm(tokens[j]) in _DIGITS and _norm(tokens[j]) != "zero":
                val += int(_DIGITS[_norm(tokens[j])])
                j += 1
            out.append(str(val))
            i = j
            continue
        if w in _TEENS:
            out.append(str(_TEENS[w]))
            i += 1
            continue
        if w in _DIGITS:
            digits = ""
            j = i
            while j < n and _norm(tokens[j]) in _DIGITS:
                digits += _DIGITS[_norm(tokens[j])]
                j += 1
            out.append(digits)
            i = j
            continue
        out.append(tokens[i])
        i += 1
    return " ".join(out)


def digits_only(text: str) -> str:
    return re.sub(r"\D", "", spoken_to_digits(text or ""))


_NUM_WORDS = set(_DIGITS) | set(_TEENS) | set(_TENS) | set(_HUNDREDS)


def _is_num(w: str) -> bool:
    n = _norm(w)
    return n.isdigit() or n in _NUM_WORDS


def collapse_repeats(text: str) -> str:
    """Colapsa repetições imediatas (o STT costuma repetir trechos).

    Não mexe em sequências numéricas faladas (para não corromper CEP/telefone):
    'zero um três um zero um zero zero' é preservado.
    """
    words = [w for w in (text or "").split() if w]
    # 1) remove palavras imediatamente repetidas (exceto números)
    out: list[str] = []
    for w in words:
        if out and _norm(w) == _norm(out[-1]) and not _is_num(w):
            continue
        out.append(w)
    # 2) colapsa frases adjacentes repetidas (nunca frases só de números)
    changed = True
    while changed:
        changed = False
        for size in range(min(10, len(out) // 2), 0, -1):
            i = 0
            while i + 2 * size <= len(out):
                a = [_norm(x) for x in out[i:i + size]]
                b = [_norm(x) for x in out[i + size:i + 2 * size]]
                if a == b and not all(_is_num(x) for x in out[i:i + size]):
                    del out[i + size:i + 2 * size]
                    changed = True
                else:
                    i += 1
    return " ".join(out)
