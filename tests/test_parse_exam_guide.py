import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.parse_exam_guide import find_objective, load_exam_guide

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAM_GUIDE_PDF = REPO_ROOT / "databricks-certified-data-engineer-associate-exam-guide-may-2026-000.pdf"


def test_parses_seven_sections_with_weights_summing_to_100():
    guide = load_exam_guide(EXAM_GUIDE_PDF)
    sections = guide["sections"]

    assert len(sections) == 7
    assert sum(s.weight_pct for s in sections) == 100
    assert sections[0].name == "Databricks Intelligence Platform"
    assert sections[1].weight_pct == 21
    assert all(s.objectives for s in sections)


def test_parses_five_sample_questions_with_four_options_each():
    guide = load_exam_guide(EXAM_GUIDE_PDF)
    sample_questions = guide["sample_questions"]

    assert len(sample_questions) == 5
    for question in sample_questions:
        assert len(question.options) == 4
        assert 0 <= question.correct_index < 4

    assert sample_questions[0].correct_index == 1  # Answers: 1. B
    assert sample_questions[2].correct_index == 0  # Answers: 3. A


def test_sample_question_objectives_match_an_outline_objective_verbatim():
    guide = load_exam_guide(EXAM_GUIDE_PDF)
    sections = guide["sections"]

    for question in guide["sample_questions"]:
        assert find_objective(sections, question.objective_text) is not None


def test_find_objective_returns_none_for_unknown_text():
    guide = load_exam_guide(EXAM_GUIDE_PDF)
    assert find_objective(guide["sections"], "this objective does not exist anywhere") is None
