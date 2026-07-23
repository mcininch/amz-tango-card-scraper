"""Module containing the YouTube downloader."""

import os
from typing import Any, Dict, List, Optional

import yt_dlp

from ..utils.logger import setup_logger
from .constants import AUDIO_FORMAT, OUTPUT_TEMPLATE, VIDEO_FORMAT
from .helpers import is_valid_youtube_url, is_youtube_playlist_url

logger = setup_logger(__name__)


def download_from_youtube(
    url: str, output_dir: str = ".", audio_only: bool = False, cookies_from_browser: Optional[str] = None
) -> List[str]:
    """
    Download a YouTube video or playlist (or their audio tracks) to the given directory.

    Single video URLs download one file. Playlist URLs (or video URLs carrying a playlist
    parameter) download every entry in the playlist, skipping entries that fail so one broken
    video does not abort the rest.

    Args:
        url: URL of the YouTube video or playlist to download.
        output_dir: Directory where the downloaded files will be stored. Created if it does not exist.
        audio_only: Whether to download only the audio tracks instead of the full videos.
        cookies_from_browser: Browser to read YouTube cookies from ("chrome", "firefox", "edge", etc.),
            optionally with a profile as "BROWSER:PROFILE". Needed for private playlists such as Liked
            Music, which are only visible while logged in.

    Returns:
        Paths to the downloaded files.

    Raises:
        ValueError: If the URL is not a valid YouTube video or playlist URL.
        yt_dlp.utils.DownloadError: If the download fails.
    """
    is_playlist = is_youtube_playlist_url(url)
    if not is_playlist and not is_valid_youtube_url(url):
        raise ValueError(f"Invalid YouTube URL: {url}")

    os.makedirs(output_dir, exist_ok=True)

    ydl_opts: Dict[str, Any] = {
        "format": AUDIO_FORMAT if audio_only else VIDEO_FORMAT,
        "outtmpl": os.path.join(output_dir, OUTPUT_TEMPLATE),
        "noplaylist": not is_playlist,
        "ignoreerrors": is_playlist,
        "quiet": True,
        "no_warnings": True,
    }
    if cookies_from_browser:
        browser, _, profile = cookies_from_browser.partition(":")
        ydl_opts["cookiesfrombrowser"] = (browser, profile or None, None, None)

    target = "playlist" if is_playlist else "video"
    logger.info("Downloading %s%s from %s...", target, " (audio only)" if audio_only else "", url)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        entries = list(info["entries"]) if info and info.get("entries") is not None else None
        if entries is not None:
            file_paths = [ydl.prepare_filename(entry) for entry in entries if entry is not None]
            skipped = sum(1 for entry in entries if entry is None)
            if skipped:
                logger.warning("Skipped %d unavailable video(s) in the playlist", skipped)
        else:
            file_paths = [ydl.prepare_filename(info)]

    if not file_paths:
        raise yt_dlp.utils.DownloadError(f"No videos could be downloaded from {url}")

    logger.info("Downloaded %d file(s) from %s", len(file_paths), url)

    return file_paths
