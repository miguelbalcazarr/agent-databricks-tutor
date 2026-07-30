import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.certifications import get_certification
from tools.parse_exam_guide_microsoft import load_exam_guide

EXAM_GUIDE_PDF = get_certification("dp-700-fabric-data-engineer").exam_guide_pdf


def test_parses_three_sections_with_range_weights():
    guide = load_exam_guide(EXAM_GUIDE_PDF)
    sections = guide["sections"]

    assert len(sections) == 3
    assert [s.weight_pct for s in sections] == ["30-35", "30-35", "30-35"]
    assert sections[0].name == "Implement and manage an analytics solution"
    assert sections[1].name == "Ingest and transform data"
    assert sections[2].name == "Monitor and optimize an analytics solution"


def test_objective_counts_per_section():
    guide = load_exam_guide(EXAM_GUIDE_PDF)
    sections = guide["sections"]

    assert [len(s.objectives) for s in sections] == [18, 19, 17]
    assert sum(len(s.objectives) for s in sections) == 54


def test_objectives_are_prefixed_with_their_subgroup():
    guide = load_exam_guide(EXAM_GUIDE_PDF)
    sections = guide["sections"]

    assert "Configure security and governance: Implement dynamic data masking" in sections[0].objectives
    assert "Monitor Fabric items: Monitor semantic model refresh" in sections[2].objectives


def test_no_sample_questions_in_this_format():
    guide = load_exam_guide(EXAM_GUIDE_PDF)
    assert guide["sample_questions"] == []
