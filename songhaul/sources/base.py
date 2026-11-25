"""What a platform has to answer about its own links. The defaults fit any link yt-dlp handles by itself."""

from urllib.parse import urlparse


class Source:
    name = "Playlist"  # shown when a playlist has no title
    hosts = frozenset()
    reasons = ()  # (kind, phrases) found in this platform's errors, most specific first

    def matches(self, url: str) -> bool:
        """The host is compared whole: youtube.com.example.it is another site. Text around the link is a no."""
        if url.split() != [url]:
            return False
        try:
            return urlparse(url if "://" in url else f"https://{url}").hostname in self.hosts
        except ValueError:  # e.g. an unclosed [ in the host
            return False

    def normalize(self, url: str) -> str:
        return url

    def is_playlist(self, url: str) -> bool:
        return False

    def track_id_in(self, message: str) -> str | None:
        """The track a yt-dlp error is about, if the message says it."""
        return None
