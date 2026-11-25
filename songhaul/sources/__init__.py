"""The platforms a link can come from. A link of none of them goes to yt-dlp as it is."""

import re

from .base import Source
from .youtube import YouTube

SOURCES = (YouTube(),)
OTHER = Source()


def source_for(url: str) -> Source:
    return next((s for s in SOURCES if s.matches(url)), OTHER)


def is_known(url: str) -> bool:
    return source_for(url) is not OTHER


def link_in(text: str | None) -> str | None:
    """The first known link in shared text: some apps share "Title https://…" rather than just the link."""
    return next(filter(is_known, re.findall(r"https://[^\s/]+/\S+", text or "")), None)
