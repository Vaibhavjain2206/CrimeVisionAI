"""OpenAI Whisper transcription service for uploaded audio evidence."""

import os
from functools import lru_cache
from pathlib import Path

DEFAULT_WHISPER_MODEL = "base"


@lru_cache(maxsize=4)
def _load_whisper_model(model_name):
    """Load a Whisper model only when the first transcription is requested."""
    import whisper

    return whisper.load_model(model_name)


def transcribe_audio(audio_path):
    """Transcribe an audio file and return text plus detected language."""
    model_name = os.getenv("WHISPER_MODEL", DEFAULT_WHISPER_MODEL)
    model = _load_whisper_model(model_name)

    try:
        result = model.transcribe(str(Path(audio_path)), fp16=False)
    except Exception as error:
        raise RuntimeError("Whisper could not transcribe this audio file.") from error

    return {
        "text": (result.get("text") or "").strip(),
        "language": result.get("language"),
    }
