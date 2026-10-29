"""Image analysis API routes."""

import os
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from services.audio_analysis_service import transcribe_audio
from services.scene_analysis_service import classify_scene
from services.object_detection_service import detect_objects, get_confidence_threshold
from services.video_analysis_service import analyze_video as analyze_video_file
from services.evidence_fusion_service import fuse_analysis_results
from services.groq_service import (
    GroqDependencyError,
    GroqProviderError,
    GroqTimeoutError,
    MissingGroqAPIKey,
    generate_evidence_reasoning,
)
from utils.file_utils import UploadValidationError, generate_safe_filename, validate_upload

analyze_blueprint = Blueprint("analyze", __name__)


@analyze_blueprint.errorhandler(RequestEntityTooLarge)
def handle_request_too_large(_error):
    return jsonify({"success": False, "message": "Upload exceeds the 100 MiB limit."}), 413


@analyze_blueprint.post("/api/analyze/image")
def analyze_image():
    uploaded_file = request.files.get("file")
    if uploaded_file is None:
        return jsonify({"success": False, "message": "Missing required multipart file field 'file'."}), 400

    try:
        metadata = validate_upload(uploaded_file)
        if metadata["file_type"] != "image":
            raise UploadValidationError("Only supported image files can be analyzed.", 415)
        threshold = get_confidence_threshold(
            current_app.config.get("RTDETR_CONFIDENCE_THRESHOLD")
        )
    except UploadValidationError as error:
        return jsonify({"success": False, "message": str(error)}), error.status_code
    except ValueError as error:
        return jsonify({"success": False, "message": str(error)}), 500

    upload_directory = Path(current_app.root_path) / current_app.config.get(
        "UPLOAD_FOLDER", "data/uploads"
    )
    image_path = upload_directory / generate_safe_filename(uploaded_file.filename)
    try:
        upload_directory.mkdir(parents=True, exist_ok=True)
        uploaded_file.save(image_path)
        detections = detect_objects(image_path, confidence_threshold=threshold)
    except ValueError as error:
        return jsonify({"success": False, "message": str(error)}), 400
    except Exception:
        current_app.logger.exception("RT-DETR image inference failed")
        return jsonify({"success": False, "message": "Image analysis failed."}), 500
    finally:
        try:
            image_path.unlink(missing_ok=True)
        except OSError:
            current_app.logger.exception("Failed to remove temporary analysis image")

    return jsonify({
        "success": True,
        "analysis": {
            "image": uploaded_file.filename,
            "detections": detections,
        },
    }), 200


@analyze_blueprint.post("/api/analyze/scene")
def analyze_scene():
    uploaded_file = request.files.get("file")
    if uploaded_file is None:
        return jsonify({"success": False, "message": "Missing required multipart file field 'file'."}), 400

    try:
        metadata = validate_upload(uploaded_file)
        if metadata["file_type"] != "image":
            raise UploadValidationError("Only supported image files can be analyzed.", 415)
    except UploadValidationError as error:
        return jsonify({"success": False, "message": str(error)}), error.status_code

    upload_directory = Path(current_app.root_path) / current_app.config.get(
        "UPLOAD_FOLDER", "data/uploads"
    )
    image_path = upload_directory / generate_safe_filename(uploaded_file.filename)
    try:
        upload_directory.mkdir(parents=True, exist_ok=True)
        uploaded_file.save(image_path)
        scene = classify_scene(image_path)
    except ValueError as error:
        return jsonify({"success": False, "message": str(error)}), 400
    except Exception:
        current_app.logger.exception("CLIP scene analysis failed")
        return jsonify({"success": False, "message": "Scene analysis failed."}), 500
    finally:
        try:
            image_path.unlink(missing_ok=True)
        except OSError:
            current_app.logger.exception("Failed to remove temporary scene image")

    return jsonify({
        "success": True,
        "analysis": {
            "image": uploaded_file.filename,
            "scene": scene["category"],
            "confidence": scene["confidence"],
            "top_predictions": scene["top_predictions"],
        },
    }), 200


@analyze_blueprint.post("/api/analyze/audio")
def analyze_audio():
    uploaded_file = request.files.get("file")
    if uploaded_file is None:
        return jsonify({"success": False, "message": "Missing required multipart file field 'file'."}), 400

    try:
        metadata = validate_upload(uploaded_file)
        if metadata["file_type"] != "audio":
            raise UploadValidationError("Only supported audio files can be transcribed.", 415)
    except UploadValidationError as error:
        return jsonify({"success": False, "message": str(error)}), error.status_code

    upload_directory = Path(current_app.root_path) / current_app.config.get(
        "UPLOAD_FOLDER", "data/uploads"
    )
    audio_path = upload_directory / generate_safe_filename(uploaded_file.filename)
    try:
        upload_directory.mkdir(parents=True, exist_ok=True)
        uploaded_file.save(audio_path)
        transcription = transcribe_audio(audio_path)
    except Exception:
        current_app.logger.exception("Whisper audio transcription failed")
        return jsonify({"success": False, "message": "Audio transcription failed."}), 500
    finally:
        try:
            audio_path.unlink(missing_ok=True)
        except OSError:
            current_app.logger.exception("Failed to remove temporary audio file")

    return jsonify({
        "success": True,
        "analysis": {
            "audio": uploaded_file.filename,
            "transcription": transcription.get("text", ""),
            "language": transcription.get("language"),
        },
    }), 200


@analyze_blueprint.post("/api/analyze/video")
def analyze_video():
    uploaded_file = request.files.get("file")
    if uploaded_file is None:
        return jsonify({"success": False, "message": "Missing required multipart file field 'file'."}), 400

    try:
        metadata = validate_upload(uploaded_file)
        if metadata["file_type"] != "video":
            raise UploadValidationError("Only supported video files can be analyzed.", 415)
    except UploadValidationError as error:
        return jsonify({"success": False, "message": str(error)}), error.status_code

    upload_directory = Path(current_app.root_path) / current_app.config.get(
        "UPLOAD_FOLDER", "data/uploads"
    )
    video_path = upload_directory / generate_safe_filename(uploaded_file.filename)
    try:
        upload_directory.mkdir(parents=True, exist_ok=True)
        uploaded_file.save(video_path)
        video_analysis = analyze_video_file(video_path)
    except ValueError as error:
        return jsonify({"success": False, "message": str(error)}), 400
    except Exception:
        current_app.logger.exception("OpenCV video analysis failed")
        return jsonify({"success": False, "message": "Video analysis failed."}), 500
    finally:
        try:
            video_path.unlink(missing_ok=True)
        except OSError:
            current_app.logger.exception("Failed to remove temporary video file")

    return jsonify({
        "success": True,
        "analysis": {
            "filename": uploaded_file.filename,
            "metadata": video_analysis["metadata"],
            "sampled_frames": video_analysis["sampled_frames"],
        },
    }), 200


@analyze_blueprint.post("/api/analyze/fusion")
def analyze_fusion():
    if not request.is_json:
        return jsonify({"success": False, "message": "Content-Type must be application/json."}), 415

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not payload:
        return jsonify({"success": False, "message": "Request body must be a non-empty JSON object."}), 400

    try:
        fusion_result = fuse_analysis_results(payload)
    except ValueError as error:
        return jsonify({"success": False, "message": str(error)}), 400

    return jsonify({"success": True, **fusion_result}), 200


@analyze_blueprint.post("/api/analyze/reason")
def analyze_reason():
    """Return cautious LLM interpretation of deterministic fusion results."""
    if not request.is_json:
        return jsonify({"success": False, "message": "Content-Type must be application/json."}), 415
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not payload:
        return jsonify({"success": False, "message": "Request body must be a non-empty JSON object."}), 400
    try:
        reasoning = generate_evidence_reasoning(payload)
    except ValueError as error:
        return jsonify({"success": False, "message": str(error)}), 400
    except MissingGroqAPIKey:
        return jsonify({"success": False, "message": "GROQ_API_KEY is not configured."}), 503
    except GroqDependencyError:
        return jsonify({"success": False, "message": "Groq SDK is unavailable."}), 503
    except GroqTimeoutError:
        return jsonify({"success": False, "message": "Groq request timed out."}), 504
    except GroqProviderError:
        return jsonify({"success": False, "message": "Groq reasoning request failed."}), 502
    return jsonify({"success": True, "reasoning": reasoning}), 200
