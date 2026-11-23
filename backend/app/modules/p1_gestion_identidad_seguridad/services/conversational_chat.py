"""Bounded conversational inference; no document access, tools or provider failover."""

import httpx


def complete_chat(system: str, prompt: str, settings) -> tuple[str, str]:
    from app.integrations.llm.self_hosted import completion, is_configured

    if is_configured(settings):
        return completion(system, prompt, max_tokens=320, timeout_seconds=45), "modelo_propio"
    if not settings.groq_api_key:
        raise ValueError("provider_unavailable")
    payload = {
        "model": settings.groq_question_model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_completion_tokens": 700,
    }
    if settings.groq_question_model == "openai/gpt-oss-20b":
        payload["reasoning_effort"] = "low"
    with httpx.Client(timeout=httpx.Timeout(12, connect=3), follow_redirects=False) as client:
        response = client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": "Bearer " + settings.groq_api_key.get_secret_value()},
            json=payload,
        )
        response.raise_for_status()
        if len(response.content) > 200_000:
            raise ValueError("response_too_large")
        choice = response.json()["choices"][0]
        if choice.get("finish_reason") != "stop":
            raise ValueError("incomplete_response")
        return choice["message"]["content"], "groq"
