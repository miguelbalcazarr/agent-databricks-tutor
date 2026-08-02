import sys
from datetime import timedelta
from email import message_from_string
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.email_report import (
    build_exam_report_email,
    build_exam_report_pdf,
    is_email_configured,
    is_valid_email,
    send_email,
)

_QUESTIONS = [
    {
        "id": 1,
        "section_number": 2,
        "section_name": "Data Ingestion and Loading",
        "scenario_text": "Escenario de prueba.",
        "options": ["Opcion A", "Opcion B", "Opcion C", "Opcion D"],
        "correct_option_index": 1,
        "explanation": "Porque si.",
    },
    {
        "id": 2,
        "section_number": 3,
        "section_name": "Data Transformation and Modeling",
        "scenario_text": "Otro escenario.",
        "options": ["Opcion A", "Opcion B"],
        "correct_option_index": 0,
        "explanation": "Porque tambien.",
    },
]


def test_is_valid_email_accepts_reasonable_addresses():
    assert is_valid_email("alumno@example.com")
    assert is_valid_email("  alumno@example.com  ")


def test_is_valid_email_rejects_malformed_addresses():
    assert not is_valid_email("")
    assert not is_valid_email("sin-arroba.com")
    assert not is_valid_email("dos@arrobas@example.com")
    assert not is_valid_email("usuario@sindominio")
    assert not is_valid_email("@example.com")


def test_is_email_configured_false_without_env_vars(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    assert is_email_configured() is False


def test_is_email_configured_true_with_all_env_vars(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "bot@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    assert is_email_configured() is True


def test_build_exam_report_email_includes_score_and_question_review():
    subject, text_body, html_body = build_exam_report_email(
        cert_display_name="Databricks Certified Data Engineer Associate",
        language="es",
        score=1,
        total=2,
        passing_threshold=0.8,
        elapsed=timedelta(minutes=12, seconds=34),
        finished_at_label="2026-07-31 10:00 UTC",
        questions=_QUESTIONS,
        answers={0: 1, 1: 1},  # primera correcta, segunda incorrecta (correct_index=0)
    )

    assert "1/2" in subject or "1 / 2" in text_body
    assert "Databricks Certified Data Engineer Associate" in text_body
    assert "12 min 34 seg" in text_body
    assert "Correcta" in text_body
    assert "Incorrecta" in text_body
    assert "Escenario de prueba." in html_body
    assert "Otro escenario." in html_body


def test_build_exam_report_email_marks_unanswered_questions():
    _, text_body, _ = build_exam_report_email(
        cert_display_name="Cert",
        language="es",
        score=0,
        total=2,
        passing_threshold=0.8,
        elapsed=timedelta(minutes=1),
        finished_at_label="2026-07-31 10:00 UTC",
        questions=_QUESTIONS,
        answers={0: None, 1: None},
    )
    assert "Sin responder" in text_body


def test_build_exam_report_pdf_returns_valid_pdf_bytes():
    pdf_bytes = build_exam_report_pdf(
        cert_display_name="Databricks Certified Data Engineer Associate",
        language="es",
        score=1,
        total=2,
        passing_threshold=0.8,
        elapsed=timedelta(minutes=12, seconds=34),
        finished_at_label="2026-07-31 10:00 UTC",
        questions=_QUESTIONS,
        answers={0: 1, 1: 1},
    )
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500


def test_build_exam_report_pdf_handles_unanswered_questions_without_crashing():
    pdf_bytes = build_exam_report_pdf(
        cert_display_name="Cert",
        language="es",
        score=0,
        total=2,
        passing_threshold=0.8,
        elapsed=timedelta(minutes=1),
        finished_at_label="2026-07-31 10:00 UTC",
        questions=_QUESTIONS,
        answers={0: None, 1: None},
    )
    assert pdf_bytes.startswith(b"%PDF")


def test_build_exam_report_pdf_survives_characters_outside_latin1():
    weird_question = [
        {
            "id": 1,
            "section_number": 1,
            "section_name": "Seccion rara",
            "scenario_text": "Escenario con caracteres raros: 中文 emoji 🚀",
            "options": ["A", "B"],
            "correct_option_index": 0,
            "explanation": "Explicacion.",
        }
    ]
    pdf_bytes = build_exam_report_pdf(
        cert_display_name="Cert",
        language="es",
        score=1,
        total=1,
        passing_threshold=0.8,
        elapsed=timedelta(minutes=1),
        finished_at_label="2026-07-31 10:00 UTC",
        questions=weird_question,
        answers={0: 0},
    )
    assert pdf_bytes.startswith(b"%PDF")


def test_send_email_returns_false_without_config_and_never_touches_network(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("no deberia intentar conectar sin SMTP configurado")

    monkeypatch.setattr("smtplib.SMTP", fail_if_called)
    monkeypatch.setattr("smtplib.SMTP_SSL", fail_if_called)

    assert send_email("alumno@example.com", "asunto", "texto", "<p>html</p>") is False


def test_send_email_returns_false_for_invalid_recipient(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "bot@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("no deberia intentar conectar con un destinatario invalido")

    monkeypatch.setattr("smtplib.SMTP", fail_if_called)

    assert send_email("no-es-un-correo", "asunto", "texto", "<p>html</p>") is False


class _FakeSMTP:
    sent = []

    def __init__(self, host, port, timeout=30):
        self.host = host
        self.port = port

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        pass

    def login(self, user, password):
        self.user = user
        self.password = password

    def sendmail(self, sender, recipients, message):
        _FakeSMTP.sent.append((sender, recipients, message))


def test_send_email_success_path_uses_starttls_for_non_ssl_port(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "bot@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    _FakeSMTP.sent = []
    monkeypatch.setattr("smtplib.SMTP", _FakeSMTP)

    ok = send_email("alumno@example.com", "asunto", "texto plano", "<p>html</p>")

    assert ok is True
    assert len(_FakeSMTP.sent) == 1
    sender, recipients, message = _FakeSMTP.sent[0]
    assert recipients == ["alumno@example.com"]
    assert "asunto" in message


def test_send_email_with_attachment_includes_pdf_part(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "bot@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    _FakeSMTP.sent = []
    monkeypatch.setattr("smtplib.SMTP", _FakeSMTP)

    fake_pdf = b"%PDF-1.3\n%fake pdf content for testing\n"
    ok = send_email(
        "alumno@example.com", "asunto", "texto plano", "<p>html</p>",
        attachment_bytes=fake_pdf, attachment_filename="simulacro_test.pdf",
    )

    assert ok is True
    assert len(_FakeSMTP.sent) == 1
    _, recipients, raw_message = _FakeSMTP.sent[0]
    assert recipients == ["alumno@example.com"]

    parsed = message_from_string(raw_message)
    pdf_parts = [p for p in parsed.walk() if p.get_content_type() == "application/pdf"]
    assert len(pdf_parts) == 1
    assert pdf_parts[0].get_filename() == "simulacro_test.pdf"
    assert pdf_parts[0].get_payload(decode=True) == fake_pdf

    text_parts = [p for p in parsed.walk() if p.get_content_type() == "text/plain"]
    assert len(text_parts) == 1


def test_send_email_without_attachment_has_no_pdf_part(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "bot@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    _FakeSMTP.sent = []
    monkeypatch.setattr("smtplib.SMTP", _FakeSMTP)

    send_email("alumno@example.com", "asunto", "texto", "<p>html</p>")

    _, _, raw_message = _FakeSMTP.sent[0]
    parsed = message_from_string(raw_message)
    pdf_parts = [p for p in parsed.walk() if p.get_content_type() == "application/pdf"]
    assert len(pdf_parts) == 0


class _RaisingSMTP:
    def __init__(self, *args, **kwargs):
        raise OSError("no se pudo conectar")


def test_send_email_returns_false_when_smtp_raises(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "bot@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setattr("smtplib.SMTP", _RaisingSMTP)

    assert send_email("alumno@example.com", "asunto", "texto", "<p>html</p>") is False
