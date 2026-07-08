import pytest

from app.exceptions import InvalidURLError
from app.models import SourcePlatform
from app.utils.validators import (
    detect_platform,
    extract_google_play_app_id,
    validate_and_extract_app_id,
)


def test_detect_platform_google_play():
    url = "https://play.google.com/store/apps/details?id=com.example.app"
    assert detect_platform(url) == SourcePlatform.GOOGLE_PLAY


def test_detect_platform_apple_raises_unsupported():
    url = "https://apps.apple.com/us/app/example-app/id123456789"
    with pytest.raises(InvalidURLError, match="Apple App Store"):
        detect_platform(url)


def test_detect_platform_empty_url_raises():
    with pytest.raises(InvalidURLError):
        detect_platform("")


def test_detect_platform_unsupported_host_raises():
    with pytest.raises(InvalidURLError):
        detect_platform("https://example.com/not-a-store")


def test_extract_google_play_app_id_valid():
    url = "https://play.google.com/store/apps/details?id=com.example.app&hl=en"
    assert extract_google_play_app_id(url) == "com.example.app"


def test_extract_google_play_app_id_missing_id_raises():
    url = "https://play.google.com/store/apps/details"
    with pytest.raises(InvalidURLError):
        extract_google_play_app_id(url)


def test_extract_google_play_app_id_malformed_id_raises():
    url = "https://play.google.com/store/apps/details?id=not_a_valid_id"
    with pytest.raises(InvalidURLError):
        extract_google_play_app_id(url)


def test_validate_and_extract_app_id_end_to_end():
    url = "https://play.google.com/store/apps/details?id=com.spotify.music"
    platform, app_id = validate_and_extract_app_id(url)
    assert platform == SourcePlatform.GOOGLE_PLAY
    assert app_id == "com.spotify.music"
