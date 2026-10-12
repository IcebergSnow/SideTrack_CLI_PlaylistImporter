# SideTrack Playlist Importer

Turn a [SideTrack](https://side-track.vercel.app/) CSV download into a **private YouTube playlist** on your own account.

The importer runs in **Terminal on macOS/Linux** or **Command Prompt on Windows**. You give it a file of songs, complete Google sign-in in your browser, and receive a playlist link. It adds the exact YouTube video IDs from the file; it does not download audio.

**First time:** install the tool → set up Google access → download a SideTrack CSV → preview → import. **Later:** download another CSV and run the import command again.

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

The check should print `PlaylistImporter 0.1.2` or a newer version. Leave `$HOME` or `%USERPROFILE%` unchanged: your shell expands it to your home folder automatically.

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

Keep the JSON file private and unchanged. The import commands below read it from Downloads using `--client-secrets`.

## 3. Import your first playlist

### A. Download the songs

1. Open [SideTrack](https://side-track.vercel.app/).
2. Paste a YouTube music link and click **Generate**.
3. Choose **Current page** for a small first import, or **Everything through this page** to combine the pages you have reached.
4. Click **CSV**. TXT downloads do not contain the video IDs the importer needs.
5. Find the downloaded CSV in Downloads and rename it **`playlist.csv`**. Leave it in Downloads.

On a Mac, select a file in Finder and press Return to rename it. On Windows, use the file's Rename action. Check the full filename so you do not end up with `.json.json` or `.csv.csv`.

You should now have two different files:

| File in Downloads | Where it came from | Purpose |
| --- | --- | --- |
| `client_secret.json` | Google Cloud | Identifies your Google OAuth client; keep it for future imports. |
| `playlist.csv` | SideTrack | Contains this playlist's songs; use a new CSV for the next import. |

If your browser saved either file somewhere else, move it to Downloads for this walkthrough or change the corresponding path in the commands.

### B. Preview without creating anything

Return to Terminal or Command Prompt. Copy the block for your operating system and press Return/Enter.

**macOS/Linux:**

```sh
"$HOME/.playlistimporter-venv/bin/playlist-importer" "$HOME/Downloads/playlist.csv" --dry-run
```

**Windows — Command Prompt:**

```bat
"%USERPROFILE%\.playlistimporter-venv\Scripts\playlist-importer.exe" "%USERPROFILE%\Downloads\playlist.csv" --dry-run
```

You should see your song list, a count such as `Loaded 20 unique videos`, and `Dry run complete`. Check the count before continuing. A dry run reads your CSV locally; it does not sign in, contact Google, or create a playlist, so you can also try it before doing the Google setup.

### C. Start the actual import

Copy the **entire block**, then press Return/Enter. The backslashes in the macOS/Linux block make it one command spread over several lines. Keep the quotes; they allow paths and playlist names with spaces.

**macOS/Linux:**

```sh
"$HOME/.playlistimporter-venv/bin/playlist-importer" \
  "$HOME/Downloads/playlist.csv" \
  --client-secrets "$HOME/Downloads/client_secret.json" \
  --name "My SideTrack playlist"
```

**Windows — Command Prompt:**

```bat
"%USERPROFILE%\.playlistimporter-venv\Scripts\playlist-importer.exe" "%USERPROFILE%\Downloads\playlist.csv" --client-secrets "%USERPROFILE%\Downloads\client_secret.json" --name "My SideTrack playlist"
```

| Command part | What it does |
| --- | --- |
| Full path ending in `playlist-importer` or `playlist-importer.exe` | Starts the installed tool. |
| Path ending in `playlist.csv` | Chooses the songs. |
| `--client-secrets` and its path | Selects the Google configuration file. Keep this argument on future imports with this setup. |
| `--name "My SideTrack playlist"` | Names the new private playlist. Change the text inside the quotes if you like. |

### D. Sign in and wait for completion

1. Your browser opens Google sign-in. Choose the **same email you added as a test user** and the intended YouTube channel if asked.
2. Review the requested access and complete sign-in on the **same computer**, within three minutes. If you get `Error 403: access_denied`, follow the [specific fix below](#google-blocked-sign-in-error-403-access_denied).
3. When the browser tells you to return to the terminal, do so. The browser's sign-in confirmation is not the end of the import.
4. Check the displayed YouTube channel. The tool prints a playlist URL and progress such as `[1/20] Added ...`.
5. Wait for **`Done. Added ...`**, then open the playlist URL. If your terminal does not make it clickable, copy it into your browser.

**The playlist URL appears before all the songs have been added.** A URL alone does not mean the import finished. If the importer stops with an error, keep that URL and use its printed resume command.

During automatic recovery, leave the terminal open and let the command finish. It may say it is waiting or checking the playlist. Do not start a second copy of the import while it is still running. Press **Control+C** if you want to stop it.

The new playlist is **private**. Some videos may be available on regular YouTube but unavailable in YouTube Music.

## Using it again

Download the next CSV, preview it if you like, and rerun the command from [step 3C](#c-start-the-actual-import). Replace the CSV filename and playlist name as needed. You can use a fresh terminal from any folder; no reinstall or activation is required with the main installation above.

Keep `client_secret.json` for future imports. If you move it to another private location, update the `--client-secrets` path. The tool saves your Google login locally, but still needs that client file. It will request sign-in again when necessary; an expired saved login may require `--reauth`.

**Each run with `--name` creates a new playlist.** To finish an interrupted playlist or append more songs to it, use `--playlist` instead, as described below.

### Combine multiple CSVs

Save two downloads in Downloads as `page-1.csv` and `page-2.csv`. Pass both file paths in one import command:

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

The printed command includes the installed Python path, `-m playlist_importer`, absolute file paths, and the existing playlist ID. **Copy it unchanged**, even though it looks different from the original import command. It works from a fresh terminal without activation or changing folders. It checks saved videos and adds only missing IDs.

To construct one yourself, take the import command from step 3C and replace `--name "My SideTrack playlist"` with:

```text
--playlist "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID"
```

Replace the example URL with your actual playlist URL. Keep the CSV and `--client-secrets` arguments. You can also use a new CSV with `--playlist` to append songs to a playlist you own; its visibility stays unchanged.

If a video is permanently unavailable, remove its row from the CSV and resume. If creation failed before a playlist URL appeared, check your YouTube library before creating another playlist: the server may have created it even though the response was lost.

### Switch accounts, sign in again, or log out

Add **`--reauth`** to your full import command to open Google sign-in again. If a partial playlist exists, add it to the printed resume command instead, so you keep the destination. Choose the account/channel that owns that playlist. Testing-mode authorization normally expires after seven days; you do not need to recreate the Google project or download a new client file just for that. [Google's expiration rules](https://support.google.com/cloud/answer/15549945?hl=en)

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
| `playlist-importer` is not found | Use the full executable path shown in this guide. With a cloned-repository install, use [its activation instructions](#other-installation-methods). |
| Full executable path is not found | Check where you installed the tool. The main walkthrough uses `.playlistimporter-venv` in your home folder; a cloned install uses `.venv` inside its project folder. |
| Windows rejects the command / PowerShell blocks activation | Open **Command Prompt** and use the Windows block from this guide. The main installation does not require activation. |
| The CSV cannot be read | Check that it is in Downloads with the exact filename from the command. Quote paths containing spaces. |
| Expected a `url` or `video_id` column | Download **CSV** from SideTrack. Renaming TXT to CSV does not convert it. |
| Couldn't load Google Desktop OAuth credentials | Check the `--client-secrets` path and that the JSON came from a **Desktop app** client. Look for `.json.json` or a browser-added filename suffix. |
| Google blocks access for unapproved testers | Follow the [403 fix](#google-blocked-sign-in-error-403-access_denied). |
| `redirect_uri_mismatch` | Use a **Desktop app** client and its downloaded JSON. A Web application client will not work. |
| Sign-in expires, times out, or uses the wrong channel | Add `--reauth` to the import or resume command and complete sign-in within three minutes. |
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

Google sign-in and API requests go directly between your computer and Google. SideTrack, Vercel, and this repository do not receive your Google password or authorization tokens. The tool uses the official YouTube Data API and does not download audio.

The default saved-login folder is:

- **macOS/Linux:** `~/.playlistimporter/`
- **Windows:** `%USERPROFILE%\.playlistimporter\`

`token.json` is created in that folder after sign-in and lets the tool reuse the authorization. The main walkthrough keeps the separate `client_secret.json` in Downloads and passes its path explicitly. If you omit `--client-secrets` and its environment variable, the tool instead looks for `client_secret.json` inside the saved-login folder.

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

After activation, replace the main guide's full executable path with `playlist-importer`. Keep the same Downloads paths and `--client-secrets` argument. In each new terminal, return to your checkout and activate `.venv` again. Alternatively, run the executable by its full path inside that checkout's `.venv/bin` directory (`.venv\Scripts` on Windows), without activation.

You can preview the included two-song file from the checkout folder:

```sh
playlist-importer examples/playlist.csv --dry-run
```

### Install with pipx

If you already use pipx:

```sh
pipx install git+https://github.com/IcebergSnow/SideTrack_CLI_PlaylistImporter.git
```

This installs the command without manually activating a project environment. Use `playlist-importer` in place of the main guide's full executable path, keeping the CSV and `--client-secrets` paths. Follow the same Google setup. The pipx installation does not place this repository's example files in your working folder.

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
