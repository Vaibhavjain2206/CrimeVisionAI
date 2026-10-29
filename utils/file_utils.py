"""Helpers for validating and safely storing uploaded evidence files."""

from pathlib import Path
from uuid import uuid4

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp",
    ".mp4", ".avi", ".mov", ".mkv",
    ".mp3", ".wav", ".m4a", ".aac",
    ".pdf",
}
FILE_TYPES = {
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image",
    ".mp4": "video", ".avi": "video", ".mov": "video", ".mkv": "video",
    ".mp3": "audio", ".wav": "audio", ".m4a": "audio", ".aac": "audio",
    ".pdf": "document",
}
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MiB per evidence file.


class UploadValidationError(ValueError):
    """Validation error with a stable HTTP status code for the upload API."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def get_extension(filename):
    """Return the lowercase extension from an untrusted client filename."""
    return Path(filename or "").suffix.lower()


def detect_file_type(filename):
    """Classify an evidence file by its supported extension."""
    return FILE_TYPES.get(get_extension(filename))


def generate_safe_filename(filename):
    """Generate an unpredictable disk name while retaining a safe extension."""
    extension = get_extension(filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise UploadValidationError("Unsupported file extension.", 415)
    # secure_filename is applied for extension normalization; the original stem
    # is intentionally not used as the stored name.
    safe_extension = Path(secure_filename("evidence" + extension)).suffix.lower()
    return f"{uuid4().hex}{safe_extension}"


def validate_upload(file_storage, max_size=MAX_UPLOAD_SIZE):
    """Validate a multipart file and return its extension, type, and byte size."""
    if file_storage is None or not isinstance(file_storage, FileStorage):
        raise UploadValidationError("A file is required.", 400)
    original_filename = file_storage.filename or ""
    if not original_filename.strip():
        raise UploadValidationError("A filename is required.", 400)

    extension = get_extension(original_filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise UploadValidationError("Unsupported file extension.", 415)

    stream = file_storage.stream
    size = 0
    while True:
        chunk = stream.read(min(1024 * 1024, max_size + 1 - size))
        if not chunk:
            break
        size += len(chunk)
        if size > max_size:
            stream.seek(0)
            raise UploadValidationError("File exceeds the 100 MiB upload limit.", 413)
    stream.seek(0)
    if size == 0:
        raise UploadValidationError("Uploaded file is empty.", 400)

    return {
        "extension": extension,
        "file_type": detect_file_type(original_filename),
        "size": size,
    }
