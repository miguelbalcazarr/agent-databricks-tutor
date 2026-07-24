"""Parses the official Databricks exam guide PDF into structured sections and sample questions.

Parses the PDF directly (pypdf, layout mode) rather than the Spanish `.md`
derivative, because the PDF's sample-question `Objective:` tags match the
outline bullets verbatim (in English) — see docs/contexto/decisiones.md D08.
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

_SECTION_HEADER = re.compile(r"Section (\d+): (.+?) \((\d+)%\)")
_BULLET = re.compile(r"●\s*(.*?)(?=●|\Z)", re.DOTALL)
_QUESTION_BLOCK = re.compile(r"Question (\d+)\s*\n(.*?)(?=Question \d+\s*\n|\Z)", re.DOTALL)
_OBJECTIVE = re.compile(r"Objective:\s*(.*?)\n\s*\n", re.DOTALL)
_OPTION_START = re.compile(r"\n?A\.\s+")
_OPTION = re.compile(r"([A-D])\.\s*(.*?)(?=\n?[A-D]\.\s|\Z)", re.DOTALL)
_ANSWER_LINE = re.compile(r"(\d+)\.\s*([A-D])")


@dataclass
class Section:
    number: int
    name: str
    weight_pct: int
    objectives: list[str]  # verbatim English text, order = objective_index


@dataclass
class SampleQuestion:
    number: int
    objective_text: str
    scenario: str
    options: list[str]
    correct_index: int


def _normalize(text: str) -> str:
    for bad, good in _LIGATURES.items():
        text = text.replace(bad, good)
    return text


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_text(pdf_path: Path) -> str:
    reader = pypdf.PdfReader(pdf_path)
    pages = [page.extract_text(extraction_mode="layout") for page in reader.pages]
    return _normalize("\n===PAGE_BREAK===\n".join(pages))


def parse_sections(text: str) -> list[Section]:
    outline_text = text[text.index("Exam outline"):text.index("Sample Questions")]
    matches = list(_SECTION_HEADER.finditer(outline_text))
    sections = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(outline_text)
        block = outline_text[start:end]
        objectives = [_collapse_whitespace(b) for b in _BULLET.findall(block)]
        sections.append(Section(
            number=int(m.group(1)),
            name=m.group(2).strip(),
            weight_pct=int(m.group(3)),
            objectives=objectives,
        ))
    return sections


def parse_sample_questions(text: str) -> list[SampleQuestion]:
    sample_text = text[text.index("Sample Questions"):]
    answers_idx = sample_text.index("Answers:")
    questions_block = sample_text[:answers_idx]
    answers_block = sample_text[answers_idx:]

    answer_key = {int(n): letter for n, letter in _ANSWER_LINE.findall(answers_block)}

    questions = []
    for qm in _QUESTION_BLOCK.finditer(questions_block):
        number = int(qm.group(1))
        body = qm.group(2)

        objective_match = _OBJECTIVE.search(body)
        objective_text = _collapse_whitespace(objective_match.group(1))

        rest = body[objective_match.end():]
        options_start = _OPTION_START.search(rest)
        scenario = _collapse_whitespace(rest[:options_start.start()])
        options_text = rest[options_start.start():]

        letters, texts = [], []
        for letter, option_text in _OPTION.findall(options_text):
            letters.append(letter)
            texts.append(_collapse_whitespace(option_text))

        correct_letter = answer_key[number]
        questions.append(SampleQuestion(
            number=number,
            objective_text=objective_text,
            scenario=scenario,
            options=texts,
            correct_index=letters.index(correct_letter),
        ))
    return questions


def load_exam_guide(pdf_path: Path) -> dict:
    text = extract_text(pdf_path)
    sections = parse_sections(text)
    sample_questions = parse_sample_questions(text)

    total_weight = sum(s.weight_pct for s in sections)
    assert total_weight == 100, f"los pesos de las secciones suman {total_weight}, no 100"

    return {"sections": sections, "sample_questions": sample_questions}


def find_objective(sections: list[Section], text: str) -> tuple[int, int] | None:
    """Busca (section_number, objective_index) para un texto de objetivo verbatim (case-insensitive)."""
    normalized = text.strip().lower()
    for section in sections:
        for idx, objective in enumerate(section.objectives):
            if objective.lower() == normalized:
                return section.number, idx
    return None
