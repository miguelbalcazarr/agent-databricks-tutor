import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.client import generate_question_with_ai
from agent.prompts import QUESTION_GENERATION_SYSTEM_PROMPT

_FAKE_QUESTION_JSON = json.dumps(
    {"scenario": "s", "options": ["a", "b"], "correct_index": 0, "explanation": "e"}
)


def test_returns_none_without_api_key_and_never_calls_network(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("no deberia intentar red sin OPENAI_API_KEY")

    monkeypatch.setattr("urllib.request.urlopen", fail_if_called)

    result = generate_question_with_ai(
        objective_text="Understand Delta Lake.",
        section_name="Databricks Intelligence Platform",
        weight_pct=6,
        source_text="Delta Lake is a storage layer...",
        sample_questions=[],
    )

    assert result is None


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({"choices": [{"message": {"content": _FAKE_QUESTION_JSON}}]}).encode("utf-8")


def _capture_request(monkeypatch, captured: list) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")

    def fake_urlopen(req, timeout=60):
        captured.append(req)
        return _FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)


def test_default_system_prompt_matches_module_constant_exactly(monkeypatch):
    captured = []
    _capture_request(monkeypatch, captured)

    generate_question_with_ai(
        objective_text="Understand Delta Lake.",
        section_name="Databricks Intelligence Platform",
        weight_pct=6,
        source_text="Delta Lake is a storage layer...",
        sample_questions=[],
    )

    payload = json.loads(captured[0].data.decode("utf-8"))
    assert payload["messages"][0]["content"] == QUESTION_GENERATION_SYSTEM_PROMPT


def test_custom_system_prompt_is_sent_in_the_payload(monkeypatch):
    captured = []
    _capture_request(monkeypatch, captured)

    generate_question_with_ai(
        objective_text="Understand Delta Lake.",
        section_name="Databricks Intelligence Platform",
        weight_pct=6,
        source_text="Delta Lake is a storage layer...",
        sample_questions=[],
        system_prompt="CUSTOM SYSTEM PROMPT",
    )

    payload = json.loads(captured[0].data.decode("utf-8"))
    assert payload["messages"][0]["content"] == "CUSTOM SYSTEM PROMPT"


def test_custom_doc_source_name_is_reflected_in_the_user_prompt(monkeypatch):
    captured = []
    _capture_request(monkeypatch, captured)

    generate_question_with_ai(
        objective_text="Understand Delta Lake.",
        section_name="Databricks Intelligence Platform",
        weight_pct=6,
        source_text="Delta Lake is a storage layer...",
        sample_questions=[],
        doc_source_name="docs.acme.example",
    )

    payload = json.loads(captured[0].data.decode("utf-8"))
    assert "docs.acme.example" in payload["messages"][1]["content"]
