import unittest

from songhaul import core


class NormalizeUrl(unittest.TestCase):
    def test_music_playlist(self):
        self.assertEqual(core.normalize_url("https://music.youtube.com/playlist?list=PL123&si=x"),
                         "https://www.youtube.com/playlist?list=PL123")

    def test_song_playing_inside_playlist(self):
        self.assertEqual(core.normalize_url("https://www.youtube.com/watch?v=abc&list=PL123&index=4"),
                         "https://www.youtube.com/playlist?list=PL123")

    def test_short_links(self):
        self.assertEqual(core.normalize_url("https://youtu.be/abc?si=x"), "https://www.youtube.com/watch?v=abc")
        self.assertEqual(core.normalize_url("https://youtu.be/abc?list=PL123&si=x"),
                         "https://www.youtube.com/playlist?list=PL123")
        self.assertEqual(core.normalize_url("https://youtu.be/abc?list=RDabc"), "https://www.youtube.com/watch?v=abc")
        self.assertTrue(core.is_playlist_url("https://youtu.be/abc?list=PL123"))
        self.assertEqual(core.normalize_url("https://youtu.be/"), "https://youtu.be/")

    def test_single_video(self):
        url = "https://www.youtube.com/watch?v=abc"
        self.assertEqual(core.normalize_url(url), url)
        self.assertEqual(core.normalize_url("https://music.youtube.com/watch?v=abc&si=x"), url)
        self.assertFalse(core.is_playlist_url(url))

    def test_song_playing_inside_radio_mix(self):
        self.assertEqual(core.normalize_url("https://music.youtube.com/watch?v=abc&list=RDAMVMabc"),
                         "https://www.youtube.com/watch?v=abc")
        # curated YouTube Music playlists start with RD too, but they are playlists
        self.assertEqual(core.normalize_url("https://music.youtube.com/watch?v=abc&list=RDCLAK5uy_x"),
                         "https://www.youtube.com/playlist?list=RDCLAK5uy_x")

    def test_other_sites_untouched(self):
        url = "https://example.com/watch?list=PL123"
        self.assertEqual(core.normalize_url(url), url)


class BuildOptions(unittest.TestCase):
    def test_mp3_converts(self):
        opts = core.build_options("out", "mp3", "320")
        keys = [pp["key"] for pp in opts["postprocessors"]]
        self.assertEqual(keys, ["FFmpegExtractAudio"])
        self.assertEqual(opts["postprocessors"][0]["preferredquality"], "320")

    def test_m4a_needs_no_ffmpeg(self):
        opts = core.build_options("out", "m4a")
        self.assertEqual(opts["format"], "bestaudio[ext=m4a]")
        self.assertNotIn("postprocessors", opts)

    def test_archive_lives_in_output_folder(self):
        self.assertTrue(core.build_options("out")["download_archive"].endswith(core.ARCHIVE))
        self.assertIn("out", core.build_options("out")["download_archive"])

    def test_cookies_only_when_browser_chosen(self):
        self.assertNotIn("cookiesfrombrowser", core.build_options("out"))
        self.assertEqual(core.build_options("out", browser="firefox")["cookiesfrombrowser"], ("firefox",))

    def test_items_and_js_runtimes(self):
        opts = core.build_options("out", items="1,3-5")
        self.assertEqual(opts["playlist_items"], "1,3-5")
        self.assertIn("node", opts["js_runtimes"])

    def test_android_layout_temp_and_archive_elsewhere(self):
        opts = core.build_options("music", "m4a", temp_dir="tmp", archive="data/a.txt")
        self.assertEqual(opts["paths"], {"home": "music", "temp": "tmp"})
        self.assertEqual(opts["download_archive"], "data/a.txt")
        self.assertNotIn("/", opts["outtmpl"])  # relative, so yt-dlp applies paths

    def test_file_names(self):
        tmpl = core.build_options("out")["outtmpl"]
        ydl = core.yt_dlp.YoutubeDL({"quiet": True})
        song = {"id": "abc", "title": "Song", "ext": "mp3"}
        self.assertEqual(ydl.prepare_filename(song, outtmpl=tmpl), "Song.mp3")
        self.assertEqual(ydl.prepare_filename(song | {"playlist_index": 4}, outtmpl=tmpl), "004 - Song.mp3")

    def test_cookies_file_wins_over_browser(self):
        opts = core.build_options("out", browser="chrome", cookies="c.txt")
        self.assertEqual(opts["cookiefile"], "c.txt")
        self.assertNotIn("cookiesfrombrowser", opts)

    def test_quickjs_from_android_native_dir(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest import mock

        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "libqjs.so").write_bytes(b"")
            with mock.patch.dict(os.environ, {"ANDROID_NATIVE_LIBRARY_DIR": d}):
                self.assertEqual(core.js_runtimes()["quickjs"], {"path": str(Path(d) / "libqjs.so")})
        self.assertEqual(core.js_runtimes()["quickjs"], {})

    def test_unknown_format(self):
        with self.assertRaises(ValueError):
            core.build_options("out", "flac")


class Tags(unittest.TestCase):
    def test_music_fields_win(self):
        info = {"track": "Makeba", "title": "Jain - Makeba (Official Video)", "artist": "Jain", "uploader": "JainVEVO",
                "album": "Zanaka"}
        self.assertEqual(core.tags_for(info), {"title": "Makeba", "artist": "Jain", "album": "Zanaka"})

    def test_plain_video_falls_back(self):
        info = {"title": "Me at the zoo", "uploader": "jawed"}
        self.assertEqual(core.tags_for(info), {"title": "Me at the zoo", "artist": "jawed"})


class Reasons(unittest.TestCase):
    def test_kinds(self):
        cases = {
            "[youtube] abcdefghijk: Private video. Sign in if you've been granted access to this video": "private",
            "[youtube] abcdefghijk: Sign in to confirm your age. This video may be inappropriate for some users. "
            "Use --cookies-from-browser or --cookies for the authentication.": "age",
            "[youtube] abcdefghijk: Sign in to confirm you’re not a bot. Use --cookies-from-browser": "bot",
            "[youtube] abcdefghijk: Video unavailable. The uploader has not made this video available in your "
            "country": "region",
            "[youtube] abcdefghijk: Video unavailable. This video is no longer available because the YouTube "
            "account associated with this video has been terminated.": "unavailable",
            "[youtube] abcdefghijk: This video is unavailable": "unavailable",
            "[youtube] abcdefghijk: Join this channel to get access to members-only content like this video": "members",
            "unable to download video data: HTTP Error 403: Forbidden": "forbidden",
            "[youtube] abcdefghijk: Unable to download webpage: <urlopen error [Errno 11001] getaddrinfo failed>":
                "network",
            "Failed to decrypt with DPAPI. See  https://github.com/yt-dlp/yt-dlp/issues/10927 (cookie)": "cookies",
            "[youtube:tab] PLx: Unable to download API page: HTTP Error 400: Bad Request": "not_found",
            "Unsupported URL: https://example.com/": "not_found",
            "something new": "other",
        }
        for message, kind in cases.items():
            self.assertEqual(core.reason_kind(message), kind, message)

    def test_video_id(self):
        self.assertEqual(core.video_id_in("[youtube] jNQXAC9IVRw: Private video"), "jNQXAC9IVRw")
        self.assertIsNone(core.video_id_in("HTTP Error 403: Forbidden"))


class Archive(unittest.TestCase):
    def test_reads_ids_and_tolerates_missing_file(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            archive = core.archive_path(d)
            self.assertEqual(core.archived_ids(archive), set())
            archive.write_text("youtube jNQXAC9IVRw\nyoutube abcdefghijk\n\n", encoding="utf-8")
            self.assertEqual(core.archived_ids(archive), {"jNQXAC9IVRw", "abcdefghijk"})


class RetryAfter403(unittest.TestCase):
    """download() with a fake YoutubeDL: no network."""

    def run_with(self, fail_times):
        import tempfile
        from unittest import mock

        class FakeYDL:
            calls = 0

            def __init__(self, opts):
                self.opts, self.pps = opts, {}

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                pass

            def add_post_processor(self, pp, when):
                self.pps[when] = pp

            def download(self, urls):
                FakeYDL.calls += 1
                info = {"id": "abcdefghijk", "title": "Song", "filepath": "x.mp3"}
                self.pps["pre_process"].run(info)
                if FakeYDL.calls <= fail_times:
                    self.opts["logger"].error("ERROR: unable to download video data: HTTP Error 403: Forbidden")
                else:
                    self.pps["after_move"].run(info)

        events = []
        with tempfile.TemporaryDirectory() as d, mock.patch.object(core.yt_dlp, "YoutubeDL", FakeYDL):
            result = core.download("https://www.youtube.com/watch?v=abcdefghijk", d, "m4a", on_event=events.append)
        return result, FakeYDL.calls, events

    def test_a_403_is_retried_once(self):
        result, calls, events = self.run_with(fail_times=1)
        self.assertEqual((result["done"], result["skipped"], calls), (1, 0, 2))
        skipped = next(e for e in events if e["type"] == "track_skipped")
        self.assertEqual((skipped["id"], skipped["title"], skipped["kind"]), ("abcdefghijk", "Song", "forbidden"))

    def test_gives_up_after_the_second_403(self):
        result, calls, _ = self.run_with(fail_times=5)
        self.assertEqual((result["done"], result["skipped"], calls), (0, 1, 2))


class CleanTitles(unittest.TestCase):
    def test_cases(self):
        cases = {
            "Felix Jaehn, Whitney Houston - It's Not Right But It's Okay (Official Video)":
                "Felix Jaehn, Whitney Houston - It's Not Right But It's Okay",
            "David Guetta & Bebe Rexha - I'm Good (Blue) [Djs From Mars Remix] [VISUALIZER]":
                "David Guetta & Bebe Rexha - I'm Good (Blue) [Djs From Mars Remix]",
            "Tom Santa - Rainfall (Praise You) ｜ Official Video": "Tom Santa - Rainfall (Praise You)",
            "Alan Walker, Dash Berlin & Vikkstar - Better Off (Alone, Pt. III) - Official Music Video":
                "Alan Walker, Dash Berlin & Vikkstar - Better Off (Alone, Pt. III)",
            "Jain - Makeba (Ian Asher Remix)": "Jain - Makeba (Ian Asher Remix)",
            "Zara Larsson, PinkPantheress - Midnight Sun (Girls Trip - Official Visualizer)":
                "Zara Larsson, PinkPantheress - Midnight Sun (Girls Trip - Official Visualizer)",
            "Sonny Fodera - Mind Still (feat. blythe) [Official Music Video]": "Sonny Fodera - Mind Still (feat. blythe)",
            "Official Video": "Official Video",  # never leave an empty title
            "Me at the zoo": "Me at the zoo",
        }
        for title, clean in cases.items():
            self.assertEqual(core.clean_title(title), clean, title)


class Covers(unittest.TestCase):
    @unittest.skipUnless(__import__("importlib.util").util.find_spec("PIL"), "Pillow not installed")
    def test_square_crop_drops_the_black_bands(self):
        import io

        from PIL import Image

        frame = Image.new("RGB", (480, 360), "black")  # hqdefault: 480x360 with a 480x270 picture in the middle
        frame.paste(Image.new("RGB", (480, 270), "red"), (0, 45))
        out = io.BytesIO()
        frame.save(out, "JPEG")
        square = Image.open(io.BytesIO(core.square_jpeg(out.getvalue())))
        self.assertEqual(square.size, (270, 270))
        r, g, b = square.getpixel((5, 5))
        self.assertGreater(r, 200)  # red, not a black band
        self.assertLess(g + b, 60)


class UpdateCheck(unittest.TestCase):
    def test_versions(self):
        from songhaul import update

        self.assertTrue(update.is_newer("v0.2.1", "0.2.0"))
        self.assertTrue(update.is_newer("v0.10.0", "0.9.9"))  # numbers, not text
        self.assertFalse(update.is_newer("v0.2.0", "0.2.0"))
        self.assertFalse(update.is_newer("v0.2.0", "0.2.0-dev.7"))  # a dev build of 0.2.0 is not older than 0.2.0
        self.assertFalse(update.is_newer("v0.1.0", "0.2.0"))


class Translations(unittest.TestCase):
    def test_same_keys_and_every_reason_explained(self):
        from songhaul.i18n import STRINGS

        self.assertEqual(STRINGS["it"].keys(), STRINGS["en"].keys())
        for kind in [k for k, _ in core._REASONS] + ["other"]:
            self.assertIn(f"reason_{kind}", STRINGS["en"])


class Rename(unittest.TestCase):
    """0.6.0 renamed the app: what earlier versions left on disk must still be found."""

    def setUp(self):
        import tempfile
        from pathlib import Path

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.old, self.new = Path(tmp.name) / "old", Path(tmp.name) / "new"
        self.old.mkdir()

    def test_data_is_copied_once(self):
        from songhaul import paths

        (self.old / "history.json").write_text("[1]", encoding="utf-8")
        (self.old / "cookies.txt").write_text("secret", encoding="utf-8")
        paths.migrate(self.old, self.new)
        self.assertEqual((self.new / "history.json").read_text(encoding="utf-8"), "[1]")
        self.assertEqual((self.new / "settings.json").read_text(encoding="utf-8"), "{}")
        self.assertTrue((self.old / "history.json").is_file())  # a copy: 0.5.0 still works
        (self.new / "cookies.txt").unlink()  # removed by the user in Settings
        paths.migrate(self.old, self.new)
        self.assertFalse((self.new / "cookies.txt").exists())

    def test_newer_data_is_never_overwritten(self):
        from songhaul import paths

        self.new.mkdir()
        (self.old / "settings.json").write_text('{"theme": "dark"}', encoding="utf-8")
        (self.new / "settings.json").write_text('{"theme": "light"}', encoding="utf-8")
        paths.migrate(self.old, self.new)
        self.assertIn("light", (self.new / "settings.json").read_text(encoding="utf-8"))

    def test_fresh_install_has_nothing_to_copy(self):
        from songhaul import paths

        paths.migrate(self.old / "missing", self.new)
        self.assertFalse(self.new.exists())

    def test_old_music_folder_stays_in_use(self):
        from songhaul import paths

        self.assertEqual(paths.music_folder(self.old), self.old / paths.NAME)
        (self.old / paths.OLD_NAME).mkdir()
        self.assertEqual(paths.music_folder(self.old), self.old / paths.OLD_NAME)

    def test_where_the_old_data_was(self):
        from pathlib import Path

        from songhaul import paths

        self.assertEqual(paths.old_data(Path("Company/Songhaul/data"), packaged=True),
                         Path("Company/YT Music Playlist Downloader/data"))
        self.assertEqual(paths.old_data(Path.home() / ".songhaul", packaged=False), Path.home() / ".ytmpd")


if __name__ == "__main__":
    unittest.main()
