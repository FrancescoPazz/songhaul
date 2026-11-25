"""A repair for M4A files downloaded in segments without FFmpeg (Android). FFmpeg, where there is one, rebuilds them."""

import os
import struct
from pathlib import Path


def _boxes(file, size):
    """(kind, start, length) of the top-level boxes; ValueError if they don't add up to the file."""
    start = 0
    while start < size:
        file.seek(start)
        header = file.read(16)
        if len(header) < 8:
            raise ValueError("truncated")
        length, kind = struct.unpack(">I4s", header[:8])
        if length == 1 and len(header) == 16:
            length = struct.unpack(">Q", header[8:])[0]
        elif length == 0:  # up to the end of the file
            length = size - start
        if length < 8 or start + length > size:
            raise ValueError("truncated")
        yield kind, start, length
        start += length


def _duration(sidx: bytes) -> int:
    """How long the segment after this index is, in the index's own time units."""
    at = 28 if sidx[8] == 0 else 36  # the times are 4 or 8 bytes long, depending on the version
    count = struct.unpack(">H", sidx[at + 2:at + 4])[0]
    return sum(struct.unpack(">I", sidx[at + 8 + 12 * i:at + 12 + 12 * i])[0] for i in range(count))


def single_index(path: str | Path) -> None:
    """SoundCloud's segments each carry their own index (`sidx`), and Android believes the first: 10 seconds, no
    seeking. Joins them in one, as in YouTube's files. The audio isn't touched, nor are files of any other shape."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(path, "rb") as source:
            boxes = list(_boxes(source, path.stat().st_size))
            first = {}  # the first index, for the track and the time units
            segments, head, audio = [], [], []  # [bytes, duration], (start, length), (start, length)
            for kind, start, length in boxes:
                if kind == b"sidx":
                    source.seek(start)
                    sidx = source.read(length)
                    first = first or {"ids": sidx[12:20]}
                    segments.append([0, _duration(sidx)])
                elif kind in (b"moof", b"mdat"):
                    segments[-1][0] += length  # IndexError if there's no index yet
                    audio.append((start, length))
                elif kind != b"styp":
                    if segments:
                        return
                    head.append((start, length))
            if len(segments) < 2:
                return
            index = struct.pack(">I", 1 << 24) + first["ids"] + struct.pack(">QQHH", 0, 0, 0, len(segments)) + b"".join(
                struct.pack(">III", size, duration, 0x90000000) for size, duration in segments)  # starts with a key frame
            with open(tmp, "wb") as out:
                for part in (head, audio):
                    for start, length in part:
                        source.seek(start)
                        _copy(source, out, length)
                    if part is head:
                        out.write(struct.pack(">I4s", len(index) + 8, b"sidx") + index)
        os.replace(tmp, path)
    except (ValueError, IndexError, struct.error):  # not the shape this is for: leave it as it is
        pass
    finally:
        tmp.unlink(missing_ok=True)


def _copy(source, out, length):
    while length:  # a long mix is hundreds of MB: not all at once in a phone's memory
        chunk = source.read(min(length, 1 << 20))
        if not chunk:
            raise ValueError("truncated")
        out.write(chunk)
        length -= len(chunk)
