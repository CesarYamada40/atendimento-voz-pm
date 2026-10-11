"""Testes do relatório de log por ocorrência."""
from app import report

FLUXO_OK = [
    "Bom dia, meu nome é João da Silva",
    "Estou sendo assaltado agora, tem um homem armado",
    "É pessoa física",
    "Avenida Paulista, CEP 01310-100, São Paulo",
    "número 1578",
    "Pode anotar 11 91234-5678",
    "não sei",
    "O homem está de camiseta preta, de moto, apontando a arma agora",
]


def test_relatorio_apos_fluxo_completo(run):
    start, _last = run(FLUXO_OK)
    rep = report.build_report(start.call_id)
    assert rep is not None
    c = rep["checks"]
    assert c["campos_obrigatorios_ok"] is True
    assert c["cep_identificado"] is True
    assert c["gravidade_calculada"] is True
    assert c["orgao_definido"] is True
    assert c["numero_gerado"] is True
    assert c["registrada"] is True
    assert rep["issues"] == []
    # registrou um passo por fala e todas as perguntas obrigatórias foram entendidas
    assert len(rep["steps"]) == len(FLUXO_OK)
    required = {"nome", "ocorrencia", "tipo", "endereco", "telefone", "fatos"}
    assert all(s["entendeu"] for s in rep["steps"] if s["pergunta"] in required)


def test_relatorio_aponta_pendencia_sem_cep(run):
    _start, _last = run([
        "João", "assalto", "pessoa física", "Rua das Flores número dez",
    ])
    rep = report.build_report(_start.call_id)
    assert rep["checks"]["cep_identificado"] is False
    assert any("CEP" in i for i in rep["issues"])


def test_relatorio_call_inexistente():
    assert report.build_report("naoexiste") is None
