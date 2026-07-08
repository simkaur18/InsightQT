import re
from urllib.parse import parse_qs, urlparse

from app.exceptions import InvalidURLError
from app.models import SourcePlatform

_PLAY_STORE_HOSTS = {"play.google.com"}
_APP_ID_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$")


def detect_platform(url: str) -> SourcePlatform:
    """Detect which app store a URL belongs to. Raises InvalidURLError if unsupported."""
    if not url or not url.strip():
        raise InvalidURLError("Please paste a Google Play Store URL.")

    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()

    if host in _PLAY_STORE_HOSTS or host.endswith(".google.com"):
        return SourcePlatform.GOOGLE_PLAY

    if host in {"apps.apple.com"} or host.endswith(".apple.com"):
        raise InvalidURLError(
            "Apple App Store URLs aren't supported yet — InsightQT currently supports "
            "Google Play Store only. Please paste a Google Play Store URL."
        )

    raise InvalidURLError(
        "That doesn't look like a valid Google Play Store URL. "
        "Expected something like https://play.google.com/store/apps/details?id=com.example.app"
    )


def extract_google_play_app_id(url: str) -> str:
    """Extract the app_id (package name) from a Google Play Store URL."""
    parsed = urlparse(url.strip())
    query = parse_qs(parsed.query)
    app_id_values = query.get("id")

    if not app_id_values or not app_id_values[0]:
        raise InvalidURLError(
            "Couldn't find an app ID in that URL. "
            "Expected a link like https://play.google.com/store/apps/details?id=com.example.app"
        )

    app_id = app_id_values[0].strip()
    if not _APP_ID_PATTERN.match(app_id):
        raise InvalidURLError(f"'{app_id}' doesn't look like a valid Google Play app ID.")

    return app_id


def validate_and_extract_app_id(url: str) -> tuple[SourcePlatform, str]:
    """Validate a pasted URL end-to-end and return (platform, app_id)."""
    platform = detect_platform(url)
    if platform == SourcePlatform.GOOGLE_PLAY:
        app_id = extract_google_play_app_id(url)
        return platform, app_id
    raise InvalidURLError("Unsupported platform.")
