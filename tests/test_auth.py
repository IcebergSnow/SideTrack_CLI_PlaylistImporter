import json
import os
import stat
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

from playlist_importer import auth
from playlist_importer.errors import ImporterError


@pytest.fixture
def client(tmp_path):
    path = tmp_path / "client.json"
    path.write_text(json.dumps({"installed": {
        "client_id": "test.apps.googleusercontent.com", "client_secret": "test-only-client",
        "auth_uri": auth.AUTH_URI, "token_uri": auth.TOKEN_URI,
    }}))
    return path


def credential(**kwargs):
    values = dict(token="test-only-access", refresh_token="test-only-refresh", token_uri=auth.TOKEN_URI,
                  client_id="test.apps.googleusercontent.com", client_secret="test-only-client", scopes=auth.SCOPES,
                  expiry=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1))
    values.update(kwargs)
    return Credentials(**values)


def test_real_library_pkce_and_local_login_settings(monkeypatch, tmp_path, client, capsys):
    observed = {}
    def local_flow(self, **kwargs):
        observed.update(kwargs)
        self.redirect_uri = "http://127.0.0.1:9999/"
        url, state = self.authorization_url(access_type="offline", prompt="consent")
        query = parse_qs(urlparse(url).query)
        assert query["code_challenge_method"] == ["S256"]
        assert query["code_challenge"] and state
        assert query["scope"] == auth.SCOPES
        print("Google sign-in URL goes to stderr")
        return credential()
    monkeypatch.setattr(auth.InstalledAppFlow, "run_local_server", local_flow)
    directory = tmp_path / "private"
    result = auth.authenticate(client, directory)
    assert result.refresh_token == "test-only-refresh"
    assert observed["host"] == "127.0.0.1" and observed["port"] == 0
    assert observed["timeout_seconds"] == 180 and observed["open_browser"] is True
    assert capsys.readouterr().out == ""
    assert (directory / "token.json").exists()
    if os.name == "posix":
        assert stat.S_IMODE(directory.stat().st_mode) == 0o700
        assert stat.S_IMODE((directory / "token.json").stat().st_mode) == 0o600


def test_cached_login_needs_no_browser(monkeypatch, tmp_path, client):
    directory = tmp_path / "private"
    auth.private_directory(directory)
    auth.save_token(directory / "token.json", credential())
    monkeypatch.setattr(auth.InstalledAppFlow, "run_local_server", lambda *a, **kw: pytest.fail("browser opened"))
    assert auth.authenticate(client, directory).token == "test-only-access"


def test_expired_credentials_refresh_and_cache(monkeypatch, tmp_path, client):
    directory = tmp_path / "private"
    auth.private_directory(directory)
    auth.save_token(directory / "token.json", credential(expiry=datetime(2000, 1, 1)))
    def refresh(self, request):
        assert isinstance(request, auth.BoundedRequest)
        self.token = "test-only-new-access"
        self.expiry = datetime(2099, 1, 1)
    monkeypatch.setattr(Credentials, "refresh", refresh)
    auth.authenticate(client, directory)
    assert auth.read_token(directory / "token.json")["token"] == "test-only-new-access"


def test_refresh_failure_does_not_leak_exception_or_replace_cache(monkeypatch, tmp_path, client):
    directory = tmp_path / "private"
    auth.private_directory(directory)
    path = directory / "token.json"
    auth.save_token(path, credential(expiry=datetime(2000, 1, 1)))
    before = path.read_bytes()
    def fail(*args, **kwargs):
        raise RefreshError("sensitive-test-token")
    monkeypatch.setattr(Credentials, "refresh", fail)
    with pytest.raises(ImporterError, match="--reauth") as error:
        auth.authenticate(client, directory)
    assert "sensitive-test-token" not in str(error.value)
    assert path.read_bytes() == before


@pytest.mark.parametrize("field,value", [("token_uri", "https://evil.test/token"), ("auth_uri", "https://evil.test/login"), ("client_id", "not-a-google-client")])
def test_external_oauth_endpoints_are_rejected(client, field, value):
    data = json.loads(client.read_text())
    data["installed"][field] = value
    client.write_text(json.dumps(data))
    with pytest.raises(ImporterError, match="Desktop"):
        auth.client_config(client)


def test_web_client_rejected(client):
    data = json.loads(client.read_text())
    client.write_text(json.dumps({"web": data["installed"]}))
    with pytest.raises(ImporterError, match="Desktop"):
        auth.client_config(client)


def test_reauth_replaces_cached_account(monkeypatch, tmp_path, client):
    directory = tmp_path / "private"
    auth.private_directory(directory)
    path = directory / "token.json"
    auth.save_token(path, credential())
    monkeypatch.setattr(auth.InstalledAppFlow, "run_local_server", lambda *a, **kw: credential(token="other-test-account"))
    auth.authenticate(client, directory, reauth=True)
    assert auth.read_token(path)["token"] == "other-test-account"


def test_denied_scope_is_not_cached(monkeypatch, tmp_path, client):
    monkeypatch.setattr(auth.InstalledAppFlow, "run_local_server", lambda *a, **kw: credential(granted_scopes=[]))
    directory = tmp_path / "private"
    with pytest.raises(ImporterError, match="not granted"):
        auth.authenticate(client, directory)
    assert not (directory / "token.json").exists()


@pytest.mark.skipif(os.name != "posix", reason="POSIX file permissions")
def test_insecure_token_and_directory_rejected(tmp_path):
    directory = tmp_path / "private"
    directory.mkdir(mode=0o755)
    directory.chmod(0o755)
    with pytest.raises(ImporterError, match="chmod 700"):
        auth.private_directory(directory)
    directory.chmod(0o700)
    token = directory / "token.json"
    token.write_text("{}")
    token.chmod(0o644)
    with pytest.raises(ImporterError, match="chmod 600"):
        auth.read_token(token)


@pytest.mark.skipif(os.name != "posix", reason="POSIX symlink support")
def test_symlinked_cache_rejected(tmp_path):
    source = tmp_path / "source"
    source.write_text("{}")
    link = tmp_path / "token.json"
    link.symlink_to(source)
    with pytest.raises(OSError):
        auth.read_token(link)


def test_logout_does_not_touch_client_or_other_files(tmp_path):
    directory = tmp_path / "private"
    auth.private_directory(directory)
    client = directory / "client_secret.json"
    client.write_text("{}")
    auth.save_token(directory / "token.json", credential())
    assert auth.logout(directory)
    assert client.exists()
    assert not auth.logout(directory)
