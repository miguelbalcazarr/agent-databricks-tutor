import streamlit as st

from tools.certifications import Certification
from tools.question_bank import get_connection, init_schema, list_sections


def _question_count(cert: Certification) -> int:
    if not cert.question_bank_db_path.exists():
        return 0
    conn = get_connection(cert.question_bank_db_path)
    init_schema(conn)
    try:
        return sum(section["question_count"] for section in list_sections(conn))
    finally:
        conn.close()


def render_home(certifications: list[Certification], quiz_pages: dict[str, st.Page]) -> None:
    st.title("Tutor de Certificaciones")
    st.write("Elegi una certificacion para practicar.")

    for cert in certifications:
        count = _question_count(cert)
        with st.container(border=True):
            st.subheader(cert.display_name)
            st.caption(cert.vendor)
            if count == 0:
                st.caption("Banco de preguntas vacio todavia.")
            else:
                st.caption(f"{count} preguntas disponibles.")
            st.page_link(quiz_pages[cert.slug], label="Entrar", icon=":material/arrow_forward:")


def make_home_page(certifications: list[Certification], quiz_pages: dict[str, st.Page]) -> st.Page:
    return st.Page(
        lambda: render_home(certifications, quiz_pages),
        title="Inicio",
        icon=":material/home:",
        url_path="home",
        default=True,
    )
