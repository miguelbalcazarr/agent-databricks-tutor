import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.certifications import get_certification, load_registry

REGISTRY_YAML = """
certifications:
  fake-cert:
    display_name: "Fake Certification"
    vendor: "Acme"
    exam_guide_pdf: "data/certifications/fake-cert/exam_guide.pdf"
    topic_sources: "data/certifications/fake-cert/topic_sources.yaml"
    question_bank_db: "data/certifications/fake-cert/question_bank.db"
    doc_source_name: "docs.acme.example"
    parser: "fake_v1"
"""


def test_load_registry_resolves_relative_paths_against_base_dir(tmp_path):
    registry_path = tmp_path / "certifications.yaml"
    registry_path.write_text(REGISTRY_YAML, encoding="utf-8")

    certifications = load_registry(registry_path, base_dir=tmp_path)

    assert len(certifications) == 1
    cert = certifications[0]
    assert cert.slug == "fake-cert"
    assert cert.display_name == "Fake Certification"
    assert cert.vendor == "Acme"
    assert cert.doc_source_name == "docs.acme.example"
    assert cert.parser == "fake_v1"
    assert cert.exam_guide_pdf == tmp_path / "data/certifications/fake-cert/exam_guide.pdf"
    assert cert.topic_sources_path == tmp_path / "data/certifications/fake-cert/topic_sources.yaml"
    assert cert.question_bank_db_path == tmp_path / "data/certifications/fake-cert/question_bank.db"


def test_get_certification_returns_matching_slug(tmp_path):
    registry_path = tmp_path / "certifications.yaml"
    registry_path.write_text(REGISTRY_YAML, encoding="utf-8")

    cert = get_certification("fake-cert", registry_path, base_dir=tmp_path)

    assert cert.slug == "fake-cert"


def test_get_certification_raises_clear_error_for_unknown_slug(tmp_path):
    registry_path = tmp_path / "certifications.yaml"
    registry_path.write_text(REGISTRY_YAML, encoding="utf-8")

    with pytest.raises(ValueError, match="unknown-cert"):
        get_certification("unknown-cert", registry_path, base_dir=tmp_path)


def test_parser_defaults_to_databricks_v1_when_omitted(tmp_path):
    registry_path = tmp_path / "certifications.yaml"
    registry_path.write_text(
        """
certifications:
  no-parser-field:
    display_name: "No Parser Field"
    vendor: "Acme"
    exam_guide_pdf: "x.pdf"
    topic_sources: "x.yaml"
    question_bank_db: "x.db"
    doc_source_name: "docs.example"
""",
        encoding="utf-8",
    )

    cert = get_certification("no-parser-field", registry_path, base_dir=tmp_path)

    assert cert.parser == "databricks_v1"
