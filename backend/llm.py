"""
Small LLM client supporting two providers:

  - Groq   (GROQ_API_KEY):   OpenAI-compatible chat API, default model openai/gpt-oss-120b
  - Gemini (GEMINI_API_KEY): Google's generateContent API

If both keys are set, Groq is used. generate() returns None when no key is set
or the call fails, so the rest of the app can fall back to non-LLM behaviour
instead of crashing.
"""
import logging

import requests
from flask import current_app

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"
log = logging.getLogger(__name__)


def provider():
    """'groq', 'gemini' or None, depending on which API key is configured."""
    if current_app.config.get("GROQ_API_KEY"):
        return "groq"
    if current_app.config.get("GEMINI_API_KEY"):
        return "gemini"
    return None


def is_enabled():
    return provider() is not None


def _post(url, headers, body):
    response = requests.post(url, headers=headers, json=body, timeout=60)
    response.raise_for_status()
    return response.json()


def _generate_groq(prompt, temperature):
    config = current_app.config
    body = {
        "model": config["GROQ_MODEL"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    # gpt-oss models "think" before answering; low effort keeps answers fast
    if config["GROQ_MODEL"].startswith("openai/gpt-oss"):
        body["reasoning_effort"] = "low"
    data = _post(GROQ_URL, {"Authorization": f"Bearer {config['GROQ_API_KEY']}"}, body)
    return data["choices"][0]["message"]["content"]


def _generate_gemini(prompt, temperature):
    config = current_app.config
    data = _post(
        f"{GEMINI_URL}/{config['GEMINI_MODEL']}:generateContent",
        {"x-goog-api-key": config["GEMINI_API_KEY"]},
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        },
    )
    return data["candidates"][0]["content"]["parts"][0]["text"]


def generate(prompt, temperature=0.2):
    """Generate text for a prompt. Returns None if the LLM is unavailable."""
    name = provider()
    if name is None:
        return None
    try:
        text = _generate_groq(prompt, temperature) if name == "groq" else _generate_gemini(prompt, temperature)
        # Some models use narrow no-break spaces; plain spaces display everywhere
        return text.replace(" ", " ").strip() or None
    except (requests.RequestException, KeyError, IndexError, TypeError, AttributeError) as e:
        log.warning("%s generate failed: %s", name, e)
        return None
