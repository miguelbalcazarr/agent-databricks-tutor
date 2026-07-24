"""Logica pura del quiz: elegir una pregunta y calificar una respuesta.

Sin dependencia de Streamlit — testeable directamente.
"""
from __future__ import annotations

import random
import sqlite3

from tools.question_bank import get_questions, get_questions_by_section


def pick_exam_questions(conn: sqlite3.Connection, language: str, count: int = 45) -> list[dict]:
    """Selecciona preguntas para un simulacro tipo examen: como maximo una por
    objetivo (sin repetir), hasta `count`. Si el banco cubre menos objetivos
    que `count` (caso actual: 1 pregunta por objetivo), retorna todas las
    disponibles en vez de repetir — ver docs/contexto/decisiones.md D11."""
    by_objective: dict[tuple[int, int], list[dict]] = {}
    for q in get_questions(conn, language=language):
        by_objective.setdefault((q["section_number"], q["objective_index"]), []).append(q)

    keys = list(by_objective.keys())
    random.shuffle(keys)
    selected = [random.choice(by_objective[k]) for k in keys[:count]]
    random.shuffle(selected)
    return selected


def pick_question(
    conn: sqlite3.Connection, section_number: int | None = None, language: str | None = None
) -> dict | None:
    if section_number is not None:
        candidates = get_questions_by_section(conn, section_number, language=language)
    else:
        rows = conn.execute("SELECT DISTINCT section_number FROM questions").fetchall()
        candidates = []
        for row in rows:
            candidates.extend(get_questions_by_section(conn, row["section_number"], language=language))

    if not candidates:
        return None
    return random.choice(candidates)


def grade_answer(question: dict, selected_option_index: int) -> bool:
    return selected_option_index == question["correct_option_index"]
