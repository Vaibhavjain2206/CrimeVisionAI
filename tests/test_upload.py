"""Tests for the evidence upload endpoint."""

import io

import pytest

from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("api.upload_routes.Path", lambda *_: tmp_path)
    app.config.update(TESTING=True, MAX_CONTENT_LENGTH=100 * 1024 * 1024)
    with app.test_client() as test_client:
        yield test_client


def test_valid_image_upload(client, tmp_path):
    response = client.post(
        "/api/upload",
        data={"file": (io.BytesIO(b"fake image bytes"), "scene.JPG")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    result = response.get_json()
    assert result["success"] is True
    assert result["evidence"]["original_filename"] == "scene.JPG"
    assert result["evidence"]["file_type"] == "image"
    assert result["evidence"]["extension"] == ".jpg"
    assert result["evidence"]["size"] == len(b"fake image bytes")
    assert (tmp_path / "data" / "uploads" / result["evidence"]["stored_filename"]).is_file()


def test_unsupported_extension(client):
    response = client.post(
        "/api/upload",
        data={"file": (io.BytesIO(b"data"), "payload.exe")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 415
    assert response.get_json()["success"] is False


def test_missing_file(client):
    response = client.post("/api/upload", data={}, content_type="multipart/form-data")

    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_empty_file(client):
    response = client.post(
        "/api/upload",
        data={"file": (io.BytesIO(b""), "empty.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "empty" in response.get_json()["message"].lower()
