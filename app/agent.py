"""Agente de atendimento por voz: formulário guiado de ocorrência.

O atendimento segue um roteiro fixo de perguntas. A cada fala do cidadão:
  1. entende a resposta (LLM + heurística);
  2. preenche o campo correspondente;
  3. pula perguntas já respondidas;
  4. ao final, gera a ocorrência com número (protocolo) e lê os dados.

Comandos do cidadão a qualquer momento: "repetir os dados", "não entendi"
(repere a pergunta), "não sei" (pula opcional), e, após gerar, "número".
"""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from . import llm, location, nlu, severity, storage
from .schemas import (
    CallStartRequest,
    CallStartResponse,
    DialogState,
    Occurrence,
    TurnRequest,
    TurnResponse,
)


@dataclass
class Question:
    id: str
    field: str
    prompt: str
    label: str
    required: bool = True


QUESTIONS: List[Question] = [
    Question("nome", "caller_name",
             "Qual é o seu nome?", "Nome"),
    Question("ocorrencia", "nature",
             "Qual é a ocorrência? O que está acontecendo?", "Ocorrência"),
    Question("tipo", "caller_type",
             "A ocorrência é para pessoa física ou empresa?", "Pessoa física ou empresa"),
    Question("endereco", "location_address",
             "Qual o endereço da ocorrência? Rua, número e bairro, ou o CEP.", "Endereço"),
    Question("numero", "location_number",
             "Qual o número do endereço? Se não souber, diga um número aproximado.",
             "Número", required=False),
    Question("estado", "location_state",
             "Qual o estado, a UF?", "Estado"),
    Question("cidade", "city",
             "Qual a cidade?", "Cidade"),
    Question("bairro", "location_neighborhood",
             "Qual o bairro?", "Bairro"),
    Question("telefone", "caller_phone",
             "Qual é um telefone para contato?", "Telefone"),
    Question("referencia", "location_reference",
             "Tem algum ponto de referência?", "Ponto de referência", required=False),
    Question("fatos", "description",
             "Agora descreva os fatos com detalhes.", "Descrição dos fatos"),
]

_Q_BY_ID = {q.id: q for q in QUESTIONS}

# --- Comandos do cidadão -------------------------------------------------------
_REPEAT_DATA = ["repetir os dados", "repita os dados", "repete os dados", "ler os dados",
                "leia os dados", "quais os dados", "quais dados", "resumo", "resuma",
                "repete tudo", "repetir tudo", "o que ja foi anotado", "le os dados"]
_REPEAT_Q = ["nao entendi", "nao ouvi", "como assim", "repete", "repita", "de novo",
             "pode repetir", "nao entendi nada"]
_DONT_KNOW = ["nao sei", "nao tenho", "sem informacao", "desconheco", "nao lembro",
              "nao tenho isso", "nao possuo"]
_NUMBER = ["numero da ocorrencia", "numero da ocorrencia", "numero ocorrencia", "numero",
           "protocolo", "qual o numero"]
_END = ["pode encerrar", "encerrar", "mais nada", "so isso", "obrigado", "obrigada",
        "era isso", "tchau", "ate logo"]
_AFFIRM = {"sim", "isso", "correto", "positivo", "pode", "certo", "confirmo", "exato",
           "ok", "beleza", "aham", "uhum"}
_NEG = {"nao", "errado", "incorreto", "negativo"}

# --- Heurísticas ---------------------------------------------------------------
_ADDR_RE = re.compile(
    r"((?:rua|r\.|avenida|av\.|travessa|alameda|praça|praca|rodovia|estrada|est\.|"
    r"servid[aã]o|beco|viela|largo)\b[^.,;?\n]{0,120})", re.IGNORECASE)
_CEP_RE = re.compile(r"\b(\d{5})-?(\d{3})\b")
_PHONE_CUES = ["telefone", "fone", "celular", "contato", "whatsapp", "zap", "anota",
               "anote", "pode anotar", "meu numero", "ligar", "chama no"]
_WEAPON = ["arma", "armado", "revolver", "pistola", "fuzil", "espingarda", "faca",
           "facão", "facao", "munição", "municao"]
_LIFE = ["morrendo", "morte", "morrer", "socorro", "sangue", "sangrando", "ferido",
         "baleado", "atirou", "atirando", "vai matar", "risco"]
_ONGOING = ["agora", "nesse momento", "neste momento", "acontecendo", "ainda",
            "continua", "nesse instante"]
_INJURY = ["ferido", "ferida", "machucado", "machucada", "sangrando", "baleado",
           "esfaqueado", "esfaqueada", "esfaqueou", "facada"]
_NAME_STOP = {"meu", "nome", "e", "sou", "o", "a", "aqui", "me", "chamo", "pode",
              "chamar", "de", "esta", "está", "falando", "quem", "ao", "telefone",
              "bom", "boa", "dia", "tarde", "noite", "ola", "olá", "alô", "alo"}
_PJ = ["empresa", "companhia", "cnpj", "ltda", "mei", "pessoa juridica", "juridica",
       "firma", "estabelecimento", "comercio", "loja", "pj"]
_PF = ["pessoa fisica", "fisica", "particular", "individual", "eu mesmo", "eu mesma",
       "pf"]


@dataclass
class CallSession:
    call_id: str
    occurrence: Occurrence
    state: DialogState = DialogState.COLLECTING
    current_qid: Optional[str] = "nome"
    skipped: Set[str] = field(default_factory=set)
    attempts: Dict[str, int] = field(default_factory=dict)
    loc_confirmed: bool = False
    awaiting_location_confirm: bool = False
    transcript: List[str] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)

    def current_question(self) -> Optional[Question]:
        return _Q_BY_ID.get(self.current_qid or "")


_sessions: Dict[str, CallSession] = {}


def _norm(text: str) -> str:
    t = (text or "").lower()
    for a, b in (("á", "a"), ("ã", "a"), ("â", "a"), ("à", "a"), ("é", "e"),
                 ("ê", "e"), ("í", "i"), ("ó", "o"), ("ô", "o"), ("õ", "o"),
                 ("ú", "u"), ("ç", "c")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def _has(nt: str, phrases: List[str]) -> bool:
    return any(p in nt for p in phrases)


def _is_filled(occ: Occurrence, q: Question) -> bool:
    return bool(getattr(occ, q.field, None))


def _next_question(occ: Occurrence, session: CallSession) -> Optional[Question]:
    for q in QUESTIONS:
        if q.id in session.skipped or _is_filled(occ, q):
            continue
        return q
    return None


# --- Parsers por campo ---------------------------------------------------------
def _parse_name(text: str) -> Optional[str]:
    words = [w for w in re.split(r"\s+", text.strip()) if w]
    while words and _norm(words[0]).strip(",.") in _NAME_STOP:
        words.pop(0)
    name = " ".join(words[:5]).strip(" ,.!-")
    return name or None


def _parse_phone(text: str, asked: bool = False) -> Optional[str]:
    """Extrai telefone; converte números falados e remove CEP para não confundir."""
    t = _CEP_RE.sub(" ", nlu.spoken_to_digits(text or ""))
    cue = asked or any(c in _norm(text) for c in _PHONE_CUES)
    cand = None
    for m in re.finditer(r"\d[\d\s().-]{6,}\d", t):
        d = re.sub(r"\D", "", m.group(0))
        if 10 <= len(d) <= 11:
            return d
        if cue and 8 <= len(d) <= 9 and cand is None:
            cand = d
    return cand


def _parse_address_number(text: str) -> Optional[str]:
    """Extrai o número do imóvel (ex.: 'número quinze' -> '15'), ignorando o CEP."""
    conv = nlu.spoken_to_digits(text or "")
    conv = re.sub(r"\b\d{5}-?\d{3}\b", " ", conv)       # remove CEP (01310-100)
    conv = re.sub(r"\b\d{2}\.\d{3}-?\d{3}\b", " ", conv)  # remove CEP com ponto
    m = re.search(r"(?:numero|num|n[º°.])\s*(\d{1,5})", conv, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"(?:rua|avenida|av|travessa|alameda|estrada|rodovia)\b"
                  r"[^\d]{0,60}?\b(\d{1,5})\b", conv, re.IGNORECASE)
    return m.group(1) if m else None


def _parse_pf_pj(text: str) -> Optional[str]:
    t = _norm(text)
    if any(k in t for k in _PJ):
        return "PJ"
    if any(k in t for k in _PF):
        return "PF"
    return None


def _parse_org(text: str) -> Optional[str]:
    m = re.search(r"(?:empresa|estabelecimento|loja|com[eé]rcio|companhia)\s+"
                  r"(?:chamada\s+|denominada\s+|de\s+)?([A-ZÀ-Ú][\w\s&.-]{2,40})",
                  text or "")
    return m.group(1).strip() if m else None


# --- Preenchimento -------------------------------------------------------------
async def _fill_field(occ: Occurrence, q: Question, text: str) -> None:
    label = q.label
    llm_val = await llm.extract_answer(label, text)

    if q.id == "nome":
        v = llm_val or _parse_name(text)
        if v:
            occ.caller_name = v
    elif q.id == "ocorrencia":
        key, _score, label_nat, _disp = severity.detect_nature(text)
        if llm_val:
            occ.nature = llm_val
        elif key != "indefinido":
            occ.nature = label_nat
    elif q.id == "tipo":
        tipo = _parse_pf_pj(llm_val or text)
        if tipo:
            occ.caller_type = tipo
        elif llm_val:
            occ.caller_type = llm_val
        # nome da empresa só faz sentido quando é pessoa jurídica
        if occ.caller_type == "PJ":
            org = _parse_org(text) or llm_val
            if org and _norm(org) not in {"empresa", "pessoa juridica", "pj",
                                          "companhia", "firma", "estabelecimento"}:
                occ.org_name = org
    elif q.id == "endereco":
        m = _ADDR_RE.search(text)
        addr = llm_val or (m.group(1).strip() if m else None) or text.strip()
        occ.location_address = nlu.collapse_repeats(nlu.spoken_to_digits(addr))
        num = _parse_address_number(text)
        if num:
            occ.location_number = num

    elif q.id == "numero":
        m = re.search(r"\d{1,5}", nlu.spoken_to_digits(text))
        occ.location_number = m.group(0) if m else nlu.collapse_repeats(text.strip())

    elif q.id == "estado":
        occ.location_state = location.parse_uf(llm_val or text) or (llm_val or text).strip()
    elif q.id == "cidade":
        occ.city = nlu.collapse_repeats(llm_val or text.strip())
    elif q.id == "bairro":
        occ.location_neighborhood = nlu.collapse_repeats(llm_val or text.strip())

    elif q.id == "telefone":
        occ.caller_phone = _parse_phone(text, asked=True) or llm_val or text.strip()

    elif q.id == "referencia":
        occ.location_reference = nlu.collapse_repeats(llm_val or text.strip())

    elif q.id == "fatos":
        occ.description = nlu.collapse_repeats(llm_val or text.strip())

    # Garantia de progresso: se nada foi extraído, usa a fala crua (sem repetições).
    if not _is_filled(occ, q):
        fallback = nlu.collapse_repeats(text.strip())
        if q.id == "tipo":
            occ.caller_type = _parse_pf_pj(fallback) or fallback
        elif fallback:
            setattr(occ, q.field, fallback)


def _autofill(occ: Occurrence, text: str) -> None:
    """Só extrai sinais de risco (arma/risco/andamento/feridos).

    Não preenche endereço/telefone/número aqui: isso é papel das perguntas,
    para não capturar um "rua" solto no meio da fala e pular a pergunta.
    """
    t = _norm(text)
    if any(w in t for w in _WEAPON):
        occ.weapon = True
    if any(w in t for w in _LIFE):
        occ.life_risk = True
    if any(w in t for w in _ONGOING):
        occ.ongoing = True
    if not occ.injuries and any(w in t for w in _INJURY):
        occ.injuries = text.strip()


async def _maybe_resolve(occ: Occurrence, session: "CallSession") -> None:
    last = session.transcript[-1] if session.transcript else ""
    full = " ".join(session.transcript)
    cep = location.find_cep(nlu.spoken_to_digits(last)) or \
        location.find_cep(nlu.spoken_to_digits(full))
    if occ.location_source and (not cep or cep == occ.cep):
        return
    raw = occ.location_address or occ.location_reference or ""
    if not cep and not raw:
        return
    geo = await location.resolve(raw or cep, cep_hint=cep)
    if not geo.resolved:
        return
    occ.cep = geo.cep or occ.cep
    occ.location_number = geo.number or occ.location_number
    occ.location_neighborhood = geo.neighborhood or occ.location_neighborhood
    occ.city = geo.city or occ.city
    occ.location_state = location.parse_uf(geo.state) or geo.state or occ.location_state
    occ.location_lat = geo.lat if geo.lat is not None else occ.location_lat
    occ.location_lng = geo.lng if geo.lng is not None else occ.location_lng
    occ.location_source = geo.source
    occ.location_confidence = geo.confidence
    if geo.street:
        occ.location_address = geo.street          # guarda o nome da rua
    elif cep or not occ.location_address:
        occ.location_address = geo.display or occ.location_address


# --- Leitura dos dados ---------------------------------------------------------
def _field_line(occ: Occurrence, q: Question) -> str:
    if q.id == "tipo":
        val = occ.caller_type or "não informado"
        if occ.org_name:
            val += f" ({occ.org_name})"
        return f"{q.label}: {val}"
    if q.id == "endereco":
        val = occ.location_address or "não informado"
        if occ.cep:
            val += f" — CEP {occ.cep}"
        return f"Endereço: {val}"
    return f"{q.label}: {getattr(occ, q.field, None) or 'não informado'}"


def _readback(occ: Occurrence) -> str:
    lines = [_field_line(occ, q) for q in QUESTIONS]
    if occ.occurrence_number:
        head = f"Ocorrência {occ.occurrence_number}. "
    else:
        head = "Dados parciais. "
    return head + " | ".join(lines) + "."


def _location_complete(occ: Occurrence) -> bool:
    return bool(occ.location_address or occ.cep) and bool(occ.city and occ.location_state)


def _confirm_phrase(occ: Occurrence) -> str:
    """Frase do local identificado para o cidadão confirmar."""
    parts = []
    if occ.location_address:
        parts.append(occ.location_address)
    if occ.location_number and str(occ.location_number) not in (occ.location_address or ""):
        parts.append(f"número {occ.location_number}")
    if occ.location_neighborhood:
        parts.append(f"bairro {occ.location_neighborhood}")
    if occ.city or occ.location_state:
        parts.append(f"{occ.city or ''}/{occ.location_state or ''}".strip("/"))
    if occ.cep:
        parts.append(f"CEP {occ.cep}")
    return ", ".join(parts) if parts else "endereço ainda não identificado"


async def _resolve_address_to_cep(occ: Occurrence) -> None:
    """Sem CEP: descobre a rua canônica e o CEP a partir de rua/bairro/cidade/UF."""
    if occ.cep or not (occ.location_address and occ.city and occ.location_state):
        return
    geo = await location.resolve_address(
        occ.location_state, occ.city, occ.location_address, occ.location_neighborhood)
    if geo.resolved:
        occ.cep = geo.cep or occ.cep
        occ.location_address = geo.street or occ.location_address
        occ.location_neighborhood = geo.neighborhood or occ.location_neighborhood
        occ.location_source = geo.source
        occ.location_confidence = geo.confidence


def _final_summary(occ: Occurrence) -> str:
    local = occ.location_address or "não informado"
    return (f"Número {occ.occurrence_number}; nome {occ.caller_name}; "
            f"tipo {occ.caller_type or 'não informado'}; ocorrência {occ.nature}; "
            f"endereço {local} (CEP {occ.cep or 'não identificado'}); "
            f"bairro {occ.location_neighborhood or 'não informado'}; "
            f"cidade {occ.city or 'não informada'}/{occ.location_state or '??'}; "
            f"telefone {occ.caller_phone}; referência {occ.location_reference or 'não informada'}; "
            f"fatos: {occ.description}")


# --- Respostas -----------------------------------------------------------------
def _respond(session: CallSession, reply: str, finished: bool = False,
             classification=None) -> TurnResponse:
    occ = session.occurrence
    storage.save_occurrence(occ)
    storage.add_turn(session.call_id, "bot", session.state.value, reply, occ.created_at)
    q = session.current_question() if session.state == DialogState.COLLECTING else None
    return TurnResponse(
        call_id=session.call_id,
        state=session.state,
        reply=reply,
        occurrence=occ,
        question_id=q.id if q else None,
        question=q.prompt if q else None,
        classification=classification,
        human_handoff=bool(classification and classification.recommend_human),
        finished=finished,
    )


async def _generate(session: CallSession) -> TurnResponse:
    occ = session.occurrence
    occ.occurrence_number = storage.next_protocol()
    occ.status = "registrada"
    occ.transcript = nlu.collapse_repeats(" ".join(session.transcript))
    occ.duration_seconds = round(time.time() - session.started_at, 1)

    classification = severity.classify(occ, occ.transcript or occ.description or "")
    occ.severity = classification.severity
    occ.severity_label = classification.label
    occ.severity_reason = classification.reason

    geo = location.GeoResult(
        raw="", resolved=True, cep=occ.cep, street=occ.location_address,
        number=occ.location_number, neighborhood=occ.location_neighborhood,
        city=occ.city, state=occ.location_state, lat=occ.location_lat,
        lng=occ.location_lng, display=occ.location_address, source=occ.location_source)
    occ.responsible_agency = location.responsible_agency(
        geo, occ.nature, classification.severity.value)
    occ.recommended_dispatch = occ.responsible_agency

    justified = await llm.justify(_final_summary(occ), classification.label)
    if justified:
        occ.severity_reason = justified.strip()

    storage.save_occurrence(occ)
    session.state = DialogState.GENERATED
    rua = occ.location_address or "local não informado"
    reply = (f"Ocorrência {occ.occurrence_number} registrada. "
             f"{rua}. Repassando para a equipe tática. Aguarde.")
    return _respond(session, reply, classification=classification)


def _after_generated(session: CallSession, text: str, nt: str) -> TurnResponse:
    occ = session.occurrence
    if _has(nt, _REPEAT_DATA):
        reply = _readback(occ) + " Deseja mais alguma coisa?"
        return _respond(session, reply)
    if _has(nt, _NUMBER):
        reply = f"O número da sua ocorrência é {occ.occurrence_number}. " \
                "A ocorrência segue para o despacho. Posso encerrar?"
        return _respond(session, reply)
    if _has(nt, _END) or any(w in _norm(nt).split() for w in _AFFIRM) or len(nt) <= 3:
        session.state = DialogState.CLOSED
        occ.status = "encerrada"
        reply = f"Atendimento encerrado. Ocorrência {occ.occurrence_number} registrada. Obrigado."
        return _respond(session, reply, finished=True)
    # informação extra após gerar: apenas reconhece, sem poluir o registro
    reply = ("Sua ocorrência já está registrada. "
             "Deseja repetir os dados, saber o número ou encerrar?")
    return _respond(session, reply)


# --- Fluxo principal -----------------------------------------------------------
def start_call(req: CallStartRequest) -> CallStartResponse:
    call_id = uuid.uuid4().hex[:12]
    occ = Occurrence(call_id=call_id, caller_phone=req.caller_phone)
    session = CallSession(call_id=call_id, occurrence=occ, state=DialogState.COLLECTING,
                          current_qid="nome")
    _sessions[call_id] = session
    storage.save_occurrence(occ)
    first = session.current_question()
    greeting = ("Central de emergência da Polícia Militar, esta ligação está sendo "
                "gravada. Vou registrar sua ocorrência. " + (first.prompt if first else ""))
    storage.add_turn(call_id, "bot", session.state.value, greeting, occ.created_at)
    return CallStartResponse(
        call_id=call_id, greeting=greeting, state=session.state,
        question_id=first.id if first else None,
        question=first.prompt if first else None, occurrence=occ)


def _get_or_create(call_id: str) -> CallSession:
    if call_id in _sessions:
        return _sessions[call_id]
    occ = storage.get_occurrence(call_id) or Occurrence(call_id=call_id)
    session = CallSession(call_id=call_id, occurrence=occ)
    _sessions[call_id] = session
    return session


_SNAP_FIELDS = ("caller_name", "nature", "caller_type", "location_address",
                "location_number", "location_neighborhood", "city", "location_state",
                "cep", "caller_phone", "location_reference", "description")


def _log_event(session: CallSession, text: str, answered_qid: Optional[str],
               resp: TurnResponse) -> None:
    occ = session.occurrence
    snapshot = {
        "answered": answered_qid,
        "next_question": resp.question_id,
        "fields": {k: getattr(occ, k, None) for k in _SNAP_FIELDS},
        "location_source": occ.location_source,
        "location_confidence": occ.location_confidence,
        "severity": occ.severity.value if occ.severity else None,
        "occurrence_number": occ.occurrence_number,
    }
    storage.add_event(session.call_id, resp.state.value, resp.question_id, text, snapshot)


async def process_turn(req: TurnRequest) -> TurnResponse:
    session = _get_or_create(req.call_id)
    occ = session.occurrence
    text = nlu.collapse_repeats((req.text or "").strip())
    nt = _norm(text)
    session.transcript.append(text)
    storage.add_turn(req.call_id, "cidadao", session.state.value, text, occ.created_at)
    answered = session.current_qid
    resp = await _process(session, text, nt)
    _log_event(session, text, answered, resp)
    return resp


async def _process(session: CallSession, text: str, nt: str) -> TurnResponse:
    occ = session.occurrence
    # Já gerada?
    if session.state in (DialogState.GENERATED, DialogState.CLOSED):
        return _after_generated(session, text, nt)

    # Confirmação do local identificado (evita viatura no endereço errado)
    if session.awaiting_location_confirm:
        session.awaiting_location_confirm = False
        afirmou = any(w in nt.split() for w in _AFFIRM) and \
            not any(w in nt.split() for w in _NEG)
        if afirmou:
            session.loc_confirmed = True
            nxt = _next_question(occ, session)
            if nxt is None:
                return await _generate(session)
            session.current_qid = nxt.id
            return _respond(session, "Local confirmado. " + nxt.prompt)
        # não confirmou: limpa o local e volta a perguntar o endereço
        for f in ("location_address", "cep", "location_number",
                  "location_neighborhood", "location_source", "location_confidence"):
            setattr(occ, f, None)
        session.current_qid = "endereco"
        return _respond(session, "Sem problema, vamos corrigir. " +
                        _Q_BY_ID["endereco"].prompt)

    # Meta-comandos
    if _has(nt, _REPEAT_DATA):
        return _respond(session, _readback(occ))
    if _has(nt, _REPEAT_Q):
        q = session.current_question()
        return _respond(session, q.prompt if q else "Pode repetir, por favor?")
    if _has(nt, _DONT_KNOW):
        q = session.current_question()
        if q and not q.required:
            session.skipped.add(q.id)
            nxt = _next_question(occ, session)
            if nxt is None:
                return await _generate(session)
            session.current_qid = nxt.id
            return _respond(session, f"Tudo bem. {nxt.prompt}")
        if q:
            return _respond(session, f"Essa informação é importante. {q.prompt}")

    # Corrigir um campo específico
    if "corrigir" in nt or "errei" in nt or "errado" in nt:
        target = _match_question(nt)
        if target:
            session.current_qid = target.id
            return _respond(session, f"Sem problema. {target.prompt}")
        return _respond(session, "Qual dado você quer corrigir? Nome, ocorrência, "
                                 "tipo, endereço, telefone, referência ou fatos?")

    # Responde a pergunta atual
    q = session.current_question() or _next_question(occ, session)
    if q:
        session.current_qid = q.id
        await _fill_field(occ, q, text)
    _autofill(occ, text)
    await _maybe_resolve(occ, session)

    nxt = _next_question(occ, session)
    if nxt is None:
        return await _generate(session)

    # Antes de seguir para o telefone, confirma o local identificado.
    if nxt.id == "telefone" and not session.loc_confirmed:
        if not occ.cep:
            await _resolve_address_to_cep(occ)
        session.awaiting_location_confirm = True
        session.current_qid = "confirmar_local"
        reply = (f"Localizei o endereço: {_confirm_phrase(occ)}. "
                 "Está correto? Diga sim para confirmar ou não para corrigir.")
        return _respond(session, reply)

    session.current_qid = nxt.id
    return _respond(session, nxt.prompt)


def _match_question(nt: str) -> Optional[Question]:
    mapping = {
        "nome": "nome", "ocorrencia": "ocorrencia", "aconteceu": "ocorrencia",
        "tipo": "tipo", "empresa": "tipo", "pessoa": "tipo", "fisica": "tipo",
        "endereco": "endereco", "rua": "endereco", "local": "endereco",
        "numero": "numero", "número": "numero",
        "estado": "estado", "uf": "estado",
        "cidade": "cidade", "municipio": "cidade",
        "bairro": "bairro",
        "telefone": "telefone", "fone": "telefone",
        "referencia": "referencia",
        "fatos": "fatos", "descricao": "fatos", "historico": "fatos",
    }
    for key, qid in mapping.items():
        if key in nt:
            return _Q_BY_ID[qid]
    return None


def get_session(call_id: str) -> Optional[CallSession]:
    if call_id in _sessions:
        return _sessions[call_id]
    occ = storage.get_occurrence(call_id)
    return CallSession(call_id=call_id, occurrence=occ) if occ else None
