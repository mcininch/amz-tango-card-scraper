"""Module containing the YouTube downloader."""

import os
from typing import Any, Dict

import yt_dlp

from ..utils.logger import setup_logger
from .constants import AUDIO_FORMAT, OUTPUT_TEMPLATE, VIDEO_FORMAT
from .helpers import is_valid_youtube_url

logger = setup_logger(__name__)


def download_from_youtube(url: str, output_dir: str = ".", audio_only: bool = False) -> str:
    """
    Download a YouTube video (or its audio track) to the given directory.

    Args:
        url: URL of the YouTube video to download.
        output_dir: Directory where the downloaded file will be stored. Created if it does not exist.
        audio_only: Whether to download only the audio track instead of the full video.

    Returns:
        Path to the downloaded file.

    Raises:
        ValueError: If the URL is not a valid YouTube video URL.
        yt_dlp.utils.DownloadError: If the download fails.
    """
    if not is_valid_youtube_url(url):
        raise ValueError(f"Invalid YouTube URL: {url}")

    os.makedirs(output_dir, exist_ok=True)

    ydl_opts: Dict[str, Any] = {
        "format": AUDIO_FORMAT if audio_only else VIDEO_FORMAT,
        "outtmpl": os.path.join(output_dir, OUTPUT_TEMPLATE),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    logger.info("Downloading %s from %s...", "audio" if audio_only else "video", url)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
    logger.info("Downloaded %s to %s", url, file_path)

    return file_path
