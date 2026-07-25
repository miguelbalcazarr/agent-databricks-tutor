"""Schema y CRUD del progreso de un alumno (SQLite local, una instancia por alumno).

Distinto de tools/question_bank.py: cada alumno tiene su propio archivo,
nunca se comparte ni se commitea (ver .gitignore: data/progress/*.db).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PROGRESS_DIR = Path("data/progress")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    section_number INTEGER NOT NULL,
    objective_text TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    selected_option_index INTEGER NOT NULL,
    answered_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_attempts_section ON attempts(section_number);

CREATE TABLE IF NOT EXISTS exam_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    score INTEGER NOT NULL,
    total INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exam_attempt_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL REFERENCES exam_attempts(id),
    question_id INTEGER NOT NULL,
    question_order INTEGER NOT NULL,
    selected_option_index INTEGER,
    is_correct INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_exam_attempt_answers_attempt ON exam_attempt_answers(attempt_id);
"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_connection_for_student(
    student_id: str, certification_slug: str, progress_dir: Path = DEFAULT_PROGRESS_DIR
) -> sqlite3.Connection:
    return get_connection(progress_dir / student_id / f"{certification_slug}.db")


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


def record_attempt(
    conn: sqlite3.Connection,
    *,
    question_id: int,
    section_number: int,
    objective_text: str,
    is_correct: bool,
    selected_option_index: int,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO attempts (
            question_id, section_number, objective_text, is_correct,
            selected_option_index, answered_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            question_id,
            section_number,
            objective_text,
            1 if is_correct else 0,
            selected_option_index,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def record_exam_attempt(
    conn: sqlite3.Connection,
    *,
    language: str,
    score: int,
    total: int,
    started_at: datetime,
    finished_at: datetime,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO exam_attempts (language, score, total, started_at, finished_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (language, score, total, started_at.isoformat(), finished_at.isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def list_exam_attempts(conn: sqlite3.Connection) -> list[dict]:
    """Ordenado cronologicamente (mas viejo primero) — pensado para graficar
    una tendencia de mejora; quien liste para mostrar 'mas reciente arriba'
    debe invertir la lista."""
    rows = conn.execute("SELECT * FROM exam_attempts ORDER BY finished_at ASC").fetchall()
    return [dict(r) for r in rows]


def record_exam_attempt_answers(conn: sqlite3.Connection, *, attempt_id: int, answers: list[dict]) -> None:
    """`answers` es una lista de dicts con question_id, question_order,
    selected_option_index (puede ser None si no se respondio) e is_correct."""
    conn.executemany(
        """
        INSERT INTO exam_attempt_answers (
            attempt_id, question_id, question_order, selected_option_index, is_correct
        ) VALUES (:attempt_id, :question_id, :question_order, :selected_option_index, :is_correct)
        """,
        [{**a, "attempt_id": attempt_id} for a in answers],
    )
    conn.commit()


def get_exam_attempt_answers(conn: sqlite3.Connection, attempt_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM exam_attempt_answers WHERE attempt_id = ? ORDER BY question_order",
        (attempt_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_weak_topics(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            section_number,
            COUNT(*) AS attempt_count,
            SUM(is_correct) AS correct_count,
            CAST(SUM(is_correct) AS REAL) / COUNT(*) AS accuracy
        FROM attempts
        GROUP BY section_number
        ORDER BY accuracy ASC
        """
    ).fetchall()
    return [dict(r) for r in rows]
