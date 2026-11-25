import json
import unittest
from pathlib import Path

from yt_dlp.utils import ExtractorError

from songhaul import core, sources
from songhaul.sources.base import UnsupportedLink
from songhaul.sources.soundcloud import SoundCloud

# Real answers of api-v2.soundcloud.com/tracks, reduced to the fields in use.
TRACKS = {str(t["id"]): t for t in
          json.loads((Path(__file__).parent / "fixtures/soundcloud_tracks.json").read_text(encoding="utf-8"))}
DRM, FREE, DOWNLOADABLE, PREVIEW = "75206121", "30510138", "47127625", "1055360503"
SET = "https://soundcloud.com/the-concept-band/sets/the-royal-concept-ep"


class FakeIE:
    _API_V2_BASE = "https://api/"
    _HEADERS = {}

    def __init__(self, fail=False):
        self.queries, self.fail = [], fail

    def initialize(self):
        pass

    def _call_api(self, url, video_id, query=None, **kwargs):
        if self.fail:
            raise ExtractorError("HTTP Error 429")
        self.queries.append(query)
        return [TRACKS[i] for i in reversed(query["ids"].split(",")) if i in TRACKS]  # SoundCloud's order isn't ours


class FakeYDL:
    def __init__(self, info=None, fail=False, redirect=None):
        self.info, self.ie, self.redirect = info, FakeIE(fail), redirect

    def extract_info(self, url, download):
        return self.info

    def get_info_extractor(self, key):
        return self.ie

    def urlopen(self, url):
        return type("Response", (), {"url": self.redirect})


def listing(ids, **kwargs):
    ydl = FakeYDL({"id": "7", "title": "Set", "entries": [{"id": i, "title": None} for i in ids]}, **kwargs)
    return SoundCloud().extract(ydl, kwargs.pop("url", SET))["entries"], ydl.ie.queries


class Links(unittest.TestCase):
    def test_normal_form(self):
        track = "https://soundcloud.com/leviryan/richard"
        for url in (track, track + "?si=1&utm_source=x", "https://m.soundcloud.com/leviryan/richard/",
                    "https://www.soundcloud.com/leviryan/richard?in=leviryan/sets/out-of-spite", "soundcloud.com/leviryan/richard"):
            self.assertEqual(core.normalize_url(url), track, url)
            self.assertFalse(core.is_playlist_url(url), url)
        self.assertEqual(core.normalize_url(SET + "/s-AbC?si=x"), SET + "/s-AbC")  # the secret link of a private set
        self.assertEqual(core.normalize_url(track + "/s-AbC"), track + "/s-AbC")
        self.assertTrue(core.is_playlist_url(SET + "?si=x"))

    def test_other_pages_are_refused(self):
        for path in ("leviryan", "leviryan/tracks", "leviryan/sets", "leviryan/likes", "leviryan/reposts", "discover",
                     "you/likes", "search?q=x", "", "leviryan/richard/comments", "stations/track/a/b"):
            url = "https://soundcloud.com/" + path
            with self.assertRaises(UnsupportedLink, msg=url) as e:
                core.normalize_url(url)
            self.assertEqual(core.reason_kind(str(e.exception)), "unsupported_link")
            self.assertFalse(core.is_playlist_url(url))  # History asks this for every row: it must not fail

    def test_similar_hosts_are_other_sites(self):
        for url in ("https://soundcloud.com.example.it/a/b", "https://notsoundcloud.com/a/b", "https://example.com/soundcloud.com/a"):
            self.assertIs(sources.source_for(url), sources.OTHER, url)

    def test_short_links_are_resolved(self):
        short = "https://on.soundcloud.com/abc"
        self.assertEqual(sources.link_in(f"Listen to X on #SoundCloud {short}"), short)
        ydl = FakeYDL(redirect=SET + "?utm_source=x")
        self.assertEqual(sources.source_for(short).resolve(ydl, short), SET)
        with self.assertRaises(UnsupportedLink):  # it can hide a whole profile
            sources.source_for(short).resolve(FakeYDL(redirect="https://soundcloud.com/leviryan?si=x"), short)
        with self.assertRaises(UnsupportedLink):
            sources.source_for(short).resolve(FakeYDL(redirect="https://example.com/a/b"), short)


class Listing(unittest.TestCase):
    def test_titles_durations_and_problems_in_one_request(self):
        entries, queries = listing([DRM, FREE, DOWNLOADABLE, PREVIEW, "1"])
        self.assertEqual(len(queries), 1)
        self.assertEqual([e.get("problem") for e in entries], ["drm", None, None, "preview", None])
        self.assertEqual(entries[1]["title"], "D-D-Dance")
        self.assertEqual(int(entries[3]["duration"]), 249)  # the song's length, not the preview's
        self.assertIsNone(entries[4]["title"])  # SoundCloud didn't return it: listed anyway

    def test_fifty_at_a_time(self):
        self.assertEqual([len(q["ids"].split(",")) for q in listing([str(i) for i in range(120)])[1]], [50, 50, 20])

    def test_private_sets_need_their_token(self):
        ydl = FakeYDL({"id": "7", "entries": [{"id": FREE}]})
        SoundCloud().extract(ydl, SET + "/s-AbC")
        self.assertEqual((ydl.ie.queries[0]["playlistId"], ydl.ie.queries[0]["playlistSecretToken"]), ("7", "s-AbC"))

    def test_without_the_request_the_list_still_works(self):
        self.assertEqual([e["id"] for e in listing([FREE], fail=True)[0]], [FREE])

    def test_single_track(self):
        info = SoundCloud().extract(FakeYDL({"id": PREVIEW, "title": "Makeba", "duration": 30}), "https://soundcloud.com/a/b")
        self.assertEqual((info["problem"], int(info["duration"])), ("preview", 249))


class Download(unittest.TestCase):
    def test_previews_are_dropped(self):
        info = {"id": "1", "formats": [{"format_id": "http_mp3_preview"}, {"format_id": "hls_aac_160k"}]}
        SoundCloud().prepare(info)
        self.assertEqual([f["format_id"] for f in info["formats"]], ["hls_aac_160k"])

    def test_a_track_with_previews_only_is_skipped_with_its_reason(self):
        with self.assertRaises(ExtractorError) as e:
            SoundCloud().prepare({"id": "123", "formats": [{"format_id": "http_mp3_preview"}]})
        message = str(e.exception)
        self.assertEqual((core.reason_kind(message), core.video_id_in(message)), ("preview", "123"))

    def test_reasons(self):
        for message, kind in {
            "[soundcloud] 75206121: This video is DRM protected; see  https://… ": "drm",
            "[soundcloud] 1: Requested format is not available. Use --list-formats": "format",
            "[soundcloud] 1: Unable to download JSON metadata: HTTP Error 429: Too Many Requests": "rate_limited",
            "[soundcloud] 1: This video is not available from your location due to geo restriction": "region",
            "[soundcloud] a/b: Unable to download JSON metadata: HTTP Error 404: Not Found": "not_found",
        }.items():
            self.assertEqual(core.reason_kind(message), kind, message)

    def test_same_id_on_two_platforms(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "archive.txt"
            archive.write_text("youtube 123\nsoundcloud 456\n", encoding="utf-8")
            self.assertEqual(core.archived_ids(archive, "soundcloud"), {"456"})
            self.assertEqual(core.archived_ids(archive, "youtube"), {"123"})


if __name__ == "__main__":
    unittest.main()
