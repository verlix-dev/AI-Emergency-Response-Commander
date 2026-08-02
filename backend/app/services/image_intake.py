"""Staging of uploaded images onto disk for detector consumption.

Detectors read from a path rather than a stream, so an upload must be materialised before
analysis. This module owns that concern, along with validation and cleanup, keeping both the
route and the vision pipeline free of transport details.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import mkdtemp
from typing import BinaryIO

from app.exceptions import ImageNotReadableError

BYTES_PER_MEGABYTE = 1024 * 1024
CHUNK_SIZE = 64 * 1024

ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/jpg", "image/png", "image/bmp", "image/webp", "image/tiff"}
)

ALLOWED_SUFFIXES: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
)


class ImageIntakeService:
    """Validate an uploaded image and stage it on disk for the duration of a request."""

    def __init__(self, max_upload_size_mb: int) -> None:
        self._max_bytes = max(1, max_upload_size_mb) * BYTES_PER_MEGABYTE

    def validate(self, file_name: str | None, content_type: str | None) -> None:
        """Reject uploads whose declared type or extension is not a supported image."""
        if content_type is not None and content_type.lower() in ALLOWED_CONTENT_TYPES:
            return
        suffix = Path(file_name or "").suffix.lower()
        if suffix in ALLOWED_SUFFIXES:
            return
        raise ImageNotReadableError(
            "Unsupported image format. Provide a JPEG, PNG, BMP, WEBP, or TIFF image."
        )

    @contextmanager
    def staged(self, source: BinaryIO, file_name: str | None) -> Iterator[str]:
        """Yield a filesystem path holding the upload, removing it on exit.

        The stream is copied in chunks and aborted as soon as the size limit is exceeded, so an
        oversized upload is never fully buffered in memory or fully written to disk.
        """
        suffix = Path(file_name or "").suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            suffix = ".img"

        staged_path = Path(mkdtemp()) / f"upload{suffix}"
        try:
            self._copy_within_limit(source, staged_path)
            yield str(staged_path)
        finally:
            staged_path.unlink(missing_ok=True)
            staged_path.parent.rmdir()

    def _copy_within_limit(self, source: BinaryIO, destination: Path) -> None:
        """Copy the upload to disk, aborting as soon as the size limit is exceeded."""
        written = 0
        with destination.open("wb") as staged_file:
            while chunk := source.read(CHUNK_SIZE):
                written += len(chunk)
                if written > self._max_bytes:
                    raise ImageNotReadableError(
                        f"Image exceeds the maximum upload size of "
                        f"{self._max_bytes // BYTES_PER_MEGABYTE} MB."
                    )
                staged_file.write(chunk)
        if written == 0:
            raise ImageNotReadableError("The uploaded image is empty.")
