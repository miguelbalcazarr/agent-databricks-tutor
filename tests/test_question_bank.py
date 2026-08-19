import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.question_bank import (
    count_questions_for_objective,
    delete_question,
    get_connection,
    get_question,
    get_questions_by_section,
    init_schema,
    insert_question,
    list_languages,
    list_sections,
    shuffle_options,
    validate_question,
)


def _make_conn(tmp_path):
    conn = get_connection(tmp_path / "bank.db")
    init_schema(conn)
    return conn


def test_insert_and_round_trip(tmp_path):
    conn = _make_conn(tmp_path)

    question_id = insert_question(
        conn,
        section_number=6,
        section_name="Troubleshooting, Monitoring, and Optimization",
        objective_index=2,
        objective_text="Identify common performance bottlenecks such as data skew...",
        scenario_text="Un data engineer nota que un job tarda el doble...",
        options=["Opcion A", "Opcion B", "Opcion C", "Opcion D"],
        correct_option_index=1,
        explanation="La opcion B es correcta porque...",
        source_urls=["https://docs.databricks.com/aws/en/optimizations/aqe"],
        generation_model="gpt-4o-mini",
    )

    question = get_question(conn, question_id)
    assert question["section_number"] == 6
    assert question["options"] == ["Opcion A", "Opcion B", "Opcion C", "Opcion D"]
    assert question["correct_option_index"] == 1
    assert question["source_urls"] == ["https://docs.databricks.com/aws/en/optimizations/aqe"]


def test_count_and_get_by_section(tmp_path):
    conn = _make_conn(tmp_path)
    assert count_questions_for_objective(conn, 2, 0) == 0

    insert_question(
        conn,
        section_number=2,
        section_name="Data Ingestion and Loading",
        objective_index=0,
        objective_text="Enable and detail data ingestion patterns...",
        scenario_text="Escenario 1",
        options=["A", "B"],
        correct_option_index=0,
        explanation="Explicacion 1",
        source_urls=[],
        generation_model="gpt-4o-mini",
    )
    insert_question(
        conn,
        section_number=2,
        section_name="Data Ingestion and Loading",
        objective_index=0,
        objective_text="Enable and detail data ingestion patterns...",
        scenario_text="Escenario 2",
        options=["A", "B"],
        correct_option_index=1,
        explanation="Explicacion 2",
        source_urls=[],
        generation_model="gpt-4o-mini",
    )

    assert count_questions_for_objective(conn, 2, 0) == 2
    questions = get_questions_by_section(conn, 2)
    assert len(questions) == 2
    assert [q["scenario_text"] for q in questions] == ["Escenario 1", "Escenario 2"]

    sections = list_sections(conn)
    assert sections == [{"section_number": 2, "section_name": "Data Ingestion and Loading", "question_count": 2}]


def test_init_schema_migrates_bank_created_before_language_column_existed(tmp_path):
    conn = get_connection(tmp_path / "old_bank.db")
    # Esquema viejo, sin `language` — simula un banco creado antes de este cambio.
    conn.execute(
        """
        CREATE TABLE questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_number INTEGER NOT NULL,
            section_name TEXT NOT NULL,
            objective_index INTEGER NOT NULL,
            objective_text TEXT NOT NULL,
            scenario_text TEXT NOT NULL,
            options_json TEXT NOT NULL,
            correct_option_index INTEGER NOT NULL,
            explanation TEXT NOT NULL,
            source_urls_json TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            generation_model TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO questions (
            section_number, section_name, objective_index, objective_text,
            scenario_text, options_json, correct_option_index, explanation,
            source_urls_json, generated_at, generation_model
        ) VALUES (6, 'Troubleshooting', 2, 'obj', 'Escenario viejo', '["A", "B"]', 0, 'e', '[]', 'ts', 'gpt-4o-mini')
        """
    )
    conn.commit()

    init_schema(conn)  # no debe fallar, y debe agregar language='es' por default

    question = get_question(conn, 1)
    assert question["language"] == "es"
    assert question["scenario_text"] == "Escenario viejo"


def test_language_defaults_to_es_and_can_be_set_to_en(tmp_path):
    conn = _make_conn(tmp_path)

    es_id = insert_question(
        conn, section_number=6, section_name="Troubleshooting", objective_index=2,
        objective_text="obj", scenario_text="Escenario en espanol", options=["A", "B"],
        correct_option_index=0, explanation="e", source_urls=[], generation_model="gpt-4o-mini",
    )
    en_id = insert_question(
        conn, section_number=6, section_name="Troubleshooting", objective_index=2,
        objective_text="obj", scenario_text="Scenario in English", options=["A", "B"],
        correct_option_index=0, explanation="e", source_urls=[], generation_model="gpt-4o-mini",
        language="en",
    )

    assert get_question(conn, es_id)["language"] == "es"
    assert get_question(conn, en_id)["language"] == "en"


def test_count_and_get_by_section_filter_by_language(tmp_path):
    conn = _make_conn(tmp_path)
    insert_question(
        conn, section_number=2, section_name="Data Ingestion and Loading", objective_index=0,
        objective_text="obj", scenario_text="Escenario ES", options=["A", "B"],
        correct_option_index=0, explanation="e", source_urls=[], generation_model="gpt-4o-mini",
        language="es",
    )
    insert_question(
        conn, section_number=2, section_name="Data Ingestion and Loading", objective_index=0,
        objective_text="obj", scenario_text="Scenario EN", options=["A", "B"],
        correct_option_index=0, explanation="e", source_urls=[], generation_model="gpt-4o-mini",
        language="en",
    )

    assert count_questions_for_objective(conn, 2, 0, language="es") == 1
    assert count_questions_for_objective(conn, 2, 0, language="en") == 1

    es_questions = get_questions_by_section(conn, 2, language="es")
    assert [q["scenario_text"] for q in es_questions] == ["Escenario ES"]

    both_questions = get_questions_by_section(conn, 2)
    assert len(both_questions) == 2

    assert list_languages(conn) == ["en", "es"]

    es_sections = list_sections(conn, language="es")
    assert es_sections == [{"section_number": 2, "section_name": "Data Ingestion and Loading", "question_count": 1}]


def test_delete_question_removes_it(tmp_path):
    conn = _make_conn(tmp_path)
    question_id = insert_question(
        conn, section_number=6, section_name="Troubleshooting", objective_index=2,
        objective_text="obj", scenario_text="Escenario", options=["A", "B"],
        correct_option_index=0, explanation="e", source_urls=[], generation_model="gpt-4o-mini",
    )
    assert get_question(conn, question_id) is not None

    delete_question(conn, question_id)

    assert get_question(conn, question_id) is None


def test_shuffle_options_preserves_the_correct_option_content():
    options = ["Opcion A", "Opcion B", "Opcion C", "Opcion D"]
    correct_index = 0

    shuffled_options, new_correct_index = shuffle_options(options, correct_index)

    assert sorted(shuffled_options) == sorted(options)
    assert shuffled_options[new_correct_index] == "Opcion A"


def test_shuffle_options_varies_the_correct_position_over_many_runs():
    positions = {
        shuffle_options(["A", "B", "C", "D"], 0)[1]
        for _ in range(200)
    }

    assert positions == {0, 1, 2, 3}


def test_validate_question_flags_missing_fields():
    ok, errors = validate_question({"scenario": "", "options": ["A"], "correct_index": 5, "explanation": ""})
    assert ok is False
    assert len(errors) == 4


def test_validate_question_passes_for_well_formed_question():
    ok, errors = validate_question({
        "scenario": "Un escenario valido",
        "options": ["A", "B", "C", "D"],
        "correct_index": 2,
        "explanation": "Una explicacion valida",
    })
    assert ok is True
    assert errors == []
