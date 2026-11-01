import os
import shlex
from pathlib import Path
from unittest.mock import Mock

import pytest

from playlist_importer import cli, interactive, terminal
from playlist_importer.errors import ImporterError, ReauthenticationRequired

A = "fJ9rUzIMcZQ"
B = "YQHsXMglC9A"
PLAYLIST = "PLtest1234567890"


@pytest.fixture
def home(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.delenv("PLAYLIST_IMPORTER_CONFIG_DIR", raising=False)
    monkeypatch.delenv("PLAYLIST_IMPORTER_CLIENT_SECRETS", raising=False)
    (tmp_path / "Downloads").mkdir()
    return tmp_path


def csv_at(path, identifier=A):
    path.write_text(f"title,artist,url\nA song,An artist,https://youtu.be/{identifier}\n")
    return path


def answers(monkeypatch, *values):
    responses = iter(values)
    monkeypatch.setattr("builtins.input", lambda: next(responses))


@pytest.fixture
def api(monkeypatch):
    youtube = Mock()
    youtube.channel.return_value = {"id": "channel"}
    youtube.create_playlist.return_value = PLAYLIST
    youtube.video_ids.return_value = set()
    youtube.existing_playlist.return_value = {"status": {"privacyStatus": "private"}}
    monkeypatch.setattr(cli, "authenticate", Mock(return_value=object()))
    monkeypatch.setattr(cli, "YouTube", Mock(return_value=youtube))
    return youtube


def test_downloads_include_browser_suffixes_ignore_other_files_and_sort_by_recency(home):
    directory = home / "Downloads"
    old = csv_at(directory / "playlist.csv")
    recent = csv_at(directory / "sidetrack-abc-page-2 (1).csv")
    csv_at(directory / "unrelated.csv")
    (directory / "sidetrack-incomplete.csv.crdownload").write_text("partial")
    (directory / "sidetrack-directory.csv").mkdir()
    os.utime(old, (100, 100))
    os.utime(recent, (200, 200))
    assert interactive.recent_downloads(directory) == [recent, old]
    assert interactive.recent_downloads(home / "absent") == []


def test_choose_latest_and_number_without_renaming(home, monkeypatch):
    first = csv_at(home / "Downloads/sidetrack-first.csv")
    second = csv_at(home / "Downloads/sidetrack-second.csv")
    os.utime(first, (200, 200))
    os.utime(second, (100, 100))
    answers(monkeypatch, "99", "2", "")
    assert interactive.choose_csv() == second
    assert interactive.choose_csv() == first
    assert first.exists() and second.exists()


def test_renamed_or_non_download_csv_can_be_entered(home, monkeypatch):
    path = csv_at(home / "my music.csv")
    answers(monkeypatch, str(path))
    assert interactive.choose_csv() == path


@pytest.mark.skipif(os.name != "posix", reason="Finder's shell escaping")
def test_quoted_and_dragged_paths_are_parsed_without_shell_execution(home):
    path = csv_at(home / "my songs $(do-not-execute).csv")
    assert interactive.entered_path(shlex.quote(str(path))) == path
    dragged = str(path).replace(" ", "\\ ").replace("(", "\\(").replace(")", "\\)").replace("$", "\\$")
    assert interactive.entered_path(dragged) == path


def test_default_mode_shows_file_and_preview_before_auth(home, monkeypatch, api, capsys):
    path = csv_at(home / "Downloads/sidetrack-original-name (2).csv")
    client = home / "Downloads/client_secret.json"
    client.write_text("test-only")
    answers(monkeypatch, "", "New music", "yes")
    assert cli.main([]) == 0
    cli.authenticate.assert_called_once_with(client, home / ".playlistimporter", False)
    api.create_playlist.assert_called_once_with("New music")
    api.add_video.assert_called_once_with(PLAYLIST, A)
    output = capsys.readouterr()
    assert str(path) in output.err and "An artist - A song" in output.err
    assert output.out.strip() == f"https://www.youtube.com/playlist?list={PLAYLIST}"
    assert "--client-secrets" in output.err


@pytest.mark.parametrize("confirmation", ["", "n", "something else"])
def test_declining_confirmation_prevents_login_and_writes(home, monkeypatch, api, confirmation):
    csv_at(home / "Downloads/sidetrack-song.csv")
    answers(monkeypatch, "", "Test playlist", confirmation)
    assert cli.main([]) == 0
    cli.authenticate.assert_not_called()
    cli.YouTube.assert_not_called()
    assert not (home / ".playlistimporter").exists()


def test_invalid_csv_fails_before_auth_or_playlist_creation(home, monkeypatch, api):
    (home / "Downloads/sidetrack-bad.csv").write_text("title\nMissing ID\n")
    answers(monkeypatch, "")
    assert cli.main([]) == 2
    cli.authenticate.assert_not_called()
    cli.YouTube.assert_not_called()


def test_interactive_dry_run_needs_no_credentials_confirmation_or_auth(home, monkeypatch, api, capsys):
    csv_at(home / "Downloads/sidetrack-song.csv")
    answers(monkeypatch, "")
    assert cli.main(["--dry-run"]) == 0
    cli.authenticate.assert_not_called()
    assert "Dry run complete" in capsys.readouterr().err
    assert not (home / ".playlistimporter").exists()


def test_missing_client_prompts_for_path_after_confirmation(home, monkeypatch, api):
    path = csv_at(home / "Downloads/sidetrack-song.csv")
    custom = home / "my client.json"
    custom.write_text("test-only")
    answers(monkeypatch, "A playlist", "y", str(custom))
    assert cli.main([str(path), "--interactive"]) == 0
    assert cli.authenticate.call_args.args[0] == custom


def test_config_client_has_priority_over_downloaded_client(home):
    config = home / "private"
    config.mkdir()
    expected = config / "client_secret.json"
    expected.write_text("test-only")
    (home / "Downloads/client_secret.json").write_text("other-test-only")
    assert interactive.choose_client(config) == expected


def test_explicit_client_is_not_replaced_by_autodiscovery(home, monkeypatch, api):
    path = csv_at(home / "Downloads/sidetrack-song.csv")
    explicit = home / "explicit.json"
    answers(monkeypatch, "A playlist", "y")
    assert cli.main([str(path), "--interactive", "--client-secrets", str(explicit)]) == 0
    assert cli.authenticate.call_args.args[0] == explicit


def test_expired_login_offers_one_reauth_before_any_playlist_writes(home, monkeypatch, api):
    path = csv_at(home / "Downloads/sidetrack-song.csv")
    cli.authenticate.side_effect = [ReauthenticationRequired("expired"), object()]
    answers(monkeypatch, "Test", "y", "")
    assert cli.main([str(path), "--interactive", "--client-secrets", str(home / "client.json")]) == 0
    assert [call.args[2] for call in cli.authenticate.call_args_list] == [False, True]
    api.create_playlist.assert_called_once()


def test_declining_reauth_does_not_create_playlist(home, monkeypatch, api):
    path = csv_at(home / "Downloads/sidetrack-song.csv")
    cli.authenticate.side_effect = ReauthenticationRequired("expired")
    answers(monkeypatch, "Test", "y", "n")
    assert cli.main([str(path), "--interactive", "--client-secrets", str(home / "client.json")]) == 0
    cli.authenticate.assert_called_once()
    cli.YouTube.assert_not_called()


@pytest.mark.parametrize("error", [ImporterError("invalid credentials"), ReauthenticationRequired("expired")])
def test_explicit_mode_keeps_noninteractive_error_behavior(home, api, error):
    path = csv_at(home / "songs.csv")
    cli.authenticate.side_effect = error
    assert cli.main([str(path)]) == 1
    cli.authenticate.assert_called_once()
    cli.YouTube.assert_not_called()


def test_authentication_permission_errors_do_not_trigger_reauth(home, monkeypatch, api):
    path = csv_at(home / "songs.csv")
    cli.authenticate.side_effect = ImporterError("token file must be private")
    answers(monkeypatch, "Test", "y")
    assert cli.main([str(path), "--interactive", "--client-secrets", str(home / "client.json")]) == 1
    cli.authenticate.assert_called_once()
    cli.YouTube.assert_not_called()


def test_reauth_failure_does_not_loop_or_write(home, monkeypatch, api):
    path = csv_at(home / "songs.csv")
    cli.authenticate.side_effect = ReauthenticationRequired("expired")
    answers(monkeypatch, "Test", "y", "y")
    assert cli.main([str(path), "--interactive", "--client-secrets", str(home / "client.json")]) == 1
    assert cli.authenticate.call_count == 2
    cli.YouTube.assert_not_called()


def test_interactive_resume_preserves_destination_and_skips_existing(home, monkeypatch, api):
    path = home / "Downloads/sidetrack-two.csv"
    path.write_text(f"video_id\n{A}\n{B}\n")
    (home / "Downloads/client_secret.json").write_text("test-only")
    api.video_ids.return_value = {A}
    answers(monkeypatch, "", "y")
    assert cli.main(["--playlist", PLAYLIST]) == 0
    api.create_playlist.assert_not_called()
    api.add_video.assert_called_once_with(PLAYLIST, B)


def test_nonterminal_does_not_wait_for_input(monkeypatch, api):
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    assert cli.main([]) == 2
    assert cli.main(["--interactive"]) == 2
    cli.authenticate.assert_not_called()


@pytest.mark.parametrize("at_confirmation", [False, True])
def test_eof_cancels_without_login(home, monkeypatch, api, at_confirmation):
    path = csv_at(home / "Downloads/sidetrack-song.csv")
    monkeypatch.setattr("builtins.input", Mock(side_effect=EOFError))
    args = [str(path), "--interactive", "--name", "Test"] if at_confirmation else []
    assert cli.main(args) == 130
    cli.authenticate.assert_not_called()


def test_quit_does_not_authenticate(home, monkeypatch, api):
    answers(monkeypatch, "q")
    assert cli.main([]) == 130
    cli.authenticate.assert_not_called()


def test_unsafe_terminal_metadata_is_sanitized(home, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda: "n")
    assert terminal.ask("A song\x1b[2J\nContinue?") == "n"
    output = capsys.readouterr()
    assert "\x1b" not in output.err and not output.out
