"""Registro de certificaciones soportadas (data/certifications.yaml).

Cada certificacion define donde viven su exam guide, sus URLs curadas y su
banco de preguntas — un archivo por certificacion, mismo patron ya usado
para progreso-por-alumno. Ver docs/contexto/decisiones.md D12.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY_PATH = REPO_ROOT / "data" / "certifications.yaml"


@dataclass(frozen=True)
class Certification:
    slug: str
    display_name: str
    vendor: str
    exam_guide_pdf: Path
    topic_sources_path: Path
    question_bank_db_path: Path
    doc_source_name: str
    parser: str = "databricks_v1"
    description: str = ""


def load_registry(registry_path: Path = DEFAULT_REGISTRY_PATH, base_dir: Path | None = None) -> list[Certification]:
    """`base_dir` es la base contra la que se resuelven los paths relativos del
    YAML — por defecto REPO_ROOT, igual que tools/generate_questions.py ya hace."""
    base = base_dir if base_dir is not None else REPO_ROOT
    raw = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    certifications = []
    for slug, fields in (raw.get("certifications") or {}).items():
        certifications.append(
            Certification(
                slug=slug,
                display_name=fields["display_name"],
                vendor=fields["vendor"],
                exam_guide_pdf=base / fields["exam_guide_pdf"],
                topic_sources_path=base / fields["topic_sources"],
                question_bank_db_path=base / fields["question_bank_db"],
                doc_source_name=fields["doc_source_name"],
                parser=fields.get("parser", "databricks_v1"),
                description=fields.get("description", ""),
            )
        )
    return certifications


def get_certification(
    slug: str, registry_path: Path = DEFAULT_REGISTRY_PATH, base_dir: Path | None = None
) -> Certification:
    for certification in load_registry(registry_path, base_dir=base_dir):
        if certification.slug == slug:
            return certification
    raise ValueError(f"certificacion desconocida: {slug!r} (revisa {registry_path})")
