import re

from yt_dlp.utils import ExtractorError

from .base import Source, UnsupportedLink, parse

SHORT_HOST = "on.soundcloud.com"
# Second words of /<user>/<word> that are pages of the profile, and first words that aren't users.
PAGES = {"albums", "comments", "followers", "following", "likes", "popular-tracks", "reposts", "sets", "spotlight",
         "toptracks", "tracks"}
NOT_USERS = {"charts", "discover", "feed", "library", "messages", "notifications", "pages", "people", "search",
             "settings", "stations", "stream", "tags", "upload", "you"}


class SoundCloud(Source):
    name = "SoundCloud"
    platform = "soundcloud"
    hosts = frozenset({"soundcloud.com", "www.soundcloud.com", "m.soundcloud.com", SHORT_HOST})
    reasons = (("preview", ("only a preview",)),)
    cookie_domain = "soundcloud.com"

    def normalize(self, url: str) -> str:
        """Drops what sharing adds (?si=, ?utm_…, ?in=<set>); keeps the s-… token of private tracks and sets."""
        if parse(url).hostname == SHORT_HOST:
            return url
        parts = self._parts(url)
        if not (self.is_playlist(url) or self._is_track(parts)):
            raise UnsupportedLink
        return "https://soundcloud.com/" + "/".join(parts)

    def resolve(self, ydl, url: str) -> str:
        if parse(url).hostname == SHORT_HOST:
            url = ydl.urlopen(url).url
            if parse(url).hostname not in self.hosts - {SHORT_HOST}:
                raise UnsupportedLink
        return self.normalize(url)

    def is_playlist(self, url: str) -> bool:
        parts = self._parts(url)
        return len(parts) == 3 + self._has_token(parts) and parts[1] == "sets"

    def extract(self, ydl, url: str) -> dict:
        """yt-dlp lists a set without titles and durations, and doesn't say which tracks it won't be able to download."""
        info = super().extract(ydl, url)
        tracks = [e for e in info.get("entries", [info]) if e]
        try:
            known = self._tracks(ydl, [e["id"] for e in tracks], self._secret(url, info))
        except Exception:  # _call_api is internal to yt-dlp: without it the list has ids instead of titles
            return info
        for e in tracks:
            if t := known.get(e["id"]):
                e["title"] = t.get("title") or e.get("title")
                e["duration"] = (t.get("full_duration") or t.get("duration") or 0) / 1000 or e.get("duration")
                e["problem"] = problem(t)
        return info

    def prepare(self, info: dict) -> None:
        formats = info.get("formats") or []
        whole = [f for f in formats if not f["format_id"].endswith("_preview")]
        if formats and not whole:  # it would be saved, and remembered, as if it were the song
            raise ExtractorError("only a preview of the song is available", expected=True, ie="soundcloud",
                                 video_id=info["id"])
        if len(whole) < len(formats):
            info["formats"] = whole

    def track_id_in(self, message: str) -> str | None:
        match = re.search(r"\[soundcloud\] (\d+):", message)
        return match.group(1) if match else None

    @staticmethod
    def _parts(url: str) -> list[str]:
        return [p for p in parse(url).path.split("/") if p]

    @staticmethod
    def _has_token(parts: list[str]) -> bool:
        return len(parts) > 2 and parts[-1].startswith("s-") and len(parts) == (4 if parts[1] == "sets" else 3)

    def _is_track(self, parts: list[str]) -> bool:
        return len(parts) == 2 + self._has_token(parts) and parts[0] not in NOT_USERS and parts[1] not in PAGES

    def _secret(self, url: str, info: dict) -> dict:
        parts = self._parts(url)
        private_set = self._has_token(parts) and parts[1] == "sets"
        return {"playlistId": info["id"], "playlistSecretToken": parts[-1]} if private_set else {}

    @staticmethod
    def _tracks(ydl, ids: list[str], secret: dict) -> dict:
        """What SoundCloud says about these tracks, by id. One request every 50."""
        ie = ydl.get_info_extractor("Soundcloud")
        ie.initialize()
        found = {}
        for i in range(0, len(ids), 50):
            for t in ie._call_api(ie._API_V2_BASE + "tracks", None, query={"ids": ",".join(ids[i:i + 50]), **secret},
                                  headers=ie._HEADERS):
                found[str(t["id"])] = t
        return found


def problem(track: dict) -> str | None:
    """Why yt-dlp won't download this track, if that's known beforehand."""
    if track.get("policy") == "BLOCK":
        return "region"
    if track.get("downloadable") and track.get("has_downloads_left"):
        return None  # the original file may be there even if the streams aren't
    streams = (track.get("media") or {}).get("transcodings") or []
    plain = [s for s in streams if not s["format"]["protocol"].startswith(("ctr-", "cbc-"))]
    if streams and not plain:
        return "drm"
    if plain and all(s.get("snipped") or "/preview/" in s["url"] for s in plain):
        return "preview"
    return None
