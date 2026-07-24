"""Logica pura del quiz: elegir una pregunta y calificar una respuesta.

Sin dependencia de Streamlit — testeable directamente.
"""
from __future__ import annotations

import random
import sqlite3

from tools.question_bank import get_questions_by_section


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
