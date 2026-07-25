"""Logica pura del quiz: elegir una pregunta y calificar una respuesta.

Sin dependencia de Streamlit — testeable directamente.
"""
from __future__ import annotations

import random
import sqlite3

from tools.question_bank import get_questions, get_questions_by_section


def pick_exam_questions(
    conn: sqlite3.Connection, language: str, count: int = 45, per_objective: int = 2
) -> list[dict]:
    """Selecciona preguntas para un simulacro tipo examen: como maximo
    `per_objective` preguntas distintas por objetivo (nunca la misma
    repetida), hasta `count` en total, sin sesgo hacia ninguna seccion. Si el
    banco cubre menos objetivos/preguntas que `count`, retorna todas las
    disponibles en vez de repetir — ver docs/contexto/decisiones.md D11."""
    by_objective: dict[tuple[int, int], list[dict]] = {}
    for q in get_questions(conn, language=language):
        by_objective.setdefault((q["section_number"], q["objective_index"]), []).append(q)

    selected: list[dict] = []
    for questions in by_objective.values():
        random.shuffle(questions)
        selected.extend(questions[:per_objective])

    random.shuffle(selected)
    return selected[:count]


def pick_question(
    conn: sqlite3.Connection,
    section_number: int | None = None,
    language: str | None = None,
    weak_topics: list[dict] | None = None,
) -> dict | None:
    """Elige una pregunta. Si `section_number` es None y se pasa
    `weak_topics` (de tools/progress_store.py::get_weak_topics), la
    seleccion se sesga hacia las secciones con menor accuracy en vez de ser
    uniforme — pensado solo para Practica, nunca para Simulacro (que debe
    reproducir el examen real sin sesgo, ver docs/contexto/decisiones.md
    D11)."""
    if section_number is not None:
        candidates = get_questions_by_section(conn, section_number, language=language)
        if not candidates:
            return None
        return random.choice(candidates)

    rows = conn.execute("SELECT DISTINCT section_number FROM questions").fetchall()
    by_section = {
        row["section_number"]: get_questions_by_section(conn, row["section_number"], language=language)
        for row in rows
    }
    by_section = {section: qs for section, qs in by_section.items() if qs}
    if not by_section:
        return None

    if not weak_topics:
        candidates = [q for qs in by_section.values() for q in qs]
        return random.choice(candidates)

    accuracy_by_section = {t["section_number"]: t["accuracy"] for t in weak_topics}
    sections = list(by_section.keys())
    # Secciones sin intentos todavia (no estan en weak_topics) reciben peso
    # medio: no sabemos si son debiles, no corresponde tratarlas como fuertes.
    weights = [max(1.0 - accuracy_by_section.get(s, 0.5), 0.1) for s in sections]
    chosen_section = random.choices(sections, weights=weights, k=1)[0]
    return random.choice(by_section[chosen_section])


def grade_answer(question: dict, selected_option_index: int) -> bool:
    return selected_option_index == question["correct_option_index"]
