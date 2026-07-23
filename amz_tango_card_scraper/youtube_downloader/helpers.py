"""Module containing helper functions for the YouTube downloader."""

import re

from .constants import YOUTUBE_CHANNEL_URL_PATTERN, YOUTUBE_PLAYLIST_URL_PATTERN, YOUTUBE_URL_PATTERN


def is_valid_youtube_url(url: str) -> bool:
    """
    Check whether the given URL points to a YouTube video.

    Args:
        url: URL to check.

    Returns:
        True if the URL is a valid YouTube video URL, False otherwise.
    """
    return re.match(YOUTUBE_URL_PATTERN, url.strip()) is not None


def is_youtube_playlist_url(url: str) -> bool:
    """
    Check whether the given URL points to a YouTube playlist or carries a playlist parameter.

    Args:
        url: URL to check.

    Returns:
        True if the URL is a YouTube playlist URL, False otherwise.
    """
    return re.match(YOUTUBE_PLAYLIST_URL_PATTERN, url.strip()) is not None


def is_youtube_channel_url(url: str) -> bool:
    """
    Check whether the given URL points to a YouTube channel or profile.

    Args:
        url: URL to check.

    Returns:
        True if the URL is a YouTube channel/profile URL, False otherwise.
    """
    return re.match(YOUTUBE_CHANNEL_URL_PATTERN, url.strip()) is not None


def to_channel_playlists_url(url: str) -> str:
    """
    Normalize a YouTube channel/profile URL to its playlists tab on www.youtube.com.

    Args:
        url: YouTube channel/profile URL.

    Returns:
        URL of the channel's playlists tab (e.g. https://www.youtube.com/@handle/playlists).

    Raises:
        ValueError: If the URL is not a YouTube channel/profile URL.
    """
    match = re.match(YOUTUBE_CHANNEL_URL_PATTERN, url.strip())
    if match is None:
        raise ValueError(f"Not a YouTube channel URL: {url}")
    return f"https://www.youtube.com/{match.group(3)}/playlists"
