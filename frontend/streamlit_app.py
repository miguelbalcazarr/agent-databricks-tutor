import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import answer_question, get_available_languages, get_available_sections, open_bank, open_progress
from tools.progress_store import get_weak_topics
from tools.quiz_engine import pick_exam_questions, pick_question

LANGUAGE_LABELS = {"es": "Español", "en": "English"}
EXAM_QUESTION_COUNT = 45
EXAM_DURATION = timedelta(minutes=90)

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
    st.header("Modo")
    modo = st.radio("Elegi el modo", ["Practica", "Simulacro"], horizontal=True)

    if st.session_state.get("modo") != modo:
        st.session_state["modo"] = modo
        st.session_state.pop("current_question", None)

    st.header("Idioma")
    chosen_language = st.selectbox(
        "Idioma de las preguntas",
        options=available_languages,
        format_func=lambda lang: LANGUAGE_LABELS.get(lang, lang),
    )

    if st.session_state.get("language") != chosen_language:
        st.session_state["language"] = chosen_language
        st.session_state.pop("current_question", None)

    if st.session_state.get("exam") is not None:
        st.caption(
            f"Tenes un simulacro en curso en "
            f"{LANGUAGE_LABELS.get(st.session_state['exam']['language'], '?')} — "
            "cambiar de modo o idioma no lo interrumpe, seguis donde quedaste."
        )

    sections = get_available_sections(bank_conn, language=chosen_language)

    if modo == "Practica":
        st.header("Elegir tema")
        section_options = {"Todas las secciones": None} | {
            f"{s['section_number']}. {s['section_name']} ({s['question_count']})": s["section_number"]
            for s in sections
        }
        chosen_label = st.selectbox("Seccion", list(section_options.keys()))
        chosen_section = section_options[chosen_label]

        if st.session_state.get("section") != chosen_section:
            st.session_state["section"] = chosen_section
            st.session_state.pop("current_question", None)

        if st.button("Nueva pregunta", use_container_width=True):
            st.session_state["current_question"] = pick_question(bank_conn, chosen_section, language=chosen_language)
            st.session_state["answered"] = False
            st.session_state["selected_index"] = None
    else:
        st.caption(
            f"El simulacro toma hasta {EXAM_QUESTION_COUNT} preguntas (una por objetivo, sin repetir) "
            "y cubre todas las secciones, sin filtro de tema."
        )

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


def render_countdown(remaining_seconds: int) -> None:
    """Cronometro visual client-side (no fuerza reruns de Streamlit). El
    cumplimiento real del limite de tiempo se revisa server-side en cada
    rerun comparando contra `start_time` — ver docs/contexto/decisiones.md D11."""
    components.html(
        f"""
        <div id="timer" style="font-size:1.6em;font-weight:bold;text-align:right;
             font-family:sans-serif;color:#444;"></div>
        <script>
        let remaining = {remaining_seconds};
        const el = document.getElementById('timer');
        function tick() {{
            const m = Math.floor(remaining / 60);
            const s = remaining % 60;
            el.innerText = (remaining > 0 ? '⏱ ' : '⏱ 00:00 - Tiempo agotado ') +
                (remaining > 0 ? `${{m}}:${{s.toString().padStart(2, '0')}}` : '');
            if (remaining > 0) {{
                remaining -= 1;
                setTimeout(tick, 1000);
            }}
        }}
        tick();
        </script>
        """,
        height=50,
    )


def render_practice_mode() -> None:
    if "current_question" not in st.session_state:
        st.session_state["current_question"] = pick_question(bank_conn, chosen_section, language=chosen_language)
        st.session_state["answered"] = False
        st.session_state["selected_index"] = None

    question = st.session_state["current_question"]
    if question is None:
        st.info("No hay preguntas para esta seccion todavia.")
        return

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
            answer_question(progress_conn, question, selected_label)
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


def start_exam() -> None:
    st.session_state["exam"] = {
        "questions": pick_exam_questions(bank_conn, language=chosen_language, count=EXAM_QUESTION_COUNT),
        "language": chosen_language,
        "index": 0,
        "answers": {},
        "start_time": datetime.now(timezone.utc),
        "finished": False,
        "recorded": False,
    }


def render_exam_results(exam: dict) -> None:
    questions = exam["questions"]
    answers = exam["answers"]
    total = len(questions)
    score = sum(1 for i, q in enumerate(questions) if answers.get(i) == q["correct_option_index"])

    if not exam["recorded"]:
        for i, q in enumerate(questions):
            if answers.get(i) is not None:
                answer_question(progress_conn, q, answers[i])
        exam["recorded"] = True

    st.subheader("Resultado del simulacro")
    st.metric("Puntaje", f"{score} / {total}", f"{score / total:.0%}" if total else "0%")
    st.caption(
        "Databricks no publica el puntaje minimo de corte exacto para aprobar — "
        "usa este resultado como referencia de progreso, no como veredicto oficial."
    )

    if st.button("Nuevo simulacro"):
        st.session_state.pop("exam", None)
        st.rerun()

    st.divider()
    st.write("### Revision pregunta por pregunta")
    for i, q in enumerate(questions):
        selected = answers.get(i)
        correct = q["correct_option_index"]
        icon = "✅" if selected == correct else ("⭕" if selected is None else "❌")
        with st.expander(f"{icon} Pregunta {i + 1} — Seccion {q['section_number']}: {q['section_name']}"):
            st.write(q["scenario_text"])
            for opt_i, opt_text in enumerate(q["options"]):
                prefix = chr(65 + opt_i)
                tag = ""
                if opt_i == correct:
                    tag = " ← correcta"
                elif opt_i == selected:
                    tag = " ← tu respuesta"
                st.write(f"{prefix}. {opt_text}{tag}")
            if selected is None:
                st.caption("No respondiste esta pregunta.")
            st.markdown(f"**Explicacion:** {q['explanation']}")


def render_exam_mode() -> None:
    exam = st.session_state.get("exam")

    if exam is None:
        st.subheader("Modo Simulacro")
        st.write(
            f"Examen real: {EXAM_QUESTION_COUNT} preguntas, 90 minutos, sin feedback hasta el final. "
            "Este simulacro usa el mismo formato con las preguntas disponibles hoy en el banco."
        )
        available = len(pick_exam_questions(bank_conn, language=chosen_language, count=EXAM_QUESTION_COUNT))
        if available == 0:
            st.info("No hay preguntas disponibles para armar un simulacro todavia.")
            return
        if available < EXAM_QUESTION_COUNT:
            st.caption(
                f"El banco tiene {available} objetivo(s) cubiertos hoy — el simulacro va a tener "
                f"{available} preguntas en vez de las {EXAM_QUESTION_COUNT} del examen real."
            )
        if st.button("Iniciar simulacro", type="primary"):
            start_exam()
            st.rerun()
        return

    elapsed = datetime.now(timezone.utc) - exam["start_time"]
    remaining = EXAM_DURATION - elapsed

    if remaining <= timedelta(0) and not exam["finished"]:
        exam["finished"] = True

    if exam["finished"]:
        render_exam_results(exam)
        return

    render_countdown(int(remaining.total_seconds()))

    questions = exam["questions"]
    total = len(questions)
    idx = exam["index"]
    question = questions[idx]

    st.progress((idx + 1) / total, text=f"Pregunta {idx + 1} de {total}")
    st.subheader(f"Seccion {question['section_number']}: {question['section_name']}")
    st.write(question["scenario_text"])

    previous_answer = exam["answers"].get(idx)
    selected_label = st.radio(
        "Opciones",
        options=list(range(len(question["options"]))),
        format_func=lambda i: f"{chr(65 + i)}. {question['options'][i]}",
        index=previous_answer,
        key=f"exam_q_{idx}",
    )

    col_prev, col_next, col_finish = st.columns(3)
    with col_prev:
        if st.button("Anterior", disabled=idx == 0, use_container_width=True):
            exam["answers"][idx] = selected_label
            exam["index"] -= 1
            st.rerun()
    with col_next:
        if idx < total - 1:
            if st.button("Siguiente", use_container_width=True):
                exam["answers"][idx] = selected_label
                exam["index"] += 1
                st.rerun()
    with col_finish:
        if st.button("Finalizar simulacro", type="primary", use_container_width=True):
            exam["answers"][idx] = selected_label
            exam["finished"] = True
            st.rerun()


if modo == "Practica":
    render_practice_mode()
else:
    render_exam_mode()
