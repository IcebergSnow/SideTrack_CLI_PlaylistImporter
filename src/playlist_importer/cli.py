import argparse
import os
import shlex
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

from . import __version__
from .auth import authenticate, logout
from .errors import ImporterError, InputError, PlaylistConflict, ReauthenticationRequired
from .files import ImportFile, Track, playlist_id, read_csvs
from .interactive import choose_client, choose_count, choose_csv, choose_link, choose_source, choose_title, confirm_import
from .recommendations import POOL_TARGET, recommend
from .snapshots import save_song_list
from .terminal import ask, progress, safe_text
from .youtube import YouTube

CONFLICT_DELAYS = (5, 10, 20)
RECHECK_DELAY = 2


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Create a private YouTube playlist from a song link or SideTrack CSV files. Google sign-in runs locally.")
    result.add_argument("files", nargs="*", type=Path, metavar="CSV", help="one or more CSVs with url or video_id columns")
    result.add_argument("--url", help="generate recommendations directly from one YouTube or YouTube Music song link")
    result.add_argument("--count", type=int, help="number of recommendations for --url (1–200; prompts in interactive mode, otherwise defaults to 20)")
    target = result.add_mutually_exclusive_group()
    target.add_argument("--name", help="new private playlist title (prompts interactively; otherwise defaults to the CSV filename or SideTrack recommendations)")
    target.add_argument("--playlist", help="append/resume into an existing playlist ID or URL, skipping videos already there")
    result.add_argument("--dry-run", action="store_true", help="preview without Google sign-in or playlist writes (song links contact YouTube Music; CSVs stay offline)")
    result.add_argument("--interactive", action="store_true", help="choose a song link or CSV, name the playlist and confirm (automatic with no CSV in a terminal)")
    result.add_argument("--client-secrets", type=Path, default=os.environ.get("PLAYLIST_IMPORTER_CLIENT_SECRETS"), help="Google Desktop OAuth JSON path (or PLAYLIST_IMPORTER_CLIENT_SECRETS)")
    result.add_argument("--config-dir", type=Path, default=os.environ.get("PLAYLIST_IMPORTER_CONFIG_DIR", str(Path.home() / ".playlistimporter")), help="private token directory (default: ~/.playlistimporter)")
    result.add_argument("--reauth", action="store_true", help="open Google sign-in again, e.g. to switch channels")
    result.add_argument("--logout", action="store_true", help="remove the local token cache; does not revoke Google's authorization")
    result.add_argument("--version", action="version", version=f"PlaylistImporter {__version__}")
    return result


def resume_command(args, identifier: str) -> str:
    command = [sys.executable, "-m", "playlist_importer", *(str(path.expanduser().resolve()) for path in args.files),
               "--playlist", identifier, "--config-dir", str(args.config_dir.expanduser().resolve())]
    if args.client_secrets:
        command.extend(["--client-secrets", str(args.client_secrets.expanduser().resolve())])
    return subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command)


def add_with_recovery(youtube: YouTube, identifier: str, video_id: str) -> bool:
    """Return False when a read confirms the video and no repeat write is needed."""
    try:
        youtube.add_video(identifier, video_id)
        return True
    except PlaylistConflict as exc:
        conflict = exc

    for attempt, delay in enumerate(CONFLICT_DELAYS, 1):
        progress(f"YouTube conflict for {video_id}. Automatic recovery {attempt}/{len(CONFLICT_DELAYS)}: waiting {delay}s, then checking the playlist.")
        time.sleep(delay)
        # Reads can lag behind successful writes. Require two separated checks
        # before retrying an absent video; never repeat a reported duplicate.
        for check in range(2):
            if check:
                time.sleep(RECHECK_DELAY)
            try:
                saved = youtube.video_ids(identifier)
            except ImporterError as exc:
                raise ImporterError(f"Automatic recovery couldn't verify the playlist. Stopped before another insertion. {exc}") from exc
            if video_id in saved:
                progress(f"Confirmed {video_id} is already saved; continuing without another insertion.")
                return False
        if conflict.reported_duplicate:
            continue
        progress(f"Video {video_id} was absent from both checks; retrying insertion ({attempt}/{len(CONFLICT_DELAYS)}).")
        try:
            youtube.add_video(identifier, video_id)
            return True
        except PlaylistConflict as exc:
            conflict = exc
    raise ImporterError(
        f"Automatic conflict recovery stopped after {len(CONFLICT_DELAYS)} rounds. "
        "The playlist was kept. Wait before using the printed resume command."
    ) from conflict


def run(args) -> int:
    args.config_dir = args.config_dir.expanduser()
    if args.client_secrets:
        args.client_secrets = args.client_secrets.expanduser()
    if args.logout:
        if args.files or args.name or args.playlist or args.dry_run or args.reauth or args.interactive or args.url is not None or args.count is not None:
            raise InputError("Use --logout by itself (optionally with --config-dir).")
        removed = logout(args.config_dir)
        progress("Removed the local login." if removed else "No saved local login was found.")
        progress("To revoke access at Google too, visit https://myaccount.google.com/connections .")
        return 0
    interactive = args.interactive or (not args.files and sys.stdin.isatty())
    if interactive and not sys.stdin.isatty():
        raise InputError("Interactive mode needs a terminal. Provide CSV paths or --url directly for scripts.")
    if args.url is not None and args.files:
        raise InputError("Choose either CSV files or --url, not both.")
    if args.count is not None and not 1 <= args.count <= POOL_TARGET:
        raise InputError(f"--count must be between 1 and {POOL_TARGET}.")
    if interactive and not args.files and args.url is None:
        if choose_source() == "link":
            args.url = choose_link()
        else:
            args.files = [choose_csv()]
    if args.count is not None and args.url is None:
        raise InputError("--count is only used with a song link; CSV imports use all unique rows.")
    identifier = playlist_id(args.playlist) if args.playlist else None
    if args.url is not None:
        progress("Checking the song and finding similar music. This may take a moment...")
        recommendations = recommend(args.url)
        available = len(recommendations["tracks"])
        seed = recommendations["seed"]
        progress(f"Starting song: {', '.join(seed['artists'])} - {seed['title']}")
        progress(f"Found {available} unique recommendations; the starting song is excluded.")
        count = args.count if args.count is not None else (choose_count(available) if interactive else 20)
        if count > available:
            raise InputError(f"Only {available} unique recommendations were available. Try again with --count {available} or a smaller number.")
        source = ImportFile([
            Track(track["video_id"], track["title"], ", ".join(track["artists"]))
            for track in recommendations["tracks"][:count]
        ], duplicates=0)
    else:
        if not args.files:
            raise InputError("Provide a CSV file or --url. Run sidetrack in a terminal for the guided menu.")
        args.files = [path.expanduser() for path in args.files]
        source = read_csvs(args.files)
    if interactive and not args.dry_run and not identifier and args.name is None:
        args.name = choose_title()
    title = args.name if args.name is not None else (args.files[0].stem if args.files else "SideTrack recommendations")
    if not identifier and (not title.strip() or len(title) > 150 or any(unicodedata.category(c).startswith("C") for c in title)):
        raise InputError("Use a playlist name with 1–150 characters and no control characters.")
    if args.url is not None:
        progress(f"Selected {len(source.tracks)} unique recommendations.")
    else:
        progress(f"Loaded {len(source.tracks)} unique videos; removed {source.duplicates} duplicate rows.")
    if args.dry_run:
        for index, track in enumerate(source.tracks, 1):
            print(safe_text(f"{index}. {track.video_id}  {track.artist} - {track.title}"))
        progress(f"Estimated write quota: {50 * (len(source.tracks) + (not identifier)):,} units; reads add a small amount.")
        if identifier:
            progress("Videos already in the destination will be checked only during a real import.")
        if args.url is not None:
            progress("Preview complete. Recommendations came from YouTube Music; no Google sign-in, saved song lists or playlist writes occurred.")
        else:
            progress("Dry run complete. No login, network requests, token files or playlists were created.")
        return 0
    if interactive:
        if not confirm_import(args, source, title, identifier):
            progress("Cancelled. No Google sign-in or playlist changes were made.")
            return 0
        if args.client_secrets is None:
            args.client_secrets = choose_client(args.config_dir)
    if args.url is not None:
        args.files = [save_song_list(source, args.config_dir)]
        progress(f"Saved this exact song list for recovery: {args.files[0]}")
    client_path = args.client_secrets or args.config_dir / "client_secret.json"
    try:
        credentials = authenticate(client_path, args.config_dir, args.reauth)
    except ReauthenticationRequired:
        if not interactive or args.reauth:
            raise
        if ask("Your saved login needs authorization again. Open Google sign-in? [Y/n]:").lower() not in {"", "y", "yes"}:
            progress("Cancelled. No playlist changes were made.")
            return 0
        credentials = authenticate(client_path, args.config_dir, True)
    youtube = YouTube(credentials)
    try:
        channel = youtube.channel()
        progress(f"YouTube channel: {channel.get('snippet', {}).get('title', '')} ({channel['id']})")
        existing = set()
        if identifier:
            destination = youtube.existing_playlist(identifier, channel["id"])
            existing = youtube.video_ids(identifier)
            progress(f"Appending to {destination.get('snippet', {}).get('title', identifier)}; existing visibility stays {destination.get('status', {}).get('privacyStatus', 'unchanged')}.")
        pending = [track for track in source.tracks if track.video_id not in existing]
        units = 50 * (len(pending) + (not identifier))
        progress(f"Adding {len(pending)} videos; skipping {len(source.tracks) - len(pending)} already present. Estimated write quota: {units:,} units.")
        if units >= 10000:
            progress("This exceeds a typical project's remaining daily quota (10,000 units/day before reads). You may need to resume after the quota resets.")
        if not identifier:
            try:
                identifier = youtube.create_playlist(title.strip())
            except (ImporterError, KeyboardInterrupt):
                progress("Playlist creation wasn't confirmed. Check your YouTube library before running again; use --playlist if it was created.")
                raise
        print(f"https://www.youtube.com/playlist?list={identifier}", flush=True)
        progress(f"To resume safely using the same CSVs: {resume_command(args, identifier)}")
        added = 0
        recovered = 0
        try:
            for track in pending:
                try:
                    inserted = add_with_recovery(youtube, identifier, track.video_id)
                except ImporterError as exc:
                    raise ImporterError(f"Couldn't confirm video {track.video_id} ({track.title or 'untitled'}): {exc}") from exc
                if inserted:
                    added += 1
                else:
                    recovered += 1
                action = "Added" if inserted else "Already saved"
                progress(f"[{added + recovered}/{len(pending)}] {action} {track.video_id}: {track.title or track.video_id}")
        except (ImporterError, KeyboardInterrupt):
            progress(f"Stopped after {added + recovered} confirmed additions of {len(pending)} planned. The playlist was kept. Resume with the command above; existing videos will be skipped.")
            raise
        progress(f"Done. Added {added} videos; skipped {len(source.tracks) - len(pending) + recovered} already present.")
        return 0
    finally:
        youtube.close()


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        return run(args)
    except InputError as exc:
        progress(f"Input error: {exc}")
        return 2
    except ImporterError as exc:
        progress(f"Error: {exc}")
        return 1
    except OSError:
        progress("Couldn't access a local file or start the local sign-in listener. Check paths, file permissions and available disk space.")
        return 1
    except KeyboardInterrupt:
        progress("Cancelled. No automatic rollback was performed.")
        return 130
