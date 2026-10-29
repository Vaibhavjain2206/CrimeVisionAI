"""Lazy RT-DETR image object detection service."""

import os
from functools import lru_cache
from pathlib import Path

DEFAULT_MODEL_ID = "PekingU/rtdetr_r50vd"
DEFAULT_CONFIDENCE_THRESHOLD = 0.5


def get_confidence_threshold(value=None):
    """Read and validate a confidence threshold in the inclusive range [0, 1]."""
    if value is None:
        value = os.getenv("RTDETR_CONFIDENCE_THRESHOLD", DEFAULT_CONFIDENCE_THRESHOLD)
    try:
        threshold = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("RT-DETR confidence threshold must be a number from 0 to 1.") from error
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("RT-DETR confidence threshold must be between 0 and 1.")
    return threshold


@lru_cache(maxsize=1)
def _load_model(model_id):
    """Import and load Transformers components only when inference is requested."""
    from transformers import RTDetrForObjectDetection, RTDetrImageProcessor

    processor = RTDetrImageProcessor.from_pretrained(model_id)
    model = RTDetrForObjectDetection.from_pretrained(model_id)
    model.eval()
    return processor, model


def detect_objects(image_path, confidence_threshold=None):
    """Run RT-DETR on an image path and return labels, scores, and pixel boxes."""
    from PIL import Image, UnidentifiedImageError

    threshold = get_confidence_threshold(confidence_threshold)
    model_id = os.getenv("RTDETR_MODEL_ID", DEFAULT_MODEL_ID)

    try:
        with Image.open(Path(image_path)) as source_image:
            image = source_image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValueError("The uploaded file is not a valid image.") from error

    processor, model = _load_model(model_id)
    inputs = processor(images=image, return_tensors="pt")
    outputs = model(**inputs)
    results = processor.post_process_object_detection(
        outputs,
        threshold=threshold,
        target_sizes=[(image.height, image.width)],
    )[0]

    detections = []
    for score, label_id, box in zip(results["scores"], results["labels"], results["boxes"]):
        label_index = int(label_id.item())
        label = model.config.id2label.get(label_index, str(label_index))
        coordinates = box.tolist()
        detections.append({
            "label": label,
            "confidence": float(score.item()),
            "bbox": {
                "x1": round(float(coordinates[0]), 2),
                "y1": round(float(coordinates[1]), 2),
                "x2": round(float(coordinates[2]), 2),
                "y2": round(float(coordinates[3]), 2),
            },
        })
    return detections
