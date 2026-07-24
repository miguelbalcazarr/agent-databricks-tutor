"""Schema y CRUD del banco de preguntas de certificacion (SQLite, persistente y compartido).

Distinto de tools/progress_store.py: este banco es el mismo para todos los
alumnos y se commitea al repo; el progreso es una DB separada por alumno.

Cada pregunta tiene un idioma (`language`, "es" o "en") — se generan como
filas independientes por objetivo, no como traduccion literal una de otra.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB_PATH = Path("data/question_bank.db")
DEFAULT_LANGUAGE = "es"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_number INTEGER NOT NULL,
    section_name TEXT NOT NULL,
    objective_index INTEGER NOT NULL,
    objective_text TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'es',
    scenario_text TEXT NOT NULL,
    options_json TEXT NOT NULL,
    correct_option_index INTEGER NOT NULL,
    explanation TEXT NOT NULL,
    source_urls_json TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    generation_model TEXT NOT NULL
);
"""

_CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_questions_section ON questions(section_number);
CREATE INDEX IF NOT EXISTS idx_questions_objective ON questions(section_number, objective_index);
CREATE INDEX IF NOT EXISTS idx_questions_language ON questions(language);
"""


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_CREATE_TABLE)

    # Migracion: bancos creados antes de que existiera la columna `language`
    # (CREATE TABLE IF NOT EXISTS no la agrega sola a una tabla ya existente).
    # Debe correr ANTES de crear el indice de `language`, o el CREATE INDEX
    # falla contra una tabla vieja que todavia no tiene esa columna.
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(questions)")}
    if "language" not in columns:
        conn.execute(f"ALTER TABLE questions ADD COLUMN language TEXT NOT NULL DEFAULT '{DEFAULT_LANGUAGE}'")

    conn.executescript(_CREATE_INDEXES)
    conn.commit()


def validate_question(parsed: dict) -> tuple[bool, list[str]]:
    errors = []

    scenario = parsed.get("scenario")
    if not scenario or not str(scenario).strip():
        errors.append("scenario vacio")

    options = parsed.get("options")
    if not isinstance(options, list) or len(options) < 2:
        errors.append("options debe ser una lista con al menos 2 elementos")
    elif any(not str(o).strip() for o in options):
        errors.append("hay una opcion vacia")

    correct_index = parsed.get("correct_index")
    if not isinstance(correct_index, int) or isinstance(options, list) and not (0 <= correct_index < len(options)):
        errors.append("correct_index invalido o fuera de rango")

    explanation = parsed.get("explanation")
    if not explanation or not str(explanation).strip():
        errors.append("explanation vacia")

    return (len(errors) == 0, errors)


def insert_question(
    conn: sqlite3.Connection,
    *,
    section_number: int,
    section_name: str,
    objective_index: int,
    objective_text: str,
    scenario_text: str,
    options: list[str],
    correct_option_index: int,
    explanation: str,
    source_urls: list[str],
    generation_model: str,
    language: str = DEFAULT_LANGUAGE,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO questions (
            section_number, section_name, objective_index, objective_text, language,
            scenario_text, options_json, correct_option_index, explanation,
            source_urls_json, generated_at, generation_model
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            section_number,
            section_name,
            objective_index,
            objective_text,
            language,
            scenario_text,
            json.dumps(options, ensure_ascii=False),
            correct_option_index,
            explanation,
            json.dumps(source_urls, ensure_ascii=False),
            datetime.now(timezone.utc).isoformat(),
            generation_model,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def delete_question(conn: sqlite3.Connection, question_id: int) -> None:
    conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    conn.commit()


def _row_to_dict(row: sqlite3.Row) -> dict:
    question = dict(row)
    question["options"] = json.loads(question.pop("options_json"))
    question["source_urls"] = json.loads(question.pop("source_urls_json"))
    return question


def count_questions_for_objective(
    conn: sqlite3.Connection, section_number: int, objective_index: int, language: str = DEFAULT_LANGUAGE
) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM questions WHERE section_number = ? AND objective_index = ? AND language = ?",
        (section_number, objective_index, language),
    ).fetchone()
    return row["n"]


def get_questions_by_section(
    conn: sqlite3.Connection, section_number: int, language: str | None = None
) -> list[dict]:
    if language is None:
        rows = conn.execute(
            "SELECT * FROM questions WHERE section_number = ? ORDER BY id", (section_number,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM questions WHERE section_number = ? AND language = ? ORDER BY id",
            (section_number, language),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_question(conn: sqlite3.Connection, question_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_sections(conn: sqlite3.Connection, language: str | None = None) -> list[dict]:
    if language is None:
        rows = conn.execute(
            """
            SELECT section_number, section_name, COUNT(*) AS question_count
            FROM questions GROUP BY section_number, section_name ORDER BY section_number
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT section_number, section_name, COUNT(*) AS question_count
            FROM questions WHERE language = ? GROUP BY section_number, section_name ORDER BY section_number
            """,
            (language,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_languages(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT DISTINCT language FROM questions ORDER BY language").fetchall()
    return [row["language"] for row in rows]
