import struct
import tempfile
import unittest
from pathlib import Path

from songhaul import mp4


def box(kind, payload=b""):
    return struct.pack(">I4s", len(payload) + 8, kind) + payload


def sidx(duration, size, version=1):
    times = struct.pack(">QQ" if version else ">II", 0, 0)
    return box(b"sidx", struct.pack(">III", version << 24, 1, 44100) + times + struct.pack(">HHIII", 0, 1, size, duration, 1 << 31))


def segment(n, version=1):
    moof, mdat = box(b"moof", bytes([n]) * 20), box(b"mdat", bytes([n]) * (100 + n))
    return box(b"styp", b"msdh") + sidx(1000 + n, len(moof + mdat), version) + moof + mdat, moof + mdat


class SingleIndex(unittest.TestCase):
    """SoundCloud's files have an index per segment; Android reads only the first one (10 s of any song)."""

    def run_on(self, data):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "a.m4a"
            path.write_bytes(data)
            mp4.single_index(path)
            self.assertEqual([p.name for p in Path(d).iterdir()], ["a.m4a"])  # no temp file left
            return path.read_bytes()

    def test_indexes_are_joined(self):
        for version in (0, 1):
            segments = [segment(n, version) for n in range(3)]
            head = box(b"ftyp", b"iso5") + box(b"moov", b"m" * 50)
            fixed = self.run_on(head + b"".join(s for s, _ in segments))
            audio = b"".join(a for _, a in segments)
            self.assertTrue(fixed.startswith(head))
            self.assertTrue(fixed.endswith(audio))  # the audio itself is untouched, and follows the index at once
            index = fixed[len(head):-len(audio)]
            self.assertEqual(index[4:8], b"sidx")
            self.assertEqual(struct.unpack(">I", index[:4])[0], len(index))
            self.assertEqual(struct.unpack(">II", index[12:20]), (1, 44100))
            count = struct.unpack(">H", index[38:40])[0]
            refs = [struct.unpack(">III", index[40 + 12 * i:52 + 12 * i]) for i in range(count)]
            self.assertEqual([(size, duration) for size, duration, _ in refs],
                             [(len(a), 1000 + n) for n, (_, a) in enumerate(segments)])
            self.assertEqual(sum(size for size, _, _ in refs), len(audio))

    def test_anything_else_is_left_alone(self):
        head = box(b"ftyp") + box(b"moov")
        one, audio = segment(1)
        for data in (head + one,  # YouTube: a single index already
                     head + box(b"mdat", b"x" * 10),  # an ordinary MP4
                     head + audio + one + one,  # audio before any index
                     head + one + one[:-5],  # cut short
                     b"", b"not an mp4 at all"):
            self.assertEqual(self.run_on(data), data)


if __name__ == "__main__":
    unittest.main()
