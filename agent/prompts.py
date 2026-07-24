LANGUAGE_NAMES = {"es": "espanol", "en": "English"}

DEFAULT_CERTIFICATION_NAME = "Databricks Certified Data Engineer Associate"
DEFAULT_DOC_SOURCE_NAME = "docs.databricks.com"


def build_system_prompt(*, certification_name: str, doc_source_name: str) -> str:
    return (
        f"Eres un generador de preguntas de certificacion {certification_name}. "
        f"Basa cada pregunta UNICAMENTE en el objetivo del exam guide y el contenido "
        f"oficial de {doc_source_name} que se te provee. Nunca inventes comandos, APIs, nombres "
        "de producto ni comportamientos que no esten mencionados en las fuentes provistas. "
        "Responde SIEMPRE en el idioma que se te pida explicitamente en el mensaje del usuario, "
        "sin importar en que idioma esten las fuentes. Responde unicamente con un objeto JSON, "
        "sin texto adicional."
    )


QUESTION_GENERATION_SYSTEM_PROMPT = build_system_prompt(
    certification_name=DEFAULT_CERTIFICATION_NAME, doc_source_name=DEFAULT_DOC_SOURCE_NAME
)


def build_generation_prompt(
    *,
    objective_text: str,
    section_name: str,
    weight_pct: int,
    source_text: str,
    sample_questions: list[dict],
    language: str = "es",
    doc_source_name: str = DEFAULT_DOC_SOURCE_NAME,
) -> str:
    language_name = LANGUAGE_NAMES.get(language, language)
    examples = "\n\n".join(
        f"Ejemplo de estilo {i + 1} (objetivo: {q['objective_text']}):\n"
        f"Escenario: {q['scenario']}\n"
        f"Opciones: {q['options']}"
        for i, q in enumerate(sample_questions)
    )

    return (
        f"Seccion del exam guide: {section_name} (peso {weight_pct}%).\n"
        f"Objetivo a evaluar: {objective_text}\n\n"
        f"Contenido oficial de {doc_source_name} para fundamentar la pregunta:\n"
        f"{source_text}\n\n"
        f"Ejemplos de estilo (escenario + opciones) tomados del exam guide oficial "
        f"(estos ejemplos NO traen explicacion oficial, son solo referencia de tono):\n"
        f"{examples}\n\n"
        f"Genera UNA pregunta nueva de certificacion, en {language_name} (escenario, opciones y "
        f"explicacion, todo en {language_name}), con este formato JSON exacto:\n"
        '{"scenario": "...", "options": ["...", "...", "...", "..."], '
        '"correct_index": 0, "explanation": "..."}\n\n'
        "Requisitos: 4 opciones, escenario realista tipo examen (puede incluir un fragmento de "
        "codigo si el objetivo lo amerita), explicacion que justifique la opcion correcta y "
        "descarte las demas, fundamentada solo en el contenido oficial provisto arriba."
    )
