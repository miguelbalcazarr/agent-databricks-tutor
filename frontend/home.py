import streamlit as st

from tools.certifications import Certification
from tools.question_bank import get_connection, init_schema, list_sections

VENDOR_ICONS = {
    "Databricks": "🧱",
}
DEFAULT_ICON = "🎓"
CARDS_PER_ROW = 3


def _question_count(cert: Certification) -> int:
    if not cert.question_bank_db_path.exists():
        return 0
    conn = get_connection(cert.question_bank_db_path)
    init_schema(conn)
    try:
        return sum(section["question_count"] for section in list_sections(conn))
    finally:
        conn.close()


def _render_card(cert: Certification, quiz_pages: dict[str, st.Page]) -> None:
    with st.container(border=True):
        icon = VENDOR_ICONS.get(cert.vendor, DEFAULT_ICON)
        st.markdown(f"#### {icon} {cert.display_name}")
        st.caption(cert.vendor)

        if cert.description:
            st.write(cert.description)

        count = _question_count(cert)
        if count == 0:
            st.caption("Banco de preguntas vacio todavia.")
        else:
            st.caption(f"📚 {count} preguntas disponibles")

        st.page_link(
            quiz_pages[cert.slug],
            label="Entrar",
            icon=":material/arrow_forward:",
            use_container_width=True,
        )


def render_home(certifications: list[Certification], quiz_pages: dict[str, st.Page]) -> None:
    st.title("Tutor de Certificaciones")
    st.caption(
        "Practica para tus examenes de certificacion con preguntas fundamentadas "
        "en la documentacion oficial de cada proveedor. Elegi un tutor para empezar."
    )
    st.divider()

    for row_start in range(0, len(certifications), CARDS_PER_ROW):
        row = certifications[row_start : row_start + CARDS_PER_ROW]
        columns = st.columns(CARDS_PER_ROW)
        for column, cert in zip(columns, row):
            with column:
                _render_card(cert, quiz_pages)


def make_home_page(certifications: list[Certification], quiz_pages: dict[str, st.Page]) -> st.Page:
    return st.Page(
        lambda: render_home(certifications, quiz_pages),
        title="Inicio",
        icon=":material/home:",
        url_path="home",
        default=True,
    )
