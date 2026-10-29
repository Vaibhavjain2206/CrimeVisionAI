"""Deterministic normalization and timeline generation for forensic evidence."""

import hashlib
import json
import math
from datetime import datetime, timezone
from numbers import Real

_INPUT_KEYS = {
    "image": ("image", "image_analysis", "object_detection"),
    "scene": ("scene", "scene_analysis"),
    "audio": ("audio", "audio_analysis", "transcription"),
    "video": ("video", "video_analysis"),
}


def _unwrap_result(value):
    if not isinstance(value, dict):
        return {}
    nested = value.get("analysis")
    return nested if isinstance(nested, dict) else value


def _get_modality_results(payload):
    results = {}
    for modality, aliases in _INPUT_KEYS.items():
        for key in aliases:
            if key in payload:
                results[modality] = _unwrap_result(payload[key])
                break

    # Also accept a single module's direct API response at the request root.
    root_analysis = _unwrap_result(payload)
    if "image" not in results and isinstance(root_analysis.get("detections"), list):
        results["image"] = root_analysis
    if "scene" not in results and "scene" in root_analysis:
        results["scene"] = root_analysis
    if "audio" not in results and "transcription" in root_analysis:
        results["audio"] = root_analysis
    if "video" not in results and isinstance(root_analysis.get("sampled_frames"), list):
        results["video"] = root_analysis
    return results


def _normalize_timestamp(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, Real):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            numeric = float(text)
            return numeric if math.isfinite(numeric) else None
        except ValueError:
            pass
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            return text
    return None


def _timestamp_sort_key(value):
    if isinstance(value, Real):
        return (0, float(value))
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return (0, parsed.timestamp())
        except ValueError:
            return (1, value.casefold())
    return (2, "")


def _confidence(value):
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    return value if math.isfinite(float(value)) else None


def _make_evidence(evidence_type, source_filename, timestamp, modality,
                   observation, confidence=None, metadata=None, ordinal=0):
    entry = {
        "evidence_type": evidence_type,
        "source_filename": source_filename,
        "timestamp": _normalize_timestamp(timestamp),
        "modality": modality,
        "observation": observation,
        "confidence": _confidence(confidence),
        "metadata": metadata or {},
    }
    identity_data = {**entry, "ordinal": ordinal}
    stable_json = json.dumps(identity_data, sort_keys=True, separators=(",", ":"), default=str)
    entry["evidence_id"] = hashlib.sha256(stable_json.encode("utf-8")).hexdigest()[:20]
    return entry


def _detection_entries(detections, filename, timestamp, modality, base_metadata, ordinal):
    entries = []
    if not isinstance(detections, list):
        return entries
    for index, detection in enumerate(detections):
        if not isinstance(detection, dict):
            continue
        label = detection.get("label")
        if not isinstance(label, str) or not label.strip():
            continue
        metadata = dict(base_metadata)
        if isinstance(detection.get("bbox"), dict):
            metadata["bbox"] = detection["bbox"]
        entries.append(_make_evidence(
            "object_detection",
            filename,
            timestamp,
            modality,
            f"Detected object: {label.strip()}",
            detection.get("confidence"),
            metadata,
            ordinal + index,
        ))
    return entries


def _normalize_image(results):
    entries = []
    filename = results.get("image") or results.get("filename")
    if not isinstance(filename, str):
        filename = None
    entries.extend(_detection_entries(
        results.get("detections"), filename, results.get("timestamp"), "image", {}, 0
    ))
    return entries


def _normalize_scene(results):
    category = results.get("scene") or results.get("category")
    if not isinstance(category, str) or not category.strip():
        return []
    filename = results.get("image") or results.get("filename")
    if not isinstance(filename, str):
        filename = None
    metadata = {}
    if isinstance(results.get("top_predictions"), list):
        metadata["top_predictions"] = results["top_predictions"]
    return [_make_evidence(
        "scene_classification", filename, results.get("timestamp"), "image",
        f"Scene category: {category.strip()}", results.get("confidence"), metadata, 0,
    )]


def _normalize_audio(results):
    filename = results.get("audio") or results.get("filename")
    if not isinstance(filename, str):
        filename = None
    language = results.get("language")
    segments = results.get("segments")
    if isinstance(segments, list) and segments:
        entries = []
        for index, segment in enumerate(segments):
            if not isinstance(segment, dict) or not isinstance(segment.get("text"), str):
                continue
            text = segment["text"].strip()
            if not text:
                continue
            timestamp = segment.get("start", segment.get("timestamp"))
            metadata = {"language": language} if language else {}
            if segment.get("end") is not None:
                metadata["end_timestamp"] = _normalize_timestamp(segment["end"])
            entries.append(_make_evidence(
                "transcription", filename, timestamp, "audio", text,
                segment.get("confidence"), metadata, index,
            ))
        if entries:
            return entries

    transcription = results.get("transcription") or results.get("text")
    if not isinstance(transcription, str) or not transcription.strip():
        return []
    metadata = {"language": language} if language else {}
    return [_make_evidence(
        "transcription", filename, results.get("timestamp"), "audio",
        transcription.strip(), results.get("confidence"), metadata, 0,
    )]


def _normalize_video(results):
    filename = results.get("filename") or results.get("video")
    if not isinstance(filename, str):
        filename = None
    frames = results.get("sampled_frames")
    if not isinstance(frames, list):
        frames = results.get("frames")
    if not isinstance(frames, list):
        return []

    entries = []
    for frame_index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            continue
        frame_number = frame.get("frame_number", frame_index)
        timestamp = frame.get("timestamp_seconds", frame.get("timestamp"))
        frame_info = frame.get("frame_info", {})
        if not isinstance(frame_info, dict):
            frame_info = {}
        try:
            display_frame_number = int(frame_number)
        except (TypeError, ValueError):
            display_frame_number = frame_index
        entries.append(_make_evidence(
            "video_frame", filename, timestamp, "video",
            f"Sampled video frame {display_frame_number}", None,
            {"frame_number": display_frame_number, "frame_info": frame_info},
            frame_index * 10000,
        ))
        frame_metadata = {"frame_number": display_frame_number, "frame_info": frame_info}
        entries.extend(_detection_entries(
            frame.get("detections"), filename, timestamp, "video",
            frame_metadata, frame_index * 10000 + 1,
        ))
    return entries


def fuse_analysis_results(payload):
    """Normalize partial multimodal results and produce a stable timeline."""
    if not isinstance(payload, dict) or not payload:
        raise ValueError("Request must contain a non-empty JSON object of analysis results.")

    modality_results = _get_modality_results(payload)
    if not modality_results:
        raise ValueError("No supported image, scene, audio, or video analysis results were provided.")
    normalizers = {
        "image": _normalize_image,
        "scene": _normalize_scene,
        "audio": _normalize_audio,
        "video": _normalize_video,
    }
    evidence = []
    for modality in ("image", "scene", "audio", "video"):
        if modality in modality_results:
            evidence.extend(normalizers[modality](modality_results[modality]))

    timeline = sorted(
        evidence,
        key=lambda entry: (
            _timestamp_sort_key(entry["timestamp"]),
            entry["modality"],
            entry["source_filename"] or "",
            entry["evidence_id"],
        ),
    )
    counts = {}
    for item in evidence:
        counts[item["modality"]] = counts.get(item["modality"], 0) + 1

    return {
        "normalized_evidence": evidence,
        "forensic_timeline": timeline,
        "summary": {
            "evidence_count": len(evidence),
            "timestamped_count": sum(item["timestamp"] is not None for item in evidence),
            "modality_counts": {key: counts[key] for key in sorted(counts)},
            "object_detection_count": sum(
                item["evidence_type"] == "object_detection" for item in evidence
            ),
        },
    }
