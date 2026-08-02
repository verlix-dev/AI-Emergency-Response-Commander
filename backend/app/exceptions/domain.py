class ApplicationError(Exception):
    """Base application exception safely exposed through the API."""
    status_code = 400
    code = "application_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(ApplicationError):
    status_code = 404
    code = "not_found"


class LLMProviderNotConfiguredError(ApplicationError):
    """Raised when an unavailable LLM provider is requested."""

    status_code = 503
    code = "llm_provider_not_configured"


class DetectorNotAvailableError(ApplicationError):
    """Raised when the configured detector backend cannot be loaded."""

    status_code = 503
    code = "detector_not_available"


class ImageNotReadableError(ApplicationError):
    """Raised when a submitted image cannot be read or decoded."""

    status_code = 400
    code = "image_not_readable"
