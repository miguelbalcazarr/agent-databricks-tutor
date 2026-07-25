import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.progress_store import (
    get_connection,
    get_connection_for_student,
    get_exam_attempt_answers,
    get_weak_topics,
    init_schema,
    list_exam_attempts,
    record_attempt,
    record_exam_attempt,
    record_exam_attempt_answers,
)


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


def test_record_exam_attempt_persists_row(tmp_path):
    conn = _make_conn(tmp_path)
    started = datetime(2026, 7, 25, 10, 0, tzinfo=timezone.utc)
    finished = started + timedelta(minutes=45)

    attempt_id = record_exam_attempt(
        conn, language="es", score=36, total=45, started_at=started, finished_at=finished
    )

    row = conn.execute("SELECT * FROM exam_attempts WHERE id = ?", (attempt_id,)).fetchone()
    assert row["language"] == "es"
    assert row["score"] == 36
    assert row["total"] == 45
    assert row["started_at"] == started.isoformat()
    assert row["finished_at"] == finished.isoformat()


def test_list_exam_attempts_orders_chronologically(tmp_path):
    conn = _make_conn(tmp_path)
    base = datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc)

    record_exam_attempt(conn, language="es", score=30, total=45, started_at=base, finished_at=base + timedelta(hours=1))
    record_exam_attempt(
        conn,
        language="es",
        score=38,
        total=45,
        started_at=base + timedelta(days=1),
        finished_at=base + timedelta(days=1, hours=1),
    )

    attempts = list_exam_attempts(conn)

    assert [a["score"] for a in attempts] == [30, 38]


def test_record_and_get_exam_attempt_answers_preserves_order(tmp_path):
    conn = _make_conn(tmp_path)
    started = datetime(2026, 7, 25, 9, 0, tzinfo=timezone.utc)
    attempt_id = record_exam_attempt(
        conn, language="es", score=1, total=2, started_at=started, finished_at=started + timedelta(minutes=10)
    )

    record_exam_attempt_answers(
        conn,
        attempt_id=attempt_id,
        answers=[
            {"question_id": 101, "question_order": 0, "selected_option_index": 1, "is_correct": 1},
            {"question_id": 102, "question_order": 1, "selected_option_index": None, "is_correct": 0},
        ],
    )

    answers = get_exam_attempt_answers(conn, attempt_id)

    assert [a["question_id"] for a in answers] == [101, 102]
    assert answers[0]["is_correct"] == 1
    assert answers[1]["selected_option_index"] is None


def test_get_exam_attempt_answers_empty_for_unknown_attempt(tmp_path):
    conn = _make_conn(tmp_path)

    assert get_exam_attempt_answers(conn, 999) == []
