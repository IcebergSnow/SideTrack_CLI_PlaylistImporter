# Development

For installation, Google access, and imports, see the [user guide](../README.md).

## Set up and run checks

Use a [source checkout](../README.md#other-installation-methods), open its folder, and activate its virtual environment. Then run:

```sh
python -m pip install -e ".[dev]"
python -m pytest -q
playlist-importer examples/playlist.csv --dry-run
python -m build
```

The automated tests cover CSV parsing, duplicate removal, OAuth setup, token handling, API requests, and recovery from partial failures. CI runs on macOS, Windows, and Linux. Test doubles are confined to tests; real imports use Google's API.

## Conflict recovery

Song insertions that receive HTTP 409 trigger at most three recovery rounds, with waits of 5, 10, then 20 seconds. Each round reads the playlist twice, with two seconds between reads. A saved video is skipped. A video absent from both reads can be inserted again, unless YouTube explicitly reported a duplicate; in that case recovery only reads.

There are at most three extra insertion attempts per song. Failed or malformed playlist reads stop recovery before another write. Persistent conflicts preserve the playlist and print a resume command. Playlist creation, connection failures, and other API errors are not retried automatically.

Tests cover delayed playlist reads, repeated conflicts, explicit duplicate responses, unreadable playlists, permanent failures, and cancellation. These checks reduce duplicate risk but cannot guarantee exactly one insertion when upstream reads are delayed or the playlist is edited concurrently.

## Check a real import

Use a Google account and Desktop OAuth client configured according to the user guide. Real imports modify that account and consume API quota.

1. Follow the [import instructions](../README.md#3-import-your-first-playlist), substituting the checkout's `examples/playlist.csv` for the input file.
2. Wait for the completion message, then open the resulting playlist. Check that it is private and contains the two example videos in CSV order.
3. Rerun with the same CSV and `--playlist` set to that playlist's URL. Confirm that zero new videos are added.

A dry run checks local input only. Passing automated tests does not verify Google authorization, current video availability, or live API behavior.
