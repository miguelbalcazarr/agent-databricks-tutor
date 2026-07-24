"""CLI: genera preguntas de certificacion nuevas y las guarda en el banco persistente.

Usage:
    python tools/generate_questions.py --section 2
    python tools/generate_questions.py --all
    python tools/generate_questions.py --section 6 --count 3 --force

Cada corrida genera SIEMPRE ambos idiomas (es + en) para cada objetivo —
no es una traduccion, cada idioma se genera por separado con su propia
llamada al LLM. El conteo de "cuantas preguntas ya tiene este objetivo"
se lleva por separado en cada idioma.

Requiere OPENAI_API_KEY en el entorno (ver agent/client.py) — sin ella,
cada objetivo se marca como error y no se genera nada (sin fallback).
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import asdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.client import generate_question_with_ai  # noqa: E402
from agent.prompts import build_system_prompt  # noqa: E402
from tools.certifications import DEFAULT_REGISTRY_PATH, get_certification  # noqa: E402
from tools.fetch_official_docs import get_doc_text  # noqa: E402
from tools.parse_exam_guide import Section, load_exam_guide  # noqa: E402
from tools.question_bank import (  # noqa: E402
    count_questions_for_objective,
    get_connection,
    init_schema,
    insert_question,
    validate_question,
)

DEFAULT_CERTIFICATION = "databricks-data-engineer-associate"
MAX_SOURCE_CHARS = 12_000
LANGUAGES = ("es", "en")


def load_topic_sources(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def get_urls_for(topic_sources: dict, section_number: int, objective_index: int) -> list[str]:
    section = topic_sources.get("sections", {}).get(section_number, {})
    objective = section.get("objectives", {}).get(objective_index, {})
    return objective.get("urls", [])


def resolve_targets(sections: list[Section], section_arg: int | None) -> list[tuple[Section, int]]:
    targets = []
    for section in sections:
        if section_arg is not None and section.number != section_arg:
            continue
        for objective_index in range(len(section.objectives)):
            targets.append((section, objective_index))
    return targets


def process_objective(
    conn,
    section: Section,
    objective_index: int,
    args: argparse.Namespace,
    topic_sources: dict,
    sample_questions: list[dict],
    system_prompt: str,
    doc_source_name: str,
) -> bool:
    objective_text = section.objectives[objective_index]
    label = f"seccion={section.number} objetivo={objective_index}"

    urls = get_urls_for(topic_sources, section.number, objective_index)
    if not urls:
        print(f"WARN  sin fuentes mapeadas {label}")
        return True

    source_texts = None  # fetch perezoso: solo si algun idioma realmente necesita generar
    ok_overall = True

    for language in LANGUAGES:
        lang_label = f"{label} idioma={language}"

        existing = count_questions_for_objective(conn, section.number, objective_index, language)
        if existing >= args.count and not args.force:
            print(f"SKIP  (ya tiene {existing}) {lang_label}")
            continue

        if source_texts is None:
            source_texts = [text for url in urls if (text := get_doc_text(url))]
            if not source_texts:
                print(f"ERROR no se pudo hacer fetch de ninguna URL {label}")
                return False

        combined_source = "\n\n".join(source_texts)[:MAX_SOURCE_CHARS]
        to_generate = args.count if args.force else args.count - existing

        for _ in range(to_generate):
            parsed = generate_question_with_ai(
                objective_text=objective_text,
                section_name=section.name,
                weight_pct=section.weight_pct,
                source_text=combined_source,
                sample_questions=sample_questions,
                language=language,
                system_prompt=system_prompt,
                doc_source_name=doc_source_name,
            )
            if parsed is None:
                print(f"ERROR no se pudo generar (sin OPENAI_API_KEY o fallo el LLM) {lang_label}")
                ok_overall = False
                continue

            valid, errors = validate_question(parsed)
            if not valid:
                print(f"INVALID {lang_label}: {', '.join(errors)}")
                ok_overall = False
                continue

            question_id = insert_question(
                conn,
                section_number=section.number,
                section_name=section.name,
                objective_index=objective_index,
                objective_text=objective_text,
                language=language,
                scenario_text=parsed["scenario"],
                options=parsed["options"],
                correct_option_index=parsed["correct_index"],
                explanation=parsed["explanation"],
                source_urls=urls,
                generation_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            )
            print(f"OK    {lang_label} -> guardado id={question_id}")

    return ok_overall


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--certification", default=DEFAULT_CERTIFICATION,
        help=f"slug de la certificacion (ver {DEFAULT_REGISTRY_PATH}), default {DEFAULT_CERTIFICATION!r}",
    )
    parser.add_argument("--section", type=int, help="genera solo para esta seccion (1-7)")
    parser.add_argument("--all", action="store_true", help="genera para todas las secciones/objetivos mapeados")
    parser.add_argument("--count", type=int, default=1, help="preguntas objetivo por (seccion, objetivo)")
    parser.add_argument("--force", action="store_true", help="genera aunque ya existan >= --count preguntas")
    args = parser.parse_args()

    if args.section is None and not args.all:
        parser.error("pasa --section N, o --all")

    cert = get_certification(args.certification)
    system_prompt = build_system_prompt(certification_name=cert.display_name, doc_source_name=cert.doc_source_name)

    guide = load_exam_guide(cert.exam_guide_pdf)
    sections = guide["sections"]
    sample_questions = [asdict(q) for q in guide["sample_questions"]]
    topic_sources = load_topic_sources(cert.topic_sources_path)

    conn = get_connection(cert.question_bank_db_path)
    init_schema(conn)

    targets = resolve_targets(sections, args.section)
    all_ok = True
    for section, objective_index in targets:
        try:
            ok = process_objective(
                conn, section, objective_index, args, topic_sources, sample_questions,
                system_prompt, cert.doc_source_name,
            )
            all_ok = all_ok and ok
        except Exception as exc:  # surface which objective failed, keep going
            print(f"ERROR seccion={section.number} objetivo={objective_index}: {exc}")
            all_ok = False

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
