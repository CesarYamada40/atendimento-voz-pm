"""Testes da matriz de gravidade (determinística)."""
from app.schemas import Occurrence, Severity
from app.severity import _score_to_severity, classify, detect_nature


def _occ(**kw) -> Occurrence:
    return Occurrence(call_id="t", **kw)


def test_assalto_armado_em_andamento_eh_g1():
    occ = _occ(weapon=True, ongoing=True)
    r = classify(occ, "estou sendo assaltado agora, homem armado")
    assert r.severity == Severity.G1
    assert r.score >= 80
    assert r.recommend_human is True


def test_perturbacao_eh_g4():
    r = classify(_occ(), "vizinho com som alto, festa até de madrugada")
    assert r.severity == Severity.G4


def test_orientacao_eh_g5():
    r = classify(_occ(), "queria uma informação sobre como fazer um boletim")
    assert r.severity == Severity.G5


def test_acidente_com_vitimas_eh_g2():
    r = classify(_occ(injuries="pessoa ferida no chão"), "acidente com feridos na avenida")
    assert r.severity in (Severity.G1, Severity.G2)  # base 70 + feridos
    assert r.recommend_human is True


def test_natureza_indefinida_vai_para_humano():
    r = classify(_occ(), "olá, boa tarde")
    assert r.severity == Severity.G3
    assert r.recommend_human is True


def test_detect_nature_por_gatilho():
    key, score, _label, _disp = detect_nature("tem um homem armado assaltando")
    assert key == "crime_em_andamento"
    assert score == 85


def test_furto_eh_g3():
    r = classify(_occ(), "levaram minha bicicleta, foi um furto")
    assert r.severity == Severity.G3


def test_esfaqueamento_eh_alta():
    r = classify(_occ(injuries="esfaqueado"), "o cara esfaqueou o outro e saiu correndo")
    assert r.severity in (Severity.G1, Severity.G2)
    assert r.recommend_human is True


def test_limites_de_score():
    assert _score_to_severity(80) == Severity.G1
    assert _score_to_severity(79) == Severity.G2
    assert _score_to_severity(60) == Severity.G2
    assert _score_to_severity(59) == Severity.G3
    assert _score_to_severity(40) == Severity.G3
    assert _score_to_severity(39) == Severity.G4
    assert _score_to_severity(20) == Severity.G4
    assert _score_to_severity(19) == Severity.G5
