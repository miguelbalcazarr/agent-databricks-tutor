"""Dispatch entre los parsers de exam guide segun `Certification.parser`.

Cada certificacion registrada en data/certifications.yaml declara que
parser usar (ver docs/contexto/decisiones.md D12) — este modulo es el unico
punto que decide, a partir de ese string, que funcion de parseo llamar.
"""
from __future__ import annotations

from tools import parse_exam_guide, parse_exam_guide_microsoft
from tools.certifications import Certification

_LOADERS = {
    "databricks_v1": parse_exam_guide.load_exam_guide,
    "microsoft_study_guide_v1": parse_exam_guide_microsoft.load_exam_guide,
}


def load_exam_guide_for(cert: Certification) -> dict:
    loader = _LOADERS.get(cert.parser)
    if loader is None:
        raise ValueError(f"parser desconocido: {cert.parser!r} (cert={cert.slug})")
    return loader(cert.exam_guide_pdf)
