"""Module for testing the YouTube downloader module."""

from amz_tango_card_scraper.youtube_downloader.helpers import is_valid_youtube_url


def test_is_valid_youtube_url():
    # Test case 1: valid YouTube URLs
    valid_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "http://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "www.youtube.com/watch?v=dQw4w9WgXcQ",
    ]
    for url in valid_urls:
        assert is_valid_youtube_url(url), url

    # Test case 2: invalid URLs
    invalid_urls = [
        "",
        "not a url",
        "https://www.google.com",
        "https://www.youtube.com/watch?v=short",
        "https://vimeo.com/123456789",
        "https://www.youtube.com/",
    ]
    for url in invalid_urls:
        assert not is_valid_youtube_url(url), url
