import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.certifications import get_certification
from tools.exam_guide_parsers import load_exam_guide_for


def test_dispatches_databricks_v1_without_regression():
    cert = get_certification("databricks-data-engineer-associate")
    guide = load_exam_guide_for(cert)

    assert len(guide["sections"]) == 7
    assert sum(s.weight_pct for s in guide["sections"]) == 100
    assert len(guide["sample_questions"]) == 5


def test_dispatches_microsoft_study_guide_v1():
    cert = get_certification("dp-700-fabric-data-engineer")
    guide = load_exam_guide_for(cert)

    assert len(guide["sections"]) == 3
    assert guide["sample_questions"] == []


def test_raises_for_unknown_parser():
    cert = replace(get_certification("databricks-data-engineer-associate"), parser="unknown_v1")

    with pytest.raises(ValueError, match="unknown_v1"):
        load_exam_guide_for(cert)
