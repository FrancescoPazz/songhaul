"""The platforms a link can come from. A link of none of them goes to yt-dlp as it is."""

import re

from .base import Source
from .soundcloud import SoundCloud
from .youtube import YouTube

SOURCES = (YouTube(), SoundCloud())
OTHER = Source()


def source_for(url: str) -> Source:
    return next((s for s in SOURCES if s.matches(url)), OTHER)


def source_of(info: dict) -> Source:
    """The platform of a track, from yt-dlp's info: a link of one site can lead to another."""
    platform = (info.get("extractor") or "").split(":")[0]
    return next((s for s in SOURCES if s.platform == platform), OTHER)


def is_known(url: str) -> bool:
    return source_for(url) is not OTHER


def link_in(text: str | None) -> str | None:
    """The first known link in shared text: some apps share "Title https://…" rather than just the link."""
    return next(filter(is_known, re.findall(r"https://[^\s/]+/\S+", text or "")), None)


def has_cookies(text: str) -> bool:
    """Whether a cookies.txt has anything for these platforms. yt-dlp reads only the Netscape format: comment lines
    and tab-separated fields."""
    return "\t" in text and any(s.cookie_domain in text for s in SOURCES)
