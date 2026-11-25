"""What a platform has to answer about its own links. The defaults fit any link yt-dlp handles by itself."""

from urllib.parse import urlparse


class UnsupportedLink(ValueError):
    """A page of a known platform that is neither a song nor a playlist, like a profile."""

    def __init__(self):
        super().__init__("this kind of link isn't supported")


class Source:
    name = "Playlist"  # shown when a playlist has no title
    platform = None  # yt-dlp's name for it: first word of an archive line, and of an extractor's name
    hosts = frozenset()
    reasons = ()  # (kind, phrases) found in this platform's errors, most specific first
    cookie_domain = None

    def matches(self, url: str) -> bool:
        """The host is compared whole: youtube.com.example.it is another site. Text around the link is a no."""
        if url.split() != [url]:
            return False
        try:
            return parse(url).hostname in self.hosts
        except ValueError:  # e.g. an unclosed [ in the host
            return False

    def normalize(self, url: str) -> str:
        """The plain form of a link, without using the network. Raises UnsupportedLink."""
        return url

    def resolve(self, ydl, url: str) -> str:
        """The plain form of a link, following it if it's a short one."""
        return self.normalize(url)

    def is_playlist(self, url: str) -> bool:
        return False

    def extract(self, ydl, url: str) -> dict:
        """yt-dlp's info of a resolved link, with the tracks' titles; "problem" is why a track can't be downloaded."""
        return ydl.extract_info(url, download=False)

    def prepare(self, info: dict) -> None:
        """Last look at a track before its format is chosen. An ExtractorError skips the track."""

    def track_id_in(self, message: str) -> str | None:
        """The track a yt-dlp error is about, if the message says it."""
        return None


def parse(url: str):
    return urlparse(url if "://" in url else f"https://{url}")
