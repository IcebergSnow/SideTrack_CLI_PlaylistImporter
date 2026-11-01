# SideTrack Playlist Importer

Create a **private YouTube playlist** from a YouTube song link or a [SideTrack](https://side-track.vercel.app/) CSV download.

The importer runs in **Terminal on macOS/Linux** or **Command Prompt on Windows**. Start from a music link to find similar songs directly, or import an existing CSV. Review the songs, complete Google sign-in if needed, and receive a playlist link. No audio is downloaded.

**First time:** install the tool → set up Google access → choose a song link or CSV → preview → import. **Later:** run `sidetrack` with the [shortcut](#use-a-short-command). The song-link option works without the SideTrack website.

[Install](#1-install-the-tool) · [Google setup](#2-set-up-google-access) · [First import](#3-import-your-first-playlist) · [Fix Google 403](#google-blocked-sign-in-error-403-access_denied) · [Recovery](#automatic-conflict-recovery) · [Troubleshooting](#troubleshooting)

## Before you start

You need:

- **Python 3.11 or newer:** [download Python](https://www.python.org/downloads/). Check with `python3 --version` on macOS/Linux or `py -3 --version` on Windows.
- **Git:** [install Git](https://git-scm.com/downloads). Check with `git --version`.
- **A Google account with a YouTube channel**, an internet connection, and a browser on the computer running the importer.
- **Access to this GitHub repository.** If GitHub requests authentication, sign in through Git with an account that has repository access. Follow [GitHub's Git sign-in instructions](https://docs.github.com/en/get-started/git-basics/caching-your-github-credentials-in-git) if installation reports `Repository not found` or an authentication failure.

Google setup is separate from GitHub access. Each person supplies their own Google Desktop OAuth client; this repository does not bundle a shared client.

<a id="short-setup-two-install-commands"></a>

## 1. Install the tool

Choose **one** operating-system block below. With the prerequisites above ready, installation takes two commands. Run the first, wait for it to finish, then run the second. Continue only if both finish without an error.

This installs into a dedicated folder named `.playlistimporter-venv` inside your home folder. The later commands use its full path, so **you do not need to change folders or activate an environment**. It does not create a source-code checkout or download the example CSVs.

Already installed from a cloned repository or with pipx? Use the [existing-installation instructions](#other-installation-methods) instead of creating a second installation.

### macOS/Linux

On a Mac, press **Command + Space**, type **Terminal**, and press Return. On Linux, open your terminal application.

```sh
python3 -m venv "$HOME/.playlistimporter-venv"
"$HOME/.playlistimporter-venv/bin/python" -m pip install git+https://github.com/IcebergSnow/SideTrack_CLI_PlaylistImporter.git
```

Optional installation check:

```sh
"$HOME/.playlistimporter-venv/bin/playlist-importer" --version
```

### Windows — Command Prompt

Open Start, search for **Command Prompt**, and open it. These commands use Command Prompt syntax; use that application for this walkthrough.

```bat
py -3 -m venv "%USERPROFILE%\.playlistimporter-venv"
"%USERPROFILE%\.playlistimporter-venv\Scripts\python.exe" -m pip install git+https://github.com/IcebergSnow/SideTrack_CLI_PlaylistImporter.git
```

Optional installation check:

```bat
"%USERPROFILE%\.playlistimporter-venv\Scripts\playlist-importer.exe" --version
```

The check should print `PlaylistImporter 0.1.4` or a newer version. Leave `$HOME` or `%USERPROFILE%` unchanged: your shell expands it to your home folder automatically.

## 2. Set up Google access

Do this once in your browser. **OAuth** is Google's process for asking you to grant account access. You enter your Google password on Google's website.

Use **the same Google Cloud project throughout this section**. The project identifies your importer to Google. The importer runs on your computer.

### A. Create a project and enable YouTube

1. Open [Google Cloud Console](https://console.cloud.google.com/) and sign in.
2. Click the project selector near the top, then **New project**.
3. Name it `Playlist Importer`, create it, and select it in the project selector. You can also use an existing project.
4. Open **APIs & Services → Library**. Search for **YouTube Data API v3**, open it, and click **Enable**.

YouTube requires the API to be enabled in the project used by your credentials. [Google's setup guide](https://developers.google.com/youtube/v3/getting-started)

### B. Set up the consent screen

Find **Google Auth Platform** in the console menu or search bar. If it is not configured, click **Get started** and enter:

| Field | What to enter |
| --- | --- |
| App name | `Playlist Importer` |
| User support email | Your email |
| Audience | **External** for a personal Google account |
| Contact email | Your email |

Review the terms and finish setup. Then **add your own account as a test user**:

1. Open **Audience** and keep the publishing status as **Testing**.
2. Find **Test users**, then click **Add users**.
3. Enter the **exact Google email you will choose during YouTube sign-in**.
4. Click **Save** and confirm that the email appears in the list.

Next open **Data Access → Add or remove scopes**. Find or manually add this permission, then update/save:

```text
https://www.googleapis.com/auth/youtube
```

This is a permission string for Google's scope selector, **not a terminal command**. The importer uses this broad YouTube permission to read your channel and playlist, create a playlist, and add videos. [Google's consent-screen instructions](https://developers.google.com/workspace/guides/configure-oauth-consent)

#### Testing mode and sign-in expiry

This walkthrough uses Google's **Testing** mode for the first setup. Only accounts you explicitly add can authorize the app, and this YouTube authorization normally expires after seven days. Add yourself even when you own the project. [Google's audience rules](https://support.google.com/cloud/answer/15549945?hl=en)

You do not need to complete public-app verification for this personal test. Google provides a [personal-use verification exception](https://support.google.com/cloud/answer/13464323?hl=en). Changing the publishing status to **In production** removes the tester-list restriction, but does not automatically verify the app; warnings and user limits can still apply. You can leave it in Testing for this walkthrough.

### C. Download your Desktop app credentials

1. Open **Google Auth Platform → Clients → Create client**.
2. Choose **Desktop app** and name it `SideTrack Importer`.
3. Click **Create**, then download the client's **JSON** file.
4. Open **Downloads** in Finder or File Explorer. Find the downloaded file, usually named `client_secret` followed by a long identifier.
5. Rename it to **`client_secret.json`** and leave it in Downloads. Keep the `.json` extension exactly once.

Select Desktop app for this importer. It does not use a Web application client, API key, or service account. No manual redirect URI is needed. [Google's Desktop client instructions](https://developers.google.com/workspace/guides/create-credentials#desktop-app)

Keep the JSON file private and unchanged. Interactive mode finds it in Downloads automatically.

## 3. Import your first playlist

### A. Choose a song link or CSV

There are two ways to choose the music:

| Menu option | What to provide | What happens |
| --- | --- | --- |
| **1. Start from a song link** | A link to one YouTube or YouTube Music song. | The importer requests similar music directly from YouTube Music, then asks how many songs to include. No website or CSV download is needed. |
| **2. Import a CSV download** | A CSV from [SideTrack](https://side-track.vercel.app/) or another file with YouTube video links. | Choose the file from recent downloads or enter its path. The importer uses its exact video IDs. |

For option 1, copy a link such as:

```text
https://music.youtube.com/watch?v=fJ9rUzIMcZQ
```

For option 2, generate songs on SideTrack, choose **Current page** or **Everything through this page**, and download **CSV**. Keep the original filename, including any `(1)` or `(2)` suffix. TXT does not contain the video IDs the importer needs.

### B. Preview without creating anything

Open Terminal or Command Prompt and run the block for your operating system:

**macOS/Linux:**

```sh
"$HOME/.playlistimporter-venv/bin/sidetrack" --dry-run
```

**Windows — Command Prompt:**

```bat
"%USERPROFILE%\.playlistimporter-venv\Scripts\sidetrack.exe" --dry-run
```

Choose **1** for a song link or **2** for a CSV:

- **Song link:** paste the link. After recommendations succeed, enter the number of songs you want. Press Enter for 20, or all available songs if fewer than 20 were found.
- **CSV:** press Enter for the newest download, type another file's number, or drag/paste a CSV file path. The recent list also recognizes `playlist.csv`.

Check the song list and count. A CSV dry run is entirely offline. A song-link preview contacts YouTube Music for real recommendations. Neither mode signs into your Google account, creates a playlist, or saves a recovery file.

### C. Start the actual import

Run the importer without `--dry-run`:

**macOS/Linux:**

```sh
"$HOME/.playlistimporter-venv/bin/sidetrack"
```

**Windows — Command Prompt:**

```bat
"%USERPROFILE%\.playlistimporter-venv\Scripts\sidetrack.exe"
```

1. Choose **1** for a song link or **2** for a CSV. Type `q` to cancel.
2. For a link, paste it and wait. If recommendations fail, the importer stops with an error before asking for a count or Google access. If they succeed, choose how many songs to include. For a CSV, choose a recent download or enter its path.
3. Enter a playlist name, or press Enter to use a name containing the current date and time.
4. Review the song preview, count, and playlist name.
5. Type **`y`** and press Return/Enter to create a private playlist. Pressing Enter without `y` cancels.

Link mode offers **up to 200 unique recommendations**, depending on what YouTube Music returns after filtering. The starting song, repeated video IDs, known audio/video counterparts, and obvious duplicate recordings are excluded. Choose a count within the displayed range. This is the importer's limit for one recommendation pool, not YouTube Music's maximum.

The importer checks its saved-login folder for `client_secret.json`, then checks Downloads. If neither location contains it, it asks for the file's path. An explicit `--client-secrets` argument or environment variable takes priority.

To type just **`sidetrack`** next time, set up the [short command below](#use-a-short-command). You can still use [explicit file paths and flags](#use-explicit-file-paths) for scripts or combining downloads.

### D. Sign in and wait for completion

1. If Google sign-in opens, choose the **same email you added as a test user** and the intended YouTube channel if asked.
2. When sign-in is requested, review the access and complete it on the **same computer**, within three minutes. If you get `Error 403: access_denied`, follow the [specific fix below](#google-blocked-sign-in-error-403-access_denied).
3. If the browser tells you to return to the terminal, do so. The browser's sign-in confirmation is not the end of the import.
4. Check the displayed YouTube channel. The tool prints a playlist URL and progress such as `[1/20] Added ...`.
5. Wait for **`Done. Added ...`**, then open the playlist URL. If your terminal does not make it clickable, copy it into your browser.

**The playlist URL appears before all the songs have been added.** A URL alone does not mean the import finished. If the importer stops with an error, keep that URL and use its printed resume command.

During automatic recovery, leave the terminal open and let the command finish. It may say it is waiting or checking the playlist. Do not start a second copy of the import while it is still running. Press **Control+C** if you want to stop it.

The new playlist is **private**. Some videos may be available on regular YouTube but unavailable in YouTube Music.

## Using it again

Start the importer with the command from [step 3C](#c-start-the-actual-import), or type `sidetrack` if you set up the shortcut below. Choose a new song link or CSV, follow the prompts, and confirm. There is no need to rename files, reinstall, or repeat Google Cloud setup.

Keep `client_secret.json` in the saved-login folder or Downloads. If a saved Google login can no longer be refreshed, interactive mode offers to open sign-in again; press Enter to accept. You do not need to remember `--reauth` for that flow.

**Each confirmed import creates a new private playlist.** To finish an interrupted playlist or append songs, use `--playlist` as explained in [Resume an interrupted import](#resume-an-interrupted-import).

### Use a short command

If you installed with [pipx](#install-with-pipx), `sidetrack` is already available in your terminal after pipx's path setup.

For the main installation on **macOS with zsh**, add this line to `~/.zshrc` using a text editor:

```sh
alias sidetrack='"$HOME/.playlistimporter-venv/bin/sidetrack"'
```

Open a **new Terminal window**, then run:

```sh
sidetrack
```

On Linux with Bash, put the same alias in `~/.bashrc`. If you installed in a cloned repository, use the path to that checkout's `.venv/bin/sidetrack` in the alias instead. On Windows, use the Command Prompt command from step 3C, or install with pipx to make the short command available.

### Combine multiple CSVs

Pass multiple CSV paths to combine downloads in one playlist. These examples use `page-1.csv` and `page-2.csv`; replace them with the actual filenames. Renaming is not required:

**macOS/Linux:**

```sh
"$HOME/.playlistimporter-venv/bin/playlist-importer" \
  "$HOME/Downloads/page-1.csv" "$HOME/Downloads/page-2.csv" \
  --client-secrets "$HOME/Downloads/client_secret.json" \
  --name "Combined discoveries"
```

**Windows — Command Prompt:**

```bat
"%USERPROFILE%\.playlistimporter-venv\Scripts\playlist-importer.exe" "%USERPROFILE%\Downloads\page-1.csv" "%USERPROFILE%\Downloads\page-2.csv" --client-secrets "%USERPROFILE%\Downloads\client_secret.json" --name "Combined discoveries"
```

Files are processed in argument order. Repeated video IDs are removed, keeping their first occurrence. Different videos of the same song are different IDs; the importer does not match titles. SideTrack's **Everything through this page** option can also put several pages into one CSV before downloading.

### Automatic conflict recovery

If YouTube reports an HTTP 409 conflict while adding a song, the importer waits, checks whether the song was saved, and retries when appropriate. Leave the terminal open. Recovery stops after three rounds per song if the conflict persists, and the tool prints a command to resume the same playlist.

Login problems, exhausted quota, unavailable videos, connection failures, and other server errors require the action shown in the error message before resuming. Automatic recovery does not restart a closed terminal.

Recovery uses additional API quota. Avoid running two imports into the same playlist at once; delayed YouTube updates or simultaneous edits can still cause duplicates.

### Resume an interrupted import

Find the line starting **`To resume safely using the same CSVs:`** in the terminal output. Once the previous command has stopped, copy the command after that label, paste it into Terminal or Command Prompt, and press Return/Enter. After a conflict, wait briefly before doing this.

For song-link imports, the tool saves the exact selected songs to a private local CSV before sign-in. The printed resume command uses that saved list, so it does not generate different recommendations. Keep the file until the import is complete.

The printed command includes the installed Python path, `-m playlist_importer`, absolute file paths, and the existing playlist ID. **Copy it unchanged**, even though it looks different from the original import command. It works from a fresh terminal without activation or changing folders. It checks saved videos and adds only missing IDs.

To choose a song link or CSV interactively and append to an existing playlist, add this option to the start command from step 3C (or to `sidetrack`):

```text
--playlist "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID"
```

Replace the example URL with the playlist URL from the interrupted import. To resume the same songs, choose CSV and enter the original CSV or saved recovery-file path. A new song-link request can produce different results. You can also choose a new link or CSV to append songs to a playlist you own; its visibility stays unchanged. For commands with explicit file paths, replace `--name` with `--playlist` and keep the CSV and client arguments.

If a video is permanently unavailable, remove its row from the CSV and resume. If creation failed before a playlist URL appeared, check your YouTube library before creating another playlist: the server may have created it even though the response was lost.

### Switch accounts, sign in again, or log out

Interactive mode offers sign-in again when the saved login cannot be refreshed. To switch accounts deliberately, add **`--reauth`** to the start command (`sidetrack --reauth` with the shortcut). If a partial playlist exists, add it to the printed resume command instead, so you keep the destination. Choose the account/channel that owns that playlist. Testing-mode authorization normally expires after seven days; you do not need to recreate the Google project or download a new client file just for that. [Google's expiration rules](https://support.google.com/cloud/answer/15549945?hl=en)

To remove the saved login from this computer:

**macOS/Linux:**

```sh
"$HOME/.playlistimporter-venv/bin/playlist-importer" --logout
```

**Windows — Command Prompt:**

```bat
"%USERPROFILE%\.playlistimporter-venv\Scripts\playlist-importer.exe" --logout
```

To revoke Google's authorization as well, remove the app under [Google account connections](https://myaccount.google.com/connections). Logging out does not delete playlists.

## Google blocked sign-in: Error 403 access_denied

If the page says **“has not completed the Google verification process”** and **“can only be accessed by developer-approved testers”**, the signing-in account is not recognized as an approved tester for that OAuth project.

1. Open [Google Cloud Console](https://console.cloud.google.com/) and select the project that issued your `client_secret.json`.
2. Open **Google Auth Platform → Audience → Test users → Add users**.
3. Add the **exact email shown on the blocked page**, click **Save**, and confirm it is listed.
4. Close the blocked browser tab. Return to the terminal and press **Control+C** if the importer is still waiting.
5. Rerun the import command and choose that same email. If a playlist was already created, use the resume command instead.

If the email was already listed, check that you edited the same project as the downloaded client file. Adding it to a different project will not fix this. An **unverified-app warning with a continue option** is different from this access block; confirm the app matches your own project before granting access. [Google's tester and publishing rules](https://support.google.com/cloud/answer/15549945?hl=en)

## Troubleshooting

| What you see | What to do |
| --- | --- |
| `python3`, `py`, or `git` is not recognized | Install the missing prerequisite, reopen your terminal, and check its version. Python must be 3.11 or newer. |
| `Repository not found` / GitHub authentication failure | Check repository access and [authenticate Git](https://docs.github.com/en/get-started/git-basics/caching-your-github-credentials-in-git). This is separate from Google sign-in. |
| `sidetrack` or `playlist-importer` is not found | Use the full executable path shown in this guide. With a cloned-repository install, use [its activation instructions](#other-installation-methods). |
| Full executable path is not found | Check where you installed the tool. The main walkthrough uses `.playlistimporter-venv` in your home folder; a cloned install uses `.venv` inside its project folder. |
| Windows rejects the command / PowerShell blocks activation | Open **Command Prompt** and use the Windows block from this guide. The main installation does not require activation. |
| The song link is rejected | Use a link to one YouTube or YouTube Music song, not a playlist-only URL. |
| Recommendations fail or the song is unsupported | Try another official music video or YouTube Music song link. No playlist or Google sign-in is started on failure. |
| Fewer recommendations than requested are available | Choose a number within the displayed range. Link mode offers at most 200 per request and does not guarantee that many for every song. |
| The CSV is not in the recent list | The list shows the ten newest `sidetrack-*.csv` files or `playlist.csv` in Downloads. Drag/paste another CSV file path into the prompt. |
| The CSV cannot be read | Check the selected path and download CSV again if needed. In commands, quote paths containing spaces. |
| Expected a `url` or `video_id` column | Download **CSV** from SideTrack. Renaming TXT to CSV does not convert it. |
| Couldn't load Google Desktop OAuth credentials | Check the `--client-secrets` path and that the JSON came from a **Desktop app** client. Look for `.json.json` or a browser-added filename suffix. |
| Google blocks access for unapproved testers | Follow the [403 fix](#google-blocked-sign-in-error-403-access_denied). |
| `redirect_uri_mismatch` | Use a **Desktop app** client and its downloaded JSON. A Web application client will not work. |
| Sign-in expires, times out, or uses the wrong channel | Accept the interactive sign-in prompt, or add `--reauth` to the import or resume command. Complete sign-in within three minutes. |
| No YouTube channel was found | Open YouTube with that Google account and create a channel, or use `--reauth` to choose the intended account/channel. |
| API is not enabled | Enable **YouTube Data API v3** in the project that issued the client file. |
| HTTP 409 / conflict | Let automatic recovery run. If it stops after three rounds, wait before using the printed resume command. Older versions need an [update](#update-the-importer). |
| Quota is exhausted | Keep the playlist URL and resume after the daily reset; see the limits below. |
| Import stopped on a video | Check the video ID reported in the error. If it is permanently unavailable, remove its row and resume. |
| A playlist URL appeared but the command is still running | Wait for **`Done. Added ...`**. The URL is printed before insertion finishes. |

If the tool reports that the config directory or token must be private, on macOS/Linux you can fix the default locations with:

```sh
chmod 700 "$HOME/.playlistimporter"
chmod 600 "$HOME/.playlistimporter/token.json"
```

Run the second command only if `token.json` exists. The tool creates it after successful sign-in.

## Update the importer

For the main installation in this guide, run the command for your operating system. Updating keeps your Google client file, saved login, and playlists.

**macOS/Linux:**

```sh
"$HOME/.playlistimporter-venv/bin/python" -m pip install --upgrade git+https://github.com/IcebergSnow/SideTrack_CLI_PlaylistImporter.git
```

**Windows — Command Prompt:**

```bat
"%USERPROFILE%\.playlistimporter-venv\Scripts\python.exe" -m pip install --upgrade git+https://github.com/IcebergSnow/SideTrack_CLI_PlaylistImporter.git
```

Use the `--version` check from step 1 afterward. See the optional reference for updating a Git checkout or pipx installation.

## Daily import limits

Google counts API usage in **quota units**, not songs. Creating a playlist costs 50 units; each video added costs another 50. A typical new project has 10,000 units per day for these operations, with a reset at midnight Pacific Time. Reading your channel and playlist uses a little more. See [Google's quota table](https://developers.google.com/youtube/v3/determine_quota_cost).

| New playlist size | Write quota needed, before reads |
| --- | ---: |
| 20 songs | 1,050 units |
| 60 songs | 3,050 units |
| 200 songs | 10,050 units — more than the typical daily allowance |

These figures exclude recovery attempts and reads. The CLI reports the estimated write quota, but cannot see what remains in your project. Other imports or apps using that project share its allowance. Check the project's actual quota in Google Cloud. Large imports may need to be resumed on another day.

## Privacy and local files

Google sign-in and API requests go directly between your computer and Google. Song-link recommendations also run directly from your computer; the SideTrack website is not contacted. SideTrack, Vercel, and this repository do not receive your Google password or authorization tokens. The tool uses the official YouTube Data API and does not download audio.

The default saved-login folder is:

- **macOS/Linux:** `~/.playlistimporter/`
- **Windows:** `%USERPROFILE%\.playlistimporter\`

`token.json` is created in that folder after sign-in and lets the tool reuse the authorization. The main walkthrough keeps the separate `client_secret.json` in Downloads. Interactive mode checks the saved-login folder first, then Downloads, then asks for a path. Noninteractive commands use the saved-login folder unless you pass `--client-secrets` or its environment variable.

After you confirm a song-link import, its selected tracks are saved under `imports/` inside the saved-login folder. These CSVs contain song titles, artists, and YouTube URLs, not login tokens. They let interrupted imports resume the same selection. They remain until you delete them; keep them while an import is unfinished. Cancelling at the song preview or using `--dry-run` does not save a file.

Recommendations use experimental, unofficial [`ytmusicapi`](https://ytmusicapi.readthedocs.io/en/stable/reference/watch.html). YouTube Music can change, throttle, or reject its requests, and repeating a link may produce different songs. Filtering relies on metadata rather than audio analysis, so alternate recordings may remain. Playlist creation and insertion use the official YouTube Data API.

**The token file is unencrypted.** On macOS/Linux, the tool creates a private folder and restricts token access to your user account. On Windows, protection depends on your user-profile folder permissions. Keep these files out of Git, shared folders, and cloud-synced folders. Someone with access to your account or computer may still be able to read them.

## Optional reference

<a id="other-installation-methods"></a>

<details>
<summary>Other installation methods, settings, and supported CSV formats</summary>

### Install from a Git checkout, or use an existing checkout

This is an alternative to the main two-command installation. Use it if you want the source code and example CSVs on your computer. Do not run both installation methods unless you intend to maintain two copies.

**Already installed in a checkout?** Open a terminal in the folder where you cloned the repository and run only the activation line below.

**New checkout — macOS/Linux:**

```sh
cd ~
git clone https://github.com/IcebergSnow/SideTrack_CLI_PlaylistImporter.git
cd SideTrack_CLI_PlaylistImporter
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

**New checkout — Windows Command Prompt:**

```bat
cd /d "%USERPROFILE%"
git clone https://github.com/IcebergSnow/SideTrack_CLI_PlaylistImporter.git
cd SideTrack_CLI_PlaylistImporter
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install .
```

After activation, run `sidetrack` to start the interactive prompts. The explicit `playlist-importer` commands also work. In each new terminal, return to your checkout and activate `.venv` again. Alternatively, run the executable by its full path inside that checkout's `.venv/bin` directory (`.venv\Scripts` on Windows), without activation.

You can preview the included two-song file from the checkout folder:

```sh
playlist-importer examples/playlist.csv --dry-run
```

### Install with pipx

If you already use pipx:

```sh
pipx install git+https://github.com/IcebergSnow/SideTrack_CLI_PlaylistImporter.git
```

After pipx's path setup, run `sidetrack` to start the interactive prompts without activating an environment. Follow the same Google setup. The pipx installation does not place this repository's example files in your working folder.

### Use explicit file paths

Providing a CSV path runs the original command-line flow without prompts. For example, from an activated source checkout or pipx installation:

```sh
playlist-importer "$HOME/Downloads/sidetrack-fJ9rUzIMcZQ-page-1.csv" --client-secrets "$HOME/Downloads/client_secret.json" --name "My discoveries"
```

Replace the example filename with your actual download. With the main installation, use the full executable path from step 1. Add `--interactive` if you want the preview, confirmation, and sign-in recovery prompts while supplying file paths yourself. For a song link, use `--url` and `--count` instead of CSV paths. For example, preview recommendations without Google sign-in:

```sh
sidetrack --url "https://music.youtube.com/watch?v=fJ9rUzIMcZQ" --count 40 --dry-run
```

In a terminal, a link command still asks for confirmation before a real import. In a script or pipe, supply explicit CSV paths or `--url`; `--url` defaults to 20 songs when `--count` is omitted. A requested count greater than the available recommendations fails before Google sign-in.

### Command options

| Option | Purpose |
| --- | --- |
| `--name "Title"` | Name a new private playlist. Interactive mode asks; scripts use the CSV filename or `SideTrack recommendations` for a link. |
| `--playlist URL_OR_ID` | Append to or resume an existing playlist you own. Use instead of `--name`. |
| `--url SONG_URL` | Generate similar songs from one YouTube or YouTube Music song. Use instead of CSV paths. |
| `--count NUMBER` | Choose 1–200 recommendations for link mode, subject to availability. Interactive mode asks if omitted; scripts default to 20. |
| `--interactive` | Choose a song link or CSV, ask for a name, preview, and confirm. Enabled automatically without CSV paths in a terminal. |
| `--dry-run` | Preview without account sign-in or playlist changes. CSV previews are offline; song links contact YouTube Music. Does not check destination contents or remaining quota. |
| `--client-secrets PATH` | Use a Desktop OAuth JSON file stored somewhere else. |
| `--config-dir PATH` | Store the local login in a different private directory, e.g. for a second account. |
| `--reauth` | Open browser sign-in again. |
| `--logout` | Delete the local token file. Use without CSV arguments. |
| `--help` / `--version` | Show usage or the installed version. |

`sidetrack`, `sidetrack-import`, and `python -m playlist_importer` run the same tool.

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
