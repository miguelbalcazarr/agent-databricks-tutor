"""Utilidades genericas compartidas por los parsers de exam guide (uno por formato de PDF).

No asume el formato de ningun vendor puntual — ver tools/parse_exam_guide.py
(Databricks) y tools/parse_exam_guide_microsoft.py (Microsoft) para los
parsers concretos, y tools/exam_guide_parsers.py para el dispatch entre
ellos segun el campo `parser` del registro (docs/contexto/decisiones.md D12).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pypdf

_LIGATURES = {
    "ﬁ": "fi",
    "ﬂ": "fl",
    "‑": "-",
    "–": "-",
    "—": "-",
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
}


@dataclass
class Section:
    number: int
    name: str
    weight_pct: int | str
    objectives: list[str]  # verbatim English text, order = objective_index


@dataclass
class SampleQuestion:
    number: int
    objective_text: str
    scenario: str
    options: list[str]
    correct_index: int


def normalize(text: str) -> str:
    for bad, good in _LIGATURES.items():
        text = text.replace(bad, good)
    return text


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_text(pdf_path: Path) -> str:
    reader = pypdf.PdfReader(pdf_path)
    pages = [page.extract_text(extraction_mode="layout") for page in reader.pages]
    return normalize("\n===PAGE_BREAK===\n".join(pages))
