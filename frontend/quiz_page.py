from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from app import answer_question, get_available_languages, get_available_sections, open_bank, open_progress
from tools.certifications import Certification
from tools.progress_store import (
    get_exam_attempt_answers,
    get_weak_topics,
    list_exam_attempts,
    record_exam_attempt,
    record_exam_attempt_answers,
)
from tools.question_bank import get_question
from tools.quiz_engine import pick_exam_questions, pick_question

LANGUAGE_LABELS = {"es": "Español", "en": "English"}
EXAM_QUESTION_COUNT = 50
EXAM_DURATION = timedelta(minutes=90)
PASSING_THRESHOLD = 0.80


def render_quiz(cert: Certification) -> None:
    """Todo el estado de sesion queda namespaceado por cert.slug (`_k`) porque
    st.session_state se comparte entre TODAS las paginas de un mismo
    st.navigation — sin esto, dos certificaciones pisarian sus claves entre
    si (ej. un simulacro en curso de una certificacion se corromperia al
    visitar la pagina de otra). Ver docs/contexto/decisiones.md D12.

    El flujo tiene dos etapas (`_k("stage")`, D17): "select" (pantalla de
    entrada: elegir modo + idioma, con el contexto de cada modo explicado)
    y "active" (la practica/simulacro en si, igual que antes). Una vez en
    "active" se puede volver a "select" sin perder un simulacro en curso —
    el dict de examen vive en su propia clave de sesion, independiente del
    modo/idioma elegidos (mismo desacople que D11)."""

    def _k(name: str) -> str:
        return f"{cert.slug}::{name}"

    bank_conn = open_bank(cert)
    progress_conn = open_progress(cert)
    weak_topics = get_weak_topics(progress_conn)

    st.title(cert.display_name)

    available_languages = get_available_languages(bank_conn)
    if not available_languages:
        st.warning(
            "El banco de preguntas esta vacio todavia. Pide a tu instructor que corra "
            f"`python tools/generate_questions.py --certification {cert.slug} --all` para generar preguntas."
        )
        return

    def render_mode_selector() -> None:
        st.write("Elegi como queres practicar hoy.")

        default_language = st.session_state.get(_k("language"), available_languages[0])
        default_index = (
            available_languages.index(default_language) if default_language in available_languages else 0
        )
        chosen = st.selectbox(
            "Idioma para empezar",
            options=available_languages,
            index=default_index,
            format_func=lambda lang: LANGUAGE_LABELS.get(lang, lang),
            key=_k("intro_language_widget"),
        )

        def enter_active_stage(modo: str) -> None:
            if st.session_state.get(_k("language")) != chosen:
                st.session_state.pop(_k("current_question"), None)
            st.session_state[_k("modo")] = modo
            st.session_state[_k("language")] = chosen
            st.session_state[_k("stage")] = "active"
            st.rerun()

        col_practice, col_exam = st.columns(2)
        with col_practice:
            with st.container(border=True, height=300):
                st.subheader("📘 Practica")
                st.write(
                    "Una pregunta a la vez. Elegis el tema, respondes, y recibis "
                    "feedback inmediato (correcto/incorrecto + explicacion). Ideal "
                    "para reforzar seccion por seccion — tu progreso por tema queda "
                    "guardado y se muestra mientras practicas."
                )
                if st.button(
                    "Practicar", type="primary", use_container_width=True, key=_k("choose_practice_button")
                ):
                    enter_active_stage("Practica")

        with col_exam:
            with st.container(border=True, height=300):
                st.subheader("⏱️ Simulacro")
                st.write(
                    f"Examen completo cronometrado: 90 minutos, hasta {EXAM_QUESTION_COUNT} "
                    "preguntas, sin feedback hasta terminar — replica el formato real del "
                    f"examen oficial. Referencia de aprobacion: {PASSING_THRESHOLD:.0%} "
                    "(Databricks no publica un corte fijo exacto, se calibra por version del examen)."
                )
                if st.button("Ir a Simulacro", use_container_width=True, key=_k("choose_exam_button")):
                    enter_active_stage("Simulacro")

    stage = st.session_state.get(_k("stage"), "select")
    if stage == "select":
        render_mode_selector()
        return

    modo = st.session_state[_k("modo")]
    chosen_language = st.session_state[_k("language")]

    with st.sidebar:
        if st.button("← Elegir otro modo", use_container_width=True, key=_k("back_to_select_button")):
            st.session_state[_k("stage")] = "select"
            st.rerun()
        st.divider()

        if st.session_state.get(_k("exam")) is not None:
            st.caption(
                f"Tenes un simulacro en curso en "
                f"{LANGUAGE_LABELS.get(st.session_state[_k('exam')]['language'], '?')} — "
                "elegir otro modo o idioma no lo interrumpe, seguis donde quedaste."
            )

        sections = get_available_sections(bank_conn, language=chosen_language)

        if modo == "Practica":
            st.header("Elegir tema")
            section_options = {"Todas las secciones": None} | {
                f"{s['section_number']}. {s['section_name']} ({s['question_count']})": s["section_number"]
                for s in sections
            }
            chosen_label = st.selectbox("Seccion", list(section_options.keys()), key=_k("section_widget"))
            chosen_section = section_options[chosen_label]

            if st.session_state.get(_k("section")) != chosen_section:
                st.session_state[_k("section")] = chosen_section
                st.session_state.pop(_k("current_question"), None)

            if st.button("Nueva pregunta", use_container_width=True, key=_k("new_question_button")):
                st.session_state[_k("current_question")] = pick_question(
                    bank_conn, chosen_section, language=chosen_language,
                    weak_topics=weak_topics if chosen_section is None else None,
                )
                st.session_state[_k("answered")] = False
                st.session_state[_k("selected_index")] = None

            st.divider()
            st.header("Tu progreso")
            if weak_topics:
                progress_df = pd.DataFrame(weak_topics).set_index("section_number")
                st.bar_chart(progress_df["accuracy"])
                weakest = weak_topics[0]
                st.caption(f"Seccion mas debil: {weakest['section_number']} ({weakest['accuracy']:.0%})")
            else:
                st.caption("Todavia no respondiste ninguna pregunta.")
        else:
            chosen_section = None
            st.caption(
                f"El simulacro toma hasta {EXAM_QUESTION_COUNT} preguntas (hasta 2 por objetivo, "
                "nunca la misma repetida) y cubre todas las secciones, sin filtro de tema."
            )

    if not sections:
        st.info(f"No hay preguntas en {LANGUAGE_LABELS.get(chosen_language, chosen_language)} todavia.")
        return

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
        if _k("current_question") not in st.session_state:
            st.session_state[_k("current_question")] = pick_question(
                bank_conn, chosen_section, language=chosen_language,
                weak_topics=weak_topics if chosen_section is None else None,
            )
            st.session_state[_k("answered")] = False
            st.session_state[_k("selected_index")] = None

        question = st.session_state[_k("current_question")]
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
            disabled=st.session_state[_k("answered")],
            key=_k("practice_radio"),
        )

        if not st.session_state[_k("answered")]:
            if st.button("Responder", disabled=selected_label is None, key=_k("answer_button")):
                answer_question(progress_conn, question, selected_label)
                st.session_state[_k("answered")] = True
                st.session_state[_k("selected_index")] = selected_label
                st.rerun()
        else:
            is_correct = st.session_state[_k("selected_index")] == question["correct_option_index"]
            if is_correct:
                st.success("¡Correcto!")
            else:
                correct_letter = chr(65 + question["correct_option_index"])
                st.error(f"Incorrecto. La respuesta correcta es {correct_letter}.")
            st.markdown(f"**Explicacion:** {question['explanation']}")

    def render_question_review(q: dict, selected: int | None, index: int | None = None) -> None:
        correct = q["correct_option_index"]
        icon = "✅" if selected == correct else ("⭕" if selected is None else "❌")
        label_prefix = f"Pregunta {index + 1} — " if index is not None else ""
        with st.expander(f"{icon} {label_prefix}Seccion {q['section_number']}: {q['section_name']}"):
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

    def start_exam() -> None:
        st.session_state[_k("exam")] = {
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
            if total:
                attempt_id = record_exam_attempt(
                    progress_conn,
                    language=exam["language"],
                    score=score,
                    total=total,
                    started_at=exam["start_time"],
                    finished_at=datetime.now(timezone.utc),
                )
                record_exam_attempt_answers(
                    progress_conn,
                    attempt_id=attempt_id,
                    answers=[
                        {
                            "question_id": q["id"],
                            "question_order": i,
                            "selected_option_index": answers.get(i),
                            "is_correct": 1 if answers.get(i) == q["correct_option_index"] else 0,
                        }
                        for i, q in enumerate(questions)
                    ],
                )
            exam["recorded"] = True

        accuracy = score / total if total else 0.0

        st.subheader("Resultado del simulacro")
        st.metric("Puntaje", f"{score} / {total}", f"{accuracy:.0%}" if total else "0%")
        if total:
            if accuracy >= PASSING_THRESHOLD:
                st.success(f"Aprobado (≥ {PASSING_THRESHOLD:.0%})")
            else:
                st.error(f"No aprobado (< {PASSING_THRESHOLD:.0%})")
        st.caption(
            f"Databricks no publica un corte fijo exacto para aprobar — se calibra por version del "
            f"examen — pero la comunidad y el FAQ oficial ubican el minimo actual en "
            f"{PASSING_THRESHOLD:.0%}. Usa este resultado como referencia de progreso, no como "
            "veredicto oficial."
        )

        if st.button("Nuevo simulacro", key=_k("new_exam_button")):
            st.session_state.pop(_k("exam"), None)
            st.rerun()

        st.divider()
        st.write("### Revision pregunta por pregunta")
        for i, q in enumerate(questions):
            render_question_review(q, answers.get(i), index=i)

    def render_exam_history() -> None:
        past_attempts = list_exam_attempts(progress_conn)
        st.divider()
        st.subheader("Tus simulacros anteriores")
        if not past_attempts:
            st.caption("Todavia no diste ningun simulacro.")
            return

        scores_df = pd.DataFrame(
            {
                "intento": list(range(1, len(past_attempts) + 1)),
                "% aciertos": [a["score"] / a["total"] if a["total"] else 0.0 for a in past_attempts],
            }
        ).set_index("intento")
        st.line_chart(scores_df)

        approved_count = sum(
            1 for a in past_attempts if a["total"] and a["score"] / a["total"] >= PASSING_THRESHOLD
        )
        st.caption(
            f"{len(past_attempts)} simulacro(s) dado(s) — {approved_count} aprobado(s) "
            f"(referencia: ≥ {PASSING_THRESHOLD:.0%})."
        )

        for attempt in reversed(past_attempts):
            accuracy = attempt["score"] / attempt["total"] if attempt["total"] else 0.0
            icon = "✅" if accuracy >= PASSING_THRESHOLD else "❌"
            fecha = attempt["finished_at"][:16].replace("T", " ")
            idioma = LANGUAGE_LABELS.get(attempt["language"], attempt["language"])
            st.write(f"{icon} {fecha} — {attempt['score']} / {attempt['total']} ({accuracy:.0%}) — {idioma}")

            if st.checkbox("Ver detalle de este intento", key=_k(f"exam_history_detail_{attempt['id']}")):
                stored_answers = get_exam_attempt_answers(progress_conn, attempt["id"])
                if not stored_answers:
                    st.caption(
                        "Detalle no disponible para este intento (se dio antes de que se guardara "
                        "el detalle por pregunta)."
                    )
                else:
                    for stored in stored_answers:
                        q = get_question(bank_conn, stored["question_id"])
                        if q is None:
                            st.caption(f"Pregunta {stored['question_order'] + 1}: ya no esta en el banco.")
                            continue
                        render_question_review(
                            q, stored["selected_option_index"], index=stored["question_order"]
                        )
            st.divider()

    def render_exam_mode() -> None:
        exam = st.session_state.get(_k("exam"))

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
            if st.button("Iniciar simulacro", type="primary", key=_k("start_exam_button")):
                start_exam()
                st.rerun()

            render_exam_history()
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
            key=_k(f"exam_q_{idx}"),
        )

        col_prev, col_next, col_finish = st.columns(3)
        with col_prev:
            if st.button("Anterior", disabled=idx == 0, use_container_width=True, key=_k("exam_prev_button")):
                exam["answers"][idx] = selected_label
                exam["index"] -= 1
                st.rerun()
        with col_next:
            if idx < total - 1:
                if st.button("Siguiente", use_container_width=True, key=_k("exam_next_button")):
                    exam["answers"][idx] = selected_label
                    exam["index"] += 1
                    st.rerun()
        with col_finish:
            if st.button(
                "Finalizar simulacro", type="primary", use_container_width=True, key=_k("exam_finish_button")
            ):
                exam["answers"][idx] = selected_label
                exam["finished"] = True
                st.rerun()

    if modo == "Practica":
        render_practice_mode()
    else:
        render_exam_mode()


def make_quiz_page(cert: Certification) -> st.Page:
    return st.Page(
        lambda: render_quiz(cert),
        title=cert.display_name,
        url_path=cert.slug,
    )
