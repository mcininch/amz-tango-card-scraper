"""Module containing constants for the YouTube downloader."""

YOUTUBE_URL_PATTERN = (
    r"^(https?://)?(www\.|m\.|music\.)?(youtube\.com/(watch\?v=|shorts/|live/|embed/)|youtu\.be/)[\w-]{11}"
)
"""Regular expression that matches YouTube video, shorts, live and youtu.be share URLs."""

OUTPUT_TEMPLATE = "%(title)s [%(id)s].%(ext)s"
"""Output file name template used by yt-dlp."""

VIDEO_FORMAT = "bestvideo*+bestaudio/best"
"""Format selector for video downloads (best video and audio merged, falling back to best single file)."""

AUDIO_FORMAT = "bestaudio/best"
"""Format selector for audio-only downloads."""
