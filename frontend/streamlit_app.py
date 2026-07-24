import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import answer_question, get_available_languages, get_available_sections, open_bank, open_progress
from tools.progress_store import get_weak_topics
from tools.quiz_engine import pick_question

LANGUAGE_LABELS = {"es": "Español", "en": "English"}

st.set_page_config(page_title="Tutor de Certificacion Databricks", layout="wide")
st.title("Tutor de Certificacion Databricks Data Engineer Associate")

bank_conn = open_bank()
progress_conn = open_progress()

available_languages = get_available_languages(bank_conn)
if not available_languages:
    st.warning(
        "El banco de preguntas esta vacio todavia. Pide a tu instructor que corra "
        "`python tools/generate_questions.py --all` para generar preguntas."
    )
    st.stop()

with st.sidebar:
    st.header("Idioma")
    chosen_language = st.selectbox(
        "Idioma de las preguntas",
        options=available_languages,
        format_func=lambda lang: LANGUAGE_LABELS.get(lang, lang),
    )

    if st.session_state.get("language") != chosen_language:
        st.session_state["language"] = chosen_language
        st.session_state.pop("current_question", None)

    st.header("Elegir tema")
    sections = get_available_sections(bank_conn, language=chosen_language)
    section_options = {"Todas las secciones": None} | {
        f"{s['section_number']}. {s['section_name']} ({s['question_count']})": s["section_number"]
        for s in sections
    }
    chosen_label = st.selectbox("Seccion", list(section_options.keys()))
    chosen_section = section_options[chosen_label]

    if st.button("Nueva pregunta", use_container_width=True):
        st.session_state["current_question"] = pick_question(bank_conn, chosen_section, language=chosen_language)
        st.session_state["answered"] = False
        st.session_state["selected_index"] = None

    st.divider()
    st.header("Tu progreso")
    weak_topics = get_weak_topics(progress_conn)
    if weak_topics:
        progress_df = pd.DataFrame(weak_topics).set_index("section_number")
        st.bar_chart(progress_df["accuracy"])
        weakest = weak_topics[0]
        st.caption(f"Seccion mas debil: {weakest['section_number']} ({weakest['accuracy']:.0%})")
    else:
        st.caption("Todavia no respondiste ninguna pregunta.")

if not sections:
    st.info(f"No hay preguntas en {LANGUAGE_LABELS.get(chosen_language, chosen_language)} todavia.")
    st.stop()

if "current_question" not in st.session_state:
    st.session_state["current_question"] = pick_question(bank_conn, chosen_section, language=chosen_language)
    st.session_state["answered"] = False
    st.session_state["selected_index"] = None

question = st.session_state["current_question"]
if question is None:
    st.info("No hay preguntas para esta seccion todavia.")
    st.stop()

st.subheader(f"Seccion {question['section_number']}: {question['section_name']}")
st.write(question["scenario_text"])

selected_label = st.radio(
    "Opciones",
    options=list(range(len(question["options"]))),
    format_func=lambda i: f"{chr(65 + i)}. {question['options'][i]}",
    index=None,
    disabled=st.session_state["answered"],
)

if not st.session_state["answered"]:
    if st.button("Responder", disabled=selected_label is None):
        is_correct = answer_question(progress_conn, question, selected_label)
        st.session_state["answered"] = True
        st.session_state["selected_index"] = selected_label
        st.rerun()
else:
    is_correct = st.session_state["selected_index"] == question["correct_option_index"]
    if is_correct:
        st.success("¡Correcto!")
    else:
        correct_letter = chr(65 + question["correct_option_index"])
        st.error(f"Incorrecto. La respuesta correcta es {correct_letter}.")
    st.markdown(f"**Explicacion:** {question['explanation']}")
