"""Testes do fluxo de atendimento (formulário guiado)."""
from app.schemas import DialogState, Severity

FLUXO_OK = [
    "Bom dia, meu nome é João da Silva",
    "Estou sendo assaltado agora, tem um homem armado",
    "É pessoa física",
    "Avenida Paulista, CEP 01310-100, São Paulo",
    "número 1578",
    "Pode anotar 11 91234-5678",
    "não sei",                                   # referência é opcional
    "O homem está de camiseta preta, de moto, apontando a arma agora",
]


def test_fluxo_completo_gera_ocorrencia_g1(run):
    start, last = run(FLUXO_OK)
    o = last.occurrence
    assert last.state == DialogState.GENERATED
    assert o.occurrence_number and o.occurrence_number.endswith("000001")
    assert o.caller_name == "João da Silva"
    assert o.caller_type == "PF"
    assert o.cep == "01310100"
    assert o.city == "São Paulo"
    assert o.caller_phone == "11912345678"
    assert o.severity == Severity.G1
    assert last.human_handoff is True
    assert "1º BPM" in (o.responsible_agency or "")


def test_primeira_pergunta_e_o_nome(run):
    start, _ = run([])
    assert start.question_id == "nome"
    assert "nome" in start.greeting.lower()


def test_nao_sei_em_campo_obrigatorio_repete_pergunta(run, turn):
    start, _ = run([])
    resp = turn(start.call_id, "não sei")
    assert resp.question_id == "nome"
    assert "importante" in resp.reply.lower()


def test_nao_sei_em_opcional_pula(run, turn):
    start, _ = run(FLUXO_OK[:6])  # até telefone
    resp = turn(start.call_id, "não sei")
    assert resp.occurrence.location_reference is None
    assert resp.question_id == "fatos"


def test_cep_nao_vira_telefone(run):
    _start, last = run([
        "João", "assalto", "pessoa física",
        "Avenida Paulista, CEP 01310-100, São Paulo",
    ])
    assert last.occurrence.caller_phone is None
    assert last.occurrence.cep == "01310100"


def test_corrigir_telefone(run, turn):
    start, _ = run([
        "João", "assalto armado agora", "pessoa física", "Rua X 10",
        "11 91234-5678",
    ])
    r1 = turn(start.call_id, "corrigir telefone")
    assert r1.question_id == "telefone"
    r2 = turn(start.call_id, "21 98888-7777")
    assert r2.occurrence.caller_phone == "21988887777"


def test_repetir_os_dados_nao_avanca(run, turn):
    start, _ = run([])
    resp = turn(start.call_id, "repetir os dados")
    assert "Dados parciais" in resp.reply
    assert resp.question_id == "nome"


def test_numero_apos_gerar(run, turn):
    start, last = run(FLUXO_OK)
    num = last.occurrence.occurrence_number
    resp = turn(start.call_id, "qual o número da ocorrência?")
    assert num in resp.reply


def test_encerrar_apos_gerar(run, turn):
    start, _ = run(FLUXO_OK)
    resp = turn(start.call_id, "sim, pode encerrar")
    assert resp.finished is True
    assert resp.state == DialogState.CLOSED


def test_telefone_falado_por_extenso(run):
    _start, last = run([
        "João", "assalto", "pessoa física", "Rua X, CEP 01310-100",
        "número 10", "nove um dois três quatro cinco seis sete oito",
    ])
    assert last.occurrence.caller_phone == "912345678"


def test_cep_falado_por_extenso_resolve(run):
    _start, last = run([
        "João", "assalto", "pessoa física",
        "Rua das Flores, CEP zero um três um zero um zero zero",
    ])
    assert last.occurrence.cep == "01310100"
    assert last.occurrence.city == "São Paulo"


def test_numero_do_endereco_falado(run):
    _start, last = run([
        "João", "assalto", "pessoa física",
        "Rua das Flores número quinze",
    ])
    assert last.occurrence.location_number == "15"


def test_pergunta_estado_cidade_bairro_sem_cep(run):
    _start, last = run([
        "João", "assalto em andamento", "pessoa física",
        "Rua das Flores número quinze",
        "Sergipe", "Aracaju", "Centro",
        "11 91234-5678", "não sei", "assalto em andamento agora",
    ])
    o = last.occurrence
    assert o.location_state == "SE"
    assert o.city == "Aracaju"
    assert o.location_neighborhood == "Centro"
    assert "Aracaju" in (o.responsible_agency or "")


def test_cep_pula_estado_cidade_bairro(run):
    _start, last = run([
        "João", "assalto", "pessoa física",
        "Rua X, CEP 01310-100",
    ])
    assert last.question_id == "numero"   # pulou estado/cidade/bairro


def test_nao_pula_endereco_por_rua_solta(run):
    # "rua" citada no meio da fala NÃO pode virar endereço e pular a pergunta
    _start, last = run([
        "João", "tem um cara com uma arma passando na rua", "pessoa física",
    ])
    assert last.question_id == "endereco"
    assert last.occurrence.location_address is None


def test_pergunta_numero_do_local(run):
    _start, last = run([
        "João", "assalto", "pessoa física",
        "Rua X, CEP 01310-100",
        "número cento e vinte",
    ])
    assert last.occurrence.location_number == "120"


def test_anuncia_local_entendido(run):
    _start, last = run([
        "João", "assalto", "pessoa física",
        "Rua X, CEP 01310-100",
    ])
    assert "Você está em" in last.reply
    assert "01310100" in last.reply


def test_mensagem_de_despacho_a_equipe(run):
    _start, last = run(FLUXO_OK)
    assert "equipe tática" in last.reply.lower()
    assert "aguarde" in last.reply.lower()


def test_frase_de_local_nao_duplica_numero(run):
    _start, last = run([
        "João", "assalto", "pessoa física",
        "Rua das Flores número dez", "Sergipe", "Aracaju",
    ])
    assert "Você está em" in last.reply
    assert "número dez" not in last.reply.lower()
    assert "número 10" in last.reply.lower()

