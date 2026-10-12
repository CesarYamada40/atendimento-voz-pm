"""Testes do fluxo de atendimento (ordem: estado→cidade→bairro→rua→nº→CEP + confirmação)."""
from app.schemas import DialogState, Severity

FLUXO_OK = [
    "Bom dia, meu nome é João da Silva",           # nome
    "Estou sendo assaltado agora, tem um homem armado",  # ocorrencia
    "É pessoa física",                             # tipo
    "São Paulo",                                   # estado -> SP
    "São Paulo",                                   # cidade
    "Bela Vista",                                  # bairro
    "Avenida Paulista",                            # rua
    "número 1578",                                 # numero
    "01310-100",                                   # cep
    "sim",                                         # confirma o local
    "Pode anotar 11 91234-5678",                   # telefone
    "não sei",                                     # referencia
    "O homem está de camiseta preta, apontando a arma agora",  # fatos
]


def test_fluxo_completo_gera_ocorrencia_g1(run):
    _start, last = run(FLUXO_OK)
    o = last.occurrence
    assert last.state == DialogState.GENERATED
    assert o.occurrence_number and o.occurrence_number.endswith("000001")
    assert o.caller_name == "João da Silva"
    assert o.caller_type == "PF"
    assert o.location_state == "SP"
    assert o.city == "São Paulo"
    assert o.location_neighborhood == "Bela Vista"
    assert o.location_address == "Avenida Paulista"
    assert o.location_number == "1578"
    assert o.cep == "01310100"
    assert o.caller_phone == "11912345678"
    assert o.severity == Severity.G1
    assert last.human_handoff is True
    assert "1º BPM" in (o.responsible_agency or "")


def test_primeira_pergunta_e_o_nome(run):
    start, _ = run([])
    assert start.question_id == "nome"


def test_nao_sei_em_campo_obrigatorio_insiste_e_pula(run, turn):
    start, _ = run([])
    r1 = turn(start.call_id, "não sei")
    assert r1.question_id == "nome"                    # insiste 1x
    r2 = turn(start.call_id, "não sei")
    assert r2.question_id == "ocorrencia"              # 2ª vez: pula (não trava)


def test_nao_sei_em_opcional_pula(run, turn):
    start, _ = run(FLUXO_OK[:12])  # até telefone
    resp = turn(start.call_id, "não sei")
    assert resp.occurrence.location_reference is None
    assert resp.question_id == "fatos"


def test_cep_resolve_e_nao_vira_telefone(run):
    _start, last = run([
        "João", "assalto", "pessoa física",
        "São Paulo", "São Paulo", "Bela Vista", "Rua X", "número 10", "01310-100",
    ])
    assert last.occurrence.cep == "01310100"
    assert last.occurrence.caller_phone is None


def test_corrigir_telefone(run, turn):
    start, _ = run(FLUXO_OK[:11])  # até telefone
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
        "João", "assalto", "pessoa física", "São Paulo", "São Paulo", "Bela Vista",
        "Avenida Paulista", "número 10", "01310-100", "sim",
        "nove um dois três quatro cinco seis sete oito",
    ])
    assert last.occurrence.caller_phone == "912345678"


def test_cep_falado_por_extenso_resolve(run):
    _start, last = run([
        "João", "assalto", "pessoa física", "São Paulo", "São Paulo", "Bela Vista",
        "Rua das Flores", "número 10", "zero um três um zero um zero zero",
    ])
    assert last.occurrence.cep == "01310100"
    assert last.occurrence.city == "São Paulo"


def test_numero_do_endereco_falado(run):
    _start, last = run([
        "João", "assalto", "pessoa física", "São Paulo", "São Paulo", "Bela Vista",
        "Rua das Flores número quinze",
    ])
    assert last.occurrence.location_number == "15"


def test_estado_cidade_bairro_rua_sem_cep(run):
    _start, last = run([
        "João", "assalto em andamento", "pessoa física",
        "Sergipe", "Aracaju", "Centro", "Rua das Flores", "número 10", "não sei",
        "sim", "11 91234-5678", "não sei", "assalto em andamento agora",
    ])
    o = last.occurrence
    assert o.location_state == "SE"
    assert o.city == "Aracaju"
    assert o.location_neighborhood == "Centro"
    assert o.cep == "49015110"                     # descoberto por rua+cidade
    assert "Aracaju" in (o.responsible_agency or "")


def test_confirma_local_identificado(run):
    _start, last = run(FLUXO_OK[:9])   # até o CEP
    assert "Localizei o endereço" in last.reply
    assert "Está correto" in last.reply
    assert "01310100" in last.reply


def test_descobre_cep_pelo_endereco_e_confirma(run):
    _start, last = run([
        "João", "assalto em andamento", "pessoa física",
        "Sergipe", "Aracaju", "Centro", "Rua das Flores", "número 10", "não sei",
    ])
    assert "Localizei o endereço" in last.reply
    assert last.occurrence.cep == "49015110"
    assert "Rua das Flores" in last.reply


def test_nao_confirma_local_volta_para_endereco(run, turn):
    start, _ = run(FLUXO_OK[:9])
    resp = turn(start.call_id, "não está certo")
    assert resp.question_id == "endereco"
    assert resp.occurrence.cep is None


def test_bairro_nao_sei_nao_trava_e_acha_cep(run):
    _start, last = run([
        "João", "assalto em andamento", "pessoa física",
        "Sergipe", "Aracaju", "não sei", "Rua das Flores", "número 10", "não sei",
    ])
    assert "Localizei o endereço" in last.reply
    assert last.occurrence.cep == "49015110"


def test_nao_pula_endereco_por_rua_solta(run):
    _start, last = run([
        "João", "tem um cara com uma arma passando na rua", "pessoa física",
        "São Paulo", "São Paulo", "Bela Vista",
    ])
    assert last.question_id == "endereco"
    assert last.occurrence.location_address is None


def test_mensagem_de_despacho_a_equipe(run):
    _start, last = run(FLUXO_OK)
    assert "equipe tática" in last.reply.lower()
    assert "aguarde" in last.reply.lower()


def test_final_curto_com_rua_e_numero(run):
    _start, last = run(FLUXO_OK)
    o = last.occurrence
    assert o.occurrence_number in last.reply
    assert o.location_address in last.reply
    assert "Aguarde" in last.reply


def test_tipo_fisica_nao_vira_empresa(run):
    _start, last = run(["João", "assalto", "física"])
    assert last.occurrence.caller_type == "PF"
    assert last.occurrence.org_name is None


def test_apos_gerar_nao_polui_os_fatos(run, turn):
    start, last = run(FLUXO_OK)
    desc = last.occurrence.description
    r = turn(start.call_id, "show de bola maluca")
    assert r.occurrence.description == desc
