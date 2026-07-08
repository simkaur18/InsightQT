class InsightQTError(Exception):
    """Base class for all InsightQT-specific errors."""


class InvalidURLError(InsightQTError):
    """Raised when the pasted URL isn't a supported, well-formed app store URL."""


class AppNotFoundError(InsightQTError):
    """Raised when the app store has no app matching the extracted app ID."""


class ReviewRetrievalError(InsightQTError):
    """Raised when review retrieval fails after retries (network, rate limiting, etc.)."""


class MissingAPIKeyError(InsightQTError):
    """Raised when GROQ_API_KEY is not configured."""


class AIAnalysisError(InsightQTError):
    """Raised when AI analysis fails entirely (not just a partial batch failure)."""


class UserAlreadyExistsError(InsightQTError):
    """Raised when creating a user whose email is already registered."""


class InvalidCredentialsError(InsightQTError):
    """Raised when a login attempt's email/password doesn't match a stored user."""


class UserNotFoundError(InsightQTError):
    """Raised when an operation references a user email that isn't registered."""
