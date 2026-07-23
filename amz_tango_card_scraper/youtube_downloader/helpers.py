"""Module containing helper functions for the YouTube downloader."""

import re

from .constants import YOUTUBE_URL_PATTERN


def is_valid_youtube_url(url: str) -> bool:
    """
    Check whether the given URL points to a YouTube video.

    Args:
        url: URL to check.

    Returns:
        True if the URL is a valid YouTube video URL, False otherwise.
    """
    return re.match(YOUTUBE_URL_PATTERN, url.strip()) is not None
