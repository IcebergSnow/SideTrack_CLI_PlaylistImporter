"""Keep an exact local song list so a partial link import can resume safely."""

import csv
import os
import tempfile
from pathlib import Path

from .auth import private_directory
from .files import ImportFile


def save_song_list(source: ImportFile, config_dir: Path) -> Path:
    private_directory(config_dir)
    directory = config_dir / "imports"
    private_directory(directory)
    descriptor, filename = tempfile.mkstemp(prefix="sidetrack-", suffix=".csv", dir=directory)
    path = Path(filename)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["title", "artist", "url"])
            for track in source.tracks:
                writer.writerow([track.title, track.artist, f"https://www.youtube.com/watch?v={track.video_id}"])
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path
