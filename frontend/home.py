from dataclasses import dataclass

import streamlit as st

from tools.certifications import Certification
from tools.email_report import is_valid_email
from tools.question_bank import get_connection, init_schema, list_sections

VENDOR_ICONS = {
    "Databricks": "🧱",
}
DEFAULT_ICON = "🎓"
CARDS_PER_ROW = 3

# Idioma: unica excepcion deliberada al namespacing por cert.slug (D12/D19) —
# es una preferencia global elegida una sola vez en el Home, no un dato de
# ninguna certificacion puntual. `frontend/quiz_page.py` la lee para decidir
# el idioma de arranque de cualquier certificacion a la que se entre despues.
LANGUAGE_LABELS = {"es": "Español", "en": "English"}
GLOBAL_LANGUAGE_KEY = "global_language"
DEFAULT_LANGUAGE = "es"

# Correo: misma excepcion deliberada al namespacing por cert.slug que el
# idioma — se pide una sola vez, al primer click en "Entrar" de CUALQUIER
# tarjeta, y se recuerda para el resto de la sesion sin volver a preguntar
# al entrar a otra certificacion. Opcional: dejarlo vacio no bloquea nada
# (D22) — solo hace que el informe por correo del Simulacro no se envie.
STUDENT_EMAIL_KEY = "student_email"


@dataclass
class HomeEntry:
    """Forma generica que el Home necesita para mostrar una tarjeta y
    enlazar a una pagina — deliberadamente sin nada especifico de
    certificaciones/quiz, para que agentes con logica totalmente distinta
    puedan aparecer en el mismo Home sin adoptar el patron de Certification.
    Ver docs/contexto/decisiones.md D19."""

    slug: str
    display_name: str
    category: str
    description: str
    icon: str
    page: st.Page
    badge: str | None = None


def _question_count(cert: Certification) -> int:
    if not cert.question_bank_db_path.exists():
        return 0
    conn = get_connection(cert.question_bank_db_path)
    init_schema(conn)
    try:
        return sum(section["question_count"] for section in list_sections(conn))
    finally:
        conn.close()


def certification_home_entries(
    certifications: list[Certification], quiz_pages: dict[str, st.Page]
) -> list[HomeEntry]:
    """Envuelve cada Certification del registro en un HomeEntry generico —
    la familia de tutores de certificacion es solo UNA fuente posible de
    entradas del Home, no la unica (D19)."""
    entries = []
    for cert in certifications:
        count = _question_count(cert)
        badge = f"📚 {count} preguntas disponibles" if count else "Banco de preguntas vacio todavia."
        entries.append(
            HomeEntry(
                slug=cert.slug,
                display_name=cert.display_name,
                category=cert.vendor,
                description=cert.description,
                icon=VENDOR_ICONS.get(cert.vendor, DEFAULT_ICON),
                page=quiz_pages[cert.slug],
                badge=badge,
            )
        )
    return entries


def _render_entry_point(entry: HomeEntry) -> None:
    """Si ya tenemos el correo del alumno (de esta sesion, cualquier
    certificacion), "Entrar" es un link directo como siempre. Si no, el
    primer click en CUALQUIER tarjeta pide el correo (opcional) antes de
    entrar — una sola vez por sesion, ver STUDENT_EMAIL_KEY arriba."""
    if st.session_state.get(STUDENT_EMAIL_KEY):
        st.page_link(
            entry.page,
            label="Entrar",
            icon=":material/arrow_forward:",
            use_container_width=True,
        )
        return

    with st.form(key=f"email_gate_{entry.slug}", border=False):
        email = st.text_input(
            "Tu correo (opcional, para el informe del Simulacro)",
            key=f"email_gate_input_{entry.slug}",
            placeholder="tu@correo.com",
        )
        submitted = st.form_submit_button(
            "Entrar", icon=":material/arrow_forward:", use_container_width=True
        )
    if submitted:
        stripped = email.strip()
        if stripped and not is_valid_email(stripped):
            st.error("Ese correo no parece valido — dejalo vacio si preferis no darlo.")
            return
        if stripped:
            st.session_state[STUDENT_EMAIL_KEY] = stripped
        st.switch_page(entry.page)


def _render_card(entry: HomeEntry) -> None:
    with st.container(border=True):
        st.markdown(f"#### {entry.icon} {entry.display_name}")
        st.caption(entry.category)

        if entry.description:
            st.write(entry.description)

        if entry.badge:
            st.caption(entry.badge)

        _render_entry_point(entry)


def _render_language_selector() -> None:
    current = st.session_state.get(GLOBAL_LANGUAGE_KEY, DEFAULT_LANGUAGE)
    options = list(LANGUAGE_LABELS.keys())
    index = options.index(current) if current in options else 0
    chosen = st.selectbox(
        "Idioma",
        options=options,
        index=index,
        format_func=lambda lang: LANGUAGE_LABELS.get(lang, lang),
        key="home_language_widget",
    )
    st.session_state[GLOBAL_LANGUAGE_KEY] = chosen


def render_home(entries: list[HomeEntry]) -> None:
    title_col, language_col = st.columns([4, 1])
    with title_col:
        st.title("Tutor de Certificaciones")
    with language_col:
        _render_language_selector()
    st.caption(
        "Practica para tus examenes de certificacion con preguntas fundamentadas "
        "en la documentacion oficial de cada proveedor. Elegi un tutor para empezar."
    )
    st.divider()

    for row_start in range(0, len(entries), CARDS_PER_ROW):
        row = entries[row_start : row_start + CARDS_PER_ROW]
        columns = st.columns(CARDS_PER_ROW)
        for column, entry in zip(columns, row):
            with column:
                _render_card(entry)


def make_home_page(entries: list[HomeEntry]) -> st.Page:
    return st.Page(
        lambda: render_home(entries),
        title="Inicio",
        icon=":material/home:",
        url_path="home",
        default=True,
    )
