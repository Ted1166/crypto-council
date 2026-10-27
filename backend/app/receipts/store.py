import asyncio
import os
import sqlite3
from contextlib import closing
from datetime import datetime

from app.receipts.schema import BoardItem, Case, Event
from app.ryo.result import utcnow

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    direction TEXT,
    conviction INTEGER,
    change_score INTEGER NOT NULL DEFAULT 0,
    change_summary TEXT,
    crossexam_count INTEGER NOT NULL DEFAULT 0,
    has_running_exam INTEGER NOT NULL DEFAULT 0,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    case_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    kind TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (case_id, seq)
);
"""


class Store:
    def __init__(self, path: str) -> None:
        self._path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _init(self) -> None:
        directory = os.path.dirname(self._path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(SCHEMA)
            connection.commit()

    def _save_case(self, case: Case, change_score: int | None, change_summary: str | None) -> None:
        case.updated_at = utcnow()
        verdict = case.verdict
        running_exam = any(exam.status == "running" for exam in case.crossexams)
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO cases (id, symbol, status, created_at, updated_at, direction, conviction,
                                   change_score, change_summary, crossexam_count, has_running_exam, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, 0), ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    updated_at = excluded.updated_at,
                    direction = excluded.direction,
                    conviction = excluded.conviction,
                    change_score = COALESCE(?, cases.change_score),
                    change_summary = COALESCE(?, cases.change_summary),
                    crossexam_count = excluded.crossexam_count,
                    has_running_exam = excluded.has_running_exam,
                    payload = excluded.payload
                """,
                (
                    case.id,
                    case.symbol,
                    case.status,
                    case.created_at.isoformat(),
                    case.updated_at.isoformat(),
                    verdict.direction if verdict else None,
                    verdict.conviction if verdict else None,
                    change_score,
                    change_summary,
                    len(case.crossexams),
                    int(running_exam),
                    case.model_dump_json(),
                    change_score,
                    change_summary,
                ),
            )
            connection.commit()

    def _get_case(self, case_id: str) -> Case | None:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT payload FROM cases WHERE id = ?", (case_id,)).fetchone()
        return Case.model_validate_json(row["payload"]) if row else None

    def _board(self, limit: int) -> list[BoardItem]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, symbol, status, direction, conviction, change_score, change_summary,
                       crossexam_count, updated_at
                FROM cases ORDER BY change_score DESC, updated_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            BoardItem(
                id=row["id"],
                symbol=row["symbol"],
                status=row["status"],
                direction=row["direction"],
                conviction=row["conviction"],
                change_score=row["change_score"],
                change_summary=row["change_summary"],
                crossexam_count=row["crossexam_count"],
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]

    def _unfinished(self) -> list[Case]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT payload FROM cases WHERE status = 'running' OR has_running_exam = 1"
            ).fetchall()
        return [Case.model_validate_json(row["payload"]) for row in rows]

    def _append_event(self, case_id: str, kind: str, message: str) -> Event:
        created = utcnow()
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                """
                INSERT INTO events (case_id, seq, kind, message, created_at)
                VALUES (?, COALESCE((SELECT MAX(seq) FROM events WHERE case_id = ?), 0) + 1, ?, ?, ?)
                """,
                (case_id, case_id, kind, message, created.isoformat()),
            )
            seq = connection.execute(
                "SELECT seq FROM events WHERE rowid = ?", (cursor.lastrowid,)
            ).fetchone()["seq"]
            connection.commit()
        return Event(seq=seq, case_id=case_id, kind=kind, message=message, created_at=created)

    def _events_after(self, case_id: str, seq: int) -> list[Event]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT seq, case_id, kind, message, created_at FROM events "
                "WHERE case_id = ? AND seq > ? ORDER BY seq",
                (case_id, seq),
            ).fetchall()
        return [
            Event(
                seq=row["seq"],
                case_id=row["case_id"],
                kind=row["kind"],
                message=row["message"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    async def init(self) -> None:
        await asyncio.to_thread(self._init)

    async def save_case(
        self, case: Case, change_score: int | None = None, change_summary: str | None = None
    ) -> None:
        await asyncio.to_thread(self._save_case, case, change_score, change_summary)

    async def get_case(self, case_id: str) -> Case | None:
        return await asyncio.to_thread(self._get_case, case_id)

    async def board(self, limit: int = 100) -> list[BoardItem]:
        return await asyncio.to_thread(self._board, limit)

    async def unfinished(self) -> list[Case]:
        return await asyncio.to_thread(self._unfinished)

    async def append_event(self, case_id: str, kind: str, message: str) -> Event:
        return await asyncio.to_thread(self._append_event, case_id, kind, message)

    async def events_after(self, case_id: str, seq: int) -> list[Event]:
        return await asyncio.to_thread(self._events_after, case_id, seq)
