import json
import os
from urllib import error, request

from agent.prompts import QUESTION_GENERATION_SYSTEM_PROMPT, build_generation_prompt


def generate_question_with_ai(
    *,
    objective_text: str,
    section_name: str,
    weight_pct: int,
    source_text: str,
    sample_questions: list[dict],
    language: str = "es",
) -> dict | None:
    """Genera una pregunta grounded via LLM. Retorna None si no hay API key o si falla la
    llamada/parseo — sin fallback heuristico: no tiene sentido inventar una pregunta sin LLM,
    el caller debe saltar el item y avisar, nunca persistir un placeholder."""
    api_key = os.getenv("OPENAI_API_KEY")
    endpoint = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        return None

    prompt = build_generation_prompt(
        objective_text=objective_text,
        section_name=section_name,
        weight_pct=weight_pct,
        source_text=source_text,
        sample_questions=sample_questions,
        language=language,
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": QUESTION_GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(endpoint, data=body, headers=headers, method="POST")
        with request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except (error.HTTPError, error.URLError, KeyError, json.JSONDecodeError, TimeoutError):
        return None
