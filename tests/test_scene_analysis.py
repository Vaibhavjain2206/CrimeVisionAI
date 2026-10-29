"""Scene analysis API tests; CLIP inference is mocked to avoid model downloads."""

import io

import pytest

from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("api.analyze_routes.Path", lambda *_: tmp_path)
    app.config.update(TESTING=True, MAX_CONTENT_LENGTH=100 * 1024 * 1024)
    with app.test_client() as test_client:
        yield test_client


def test_scene_analysis_returns_prediction_structure(client, monkeypatch):
    scene_result = {
        "category": "street or roadway",
        "confidence": 0.82,
        "top_predictions": [
            {"category": "street or roadway", "confidence": 0.82},
            {"category": "parking area", "confidence": 0.11},
        ],
    }
    monkeypatch.setattr("api.analyze_routes.classify_scene", lambda _path: scene_result)

    response = client.post(
        "/api/analyze/scene",
        data={"file": (io.BytesIO(b"mocked image bytes"), "scene.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["analysis"]["image"] == "scene.jpg"
    assert payload["analysis"]["scene"] == "street or roadway"
    assert payload["analysis"]["confidence"] == 0.82
    assert payload["analysis"]["top_predictions"] == scene_result["top_predictions"]


def test_scene_analysis_rejects_missing_file(client):
    response = client.post("/api/analyze/scene", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_scene_analysis_rejects_unsupported_extension(client):
    response = client.post(
        "/api/analyze/scene",
        data={"file": (io.BytesIO(b"document"), "evidence.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 415
    assert response.get_json()["success"] is False


def test_scene_analysis_rejects_empty_image(client):
    response = client.post(
        "/api/analyze/scene",
        data={"file": (io.BytesIO(b""), "empty.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "empty" in response.get_json()["message"].lower()
