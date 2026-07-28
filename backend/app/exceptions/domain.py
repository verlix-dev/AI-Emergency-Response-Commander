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
