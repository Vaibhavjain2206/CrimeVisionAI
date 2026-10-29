"""Tests for deterministic multimodal evidence normalization and timelines."""

import pytest

from app import app
from services.evidence_fusion_service import fuse_analysis_results


def test_normalizes_image_scene_audio_and_video_evidence():
    result = fuse_analysis_results({
        "image_analysis": {
            "analysis": {
                "image": "scene.jpg",
                "detections": [{
                    "label": "person", "confidence": 0.94,
                    "bbox": {"x1": 1, "y1": 2, "x2": 3, "y2": 4},
                }],
            }
        },
        "scene_analysis": {
            "analysis": {
                "image": "scene.jpg", "scene": "street or roadway",
                "confidence": 0.81,
                "top_predictions": [{"category": "street or roadway", "confidence": 0.81}],
            }
        },
        "audio_analysis": {
            "analysis": {"audio": "recording.wav", "transcription": "Help me.", "language": "en"}
        },
        "video_analysis": {
            "analysis": {
                "filename": "camera.mp4",
                "sampled_frames": [{
                    "frame_number": 30, "timestamp_seconds": 1.0,
                    "frame_info": {"width": 640, "height": 480, "channels": 3},
                    "detections": [{"label": "car", "confidence": 0.72}],
                }],
            }
        },
    })

    modalities = {item["modality"] for item in result["normalized_evidence"]}
    assert modalities == {"image", "audio", "video"}
    assert {item["evidence_type"] for item in result["normalized_evidence"]} >= {
        "object_detection", "scene_classification", "transcription", "video_frame"
    }


def test_timeline_is_sorted_chronologically_and_preserves_confidence():
    result = fuse_analysis_results({
        "video": {"filename": "clip.mp4", "sampled_frames": [
            {"frame_number": 60, "timestamp_seconds": 2.0, "frame_info": {}},
            {"frame_number": 0, "timestamp_seconds": 0.0, "frame_info": {}},
        ]},
        "audio": {"audio": "voice.mp3", "transcription": "Wait", "timestamp": 1.0, "confidence": 0.875},
    })

    timestamps = [item["timestamp"] for item in result["forensic_timeline"]]
    assert timestamps == sorted(timestamps)
    audio_item = next(item for item in result["normalized_evidence"] if item["modality"] == "audio")
    assert audio_item["confidence"] == 0.875


def test_missing_optional_modalities_are_handled():
    result = fuse_analysis_results({
        "audio_analysis": {"transcription": "A door closed.", "language": "en"}
    })

    assert len(result["normalized_evidence"]) == 1
    assert result["summary"]["modality_counts"] == {"audio": 1}


def test_fusion_is_deterministic():
    payload = {"image": {"image": "scene.jpg", "detections": [
        {"label": "person", "confidence": 0.94}
    ]}}
    assert fuse_analysis_results(payload) == fuse_analysis_results(payload)


def test_empty_service_request_is_rejected():
    with pytest.raises(ValueError):
        fuse_analysis_results({})


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_fusion_endpoint_returns_normalized_results(client):
    response = client.post(
        "/api/analyze/fusion",
        json={"audio": {"audio": "voice.wav", "transcription": "Hello", "language": "en"}},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["normalized_evidence"][0]["observation"] == "Hello"
    assert payload["forensic_timeline"]
    assert payload["summary"]["evidence_count"] == 1


@pytest.mark.parametrize("body", [b"", b"{not json", b"{}", b"[]"])
def test_fusion_endpoint_rejects_malformed_or_empty_json(client, body):
    response = client.post(
        "/api/analyze/fusion", data=body, content_type="application/json"
    )
    assert response.status_code == 400
    assert response.get_json()["success"] is False
