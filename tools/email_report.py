"""Envio del informe por correo al terminar un Simulacro.

SMTP puro via smtplib (stdlib, sin dependencias nuevas) — mismo patron que
agent/client.py: variables de entorno controlan las credenciales, y si no
estan configuradas la funcion no falla ni bloquea nada, simplemente no
envia (ver docs/contexto/decisiones.md D22). El Quiz nunca REQUIERE esto —
es un plus opcional encima de la revision pregunta por pregunta que ya
existe en pantalla.
"""
from __future__ import annotations

import os
import smtplib
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def is_valid_email(value: str) -> bool:
    value = value.strip()
    if not value or value.count("@") != 1:
        return False
    local, _, domain = value.partition("@")
    return bool(local) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


def is_email_configured() -> bool:
    return all(os.getenv(var) for var in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))


def _format_duration(elapsed: timedelta) -> str:
    total_seconds = int(elapsed.total_seconds())
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes} min {seconds} seg"


def build_exam_report_email(
    *,
    cert_display_name: str,
    language: str,
    score: int,
    total: int,
    passing_threshold: float,
    elapsed: timedelta,
    finished_at_label: str,
    questions: list[dict],
    answers: dict[int, int | None],
) -> tuple[str, str, str]:
    """Arma (subject, texto_plano, html) del informe. `questions` es la lista
    de preguntas del examen en orden, `answers` mapea indice de pregunta ->
    opcion elegida (o None si no se respondio)."""
    accuracy = score / total if total else 0.0
    passed = accuracy >= passing_threshold
    veredicto = "Aprobado" if passed else "No aprobado"

    subject = f"Resultado de tu simulacro — {cert_display_name}: {score}/{total} ({accuracy:.0%})"

    header_lines = [
        f"Certificacion: {cert_display_name}",
        f"Puntaje: {score} / {total} ({accuracy:.0%}) — {veredicto} (referencia: >= {passing_threshold:.0%})",
        f"Tiempo utilizado: {_format_duration(elapsed)}",
        f"Fecha: {finished_at_label}",
    ]

    text_parts = ["\n".join(header_lines), "", "Revision pregunta por pregunta:", ""]
    html_rows = []
    for i, q in enumerate(questions):
        selected = answers.get(i)
        correct = q["correct_option_index"]
        if selected is None:
            icon, status = "⭕", "Sin responder"
        elif selected == correct:
            icon, status = "✅", "Correcta"
        else:
            icon, status = "❌", "Incorrecta"

        options_lines = []
        for opt_i, opt_text in enumerate(q["options"]):
            tag = ""
            if opt_i == correct:
                tag = " (correcta)"
            elif opt_i == selected:
                tag = " (tu respuesta)"
            options_lines.append(f"    {chr(65 + opt_i)}. {opt_text}{tag}")

        text_parts.append(
            f"{icon} Pregunta {i + 1} [{status}] — Seccion {q['section_number']}: {q['section_name']}\n"
            f"{q['scenario_text']}\n" + "\n".join(options_lines) + f"\n  Explicacion: {q['explanation']}\n"
        )

        options_html = "".join(
            f"<li{' style=\"font-weight:bold;color:#1a7f37\"' if opt_i == correct else ''}"
            f"{' style=\"font-style:italic\"' if opt_i == selected and opt_i != correct else ''}>"
            f"{chr(65 + opt_i)}. {opt_text}"
            f"{' ← correcta' if opt_i == correct else ''}"
            f"{' ← tu respuesta' if opt_i == selected and opt_i != correct else ''}"
            "</li>"
            for opt_i, opt_text in enumerate(q["options"])
        )
        html_rows.append(
            f"<h4>{icon} Pregunta {i + 1} [{status}] — Seccion {q['section_number']}: {q['section_name']}</h4>"
            f"<p>{q['scenario_text']}</p>"
            f"<ul>{options_html}</ul>"
            f"<p><em>Explicacion:</em> {q['explanation']}</p><hr/>"
        )

    text_body = "\n".join(text_parts)
    html_header = "".join(f"<p>{line}</p>" for line in header_lines)
    html_body = f"<html><body>{html_header}<hr/>{''.join(html_rows)}</body></html>"

    return subject, text_body, html_body


def send_email(to_address: str, subject: str, text_body: str, html_body: str) -> bool:
    """Envia el correo via SMTP. Retorna False sin lanzar excepcion si algo
    falla (credenciales faltantes, host inalcanzable, auth invalida, etc.)
    — nunca debe tumbar la pantalla de resultados del simulacro."""
    if not is_email_configured() or not is_valid_email(to_address):
        return False

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM", user)

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_address
    message.attach(MIMEText(text_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=30) as server:
                server.login(user, password)
                server.sendmail(sender, [to_address], message.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.starttls()
                server.login(user, password)
                server.sendmail(sender, [to_address], message.as_string())
        return True
    except (smtplib.SMTPException, OSError):
        return False
