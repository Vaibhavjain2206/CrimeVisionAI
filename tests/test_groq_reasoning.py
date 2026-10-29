import json
from types import SimpleNamespace

import pytest

from api import analyze_routes
from services import groq_service


def _result():
    return {
        "case_summary": "The evidence records several observations.",
        "key_observations": ["A person-shaped object was detected."],
        "timeline_interpretation": "The supplied events are presented chronologically.",
        "evidence_assessment": ["The model-generated observation needs review."],
        "uncertainties": ["Identity and intent are not established."],
        "recommended_investigator_checks": ["Verify timestamps against source files."],
    }


def _payload():
    return {
        "normalized_evidence": [{"evidence_id": "ev-1", "modality": "image"}],
        "forensic_timeline": [],
        "summary": {"evidence_count": 1},
        "unrelated": "must not be sent to Groq",
    }


def _completion(result):
    message = SimpleNamespace(content=json.dumps(result))
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _client(create):
    return SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=create)
    ))


@pytest.fixture
def flask_client():
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(analyze_routes.analyze_blueprint)
    return app.test_client()


def test_success_returns_structured_reasoning(monkeypatch, flask_client):
    monkeypatch.setenv("GROQ_API_KEY", "mock-key")
    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        return _completion(_result())

    monkeypatch.setattr(groq_service, "_create_client", lambda _key: _client(create))
    response = flask_client.post("/api/analyze/reason", json=_payload())
    body = response.get_json()
    assert response.status_code == 200
    assert body["reasoning"] == _result()
    assert set(body["reasoning"]) == set(groq_service.RESPONSE_FIELDS)
    assert captured["response_format"] == {"type": "json_object"}


def test_model_receives_only_relevant_deterministic_context(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "mock-key")
    monkeypatch.setenv("GROQ_MODEL", "test-model")
    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        return _completion(_result())

    monkeypatch.setattr(groq_service, "_create_client", lambda _key: _client(create))
    groq_service.generate_evidence_reasoning(_payload())
    prompt_data = captured["messages"][1]["content"]
    assert captured["model"] == "test-model"
    assert '"evidence_id":"ev-1"' in prompt_data
    assert "unrelated" not in prompt_data


def test_missing_api_key_returns_503(monkeypatch, flask_client):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    response = flask_client.post("/api/analyze/reason", json=_payload())
    assert response.status_code == 503


@pytest.mark.parametrize(
    "data,content_type",
    [
        ("", "application/json"),
        ("{bad json", "application/json"),
        ("{}", "application/json"),
        ('{"unexpected": 1}', "application/json"),
        ('{"summary": []}', "application/json"),
        ('{"summary": {}}', "text/plain"),
    ],
)
def test_empty_malformed_or_invalid_request_returns_client_error(
    flask_client, data, content_type
):
    response = flask_client.post(
        "/api/analyze/reason", data=data, content_type=content_type
    )
    assert response.status_code in (400, 415)


def test_provider_failure_returns_502(monkeypatch, flask_client):
    monkeypatch.setenv("GROQ_API_KEY", "mock-key")

    def fail(**_kwargs):
        raise RuntimeError("provider failure")

    monkeypatch.setattr(groq_service, "_create_client", lambda _key: _client(fail))
    response = flask_client.post("/api/analyze/reason", json=_payload())
    assert response.status_code == 502


def test_provider_timeout_returns_504(monkeypatch, flask_client):
    monkeypatch.setenv("GROQ_API_KEY", "mock-key")

    class APITimeoutError(Exception):
        pass

    def fail(**_kwargs):
        raise APITimeoutError("timeout")

    monkeypatch.setattr(groq_service, "_create_client", lambda _key: _client(fail))
    response = flask_client.post("/api/analyze/reason", json=_payload())
    assert response.status_code == 504


def test_invalid_provider_response_returns_502(monkeypatch, flask_client):
    monkeypatch.setenv("GROQ_API_KEY", "mock-key")
    monkeypatch.setattr(
        groq_service,
        "_create_client",
        lambda _key: _client(lambda **_kwargs: _completion({"unexpected": True})),
    )
    response = flask_client.post("/api/analyze/reason", json=_payload())
    assert response.status_code == 502
