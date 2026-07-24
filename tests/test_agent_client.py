import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.client import generate_question_with_ai


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
