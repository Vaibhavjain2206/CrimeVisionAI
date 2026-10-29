"""OpenCV frame sampling with optional RT-DETR detections per sampled frame."""

import os
import tempfile
from pathlib import Path

from services.object_detection_service import detect_objects

DEFAULT_SAMPLING_INTERVAL_SECONDS = 1.0


def _get_sampling_interval(value=None):
    if value is None:
        value = os.getenv(
            "VIDEO_FRAME_INTERVAL_SECONDS",
            str(DEFAULT_SAMPLING_INTERVAL_SECONDS),
        )
    try:
        interval = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Video sampling interval must be a positive number of seconds.") from error
    if interval <= 0:
        raise ValueError("Video sampling interval must be a positive number of seconds.")
    return interval


def analyze_video(video_path, sampling_interval_seconds=None, include_detections=True):
    """Extract frames at a fixed interval and analyze each sampled frame."""
    import cv2

    sampling_interval = _get_sampling_interval(sampling_interval_seconds)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        capture.release()
        raise ValueError("The uploaded file is not a readable video.")

    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
            raise ValueError("Video metadata is invalid or unavailable.")

        duration = frame_count / fps
        frame_step = max(1, int(round(sampling_interval * fps)))
        sampled_frames = []

        with tempfile.TemporaryDirectory(prefix="crimevision_frames_") as temp_directory:
            for frame_number in range(0, frame_count, frame_step):
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                success, frame = capture.read()
                if not success or frame is None:
                    continue

                frame_height, frame_width = frame.shape[:2]
                frame_result = {
                    "frame_number": frame_number,
                    "timestamp_seconds": round(frame_number / fps, 3),
                    "frame_info": {
                        "width": frame_width,
                        "height": frame_height,
                        "channels": int(frame.shape[2]) if len(frame.shape) > 2 else 1,
                    },
                }

                if include_detections:
                    frame_path = Path(temp_directory) / f"frame_{frame_number}.jpg"
                    if cv2.imwrite(str(frame_path), frame):
                        try:
                            frame_result["detections"] = detect_objects(frame_path)
                        except Exception:
                            # Keep the sampled timeline useful when detection is
                            # unavailable (for example, model weights are offline).
                            frame_result["detections"] = None
                            frame_result["detection_error"] = "Object detection was unavailable for this frame."
                    else:
                        frame_result["detections"] = None
                        frame_result["detection_error"] = "Could not prepare this frame for object detection."

                sampled_frames.append(frame_result)

        return {
            "metadata": {
                "fps": fps,
                "frame_count": frame_count,
                "duration_seconds": round(duration, 3),
                "width": width,
                "height": height,
                "sampling_interval_seconds": sampling_interval,
            },
            "sampled_frames": sampled_frames,
        }
    finally:
        capture.release()
