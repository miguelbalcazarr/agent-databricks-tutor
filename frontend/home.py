from dataclasses import dataclass

import streamlit as st

from tools.certifications import Certification
from tools.question_bank import get_connection, init_schema, list_sections

VENDOR_ICONS = {
    "Databricks": "🧱",
}
DEFAULT_ICON = "🎓"
CARDS_PER_ROW = 3


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


def _render_card(entry: HomeEntry) -> None:
    with st.container(border=True):
        st.markdown(f"#### {entry.icon} {entry.display_name}")
        st.caption(entry.category)

        if entry.description:
            st.write(entry.description)

        if entry.badge:
            st.caption(entry.badge)

        st.page_link(
            entry.page,
            label="Entrar",
            icon=":material/arrow_forward:",
            use_container_width=True,
        )


def render_home(entries: list[HomeEntry]) -> None:
    st.title("Tutor de Certificaciones")
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
