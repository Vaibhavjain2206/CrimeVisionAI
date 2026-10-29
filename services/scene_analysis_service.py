"""CLIP-based scene classification for uploaded image evidence."""

from functools import lru_cache
from pathlib import Path

SCENE_CATEGORIES = (
    "residential interior",
    "street or roadway",
    "commercial interior",
    "office workspace",
    "parking area",
    "wooded outdoor area",
    "public park",
    "warehouse or industrial area",
    "shop or retail area",
    "vehicle interior",
    "waterfront or beach",
    "construction site",
)
DEFAULT_MODEL_ID = "openai/clip-vit-base-patch32"


@lru_cache(maxsize=1)
def _load_clip_model(model_id):
    """Load CLIP only on the first classification request."""
    from transformers import CLIPModel, CLIPProcessor

    processor = CLIPProcessor.from_pretrained(model_id)
    model = CLIPModel.from_pretrained(model_id)
    model.eval()
    return processor, model


def classify_scene(image_path, top_k=5):
    """Rank candidate scene categories for an image using CLIP similarity."""
    import os

    from PIL import Image, UnidentifiedImageError

    model_id = os.getenv("CLIP_MODEL_ID", DEFAULT_MODEL_ID)
    try:
        with Image.open(Path(image_path)) as source_image:
            image = source_image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValueError("The uploaded file is not a valid image.") from error

    processor, model = _load_clip_model(model_id)
    prompts = [f"a photograph of a {category}" for category in SCENE_CATEGORIES]
    inputs = processor(text=prompts, images=image, return_tensors="pt", padding=True)
    outputs = model(**inputs)
    probabilities = outputs.logits_per_image[0].softmax(dim=0)

    count = min(max(int(top_k), 1), len(SCENE_CATEGORIES))
    scores, indices = probabilities.topk(count)
    predictions = [
        {"category": SCENE_CATEGORIES[int(index.item())], "confidence": float(score.item())}
        for score, index in zip(scores, indices)
    ]
    return {
        "category": predictions[0]["category"],
        "confidence": predictions[0]["confidence"],
        "top_predictions": predictions,
    }
