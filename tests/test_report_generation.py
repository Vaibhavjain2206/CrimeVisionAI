import re

import pytest
from flask import Flask

from api.report_routes import report_blueprint


@pytest.fixture
def report_app(tmp_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.root_path = str(tmp_path)
    (tmp_path / "data" / "reports").mkdir(parents=True)
    app.register_blueprint(report_blueprint)
    return app


def _payload():
    return {
        "case_id": "CASE-TEST-01",
        "fusion": {
            "normalized_evidence": [
                {
                    "evidence_id": "ev-test",
                    "evidence_type": "object_detection",
                    "source_filename": "evidence.jpg",
                    "timestamp": 2.5,
                    "modality": "image",
                    "observation": "Detected object: person",
                    "confidence": 0.91,
                    "metadata": {"bbox": {"x1": 1, "y1": 2, "x2": 3, "y2": 4}},
                },
                {
                    "evidence_id": "ev-audio",
                    "evidence_type": "transcription",
                    "source_filename": "recording.wav",
                    "timestamp": 3.0,
                    "modality": "audio",
                    "observation": "Door closes",
                    "confidence": None,
                    "metadata": {"language": "en"},
                },
            ],
            "forensic_timeline": [
                {"evidence_id": "ev-test", "timestamp": 2.5,
                 "source_filename": "evidence.jpg", "observation": "Detected object: person",
                 "confidence": 0.91, "modality": "image", "evidence_type": "object_detection"}
            ],
            "summary": {"evidence_count": 2, "modality_counts": {"audio": 1, "image": 1}},
        },
        "reasoning": {
            "case_summary": "The supplied results describe one image detection and one transcript entry.",
            "key_observations": ["A person label was detected in evidence.jpg."],
            "timeline_interpretation": "The image event is timestamped at 2.5 seconds.",
            "evidence_assessment": ["The detection confidence is 0.91."],
            "uncertainties": ["The detection does not establish identity."],
            "recommended_investigator_checks": ["Review the original image."],
        },
    }


def test_successful_report_generation_and_download(report_app):
    client = report_app.test_client()
    response = client.post("/api/report/generate", json=_payload())
    assert response.status_code == 201
    body = response.get_json()
    assert body["status"] == "generated"
    assert re.fullmatch(r"[a-f0-9]{32}", body["report_id"])
    report_file = report_app.root_path + "/data/reports/" + body["filename"]
    with open(report_file, "rb") as handle:
        pdf = handle.read()
    assert pdf.startswith(b"%PDF-")
    assert b"CrimeVision AI" in pdf
    assert b"Detected object: person" in pdf
    assert b"Door closes" in pdf
    assert b"evidence.jpg" in pdf
    assert b"person label was detected" in pdf
    for section in (
        b"Evidence summary",
        b"Key observations",
        b"Detected objects",
        b"Scene analysis",
        b"Audio and transcription findings",
        b"Video analysis and timeline",
        b"Evidence fusion timeline",
        b"Evidence assessment",
        b"Uncertainties and conflicting evidence",
        b"Recommended investigator checks",
    ):
        assert section in pdf
    assert b"does not determine guilt" in pdf
    download = client.get(body["report_path"])
    assert download.status_code == 200
    assert download.mimetype == "application/pdf"


def test_generated_report_filenames_are_unique(report_app):
    client = report_app.test_client()
    first = client.post("/api/report/generate", json=_payload()).get_json()
    second = client.post("/api/report/generate", json=_payload()).get_json()
    assert first["filename"] != second["filename"]
    assert first["report_id"] != second["report_id"]


@pytest.mark.parametrize("data", [None, {}, {"fusion": {}, "reasoning": {}}])
def test_invalid_or_empty_report_input_is_rejected(report_app, data):
    response = report_app.test_client().post("/api/report/generate", json=data)
    assert response.status_code == 400


def test_malformed_json_is_rejected(report_app):
    response = report_app.test_client().post(
        "/api/report/generate", data="{broken", content_type="application/json"
    )
    assert response.status_code == 400


def test_download_returns_not_found_for_unknown_id(report_app):
    response = report_app.test_client().get("/api/report/" + "a" * 32)
    assert response.status_code == 404


def test_missing_observation_is_not_fabricated(report_app):
    payload = _payload()
    payload["fusion"]["normalized_evidence"][0]["observation"] = ""
    client = report_app.test_client()
    result = client.post("/api/report/generate", json=payload).get_json()
    with open(report_app.root_path + "/data/reports/" + result["filename"], "rb") as handle:
        pdf = handle.read()
    assert b"Not provided in submitted evidence." in pdf
