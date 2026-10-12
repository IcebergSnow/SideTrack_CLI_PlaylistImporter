# PlaylistImporter

Import a [SideTrack](https://side-track.vercel.app/) CSV into your YouTube account from your own computer.

```sh
playlist-importer playlist.csv --name "My discoveries"
```

The CLI opens Google sign-in when needed, creates a **private** YouTube playlist, adds the exact video IDs in file order, and prints the playlist URL. It can combine CSVs and resume an interrupted import without adding video IDs already in the destination. Google authorization stays between your computer and Google; SideTrack and Vercel receive no credentials or tokens.

Python 3.11+ and a desktop web browser are required. This is a local CLI, with no website, database, hosted backend, audio downloads, song-title search, or unofficial YouTube API.

## Install

```sh
git clone https://github.com/IcebergSnow/PlaylistImporter.git
cd PlaylistImporter
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
playlist-importer --help
```

On Windows, use `py -3 -m venv .venv`, then `.venv\Scripts\Activate.ps1` in PowerShell. If activation is unavailable, invoke `.venv\Scripts\playlist-importer.exe` directly.

If you already use pipx, you can instead install from GitHub:

```sh
pipx install git+https://github.com/IcebergSnow/PlaylistImporter.git
```

`sidetrack-import` is an alias for the same command. `python -m playlist_importer` also works in the installed environment.

## Configure Google once

Each user supplies their own Google Cloud Desktop OAuth client. No shared client credentials are bundled.

1. Open [Google Cloud Console](https://console.cloud.google.com/) and create or select a project.
2. Under **APIs & Services → Library**, enable **YouTube Data API v3**.
3. Open **Google Auth Platform** and configure the app's branding/consent screen. For personal testing, use **External**, keep the audience in **Testing**, and add the Google account you will use under **Test users**.
4. Under **Data Access**, add `https://www.googleapis.com/auth/youtube`. This is broad YouTube account access; Google does not offer a playlist-write-only scope for these endpoints. Review the consent screen before granting it. The CLI only reads your channel and destination playlist, creates a playlist, and inserts playlist items.
5. Under **Clients**, create an OAuth client with application type **Desktop app**, then download its JSON. A Web application client, API key, or service account is not a substitute. You do not configure a Vercel callback: the CLI uses a temporary `127.0.0.1` callback on your computer.
6. Put that JSON at `~/.playlistimporter/client_secret.json`, or pass its actual location with `--client-secrets` on each run.

For the default location on macOS/Linux:

```sh
mkdir -p "$HOME/.playlistimporter"
chmod 700 "$HOME/.playlistimporter"
cp /path/to/downloaded-client.json "$HOME/.playlistimporter/client_secret.json"
chmod 600 "$HOME/.playlistimporter/client_secret.json"
```

On Windows, the default is `%USERPROFILE%\.playlistimporter\client_secret.json`. Create that directory within your own user profile, copy the downloaded JSON there, and keep the directory private to your Windows account.

Follow [Google's desktop OAuth documentation](https://developers.google.com/identity/protocols/oauth2/native-app). An External app in Testing normally has refresh tokens that expire after seven days; use `--reauth` when needed. Public distribution using a shared OAuth client requires addressing Google's verification requirements. See [Google's token-expiration rules](https://developers.google.com/identity/protocols/oauth2#expiration).

## Import

1. Generate songs in SideTrack and choose the current page or everything through it.
2. Download **CSV**. SideTrack's TXT download only contains artist/title text and is not supported by this importer.
3. Preview the input without sign-in, network access or file writes:

   ```sh
   playlist-importer playlist.csv --dry-run
   ```

4. Import it:

   ```sh
   playlist-importer playlist.csv --name "My discoveries"
   ```

5. Complete Google sign-in in the browser on the same computer. Select the intended YouTube channel, including the correct Brand Account if applicable. Return to the terminal for progress and the resulting link. A YouTube channel is required, not just a Google account.

Combine several exports into one new playlist:

```sh
playlist-importer page-1.csv page-2.csv another-list.csv --name "Combined discoveries"
```

Files are processed in argument order; repeated video IDs are removed while keeping their first occurrence. Titles/artists are only labels. The importer does not merge different IDs that happen to be alternate recordings of the same song.

Use a credentials file stored elsewhere:

```sh
playlist-importer playlist.csv --client-secrets /path/to/client_secret.json
```

The playlist URL goes to stdout; sign-in instructions and progress go to stderr. A nonzero exit code means the import did not complete, even if a playlist URL was printed. Exit codes: `0` success, `1` API/auth/file-system failure, `2` input/usage error, `130` cancelled.

## Resume or append

The CLI prints a resume command immediately after learning the playlist ID:

```sh
playlist-importer playlist.csv --playlist "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID"
```

Use the **same input files** to resume. The tool checks all pages of the existing playlist, skips video IDs already present, and appends the remaining IDs. It only appends to a playlist owned by the signed-in channel. Existing visibility and existing songs are unchanged. To preserve file order, avoid editing that playlist or running another import against it at the same time. Duplicate checking is not an atomic lock against concurrent writers.

Imports stop on the first error. They do not silently skip unavailable videos or delete a partially created playlist. For a permanently unavailable video, remove its row from the CSV and resume. The tool never automatically retries a playlist creation or item insertion after a transport/server error because the write may already have succeeded. Resuming reconciles the server's current playlist contents first. If playlist creation itself timed out before an ID was returned, inspect your YouTube library and pass the playlist URL if one was created.

## Quota and limitations

YouTube charges **50 quota units to create a playlist and 50 per inserted video**. Playlist/channel reads add a small amount. A new project typically receives **10,000 units per day** for these endpoints, resetting at midnight Pacific Time. A new 20-song playlist needs about 1,050 units plus reads; 200 songs need about 10,050 plus reads, so they may require more than one day with the default quota. The CLI reports the write estimate; it cannot see your remaining project quota. Check your project's actual allowance in Google Cloud. Sources: [playlist creation](https://developers.google.com/youtube/v3/docs/playlists/insert), [item insertion](https://developers.google.com/youtube/v3/docs/playlistItems/insert), [quota costs](https://developers.google.com/youtube/v3/determine_quota_cost).

If quota runs out, keep the printed URL and resume with `--playlist` after the reset. Running again without `--playlist` creates another playlist.

- CSV must be UTF-8, with a `url` or `video_id` column. `title` and `artist` are optional. SideTrack's CSV works unchanged, including quoted fields and a UTF-8 BOM. If both ID and URL are supplied, they must agree.
- YouTube watch, Music, short-link, shorts, embed and live video URLs are accepted. Playlist-only song rows and non-YouTube URLs are rejected before sign-in. The importer never fetches URLs from the CSV.
- Input is limited locally to 10 MiB per file and 5,000 unique videos per invocation. Those are tool limits, not promises about YouTube's quota or playlist limits.
- Deleted, private, region-restricted or otherwise unavailable videos may fail to add or play. YouTube Music may not display/play every video that a regular YouTube playlist can contain. The returned link is a YouTube playlist URL.
- A dry run validates input only; it does not check availability, authorization, destination contents or quota.

## Local credentials

The default token cache is `~/.playlistimporter/token.json`. Google OAuth uses the official authentication library, a random loopback port, state validation and PKCE. API/token calls go directly to Google's HTTPS endpoints. No Google password, browser cookies or tokens go to GitHub, SideTrack, Vercel or a transfer service.

Tokens are stored as **unencrypted JSON**. On macOS/Linux, the CLI creates the config directory with mode `700` and token files with mode `600`, rejects an insecure cache, and replaces token files atomically. On Windows, protection depends on your user-profile directory ACLs; Unix permission modes are not an encryption or Windows ACL mechanism. Keep this directory out of shared folders, cloud-synced folders and source control. This protects against other ordinary local users on a correctly configured machine, not malware or someone with access to your account.

Use `--config-dir /path/to/private/directory` for a separate local profile, or set `PLAYLIST_IMPORTER_CONFIG_DIR`. Set `PLAYLIST_IMPORTER_CLIENT_SECRETS` for an alternate client JSON. `.env.example` documents these paths; `.env` files are **not automatically loaded**. A separate config directory can hold a different account; `--reauth` replaces the saved login in the selected directory.

```sh
playlist-importer playlist.csv --reauth
playlist-importer --logout
```

`--logout` deletes only the local token file. To revoke authorization at Google as well, remove the app under [Google account connections](https://myaccount.google.com/connections).

## Development and verification

```sh
python -m pip install -e ".[dev]"
python -m pytest -q
playlist-importer examples/playlist.csv --dry-run
python -m build
```

Tests cover real CSV parsing, ID extraction, duplicate removal, the installed Google library's PKCE URL generation, token permissions/refresh, private playlist request bodies, pagination, partial failures, safe resumption, and CLI exit codes. Test doubles are confined to tests; production always uses Google's API. CI runs the tests, a dry run and packaging on macOS, Windows and Linux.

**Live Google sign-in and playlist writes require your Desktop OAuth client and account consent. They have not been verified during initial development.** For the first live check, import `examples/playlist.csv` as a private two-song playlist, open the printed URL, check its privacy and video order, then rerun with `--playlist` and confirm that zero new videos are added. A dry run or passing unit test is not evidence of a successful Google export.
