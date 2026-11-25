import shutil
import tempfile
import unittest
from pathlib import Path

from mutagen.id3 import ID3, TXXX
from mutagen.mp4 import MP4

from songhaul import core

YOUTUBE = {"extractor": "youtube", "title": "Jain - Makeba (Official Video)", "track": "Makeba", "artist": "Jain",
           "album": "Zanaka", "release_year": 2015, "upload_date": "20161202", "playlist_index": 7,
           "categories": ["Music"], "description": "Long text", "webpage_url": "https://…"}
SOUNDCLOUD = {"extractor": "soundcloud", "title": "Makeba", "track": "Makeba", "uploader": "Jain", "album": "Zanaka",
              "upload_date": "20151106", "playlist_index": 7, "genres": ["Pop"], "description": "Long text"}
PLAIN = {"extractor": "youtube", "title": "Me at the zoo", "uploader": "jawed", "upload_date": "20050424"}


class Written(unittest.TestCase):
    """What is read back from the file: the same fields from every platform, in both formats."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.mp3, self.m4a = Path(tmp.name) / "a.mp3", Path(tmp.name) / "a.m4a"
        self.mp3.write_bytes(b"\xff\xfb\x90\x00" + bytes(413))
        shutil.copy(Path(__file__).parent / "fixtures/silence.m4a", self.m4a)

    def write(self, info):
        for path in (self.mp3, self.m4a):
            core.Tags().run(info | {"filepath": str(path)})
        mp3, m4a = ID3(self.mp3, translate=False), MP4(self.m4a)
        read = {name: str(mp3[frame]) if frame in mp3 else None for name, frame in
                (("title", "TIT2"), ("artist", "TPE1"), ("album", "TALB"), ("track", "TRCK"), ("year", "TYER"), ("genre", "TCON"))}
        same = {name: str(m4a[key][0]) if key in m4a else None for name, key in
                (("title", "\xa9nam"), ("artist", "\xa9ART"), ("album", "\xa9alb"), ("year", "\xa9day"), ("genre", "\xa9gen"))}
        same["track"] = str(m4a["trkn"][0][0]) if "trkn" in m4a else None
        self.assertEqual(read, same)
        return read

    def test_every_platform(self):
        song = {"title": "Makeba", "artist": "Jain", "album": "Zanaka", "track": "7", "year": "2015"}
        self.assertEqual(self.write(YOUTUBE), song | {"genre": None})  # YouTube's category isn't a genre
        self.assertEqual(self.write(SOUNDCLOUD), song | {"genre": "Pop"})

    def test_single_video(self):
        self.assertEqual(self.write(PLAIN), {"title": "Me at the zoo", "artist": "jawed", "album": None, "track": None,
                                             "year": None, "genre": None})  # the upload's year isn't the song's
        self.assertEqual(self.write(SOUNDCLOUD | {"playlist_index": None})["year"], "2015")  # there it usually is

    def test_mp3_stays_at_2_3_without_leftovers(self):
        tags = ID3()  # FFmpeg copies the source's technical fields
        tags.add(TXXX(encoding=3, desc="major_brand", text="isom"))
        tags.save(self.mp3)
        self.write(YOUTUBE)
        core.embed_cover(str(self.mp3), b"\xff\xd8jpeg")
        mp3 = ID3(self.mp3, translate=False)
        self.assertEqual(mp3.version, (2, 3, 0))
        self.assertEqual(sorted(f.FrameID for f in mp3.values()), ["APIC", "TALB", "TIT2", "TPE1", "TRCK", "TYER"])

    def test_m4a_without_leftovers(self):
        audio = MP4(self.m4a)
        audio["\xa9cmt"] = ["Follow me on…"]
        audio.save()
        self.write(PLAIN)
        self.assertEqual(sorted(MP4(self.m4a)), ["\xa9ART", "\xa9nam"])

    def test_cover_in_m4a(self):
        self.write(YOUTUBE)
        core.embed_cover(str(self.m4a), b"\xff\xd8jpeg")
        self.assertEqual((bytes(MP4(self.m4a)["covr"][0]), MP4(self.m4a)["\xa9nam"]), (b"\xff\xd8jpeg", ["Makeba"]))


class FileNames(unittest.TestCase):
    def name(self, info, clean=False):
        info = dict(info, id="1", ext="mp3")
        core._Current(core._Logger(lambda e: None), clean, artist_names=True).run(info)
        return core.yt_dlp.YoutubeDL({"quiet": True}).prepare_filename(info, outtmpl=core.build_options("out")["outtmpl"])

    def test_artist_in_front(self):
        self.assertEqual(self.name(SOUNDCLOUD), "007 - Jain - Makeba.mp3")
        self.assertEqual(self.name(SOUNDCLOUD | {"playlist_index": None}), "Jain - Makeba.mp3")

    def test_not_twice(self):
        self.assertEqual(self.name(YOUTUBE), "007 - Jain - Makeba (Official Video).mp3")
        self.assertEqual(self.name(YOUTUBE, clean=True), "007 - Jain - Makeba.mp3")
        self.assertEqual(self.name(YOUTUBE | {"artist": "JAIN, Someone"}), "007 - Jain - Makeba (Official Video).mp3")

    def test_a_channel_is_not_an_artist(self):
        self.assertEqual(self.name(PLAIN), "Me at the zoo.mp3")

    def test_off_by_default(self):
        info = dict(SOUNDCLOUD, id="1", ext="mp3")
        core._Current(core._Logger(lambda e: None)).run(info)
        self.assertNotIn("file_name", info)

    def test_clean_titles_reach_the_tags(self):
        info = {"extractor": "soundcloud", "title": "Song (Official Audio)", "track": "Song (Official Audio)"}
        core._Current(core._Logger(lambda e: None), clean=True).run(info)
        self.assertEqual(core.tags_for(info)["title"], "Song")


if __name__ == "__main__":
    unittest.main()
