"""Persistência em SQLite (ocorrências + transcrição por turno)."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import List, Optional

from .config import settings
from .schemas import Occurrence

_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


def _connect() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
        _conn = sqlite3.connect(settings.db_path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def init_db() -> None:
    with _lock:
        conn = _connect()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS occurrences (
                call_id   TEXT PRIMARY KEY,
                id        INTEGER,
                created_at TEXT,
                severity  TEXT,
                status    TEXT,
                data      TEXT
            );
            CREATE TABLE IF NOT EXISTS turns (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id   TEXT,
                role      TEXT,
                state     TEXT,
                text      TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id     TEXT,
                created_at  TEXT,
                state       TEXT,
                question_id TEXT,
                text        TEXT,
                snapshot    TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_ev_call ON events(call_id);
            CREATE INDEX IF NOT EXISTS idx_occ_severity ON occurrences(severity);
            CREATE INDEX IF NOT EXISTS idx_occ_status ON occurrences(status);
            """
        )
        conn.commit()


def save_occurrence(occ: Occurrence) -> Occurrence:
    with _lock:
        conn = _connect()
        cur = conn.execute(
            "INSERT OR IGNORE INTO occurrences (call_id, created_at, severity, status, data) "
            "VALUES (?,?,?,?,?)",
            (occ.call_id, occ.created_at, occ.severity.value if occ.severity else None,
             occ.status, occ.model_dump_json()),
        )
        if occ.id is None:
            occ.id = cur.lastrowid
        conn.execute(
            "UPDATE occurrences SET id=?, severity=?, status=?, data=? WHERE call_id=?",
            (occ.id, occ.severity.value if occ.severity else None, occ.status,
             occ.model_dump_json(), occ.call_id),
        )
        conn.commit()
    return occ


def get_occurrence(call_id: str) -> Optional[Occurrence]:
    with _lock:
        row = _connect().execute(
            "SELECT data FROM occurrences WHERE call_id=?", (call_id,)
        ).fetchone()
    return Occurrence(**json.loads(row["data"])) if row else None


def list_occurrences(limit: int = 50) -> List[Occurrence]:
    with _lock:
        rows = _connect().execute(
            "SELECT data FROM occurrences ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [Occurrence(**json.loads(r["data"])) for r in rows]


def next_protocol() -> str:
    """Gera o número da ocorrência (protocolo sequencial por ano)."""
    with _lock:
        row = _connect().execute("SELECT COUNT(*) AS c FROM occurrences").fetchone()
    seq = row["c"] or 1
    return f"{datetime.now().year}-{seq:06d}"


def add_turn(call_id: str, role: str, state: str, text: str, created_at: str) -> None:
    with _lock:
        conn = _connect()
        conn.execute(
            "INSERT INTO turns (call_id, role, state, text, created_at) VALUES (?,?,?,?,?)",
            (call_id, role, state, text, created_at),
        )
        conn.commit()


def add_event(call_id: str, state: str, question_id: str, text: str,
              snapshot: dict) -> None:
    """Registra um evento de processamento (para o relatório por ocorrência)."""
    with _lock:
        conn = _connect()
        conn.execute(
            "INSERT INTO events (call_id, created_at, state, question_id, text, snapshot) "
            "VALUES (?,?,?,?,?,?)",
            (call_id, datetime.now(timezone.utc).isoformat(), state, question_id,
             text, json.dumps(snapshot, ensure_ascii=False)),
        )
        conn.commit()


def get_events(call_id: str) -> List[dict]:
    with _lock:
        rows = _connect().execute(
            "SELECT created_at, state, question_id, text, snapshot FROM events "
            "WHERE call_id=? ORDER BY id", (call_id,)
        ).fetchall()
    out = []
    for r in rows:
        try:
            snap = json.loads(r["snapshot"]) if r["snapshot"] else {}
        except (ValueError, TypeError):
            snap = {}
        out.append({"created_at": r["created_at"], "state": r["state"],
                    "question_id": r["question_id"], "text": r["text"], "snapshot": snap})
    return out


def get_turns(call_id: str) -> List[dict]:
    with _lock:
        rows = _connect().execute(
            "SELECT role, state, text, created_at FROM turns WHERE call_id=? ORDER BY id",
            (call_id,)
        ).fetchall()
    return [dict(r) for r in rows]
