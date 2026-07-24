import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.progress_store import get_connection, get_connection_for_student, get_weak_topics, init_schema, record_attempt


def _make_conn(tmp_path):
    conn = get_connection(tmp_path / "progress.db")
    init_schema(conn)
    return conn


def test_record_attempt_persists_row(tmp_path):
    conn = _make_conn(tmp_path)
    attempt_id = record_attempt(
        conn,
        question_id=1,
        section_number=6,
        objective_text="Identify common performance bottlenecks...",
        is_correct=True,
        selected_option_index=1,
    )
    row = conn.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
    assert row["is_correct"] == 1
    assert row["section_number"] == 6


def test_get_weak_topics_orders_by_accuracy_ascending(tmp_path):
    conn = _make_conn(tmp_path)

    # section 2: 1/2 correct (50%)
    record_attempt(conn, question_id=1, section_number=2, objective_text="obj", is_correct=True, selected_option_index=0)
    record_attempt(conn, question_id=2, section_number=2, objective_text="obj", is_correct=False, selected_option_index=1)
    # section 6: 2/2 correct (100%)
    record_attempt(conn, question_id=3, section_number=6, objective_text="obj", is_correct=True, selected_option_index=0)
    record_attempt(conn, question_id=4, section_number=6, objective_text="obj", is_correct=True, selected_option_index=0)

    weak_topics = get_weak_topics(conn)

    assert [t["section_number"] for t in weak_topics] == [2, 6]
    assert weak_topics[0]["accuracy"] == 0.5
    assert weak_topics[1]["accuracy"] == 1.0
    assert weak_topics[0]["attempt_count"] == 2


def test_get_connection_for_student_nests_by_student_and_certification(tmp_path):
    conn = get_connection_for_student("alice", "some-cert", progress_dir=tmp_path)
    conn.close()

    assert (tmp_path / "alice" / "some-cert.db").exists()
