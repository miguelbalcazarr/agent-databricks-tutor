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
