#!/usr/bin/env python3
"""Standalone YouTube Music downloader.

Downloads all playlists of a YouTube profile (plus Liked Music when logged in)
as audio files into your Music folder. No setup needed — just run:

    python download_my_music.py

Optionally pass a different video/playlist/profile URL:

    python download_my_music.py "https://music.youtube.com/playlist?list=..."
"""

import os
import subprocess
import sys

PROFILE_PLAYLISTS_URL = "https://www.youtube.com/@johnmc4699/playlists"
LIKED_MUSIC_URL = "https://music.youtube.com/playlist?list=LM"
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Music", "YouTube Music")
BROWSERS = ["chrome", "edge", "firefox", "brave", "safari", "opera", "vivaldi"]


def ensure_yt_dlp():
    """Import yt-dlp, installing it first if it is missing."""
    try:
        import yt_dlp
    except ImportError:
        print("First run: installing the yt-dlp downloader (one-time setup)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "--quiet", "yt-dlp"])
        import yt_dlp
    return yt_dlp


def count_files(directory):
    """Count files in a directory tree."""
    return sum(len(files) for _, _, files in os.walk(directory)) if os.path.isdir(directory) else 0


def find_logged_in_browser(yt_dlp):
    """Return the first browser whose YouTube cookies can be read, or None."""
    from yt_dlp.cookies import extract_cookies_from_browser

    for browser in BROWSERS:
        try:
            extract_cookies_from_browser(browser)
            print(f"Using your {browser.title()} login for private playlists.")
            return browser
        except Exception:
            continue
    print("No browser login found - private playlists (like Liked Music) will be skipped.")
    print("Tip: close your browser completely and run this again to include them.")
    return None


def download(yt_dlp, url, browser):
    """Download a URL as audio files, one subfolder per playlist. Returns True on success."""
    options = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(OUTPUT_DIR, "%(playlist_title,channel,id)s", "%(title)s [%(id)s].%(ext)s"),
        "ignoreerrors": True,
        "noplaylist": False,
    }
    if browser:
        options["cookiesfrombrowser"] = (browser, None, None, None)
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
        return True
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"\nProblem downloading {url}:\n  {e}\n")
        return False


def main():
    yt_dlp = ensure_yt_dlp()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    files_before = count_files(OUTPUT_DIR)

    browser = find_logged_in_browser(yt_dlp)

    if len(sys.argv) > 1:
        urls = sys.argv[1:]
    else:
        urls = [PROFILE_PLAYLISTS_URL] + ([LIKED_MUSIC_URL] if browser else [])

    print(f"Saving music to: {OUTPUT_DIR}\n")
    for url in urls:
        print(f"=== Downloading {url} ===")
        download(yt_dlp, url, browser)

    new_files = count_files(OUTPUT_DIR) - files_before
    print(f"\nDone! {new_files} new file(s) saved in: {OUTPUT_DIR}")
    if new_files == 0:
        print("Nothing new was downloaded. If your playlists are private, close your browser and run this again,")
        print("or make the playlists public/unlisted in YouTube Music and retry.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped. Files downloaded so far are kept in:", OUTPUT_DIR)
