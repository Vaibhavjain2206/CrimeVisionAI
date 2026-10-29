"""REST endpoint for uploading forensic evidence files."""

from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from utils.file_utils import (
    UploadValidationError,
    generate_safe_filename,
    validate_upload,
)

upload_blueprint = Blueprint("upload", __name__)


@upload_blueprint.errorhandler(RequestEntityTooLarge)
def handle_request_too_large(_error):
    return jsonify({"success": False, "message": "Upload exceeds the 100 MiB limit."}), 413


@upload_blueprint.post("/api/upload")
def upload_evidence():
    uploaded_file = request.files.get("file")
    if uploaded_file is None:
        return jsonify({"success": False, "message": "Missing required multipart file field 'file'."}), 400

    try:
        metadata = validate_upload(uploaded_file)
        stored_filename = generate_safe_filename(uploaded_file.filename)
    except UploadValidationError as error:
        return jsonify({"success": False, "message": str(error)}), error.status_code

    upload_directory = Path(current_app.root_path) / current_app.config.get(
        "UPLOAD_FOLDER", "data/uploads"
    )
    try:
        upload_directory.mkdir(parents=True, exist_ok=True)
        uploaded_file.save(upload_directory / stored_filename)
    except OSError:
        current_app.logger.exception("Failed to save uploaded evidence")
        return jsonify({"success": False, "message": "Unable to save uploaded evidence."}), 500

    evidence = {
        "id": uuid4().hex,
        "original_filename": uploaded_file.filename,
        "stored_filename": stored_filename,
        "file_type": metadata["file_type"],
        "extension": metadata["extension"],
        "size": metadata["size"],
    }
    return jsonify({
        "success": True,
        "message": "Evidence uploaded successfully",
        "evidence": evidence,
    }), 201
