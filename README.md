# SideTrack Playlist Importer

Turn a [SideTrack](https://side-track.vercel.app/) CSV download into a **private YouTube playlist** from your own computer.

This is a command-line tool: you run it in Terminal or Command Prompt. It opens Google sign-in when needed, adds the exact YouTube videos from your file in order, and gives you a playlist link. It automatically recovers from temporary playlist conflicts while running. You can also combine several CSVs or finish an interrupted import.

**First-time setup requires your own Google Cloud project and Desktop OAuth credentials.** The steps below explain how to create them. After setup, importing looks like this:

```sh
playlist-importer playlist.csv --name "My discoveries"
```

[Short setup](#short-setup-two-install-commands) · [Step-by-step install](#1-install-the-tool) · [Set up Google](#2-set-up-google-access) · [First import](#3-import-your-first-playlist) · [Use it again](#using-it-again) · [Troubleshooting](#troubleshooting)

> **Verification status:** A real-account Google sign-in, private playlist creation, and 40-video import have been verified, including recovery from HTTP 409 conflicts. The final playlist contained all 40 unique videos in CSV order.

## Short setup: two install commands

With **Python 3.11+ and Git already installed**, you can install in two commands and import in one. This route skips manually cloning a project folder and activating its environment. The longer walkthrough below is an alternative; you do not need to do both.

**Repository access:** This repository is currently private. Your Git client must already be signed in with a GitHub account that has access. A `Repository not found` error can mean you are not signed in or have not been granted access.

### macOS/Linux

Run these two commands once in Terminal:

```sh
python3 -m venv "$HOME/.playlistimporter-venv"
"$HOME/.playlistimporter-venv/bin/python" -m pip install git+https://github.com/IcebergSnow/SideTrack_CLI_PlaylistImporter.git
```

Complete [Google setup steps A–C](#a-create-a-project-and-enable-youtube) once. Leave the downloaded Desktop client JSON in Downloads, renamed `client_secret.json`. Download a SideTrack **CSV** to Downloads and rename it `playlist.csv`. Then import:

```sh
"$HOME/.playlistimporter-venv/bin/playlist-importer" "$HOME/Downloads/playlist.csv" --client-secrets "$HOME/Downloads/client_secret.json" --name "My discoveries"
```

### Windows — Command Prompt

Run these two commands once in **Command Prompt**:

```bat
py -3 -m venv "%USERPROFILE%\.playlistimporter-venv"
"%USERPROFILE%\.playlistimporter-venv\Scripts\python.exe" -m pip install git+https://github.com/IcebergSnow/SideTrack_CLI_PlaylistImporter.git
```

Complete [Google setup steps A–C](#a-create-a-project-and-enable-youtube) once. Leave the downloaded Desktop client JSON in Downloads, renamed `client_secret.json`. Download a SideTrack **CSV** to Downloads and rename it `playlist.csv`. Then import:

```bat
"%USERPROFILE%\.playlistimporter-venv\Scripts\playlist-importer.exe" "%USERPROFILE%\Downloads\playlist.csv" --client-secrets "%USERPROFILE%\Downloads\client_secret.json" --name "My discoveries"
```

**Next time, run only the import command**, changing the CSV path and playlist name as needed. It works in a fresh terminal without changing folders or activating anything. Keep `--client-secrets` on future imports: the tool reads that file each time but does not copy it. If you move it to another private location, update the path. This flag replaces the credential-copy commands in step 2D.

Add `--dry-run` to the import command for an offline preview before signing in. For a real import, finish sign-in in the browser and wait for **`Done. Added ...`** in the terminal before treating the playlist as complete. Google setup is still required; a shorter install does not remove it.

The later examples use the short command name `playlist-importer`. With this installation, replace that name with the full executable path shown above; keep your CSV paths and `--client-secrets` where applicable. The resume command printed by version 0.1.1 and newer already includes the full Python path and absolute file paths, so you can copy it unchanged into a fresh terminal. No project folder or example CSV is created by this installation.

## Before you start

You need:

- **Python 3.11 or newer:** [download Python](https://www.python.org/downloads/). Check with `python3 --version` on macOS/Linux or `py -3 --version` on Windows.
- **Git:** [install Git](https://git-scm.com/downloads) if `git --version` is not recognized.
- **A Google account with a YouTube channel**, an internet connection, and a web browser on the computer running the tool. An account that has never created a YouTube channel may need to do that on YouTube first.
- **A CSV export from SideTrack.** Choose **CSV**, not TXT. CSV contains the video links this tool needs; SideTrack TXT files only contain song names.

Start with one page of 20 songs. Large imports can run into Google's daily API limit; [see the examples below](#daily-import-limits).

## 1. Install the tool

Choose the instructions for your operating system. These commands download the project into your home folder and install it in a separate Python environment called `.venv`.

Already cloned the repository? Open its existing folder and start at the `venv` command instead.

### macOS or Linux — Terminal

```sh
cd ~
git clone https://github.com/IcebergSnow/SideTrack_CLI_PlaylistImporter.git
cd SideTrack_CLI_PlaylistImporter
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

### Windows — Command Prompt

Open **Command Prompt** from the Start menu. Use these commands there; the activation command is different in PowerShell.

```bat
cd /d "%USERPROFILE%"
git clone https://github.com/IcebergSnow/SideTrack_CLI_PlaylistImporter.git
cd SideTrack_CLI_PlaylistImporter
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install .
```

Keep this terminal open for the remaining steps. An activated environment usually shows `(.venv)` at the start of the prompt.

### Check that installation worked

Run the included two-song example in **dry-run** mode:

```sh
playlist-importer examples/playlist.csv --dry-run
```

You should see `Loaded 2 unique videos`, the two video IDs, and `Dry run complete`. This checks the file locally. It does **not** sign in, contact Google, or create a playlist, so you can try it before setting up Google access.

## 2. Set up Google access

Google requires permission before a program can create playlists in your account. **OAuth** is the browser sign-in process that grants that permission. You enter your Google password on Google's website, not in this tool.

Use the same Google Cloud project for all the steps in this section. Each person using the importer needs their own setup; this repository does not bundle a shared Google client.

### A. Create a project and enable YouTube

1. Open [Google Cloud Console](https://console.cloud.google.com/) and sign in.
2. Use the project selector at the top to create a project, such as **SideTrack Personal**, or select an existing project.
3. Open **APIs & Services → Library**, search for **YouTube Data API v3**, and click **Enable**.

### B. Set up the consent screen

Open **Google Auth Platform**. If it is not configured, click **Get started**. Fill in the setup screens using these settings:

| Setting | What to use |
| --- | --- |
| App name | `SideTrack Playlist Importer` |
| User support email | Your email address |
| Audience | **External** for a personal Google account |
| Contact email | Your email address |

Review Google's terms and finish setup. In **Audience**, keep the app in **Testing** and add the Google account you will import into under **Test users**.

In **Data Access → Add or remove scopes**, add this permission, then save:

```text
https://www.googleapis.com/auth/youtube
```

This is a permission string to paste into Google's scope selector, not a terminal command. Google describes it as broad YouTube account access. The importer uses it to read your channel/playlist, create a playlist, and add videos. [Google's consent-screen guide](https://developers.google.com/workspace/guides/configure-oauth-consent) covers these settings.

### C. Download your Desktop app credentials

1. Open **Google Auth Platform → Clients → Create client**.
2. Choose **Desktop app** and give it a name, such as **PlaylistImporter desktop**.
3. Create the client and download its JSON file.
4. In your Downloads folder, rename the downloaded file to **`client_secret.json`**. Keep the `.json` extension exactly once.

Choose **Desktop app**, not Web application. You do not need a Vercel URL or a manually configured redirect URI. The tool receives the sign-in response through a temporary local address on your computer. See [Google's Desktop client instructions](https://developers.google.com/workspace/guides/create-credentials#desktop-app).

### D. Save the credentials where the tool expects them

These commands assume you renamed the file and left it in **Downloads**. If you saved it elsewhere, change the source path before running the copy command.

**macOS/Linux:**

```sh
mkdir -p "$HOME/.playlistimporter"
chmod 700 "$HOME/.playlistimporter"
cp "$HOME/Downloads/client_secret.json" "$HOME/.playlistimporter/client_secret.json"
chmod 600 "$HOME/.playlistimporter/client_secret.json"
```

**Windows Command Prompt:**

```bat
mkdir "%USERPROFILE%\.playlistimporter"
copy "%USERPROFILE%\Downloads\client_secret.json" "%USERPROFILE%\.playlistimporter\client_secret.json"
```

If Windows says the directory already exists, continue with the copy command. Keep this folder within your own user profile and private to your account.

The two files you will use have different purposes:

| File | Where it comes from | What it does |
| --- | --- | --- |
| `client_secret.json` | Google Cloud | Identifies your Desktop OAuth client; keep it locally for future imports. |
| `playlist.csv` | SideTrack | Lists the songs to import; you can download a new one whenever you like. |

## 3. Import your first playlist

1. Open [SideTrack](https://side-track.vercel.app/), generate recommendations, and choose **Current page** or **Everything through this page**.
2. Click **CSV** and find the downloaded file.
3. For this walkthrough, copy it into the project folder and rename it **`playlist.csv`**. This avoids having to type a long Downloads path.
4. Preview it in your still-open terminal:

   ```sh
   playlist-importer playlist.csv --dry-run
   ```

5. If the song count looks right, start the import:

   ```sh
   playlist-importer playlist.csv --name "My discoveries"
   ```

6. Complete Google sign-in in the browser on the **same computer**. Choose the intended Google account and YouTube channel, and review the requested permission. The tool waits up to three minutes for this step.
7. Return to the terminal. It shows the selected channel, a playlist link, and progress such as `[1/20] Added ...`.
8. Wait for **`Done. Added ...`**, then open the playlist link and check the songs and privacy setting.

**Keep the terminal open during automatic recovery.** If YouTube returns a temporary playlist conflict, the importer pauses, checks which videos were saved, and continues when it can. No extra flag is needed.

**A playlist link appears before all songs are added.** If you see an error instead of `Done`, keep the link and follow [Resume an interrupted import](#resume-an-interrupted-import). The partial playlist is kept.

The tool creates a **private YouTube playlist**. Some videos may not appear or play in YouTube Music even when they work on regular YouTube.

## Using it again

You do not need to reinstall or create a Google client for each playlist. Open the project folder and activate its environment whenever you open a new terminal.

**macOS/Linux**, if you installed in your home folder as above:

```sh
cd ~/SideTrack_CLI_PlaylistImporter
source .venv/bin/activate
```

**Windows Command Prompt:**

```bat
cd /d "%USERPROFILE%\SideTrack_CLI_PlaylistImporter"
.venv\Scripts\activate.bat
```

Use your actual project path if you installed somewhere else. Then run an import command with your latest CSV. Quote any file path that contains spaces:

```sh
playlist-importer "my playlist.csv" --name "Weekend music"
```

### Combine multiple CSVs

```sh
playlist-importer page-1.csv page-2.csv another-list.csv --name "Combined discoveries"
```

The tool processes files in the order you list them and keeps the first occurrence of each video ID. Different videos of the same song are treated as different IDs; there is no title matching.

### Automatic conflict recovery

Version **0.1.2** handles HTTP 409 conflicts during song insertion automatically. It waits **5, 10, then 20 seconds** across up to three recovery rounds per song. Before repeating an insertion, it reads the playlist twice, with two seconds between those checks. If the song is already there, it continues without adding it again. If YouTube explicitly reports a duplicate, it only checks for the saved song; it does not repeat that insertion.

There are at most **three extra insertion attempts per song**. Recovery stops if the conflict persists or the playlist cannot be read reliably, leaving the playlist and a manual resume command. Login problems, exhausted quota, unavailable videos, connection failures, and other server errors still require manual recovery. Playlist creation is never retried automatically.

This works while the command is running; it does not restart a closed terminal or a stopped process. Press **Control+C** to cancel. Recovery reads and repeated insertions can use additional API quota beyond the initial estimate. Checks reduce duplicate risk, but delayed YouTube updates or simultaneous edits cannot provide an exact-once guarantee.

### Resume an interrupted import

Copy the **resume command printed by the tool**. It supplies the installed Python path, original files, credentials path, and destination playlist, so it works from a fresh terminal without activation or changing folders. Wait briefly before resuming after a conflict: a just-added video may take time to appear in playlist reads.

If you are using an activated environment, the equivalent command looks like this; replace `YOUR_PLAYLIST_ID` with the ID from your real link:

```sh
playlist-importer playlist.csv --playlist "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID"
```

Use the same CSV files to finish the import. The tool checks what is already in the playlist and adds only missing video IDs. You can also use `--playlist` with a new CSV to append more songs to a playlist you own. Its existing visibility stays unchanged.

**Running without `--playlist` creates another playlist.** Avoid importing to or editing the same destination in two places at once; the duplicate check does not lock the playlist against other writers.

If a video is permanently unavailable, remove its row from the CSV and resume. If playlist creation itself failed before a link was printed, check your YouTube library first: the playlist may have been created before the connection failed.

### Switch accounts or sign in again

```sh
playlist-importer playlist.csv --reauth
```

This opens Google sign-in again and replaces the saved login. An External Google app in Testing normally needs renewed authorization after seven days because of [Google's token-expiration rules](https://developers.google.com/identity/protocols/oauth2#expiration).

To remove the saved login from this computer:

```sh
playlist-importer --logout
```

To revoke Google's authorization as well, remove the app under [Google account connections](https://myaccount.google.com/connections). Logging out does not delete playlists.

## Troubleshooting

| What you see | What to do |
| --- | --- |
| `python3`, `py`, or `git` is not recognized | Install the missing prerequisite, reopen your terminal, and check its version. Python must be 3.11 or newer. |
| `playlist-importer` is not found | Open the project folder and activate `.venv` as shown in **Using it again**. If needed, run `python -m pip install .` in that environment. |
| PowerShell blocks `Activate.ps1` | Use **Command Prompt** with the Windows instructions above. Or, from the project folder in PowerShell, replace `playlist-importer` with `.\.venv\Scripts\playlist-importer.exe`; activation is not required for that form. |
| The CSV cannot be read | Check the filename and current folder. Use the full file path in quotes, or copy the CSV into the project folder. |
| Expected a `url` or `video_id` column | Download **CSV** from SideTrack. Renaming a TXT file to `.csv` does not convert its contents. |
| Couldn't load Google Desktop OAuth credentials | Check that `client_secret.json` is in the location from step 2D and came from a **Desktop app** client. Check for an accidental `.json.json` extension. |
| Google says access is denied or the user is not allowed | Add the exact Google account under your project's **Audience → Test users**, then try again. A managed work/school account may have additional restrictions. |
| Google shows an unverified-app notice | Personal test apps may show this. Check that the app name matches the Cloud project you created and that you are a test user. Public distribution has separate [verification requirements](https://developers.google.com/identity/protocols/oauth2/native-app#identify-access-scopes). |
| `redirect_uri_mismatch` | Check that the client type is **Desktop app**, download its JSON, and try again. A Web application client will not work with this tool. |
| Sign-in expires, times out, or selects the wrong channel | Use `--reauth` and finish browser sign-in on the same computer within three minutes. If a partial playlist already exists, also include `--playlist` to resume it. |
| No YouTube channel was found | Open YouTube with that Google account and create a channel, or use `--reauth` to select the correct account/channel. |
| API is not enabled | Enable **YouTube Data API v3** in the same Google Cloud project that issued your client JSON. |
| HTTP 409 / conflict | Leave the terminal open while automatic recovery checks the playlist. If it stops after three rounds, wait before running the printed resume command. |
| Quota is exhausted | Keep the playlist URL and resume after the daily reset; see the limits below. |
| Import stopped on a video | The error identifies its video ID. Check whether it still exists and is accessible. Remove a permanently unavailable row, then resume into the existing playlist. |

On macOS/Linux, a `chmod 700` or `chmod 600` error means the local credential folder or token file is accessible to other users. For the default location, apply the appropriate command:

```sh
chmod 700 "$HOME/.playlistimporter"
chmod 600 "$HOME/.playlistimporter/token.json"
```

Run the second command only if `token.json` exists; it is created after a successful login.

## Daily import limits

Google counts API usage in **quota units**, not songs. Creating a playlist costs 50 units; each video added costs another 50. A typical new project has 10,000 units per day for these operations, with a reset at midnight Pacific Time. Reading your channel and playlist uses a little more. See [Google's quota table](https://developers.google.com/youtube/v3/determine_quota_cost).

| New playlist size | Write quota needed, before reads |
| --- | ---: |
| 20 songs | 1,050 units |
| 60 songs | 3,050 units |
| 200 songs | 10,050 units — more than the typical daily allowance |

The CLI reports the estimated write quota, but cannot see what remains in your project. Other imports or apps using that project share its allowance. Check the project's actual quota in Google Cloud. Large imports may need to be resumed on another day.

## Privacy and local files

Google sign-in and API requests go directly between your computer and Google. SideTrack, Vercel, and this repository do not receive your Google password or authorization tokens. The tool uses the official YouTube Data API and does not download audio.

The default credential folder is:

- **macOS/Linux:** `~/.playlistimporter/`
- **Windows:** `%USERPROFILE%\.playlistimporter\`

`client_secret.json` holds the Google client configuration. `token.json` is created after sign-in and lets the tool reuse that authorization.

**The token file is unencrypted.** On macOS/Linux, the tool creates a private folder and restricts token access to your user account. On Windows, protection depends on your user-profile folder permissions. Keep these files out of Git, shared folders, and cloud-synced folders. Someone with access to your account or computer may still be able to read them.

## Optional reference

<details>
<summary>Other installation methods, settings, and supported CSV formats</summary>

### Install with pipx

If you already use pipx:

```sh
pipx install git+https://github.com/IcebergSnow/SideTrack_CLI_PlaylistImporter.git
```

This installs the command without manually activating a project environment. Follow the Google setup steps above and provide the path to your CSV. The pipx installation does not place this repository's example files in your working folder.

### Command options

| Option | Purpose |
| --- | --- |
| `--name "Title"` | Name a new private playlist. Defaults to the first CSV's filename without its extension. |
| `--playlist URL_OR_ID` | Append to or resume an existing playlist you own. Use instead of `--name`. |
| `--dry-run` | Validate input locally without Google access or changes. Does not check video availability, destination contents, or quota. |
| `--client-secrets PATH` | Use a Desktop OAuth JSON file stored somewhere else. |
| `--config-dir PATH` | Store the local login in a different private directory, e.g. for a second account. |
| `--reauth` | Open browser sign-in again. |
| `--logout` | Delete the local token file. Use without CSV arguments. |
| `--help` / `--version` | Show usage or the installed version. |

`sidetrack-import` and `python -m playlist_importer` run the same tool.

You can set `PLAYLIST_IMPORTER_CLIENT_SECRETS` and `PLAYLIST_IMPORTER_CONFIG_DIR` instead of passing the matching flags. [`.env.example`](.env.example) documents them; `.env` files are **not automatically loaded**. With a custom config directory, either put `client_secret.json` there or pass `--client-secrets` as well.

### CSV format

Files must be UTF-8 CSVs with a `url` or `video_id` column. `title` and `artist` are optional. If both URL and ID are present, they must identify the same video. SideTrack's CSV works unchanged, including quoted fields and a UTF-8 BOM.

```csv
title,artist,url
Bohemian Rhapsody,Queen,https://www.youtube.com/watch?v=fJ9rUzIMcZQ
Hello,Adele,https://www.youtube.com/watch?v=YQHsXMglC9A
```

YouTube watch, Music, short-link, shorts, embed and live video URLs are accepted. Playlist-only rows and non-YouTube URLs are rejected before sign-in. The importer extracts video IDs; it does not fetch the URLs in the CSV. Local input limits are 10 MiB per file and 5,000 unique videos per run. YouTube's own availability and quota limits still apply.

### Scripting and updates

The playlist URL goes to stdout. Sign-in instructions and progress go to stderr. Exit codes are `0` for success, `1` for API/auth/file-system errors, `2` for invalid input or usage, and `130` for cancellation. A printed playlist URL alone does not mean the import completed.

Song insertion conflicts use the bounded automatic recovery described above. Other errors, or exhausted recovery attempts, stop the import and preserve a resume command. Connection failures and other server errors are not automatically retried because Google may already have completed the write. Manual resuming checks the destination before adding more videos.

To update a Git installation, open the project folder, activate `.venv`, then run:

```sh
git pull --ff-only
python -m pip install .
```

For pipx, use `pipx upgrade playlistimporter`.

</details>

<details>
<summary>Development and verification</summary>

From the repository folder in an activated environment:

```sh
python -m pip install -e ".[dev]"
python -m pytest -q
playlist-importer examples/playlist.csv --dry-run
python -m build
```

The automated tests cover CSV parsing, duplicate removal, OAuth setup, token handling, API requests, and recovery from partial failures. CI runs on macOS, Windows, and Linux. Test doubles are confined to tests; the running tool always uses Google's API for real imports.

**Live verification on October 12, 2026:** Google sign-in and private playlist creation succeeded with a real account. Two HTTP 409 interruptions were recovered manually by checking the saved playlist and resuming, before automatic recovery was added. An API read confirmed exactly 40 unique videos in the same order as the input CSV, with private visibility. This verifies that flow for one account; it does not guarantee every video or account will work.

Automatic recovery is covered by tests for delayed playlist reads, repeated conflicts, duplicate responses, unreadable playlists, permanent failures, and cancellation. A live HTTP 409 has not yet been observed with the new automatic recovery version.

For your own small first check, import `examples/playlist.csv`, open the resulting private two-song playlist, and check its order. Rerun with `--playlist` and confirm that zero new videos are added. A dry run or passing unit test alone does not prove that Google authorization or export has succeeded.

</details>
