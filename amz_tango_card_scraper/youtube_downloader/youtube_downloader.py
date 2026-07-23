"""Module containing the YouTube downloader."""

import os
from typing import Any, Dict, List, Optional

import yt_dlp

from ..utils.logger import setup_logger
from .constants import AUDIO_FORMAT, OUTPUT_TEMPLATE, VIDEO_FORMAT
from .helpers import is_valid_youtube_url, is_youtube_channel_url, is_youtube_playlist_url, to_channel_playlists_url

logger = setup_logger(__name__)


def _collect_file_paths(ydl: yt_dlp.YoutubeDL, info: Optional[Dict[str, Any]]) -> List[str]:
    """
    Recursively collect the file paths of all downloaded videos in an extraction result.

    Handles plain videos, playlists and nested collections such as a channel's playlists tab
    (a playlist of playlists). Unavailable entries (None) are skipped.

    Args:
        ydl: YoutubeDL instance used for the download.
        info: Extraction result to collect file paths from.

    Returns:
        Paths of the downloaded files.
    """
    if info is None:
        return []
    entries = info.get("entries")
    if entries is None:
        return [ydl.prepare_filename(info)]
    file_paths: List[str] = []
    for entry in list(entries):
        file_paths.extend(_collect_file_paths(ydl, entry))
    return file_paths


def download_from_youtube(
    url: str, output_dir: str = ".", audio_only: bool = False, cookies_from_browser: Optional[str] = None
) -> List[str]:
    """
    Download a YouTube video or playlist (or their audio tracks) to the given directory.

    Single video URLs download one file. Playlist URLs (or video URLs carrying a playlist
    parameter) download every entry in the playlist, skipping entries that fail so one broken
    video does not abort the rest. Channel/profile URLs (e.g. https://www.youtube.com/@handle)
    download every playlist of that channel.

    Args:
        url: URL of the YouTube video, playlist or channel to download.
        output_dir: Directory where the downloaded files will be stored. Created if it does not exist.
        audio_only: Whether to download only the audio tracks instead of the full videos.
        cookies_from_browser: Browser to read YouTube cookies from ("chrome", "firefox", "edge", etc.),
            optionally with a profile as "BROWSER:PROFILE". Needed for private playlists such as Liked
            Music, which are only visible while logged in.

    Returns:
        Paths to the downloaded files.

    Raises:
        ValueError: If the URL is not a valid YouTube video, playlist or channel URL.
        yt_dlp.utils.DownloadError: If the download fails.
    """
    is_channel = is_youtube_channel_url(url)
    if is_channel:
        url = to_channel_playlists_url(url)
    is_playlist = is_channel or is_youtube_playlist_url(url)
    if not is_playlist and not is_valid_youtube_url(url):
        raise ValueError(f"Invalid YouTube URL: {url}")

    os.makedirs(output_dir, exist_ok=True)

    if is_channel:
        output_template = os.path.join(output_dir, "%(playlist_title)s", OUTPUT_TEMPLATE)
    else:
        output_template = os.path.join(output_dir, OUTPUT_TEMPLATE)

    ydl_opts: Dict[str, Any] = {
        "format": AUDIO_FORMAT if audio_only else VIDEO_FORMAT,
        "outtmpl": output_template,
        "noplaylist": not is_playlist,
        "ignoreerrors": is_playlist,
        "quiet": True,
        "no_warnings": True,
    }
    if cookies_from_browser:
        browser, _, profile = cookies_from_browser.partition(":")
        ydl_opts["cookiesfrombrowser"] = (browser, profile or None, None, None)

    target = "all channel playlists" if is_channel else "playlist" if is_playlist else "video"
    logger.info("Downloading %s%s from %s...", target, " (audio only)" if audio_only else "", url)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_paths = _collect_file_paths(ydl, info)

    if not file_paths:
        raise yt_dlp.utils.DownloadError(f"No videos could be downloaded from {url}")

    logger.info("Downloaded %d file(s) from %s", len(file_paths), url)

    return file_paths
