"""Command line entry point for the YouTube downloader."""

import argparse
import sys

from .youtube_downloader import download_from_youtube


def main() -> None:
    """Parse command line arguments and download the requested YouTube video."""
    parser = argparse.ArgumentParser(description="Download a YouTube video or its audio track.")
    parser.add_argument("url", help="URL of the YouTube video to download")
    parser.add_argument("-o", "--output-dir", default=".", help="directory to store the downloaded file (default: .)")
    parser.add_argument("-a", "--audio-only", action="store_true", help="download only the audio track")
    args = parser.parse_args()

    try:
        file_path = download_from_youtube(args.url, output_dir=args.output_dir, audio_only=args.audio_only)
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(file_path)


if __name__ == "__main__":
    main()
