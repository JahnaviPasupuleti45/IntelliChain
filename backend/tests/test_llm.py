"""LLM path tests. The Groq and Gemini HTTP APIs are faked, so no key or network is needed."""
import pytest
import requests

import llm
from app import create_app
from config import TestConfig
from conftest import send_reading

ANSWER = "Notify QA within 30 minutes [Pharmaceutical Cold Chain SOP - Pharma temperature excursion response]."


class GroqConfig(TestConfig):
    GROQ_API_KEY = "fake-groq-key"


class GeminiConfig(TestConfig):
    GEMINI_API_KEY = "fake-gemini-key"


class FakeResponse:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


@pytest.fixture
def fake_api(monkeypatch):
    """Replace requests.post with a fake that answers like Groq or Gemini and records calls."""
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "body": json})
        if "groq" in url:
            return FakeResponse({"choices": [{"message": {"content": ANSWER}}]})
        return FakeResponse({"candidates": [{"content": {"parts": [{"text": ANSWER}]}}]})

    monkeypatch.setattr(llm.requests, "post", fake_post)
    return calls


def test_groq_report_uses_sop_context(fake_api):
    client = create_app(GroqConfig).test_client()
    res = send_reading(client, temperature=18, humidity=70, delay_hours=6)
    assert res.json["report_source"] == "llm"
    assert res.json["report"] == ANSWER

    call = fake_api[0]
    assert call["url"] == llm.GROQ_URL
    assert call["headers"]["Authorization"] == "Bearer fake-groq-key"
    assert call["body"]["model"] == "openai/gpt-oss-120b"
    # The retrieved pharma SOP is in the prompt (this is the RAG part)
    assert "Pharma temperature excursion response" in call["body"]["messages"][0]["content"]


def test_gemini_report(fake_api):
    client = create_app(GeminiConfig).test_client()
    res = send_reading(client, temperature=18, humidity=70, delay_hours=6)
    assert res.json["report_source"] == "llm"
    assert fake_api[0]["url"].endswith("gemini-2.5-flash:generateContent")
    assert fake_api[0]["headers"]["x-goog-api-key"] == "fake-gemini-key"


def test_health_reports_provider(fake_api):
    assert create_app(GroqConfig).test_client().get("/api/health").json["llm_provider"] == "groq"
    assert create_app(TestConfig).test_client().get("/api/health").json["llm_provider"] is None


def test_low_risk_report_skips_the_llm(fake_api):
    client = create_app(GroqConfig).test_client()
    res = send_reading(client, temperature=5, humidity=45, delay_hours=0.2)
    assert res.json["report_source"] == "template"
    assert fake_api == []


def test_llm_failure_falls_back_to_template(monkeypatch):
    def failing_post(*args, **kwargs):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(llm.requests, "post", failing_post)
    client = create_app(GroqConfig).test_client()
    res = send_reading(client, temperature=18, humidity=70, delay_hours=6)
    assert res.status_code == 201
    assert res.json["report_source"] == "template"
