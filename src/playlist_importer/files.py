"""Validate the whole input before authenticating or changing a playlist."""

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .errors import InputError

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
PLAYLIST_ID = re.compile(r"^[A-Za-z0-9_-]{10,150}$")
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TRACKS = 5000  # A local guard, not a statement of YouTube's current limit.


@dataclass(frozen=True)
class Track:
    video_id: str
    title: str = ""
    artist: str = ""


@dataclass(frozen=True)
class ImportFile:
    tracks: list[Track]
    duplicates: int


def youtube_url(value: str):
    if "://" not in value:
        value = "https://" + value
    try:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password or parsed.port:
            raise ValueError
        if parsed.hostname not in YOUTUBE_HOSTS | {"youtu.be", "www.youtu.be"}:
            raise ValueError
        return parsed
    except ValueError as exc:
        raise InputError("Use a YouTube or YouTube Music URL, or an 11-character video ID.") from exc


def video_id(value: str) -> str:
    value = value.strip()
    if VIDEO_ID.fullmatch(value):
        return value
    parsed = youtube_url(value)
    parts = parsed.path.strip("/").split("/")
    if parsed.hostname in {"youtu.be", "www.youtu.be"} and len(parts) == 1:
        candidate = parts[0]
    elif parsed.path.rstrip("/") == "/watch":
        values = parse_qs(parsed.query).get("v", [])
        candidate = values[0] if len(values) == 1 else ""
    elif len(parts) == 2 and parts[0] in {"shorts", "embed", "live"}:
        candidate = parts[1]
    else:
        candidate = ""
    if not VIDEO_ID.fullmatch(candidate):
        raise InputError("A song needs a valid YouTube video ID; playlist-only links are not songs.")
    return candidate


def playlist_id(value: str) -> str:
    value = value.strip()
    if PLAYLIST_ID.fullmatch(value):
        return value
    parsed = youtube_url(value)
    values = parse_qs(parsed.query).get("list", [])
    if len(values) == 1 and PLAYLIST_ID.fullmatch(values[0]):
        return values[0]
    raise InputError("--playlist needs a YouTube playlist URL or playlist ID.")


def read_csvs(paths: list[Path]) -> ImportFile:
    tracks = []
    seen = set()
    duplicates = 0
    for path in paths:
        if path.suffix.lower() != ".csv":
            raise InputError(f"{path.name}: use a CSV export. SideTrack TXT files contain titles, not video IDs.")
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                raise InputError(f"{path.name}: CSV files must be no larger than 10 MiB.")
            with path.open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream, strict=True)
                if not reader.fieldnames:
                    raise InputError(f"{path.name}: the CSV is empty.")
                headers = [name.strip().lower() for name in reader.fieldnames]
                if len(headers) != len(set(headers)) or any(not name for name in headers):
                    raise InputError(f"{path.name}: CSV headers must be nonempty and unique.")
                if not {"url", "video_id"}.intersection(headers):
                    raise InputError(f"{path.name}: expected a 'url' or 'video_id' column. Download CSV from SideTrack.")
                reader.fieldnames = headers
                for row in reader:
                    if None in row or any(value is None for value in row.values()):
                        raise InputError(f"{path.name}, line {reader.line_num}: column count does not match the header.")
                    if not any(value.strip() for value in row.values()):
                        continue
                    try:
                        supplied = [row[key].strip() for key in ("video_id", "url") if row.get(key, "").strip()]
                        if not supplied:
                            raise InputError("Missing video URL or ID.")
                        ids = {video_id(value) for value in supplied}
                        if len(ids) != 1:
                            raise InputError("The url and video_id columns refer to different videos.")
                        identifier = ids.pop()
                    except InputError as exc:
                        raise InputError(f"{path.name}, line {reader.line_num}: {exc}") from exc
                    if identifier in seen:
                        duplicates += 1
                        continue
                    seen.add(identifier)
                    tracks.append(Track(identifier, row.get("title", "").strip(), row.get("artist", "").strip()))
                    if len(tracks) > MAX_TRACKS:
                        raise InputError(f"Import at most {MAX_TRACKS:,} unique videos at a time.")
        except (OSError, UnicodeError, csv.Error) as exc:
            raise InputError(f"Couldn't read {path.name}. Check the path and use a valid UTF-8 CSV file.") from exc
    if not tracks:
        raise InputError("No songs found in the CSV files.")
    return ImportFile(tracks, duplicates)
