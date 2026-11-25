"""Where the app keeps its data and the music, including what versions before 0.6.0 (the rename) left on disk.

No Flet here, so the tests can import it.
"""

import shutil
from pathlib import Path

NAME = "Songhaul"
OLD_NAME = "YT Music Playlist Downloader"


def old_data(data: Path, packaged: bool) -> Path:
    """The data folder before the rename. Only Windows puts the app's name in the path (<company>/<product>/data);
    the other systems use the bundle_id, which hasn't changed, so there the result simply doesn't exist."""
    return data.parent.parent / OLD_NAME / "data" if packaged else Path.home() / ".ytmpd"


def migrate(old: Path, new: Path) -> None:
    """Copies the old data once. settings.json goes last and marks it as done: without the mark, a cookies.txt the
    user removes would come back at the next start."""
    if (new / "settings.json").exists() or not old.is_dir():
        return
    try:
        new.mkdir(parents=True, exist_ok=True)
        for name in ("history.json", "cookies.txt"):
            if (old / name).is_file():
                shutil.copy2(old / name, new / name)
        if (old / "settings.json").is_file():
            shutil.copy2(old / "settings.json", new / "settings.json")
        else:
            (new / "settings.json").write_text("{}", encoding="utf-8")
    except OSError as e:  # the app works without it, and the old files are still there
        print(f"songhaul warning: could not copy {old}: {e}", flush=True)


def music_folder(music: Path) -> Path:
    """The default folder. An existing one keeps its old name: its archives say what is already downloaded."""
    old = music / OLD_NAME
    return old if old.is_dir() else music / NAME
