"""A small terminal walkthrough; no saved preferences or extra dependencies."""

import os
import shlex
import unicodedata
from datetime import datetime
from pathlib import Path

from .terminal import ask, progress


def recent_downloads(directory: Path) -> list[Path]:
    candidates = []
    try:
        for path in directory.iterdir():
            if path.suffix.lower() != ".csv":
                continue
            if not (path.name.lower().startswith("sidetrack-") or path.name.lower() == "playlist.csv"):
                continue
            try:
                if path.is_file():
                    candidates.append((path.stat().st_mtime_ns, path.name, path))
            except OSError:
                continue
    except OSError:
        return []
    return [item[2] for item in sorted(candidates, reverse=True)[:10]]


def entered_path(value: str) -> Path:
    # Accept literal paths as well as Finder's escaped drag-and-drop paths.
    # This is parsing only: never run pasted text as a shell command.
    literal = Path(value).expanduser()
    if literal.exists():
        return literal
    if os.name == "nt":
        return Path(value.strip('"')).expanduser()
    try:
        parts = shlex.split(value)
    except ValueError:
        return literal
    return Path(parts[0]).expanduser() if len(parts) == 1 else literal


def choose_csv() -> Path:
    candidates = recent_downloads(Path.home() / "Downloads")
    if candidates:
        progress("Recent SideTrack CSV downloads (newest first):")
        for number, path in enumerate(candidates, 1):
            timestamp = datetime.fromtimestamp(path.stat().st_mtime).strftime("%b %d %H:%M")
            progress(f"  {number}. {path.name}  ({timestamp})")
    else:
        progress("No SideTrack CSVs found in Downloads. Download CSV from SideTrack, or enter a file path below.")
    while True:
        hint = " [Enter = 1]" if candidates else ""
        answer = ask(f"Choose a number, or drag/paste a CSV file path{hint}; q to cancel:")
        if answer.lower() == "q":
            raise KeyboardInterrupt
        if not answer and candidates:
            return candidates[0]
        if answer.isdecimal():
            index = int(answer) - 1
            if 0 <= index < len(candidates):
                return candidates[index]
            progress("Choose one of the displayed numbers, or enter a CSV file path.")
        elif answer:
            return entered_path(answer)


def choose_title() -> str:
    default = datetime.now().strftime("SideTrack %Y-%m-%d %H%M")
    while True:
        title = ask(f"Playlist name [Enter = {default}]:") or default
        if len(title) <= 150 and not any(unicodedata.category(c).startswith("C") for c in title):
            return title
        progress("Use a name with 1–150 characters and no control characters.")


def confirm_import(args, source, title: str, identifier: str | None) -> bool:
    for path in args.files:
        progress(f"File: {path.resolve()}")
    progress("Song preview:")
    for track in source.tracks[:5]:
        progress(f"  {track.artist} - {track.title or track.video_id}")
    if len(source.tracks) > 5:
        progress(f"  ... and {len(source.tracks) - 5} more.")
    if identifier:
        progress(f"Destination: https://www.youtube.com/playlist?list={identifier}")
        question = f"Check this playlist and add missing videos from these {len(source.tracks)} songs? [y/N]:"
    else:
        progress(f"New private playlist: {title}")
        question = f"Import these {len(source.tracks)} songs? [y/N]:"
    return ask(question).lower() in {"y", "yes"}


def choose_client(config_dir: Path) -> Path:
    for path in (config_dir / "client_secret.json", Path.home() / "Downloads/client_secret.json"):
        if path.is_file():
            return path
    progress("Google Desktop OAuth JSON was not found. See the README's Google setup if you haven't created one.")
    answer = ask("Drag/paste the client JSON file path, or q to cancel:")
    if not answer or answer.lower() == "q":
        raise KeyboardInterrupt
    return entered_path(answer)
