"""Testes do NLU de números falados (pt-BR)."""
from app import nlu


def test_digitos_falados_individuais():
    assert nlu.spoken_to_digits("sete zero zero quatro zero zero um zero") == "70040010"


def test_dezenas_e_unidades():
    assert nlu.spoken_to_digits("vinte e cinco") == "25"
    assert nlu.spoken_to_digits("trinta e um") == "31"


def test_centenas():
    assert nlu.spoken_to_digits("cento e cinquenta") == "150"
    assert nlu.spoken_to_digits("duzentos e dez") == "210"
    assert nlu.spoken_to_digits("cem") == "100"


def test_dezenas_teen():
    assert nlu.spoken_to_digits("onze") == "11"
    assert nlu.spoken_to_digits("quinze") == "15"


def test_em_contexto_de_endereco():
    assert nlu.spoken_to_digits("rua das flores numero dez") == "rua das flores numero 10"


def test_preserva_texto_livre():
    assert nlu.spoken_to_digits("homem armado em uma moto") == "homem armado em uma moto"


def test_digits_only():
    assert nlu.digits_only("CEP sete zero zero quatro zero zero um zero") == "70040010"


def test_colapsa_repeticao_de_frase():
    assert nlu.collapse_repeats(
        "tem um cara brigando aqui tem um cara brigando aqui") == "tem um cara brigando aqui"


def test_colapsa_palavra_repetida():
    assert nlu.collapse_repeats("a CEP a CEP a CEP") == "a CEP"
    assert nlu.collapse_repeats("muito muito bom") == "muito bom"


def test_nao_mexe_em_texto_normal():
    assert nlu.collapse_repeats("homem armado em uma moto") == "homem armado em uma moto"


def test_colapsa_nao_corrompe_digitos_falados():
    assert nlu.collapse_repeats("zero um três um zero um zero zero") == \
        "zero um três um zero um zero zero"
    assert nlu.collapse_repeats("nove nove um dois") == "nove nove um dois"
