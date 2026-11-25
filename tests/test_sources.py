import unittest

from songhaul import sources
from songhaul.sources import youtube


class Recognising(unittest.TestCase):
    def test_hosts_are_compared_whole(self):
        for url in ("https://music.youtube.com/playlist?list=PL1", "https://youtu.be/abc",
                    "http://m.youtube.com/watch?v=a", "www.youtube.com/watch?v=abc", "https://YouTube.com/watch?v=abc"):
            self.assertEqual(sources.source_for(url).name, "YouTube", url)
        for url in ("https://youtube.com.example.it/watch?v=abc", "https://notyoutube.com/watch?v=abc",
                    "https://example.com/?u=https://youtu.be/abc", "https://youtu.be@example.com/abc",
                    "Title https://youtu.be/abc", "https://youtu.be/abc\nhttps://youtu.be/def", "", "youtube"):
            self.assertFalse(sources.is_known(url), url)

    def test_broken_links_are_just_unknown(self):
        self.assertFalse(sources.is_known("https://[youtube.com/watch?v=abc"))

    def test_unknown_links_go_to_ytdlp_unchanged(self):
        url = "https://example.com/playlist?list=PL123"
        source = sources.source_for(url)
        self.assertEqual((source.normalize(url), source.is_playlist(url)), (url, False))

    def test_link_in_shared_text(self):
        link = "https://music.youtube.com/watch?v=abc&si=x"
        self.assertEqual(sources.link_in(f"Ascolta su YouTube Music {link}\nciao"), link)
        self.assertEqual(sources.link_in(f"https://example.com/a {link}"), link)
        for text in ("https://example.com/a", "https://www.youtube.com", "no link", "", None):
            self.assertIsNone(sources.link_in(text), text)


class YouTube(unittest.TestCase):
    def test_link_from_route(self):
        self.assertEqual(youtube.link_from_route("/watch?v=abc"), "https://www.youtube.com/watch?v=abc")
        for route in ("/", "", None):
            self.assertIsNone(youtube.link_from_route(route))


if __name__ == "__main__":
    unittest.main()
