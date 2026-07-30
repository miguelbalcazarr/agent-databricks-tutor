"""Parsea el "Study Guide" oficial de Microsoft (ej. DP-700) en secciones/objetivos.

Formato distinto al exam guide de Databricks (tools/parse_exam_guide.py):
es una pagina de learn.microsoft.com exportada a PDF, con 3 niveles de texto
distinguibles solo por indentacion (extraccion pypdf, modo "layout"):

  - indentacion 0: boilerplate de pagina (header de fecha/titulo, footer de
    URL/numero de pagina) — se descarta.
  - indentacion ~5: headers — una seccion de nivel superior si matchea
    "Nombre (NN-NN%)", o si no, un subgrupo (bold en el original) que agrupa
    los bullets que le siguen.
  - indentacion ~12: bullets (objetivos concretos).

No trae "Sample Questions" ni answer key (Microsoft no las publica en este
documento) — sample_questions siempre es [].

Cada objetivo se guarda como "{subgrupo}: {bullet}" para darle mas contexto
a la Generacion sin cambiar el contrato de Section.objectives (list[str]).
"""
from __future__ import annotations

import re
from pathlib import Path

from tools.exam_guide_common import Section, SampleQuestion, collapse_whitespace, extract_text

_SECTION_HEADER = re.compile(r"^(.+?)\s*\((\d+)-(\d+)%\)$")
_HEADER_INDENT_MAX = 6
_END_MARKER = "Study resources"


def _blocks(text: str) -> list[tuple[int, str]]:
    """Agrupa lineas no-boilerplate en bloques (indentacion, texto colapsado).

    Un bloque = corrida de lineas consecutivas sin linea en blanco entre
    ellas (una linea en blanco separa una entrada de la siguiente; lineas
    consecutivas sin blanco de por medio son el wrap de la misma entrada).
    Las lineas con indentacion 0 (boilerplate de pagina) se descartan antes
    de agrupar.
    """
    blocks: list[tuple[int, str]] = []
    current_indent: int | None = None
    current_lines: list[str] = []

    def flush() -> None:
        if current_lines:
            blocks.append((current_indent, collapse_whitespace(" ".join(current_lines))))

    for raw_line in text.split("\n"):
        stripped = raw_line.lstrip()
        if not stripped:
            flush()
            current_lines.clear()
            current_indent = None
            continue
        indent = len(raw_line) - len(stripped)
        if indent == 0:
            continue
        if current_indent is not None and indent != current_indent:
            flush()
            current_lines.clear()
        current_indent = indent
        current_lines.append(stripped.rstrip())
    flush()
    return blocks


def parse_sections(text: str) -> list[Section]:
    all_blocks = _blocks(text)

    start_idx = None
    end_idx = len(all_blocks)
    for i, (indent, block_text) in enumerate(all_blocks):
        if start_idx is None and indent <= _HEADER_INDENT_MAX and _SECTION_HEADER.match(block_text):
            start_idx = i
        if start_idx is not None and indent <= _HEADER_INDENT_MAX and block_text == _END_MARKER:
            end_idx = i
            break
    if start_idx is None:
        raise ValueError("no se encontro ningun header de seccion (\"Nombre (NN-NN%)\")")

    sections: list[Section] = []
    current_section: Section | None = None
    current_subgroup: str | None = None

    for indent, block_text in all_blocks[start_idx:end_idx]:
        header_match = _SECTION_HEADER.match(block_text) if indent <= _HEADER_INDENT_MAX else None
        if header_match:
            current_section = Section(
                number=len(sections) + 1,
                name=header_match.group(1).strip(),
                weight_pct=f"{header_match.group(2)}-{header_match.group(3)}",
                objectives=[],
            )
            sections.append(current_section)
            current_subgroup = None
        elif indent <= _HEADER_INDENT_MAX:
            current_subgroup = block_text
        else:
            if current_section is None:
                continue
            objective = f"{current_subgroup}: {block_text}" if current_subgroup else block_text
            current_section.objectives.append(objective)

    return sections


def load_exam_guide(pdf_path: Path) -> dict:
    text = extract_text(pdf_path)
    sections = parse_sections(text)
    return {"sections": sections, "sample_questions": []}
