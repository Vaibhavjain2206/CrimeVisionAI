"""Audio analysis API tests with Whisper inference mocked."""

import io

import pytest

from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("api.analyze_routes.Path", lambda *_: tmp_path)
    app.config.update(TESTING=True, MAX_CONTENT_LENGTH=100 * 1024 * 1024)
    with app.test_client() as test_client:
        yield test_client


def test_audio_analysis_returns_transcription_and_metadata(client, monkeypatch):
    result = {"text": "Please leave the area.", "language": "en"}
    monkeypatch.setattr("api.analyze_routes.transcribe_audio", lambda _path: result)

    response = client.post(
        "/api/analyze/audio",
        data={"file": (io.BytesIO(b"mocked audio bytes"), "recording.MP3")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["analysis"]["audio"] == "recording.MP3"
    assert payload["analysis"]["transcription"] == result["text"]
    assert payload["analysis"]["language"] == "en"


def test_audio_analysis_rejects_missing_file(client):
    response = client.post("/api/analyze/audio", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_audio_analysis_rejects_unsupported_extension(client):
    response = client.post(
        "/api/analyze/audio",
        data={"file": (io.BytesIO(b"not audio"), "evidence.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 415
    assert response.get_json()["success"] is False


def test_audio_analysis_rejects_empty_file(client):
    response = client.post(
        "/api/analyze/audio",
        data={"file": (io.BytesIO(b""), "empty.wav")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "empty" in response.get_json()["message"].lower()
