"""Video analysis API tests with OpenCV and RT-DETR processing mocked."""

import io

import pytest

from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("api.analyze_routes.Path", lambda *_: tmp_path)
    app.config.update(TESTING=True, MAX_CONTENT_LENGTH=100 * 1024 * 1024)
    with app.test_client() as test_client:
        yield test_client


def test_video_analysis_returns_metadata_and_sampled_frames(client, monkeypatch):
    result = {
        "metadata": {
            "fps": 30.0,
            "frame_count": 90,
            "duration_seconds": 3.0,
            "width": 640,
            "height": 480,
            "sampling_interval_seconds": 1.0,
        },
        "sampled_frames": [
            {
                "frame_number": 0,
                "timestamp_seconds": 0.0,
                "frame_info": {"width": 640, "height": 480, "channels": 3},
                "detections": [{
                    "label": "person",
                    "confidence": 0.91,
                    "bbox": {"x1": 10, "y1": 20, "x2": 100, "y2": 200},
                }],
            }
        ],
    }
    monkeypatch.setattr("api.analyze_routes.analyze_video_file", lambda _path: result)

    response = client.post(
        "/api/analyze/video",
        data={"file": (io.BytesIO(b"mocked video bytes"), "scene.MP4")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["analysis"]["filename"] == "scene.MP4"
    assert payload["analysis"]["metadata"]["fps"] == 30.0
    assert payload["analysis"]["sampled_frames"][0]["frame_number"] == 0
    assert payload["analysis"]["sampled_frames"][0]["detections"][0]["label"] == "person"


def test_video_analysis_rejects_missing_file(client):
    response = client.post("/api/analyze/video", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_video_analysis_rejects_unsupported_extension(client):
    response = client.post(
        "/api/analyze/video",
        data={"file": (io.BytesIO(b"not video"), "evidence.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 415
    assert response.get_json()["success"] is False


def test_video_analysis_rejects_empty_file(client):
    response = client.post(
        "/api/analyze/video",
        data={"file": (io.BytesIO(b""), "empty.mkv")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "empty" in response.get_json()["message"].lower()
