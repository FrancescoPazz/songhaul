import re
from urllib.parse import parse_qs, urlparse

from .base import Source


def is_mix(playlist_id: str) -> bool:
    """YouTube's endless radio mixes (RD...), started from a song. RDCLAK/RDTMAK ones are real, finite playlists."""
    return playlist_id.startswith("RD") and not playlist_id.startswith(("RDCLAK", "RDTMAK"))


def link_from_route(route: str | None) -> str | None:
    """A link opened with the app on Android arrives as a route like "/playlist?list=..." or "/watch?v=...": the host
    is lost, but pyproject.toml declares only YouTube's links."""
    return f"https://www.youtube.com{route}" if route and ("list=" in route or "v=" in route) else None


class YouTube(Source):
    name = "YouTube"
    platform = "youtube"
    hosts = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"})
    cookie_domain = "youtube.com"
    upload_year = False  # an old song's video is often years younger than the song
    reasons = (
        ("age", ("confirm your age", "age-restricted", "inappropriate for some users")),
        ("bot", ("not a bot",)),
        ("private", ("private video",)),
        ("members", ("members-only", "join this channel", "premium")),
        ("region", ("in your country", "geo restrict")),
        ("unavailable", ("video unavailable", "video is unavailable", "has been removed", "is not available",
                         "account associated")),
    )

    def normalize(self, url: str) -> str:
        """A link with list= becomes the plain playlist link, a song the plain video link. A song playing inside a
        radio mix is the song: the mix never ends."""
        parsed = urlparse(url)
        if parsed.netloc not in self.hosts:
            return url
        query = parse_qs(parsed.query)
        playlist_id, video_id = query.get("list", [None])[0], query.get("v", [None])[0]
        if parsed.netloc == "youtu.be":
            video_id = parsed.path.strip("/")
        if playlist_id and not (video_id and is_mix(playlist_id)):
            return f"https://www.youtube.com/playlist?list={playlist_id}"
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
        return url

    def is_playlist(self, url: str) -> bool:
        return "list=" in self.normalize(url)

    def track_id_in(self, message: str) -> str | None:
        match = re.search(r"\[youtube\] ([\w-]{11}):", message)
        return match.group(1) if match else None
