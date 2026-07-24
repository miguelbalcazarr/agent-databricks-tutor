import os
import sqlite3

from tools.certifications import Certification, get_certification
from tools.progress_store import get_connection_for_student, get_weak_topics, init_schema as init_progress_schema, record_attempt
from tools.question_bank import (
    get_connection as get_bank_connection,
    init_schema as init_bank_schema,
    list_languages,
    list_sections,
)
from tools.quiz_engine import grade_answer, pick_question

DEFAULT_LANGUAGE = "es"
DEFAULT_CERTIFICATION = "databricks-data-engineer-associate"


def get_certification_slug() -> str:
    return os.getenv("CERTIFICATION", DEFAULT_CERTIFICATION)


def get_student_id() -> str:
    return os.getenv("STUDENT_ID", "default")


def open_bank(cert: Certification) -> sqlite3.Connection:
    conn = get_bank_connection(cert.question_bank_db_path)
    init_bank_schema(conn)
    return conn


def open_progress(cert: Certification) -> sqlite3.Connection:
    conn = get_connection_for_student(get_student_id(), cert.slug)
    init_progress_schema(conn)
    return conn


def get_available_languages(bank_conn: sqlite3.Connection) -> list[str]:
    return list_languages(bank_conn)


def get_available_sections(bank_conn: sqlite3.Connection, language: str | None = None) -> list[dict]:
    return list_sections(bank_conn, language=language)


def answer_question(progress_conn: sqlite3.Connection, question: dict, selected_option_index: int) -> bool:
    is_correct = grade_answer(question, selected_option_index)
    record_attempt(
        progress_conn,
        question_id=question["id"],
        section_number=question["section_number"],
        objective_text=question["objective_text"],
        is_correct=is_correct,
        selected_option_index=selected_option_index,
    )
    return is_correct


def main() -> None:
    cert = get_certification(get_certification_slug())
    bank_conn = open_bank(cert)
    progress_conn = open_progress(cert)

    language = os.getenv("QUIZ_LANGUAGE", DEFAULT_LANGUAGE)
    sections = get_available_sections(bank_conn, language=language)
    if not sections:
        print("El banco de preguntas esta vacio. Corre tools/generate_questions.py primero.")
        raise SystemExit(1)

    print(f"Secciones disponibles (idioma={language}):")
    for section in sections:
        print(f"  {section['section_number']}. {section['section_name']} ({section['question_count']} preguntas)")

    question = pick_question(bank_conn, language=language)
    print("\nPregunta de ejemplo:")
    print(question["scenario_text"])
    for i, option in enumerate(question["options"]):
        print(f"  {chr(65 + i)}. {option}")

    weak_topics = get_weak_topics(progress_conn)
    if weak_topics:
        print("\nProgreso por seccion (de mas debil a mas fuerte):")
        for topic in weak_topics:
            print(f"  seccion {topic['section_number']}: {topic['accuracy']:.0%} ({topic['attempt_count']} intentos)")


if __name__ == "__main__":
    main()
