"""Command line entry point for the YouTube downloader."""

import argparse
import sys

from .youtube_downloader import download_from_youtube


def main() -> None:
    """Parse command line arguments and download the requested YouTube video or playlist."""
    parser = argparse.ArgumentParser(description="Download a YouTube video, playlist or their audio tracks.")
    parser.add_argument("url", help="URL of the YouTube video or playlist to download")
    parser.add_argument("-o", "--output-dir", default=".", help="directory to store the downloaded files (default: .)")
    parser.add_argument("-a", "--audio-only", action="store_true", help="download only the audio tracks")
    parser.add_argument(
        "-c",
        "--cookies-from-browser",
        metavar="BROWSER[:PROFILE]",
        help="read YouTube cookies from this browser (chrome, firefox, edge, ...) to access private playlists",
    )
    args = parser.parse_args()

    try:
        file_paths = download_from_youtube(
            args.url,
            output_dir=args.output_dir,
            audio_only=args.audio_only,
            cookies_from_browser=args.cookies_from_browser,
        )
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        sys.exit(1)

    for file_path in file_paths:
        print(file_path)


if __name__ == "__main__":
    main()
