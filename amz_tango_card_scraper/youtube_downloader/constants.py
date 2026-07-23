"""Module containing constants for the YouTube downloader."""

YOUTUBE_URL_PATTERN = (
    r"^(https?://)?(www\.|m\.|music\.)?(youtube\.com/(watch\?v=|shorts/|live/|embed/)|youtu\.be/)[\w-]{11}"
)
"""Regular expression that matches YouTube video, shorts, live and youtu.be share URLs."""

YOUTUBE_PLAYLIST_URL_PATTERN = (
    r"^(https?://)?(www\.|m\.|music\.)?(youtube\.com/playlist\?list=[\w-]+"
    r"|(youtube\.com/watch\?|youtu\.be/[\w-]{11}\?)[^#]*[?&]?list=[\w-]+)"
)
"""Regular expression that matches YouTube playlist URLs and video URLs that carry a playlist parameter."""

OUTPUT_TEMPLATE = "%(title)s [%(id)s].%(ext)s"
"""Output file name template used by yt-dlp."""

VIDEO_FORMAT = "bestvideo*+bestaudio/best"
"""Format selector for video downloads (best video and audio merged, falling back to best single file)."""

AUDIO_FORMAT = "bestaudio/best"
"""Format selector for audio-only downloads."""
