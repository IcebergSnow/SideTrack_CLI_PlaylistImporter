"""Browser-based desktop OAuth with a private, local token cache."""

import json
import os
import stat
import tempfile
import sys
import webbrowser
from contextlib import redirect_stdout
from functools import partial
from pathlib import Path

import requests
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from oauthlib.oauth2 import OAuth2Error

from .errors import ImporterError

SCOPES = ["https://www.googleapis.com/auth/youtube"]
TOKEN_URI = "https://oauth2.googleapis.com/token"
AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"


def private_directory(directory: Path) -> None:
    if directory.is_symlink():
        raise ImporterError("The config directory must not be a symlink. Choose a private directory with --config-dir.")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name == "posix":
        info = directory.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ImporterError("The config directory must be owned by you and private (chmod 700). Choose a dedicated --config-dir.")


def read_token(path: Path) -> dict | None:
    try:
        # O_NOFOLLOW avoids accepting a symlink in the private cache directory.
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except FileNotFoundError:
        return None
    with os.fdopen(fd, encoding="utf-8") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
            raise ImporterError("Invalid local token file. Run --logout, then sign in again.")
        if os.name == "posix" and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
            raise ImporterError("The token file must be owned by you and private (chmod 600).")
        try:
            data = json.load(stream)
        except (ValueError, UnicodeError) as exc:
            raise ImporterError("The local token file is invalid. Run --logout, then sign in again.") from exc
        if not isinstance(data, dict):
            raise ImporterError("The local token file is invalid. Run --logout, then sign in again.")
        return data


def save_token(path: Path, credentials: Credentials) -> None:
    # Atomic replacement prevents a crash from truncating the existing cache.
    descriptor, temporary = tempfile.mkstemp(prefix=".token-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(credentials.to_json())
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def client_config(path: Path) -> dict:
    try:
        if path.stat().st_size > 65536:
            raise ValueError
        document = json.loads(path.read_text(encoding="utf-8"))
        installed = document.get("installed", {})
        if not isinstance(installed.get("client_id"), str) or not installed["client_id"].endswith(".apps.googleusercontent.com"):
            raise ValueError
        if not isinstance(installed.get("client_secret"), str) or not installed["client_secret"]:
            raise ValueError
        if installed.get("auth_uri") not in {AUTH_URI, "https://accounts.google.com/o/oauth2/auth"}:
            raise ValueError
        if installed.get("token_uri") != TOKEN_URI:
            raise ValueError
        # Never take authentication or token endpoints from arbitrary input.
        return {"installed": {
            "client_id": installed["client_id"], "client_secret": installed["client_secret"],
            "auth_uri": AUTH_URI, "token_uri": TOKEN_URI,
        }}
    except (OSError, ValueError, AttributeError, TypeError) as exc:
        raise ImporterError(
            "Couldn't load Google Desktop OAuth credentials. Download the Desktop app JSON from Google Cloud, "
            "then pass --client-secrets /path/to/client_secret.json. See the README setup instructions."
        ) from exc


class BoundedRequest(Request):
    def __call__(self, *args, **kwargs):
        kwargs["timeout"] = 30
        return super().__call__(*args, **kwargs)


def authenticate(client_path: Path, directory: Path, reauth: bool = False) -> Credentials:
    token_path = directory / "token.json"
    if client_path.resolve() == token_path.resolve():
        raise ImporterError("The client credentials and token cache must be different files.")
    config = client_config(client_path)
    private_directory(directory)
    cached = None if reauth else read_token(token_path)
    try:
        if cached:
            if cached.get("client_id") != config["installed"]["client_id"] or cached.get("scopes") != SCOPES:
                raise ImporterError("The cached login belongs to a different OAuth client or permissions. Run again with --reauth.")
            # Rebuild from known fields; token refresh always goes to Google's endpoint.
            cached = {key: cached.get(key) for key in ("token", "refresh_token", "expiry")}
            cached.update(config["installed"], scopes=SCOPES)
            credentials = Credentials.from_authorized_user_info(cached, SCOPES)
            if not credentials.valid:
                with requests.Session() as session:
                    credentials.refresh(BoundedRequest(session=session))
        else:
            flow = InstalledAppFlow.from_client_config(config, SCOPES, autogenerate_code_verifier=True)
            flow.oauth2session.request = partial(flow.oauth2session.request, timeout=30)
            with redirect_stdout(sys.stderr):
                credentials = flow.run_local_server(
                    host="127.0.0.1", port=0, open_browser=True, timeout_seconds=180,
                    authorization_prompt_message="Open this Google sign-in link in your browser:\n{url}",
                    success_message="Sign-in response received. Return to your terminal to see whether authorization succeeded.",
                    access_type="offline", prompt="consent",
                )
        granted = credentials.granted_scopes
        if not credentials.has_scopes(SCOPES) or (granted is not None and not set(SCOPES).issubset(granted)):
            raise ImporterError("YouTube access was not granted. Run again with --reauth and approve the requested permission.")
        if not credentials.refresh_token:
            raise ImporterError("Google didn't return an offline login token. Run again with --reauth to grant access again.")
        save_token(token_path, credentials)
        return credentials
    except webbrowser.Error as exc:
        raise ImporterError("Couldn't open a browser for Google sign-in. Run the CLI on a computer with a default web browser.") from exc
    except (GoogleAuthError, OAuth2Error, requests.RequestException, ValueError, AttributeError, Warning) as exc:
        raise ImporterError(
            "Google sign-in or token refresh failed. Check your connection, Desktop OAuth setup and test-user access. "
            "If the saved login expired or was revoked, run again with --reauth. No tokens were printed."
        ) from exc


def logout(directory: Path) -> bool:
    path = directory / "token.json"
    if not directory.exists():
        return False
    private_directory(directory)
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
