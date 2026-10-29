"""API contract tests for RT-DETR image analysis (inference is mocked)."""

import io

import pytest

from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("api.analyze_routes.Path", lambda *_: tmp_path)
    app.config.update(TESTING=True, MAX_CONTENT_LENGTH=100 * 1024 * 1024)
    with app.test_client() as test_client:
        yield test_client


def test_analyze_image_response_structure(client, monkeypatch):
    detections = [{
        "label": "person",
        "confidence": 0.94,
        "bbox": {"x1": 120, "y1": 80, "x2": 420, "y2": 600},
    }]
    monkeypatch.setattr("api.analyze_routes.detect_objects", lambda *_args, **_kwargs: detections)

    response = client.post(
        "/api/analyze/image",
        data={"file": (io.BytesIO(b"sample image bytes"), "scene.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    result = response.get_json()
    assert result["success"] is True
    assert result["analysis"]["image"] == "scene.jpg"
    assert result["analysis"]["detections"] == detections


def test_analyze_image_rejects_missing_file(client):
    response = client.post("/api/analyze/image", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_analyze_image_rejects_unsupported_extension(client):
    response = client.post(
        "/api/analyze/image",
        data={"file": (io.BytesIO(b"not an image"), "evidence.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 415
    assert response.get_json()["success"] is False


def test_analyze_image_rejects_empty_file(client):
    response = client.post(
        "/api/analyze/image",
        data={"file": (io.BytesIO(b""), "empty.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "empty" in response.get_json()["message"].lower()
