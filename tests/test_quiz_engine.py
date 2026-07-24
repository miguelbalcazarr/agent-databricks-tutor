import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.question_bank import get_connection, init_schema, insert_question
from tools.quiz_engine import grade_answer, pick_question


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
