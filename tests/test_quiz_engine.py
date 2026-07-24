import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.question_bank import get_connection, init_schema, insert_question
from tools.quiz_engine import grade_answer, pick_exam_questions, pick_question


def test_pick_question_returns_none_for_empty_bank(tmp_path):
    conn = get_connection(tmp_path / "bank.db")
    init_schema(conn)
    assert pick_question(conn) is None


def test_pick_question_filters_by_section(tmp_path):
    conn = get_connection(tmp_path / "bank.db")
    init_schema(conn)
    insert_question(
        conn, section_number=2, section_name="Data Ingestion and Loading", objective_index=0,
        objective_text="obj", scenario_text="s2", options=["A", "B"], correct_option_index=0,
        explanation="e", source_urls=[], generation_model="gpt-4o-mini",
    )
    insert_question(
        conn, section_number=6, section_name="Troubleshooting", objective_index=2,
        objective_text="obj", scenario_text="s6", options=["A", "B"], correct_option_index=1,
        explanation="e", source_urls=[], generation_model="gpt-4o-mini",
    )

    question = pick_question(conn, section_number=6)
    assert question["scenario_text"] == "s6"


def test_pick_question_filters_by_language(tmp_path):
    conn = get_connection(tmp_path / "bank.db")
    init_schema(conn)
    insert_question(
        conn, section_number=6, section_name="Troubleshooting", objective_index=2,
        objective_text="obj", scenario_text="Escenario en espanol", options=["A", "B"],
        correct_option_index=0, explanation="e", source_urls=[], generation_model="gpt-4o-mini",
        language="es",
    )
    insert_question(
        conn, section_number=6, section_name="Troubleshooting", objective_index=2,
        objective_text="obj", scenario_text="Scenario in English", options=["A", "B"],
        correct_option_index=0, explanation="e", source_urls=[], generation_model="gpt-4o-mini",
        language="en",
    )

    question = pick_question(conn, language="en")
    assert question["scenario_text"] == "Scenario in English"


def test_grade_answer():
    question = {"correct_option_index": 2}
    assert grade_answer(question, 2) is True
    assert grade_answer(question, 0) is False


def test_pick_exam_questions_returns_empty_for_empty_bank(tmp_path):
    conn = get_connection(tmp_path / "bank.db")
    init_schema(conn)
    assert pick_exam_questions(conn, language="es", count=45) == []


def test_pick_exam_questions_never_repeats_an_objective(tmp_path):
    conn = get_connection(tmp_path / "bank.db")
    init_schema(conn)
    for section, objective in [(1, 0), (1, 1), (2, 0)]:
        insert_question(
            conn, section_number=section, section_name="Seccion", objective_index=objective,
            objective_text="obj", scenario_text=f"s{section}-{objective}", options=["A", "B"],
            correct_option_index=0, explanation="e", source_urls=[], generation_model="gpt-4o-mini",
        )

    questions = pick_exam_questions(conn, language="es", count=45)

    assert len(questions) == 3
    seen = {(q["section_number"], q["objective_index"]) for q in questions}
    assert len(seen) == 3


def test_pick_exam_questions_respects_count_cap(tmp_path):
    conn = get_connection(tmp_path / "bank.db")
    init_schema(conn)
    for objective in range(5):
        insert_question(
            conn, section_number=1, section_name="Seccion", objective_index=objective,
            objective_text="obj", scenario_text=f"s{objective}", options=["A", "B"],
            correct_option_index=0, explanation="e", source_urls=[], generation_model="gpt-4o-mini",
        )

    assert len(pick_exam_questions(conn, language="es", count=3)) == 3


def test_pick_exam_questions_filters_by_language(tmp_path):
    conn = get_connection(tmp_path / "bank.db")
    init_schema(conn)
    insert_question(
        conn, section_number=1, section_name="Seccion", objective_index=0,
        objective_text="obj", scenario_text="es", options=["A", "B"], correct_option_index=0,
        explanation="e", source_urls=[], generation_model="gpt-4o-mini", language="es",
    )
    insert_question(
        conn, section_number=1, section_name="Seccion", objective_index=1,
        objective_text="obj", scenario_text="en", options=["A", "B"], correct_option_index=0,
        explanation="e", source_urls=[], generation_model="gpt-4o-mini", language="en",
    )

    questions = pick_exam_questions(conn, language="es", count=45)

    assert len(questions) == 1
    assert questions[0]["scenario_text"] == "es"
