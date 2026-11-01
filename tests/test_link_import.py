import os
import stat
from pathlib import Path
from unittest.mock import Mock

import pytest

from playlist_importer import cli, interactive, snapshots
from playlist_importer.errors import ImporterError
from playlist_importer.files import ImportFile, Track, read_csvs
from playlist_importer.recommendations import RecommendationError

SEED = "https://music.youtube.com/watch?v=fJ9rUzIMcZQ"
PLAYLIST = "PLtest1234567890"


@pytest.fixture
def home(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.delenv("PLAYLIST_IMPORTER_CONFIG_DIR", raising=False)
    monkeypatch.delenv("PLAYLIST_IMPORTER_CLIENT_SECRETS", raising=False)
    (tmp_path / "Downloads").mkdir()
    (tmp_path / "Downloads/client_secret.json").write_text("test-only")
    return tmp_path


@pytest.fixture
def radio(monkeypatch):
    tracks = [{"video_id": f"v{i:010d}", "title": f"Song {i}", "artists": ["Artist"]} for i in range(30)]
    result = {"seed": {"video_id": "fJ9rUzIMcZQ", "title": "Seed song", "artists": ["Seed artist"]}, "tracks": tracks}
    call = Mock(return_value=result)
    monkeypatch.setattr(cli, "recommend", call)
    return call


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


def answers(monkeypatch, *values):
    responses = iter(values)
    monkeypatch.setattr("builtins.input", lambda: next(responses))


def test_link_menu_checks_recommendations_before_asking_count(home, monkeypatch, radio, api, capsys):
    replies = iter(["1", SEED, "12", "My discoveries", "y"])
    def answer():
        value = next(replies)
        if value == "12":
            radio.assert_called_once_with(SEED)
            cli.authenticate.assert_not_called()
        return value
    monkeypatch.setattr("builtins.input", answer)
    assert cli.main([]) == 0
    api.create_playlist.assert_called_once_with("My discoveries")
    expected_ids = [f"v{i:010d}" for i in range(12)]
    assert [call.args[1] for call in api.add_video.call_args_list] == expected_ids
    saved = list((home / ".playlistimporter/imports").glob("*.csv"))
    assert len(saved) == 1
    assert [track.video_id for track in read_csvs(saved).tracks] == expected_ids
    output = capsys.readouterr()
    assert "Found 30 unique" in output.err
    assert "Selected 12 unique" in output.err
    assert output.out.strip() == f"https://www.youtube.com/playlist?list={PLAYLIST}"
    resume = output.err.split("To resume safely using the same CSVs: ")[1].splitlines()[0]
    assert "--url" not in resume and str(saved[0]) in resume


@pytest.mark.parametrize("failure", [
    RecommendationError("Paste a single song link.", 400),
    RecommendationError("This song is unavailable.", 422),
    RecommendationError("No related songs were available.", 404),
    RecommendationError("YouTube Music took too long.", 504),
])
def test_recommendation_failure_never_prompts_count_or_authenticates(home, monkeypatch, radio, api, capsys, failure):
    radio.side_effect = failure
    answers(monkeypatch, "1", SEED)
    monkeypatch.setattr(cli, "choose_count", Mock(side_effect=AssertionError("count asked after failure")))
    assert cli.main([]) == 1
    cli.authenticate.assert_not_called()
    cli.YouTube.assert_not_called()
    assert not (home / ".playlistimporter").exists()
    assert str(failure) in capsys.readouterr().err


def test_no_playlist_when_user_declines_link_preview(home, monkeypatch, radio, api):
    answers(monkeypatch, "1", SEED, "5", "A playlist", "n")
    assert cli.main([]) == 0
    cli.authenticate.assert_not_called()
    cli.YouTube.assert_not_called()
    assert not (home / ".playlistimporter").exists()


def test_count_reprompts_with_available_limit_without_another_radio_request(home, monkeypatch, radio, api):
    radio.return_value["tracks"] = radio.return_value["tracks"][:7]
    answers(monkeypatch, "1", SEED, "20", "0", "-5", "2.5", "hello", "7", "Short list", "y")
    assert cli.main([]) == 0
    radio.assert_called_once()
    assert api.add_video.call_count == 7


@pytest.mark.parametrize("available,expected", [(30, 20), (3, 3)])
def test_enter_uses_default_count_that_fits_available_results(home, monkeypatch, radio, api, available, expected):
    radio.return_value["tracks"] = radio.return_value["tracks"][:available]
    answers(monkeypatch, "", SEED, "", "Default count", "y")
    assert cli.main([]) == 0
    assert api.add_video.call_count == expected


def test_cancel_at_count_does_not_save_or_authenticate(home, monkeypatch, radio, api):
    answers(monkeypatch, "1", SEED, "q")
    assert cli.main([]) == 130
    cli.authenticate.assert_not_called()
    assert not (home / ".playlistimporter").exists()


def test_link_preview_contacts_radio_but_never_saves_or_authenticates(home, monkeypatch, radio, api, capsys):
    answers(monkeypatch, "1", SEED, "6")
    assert cli.main(["--dry-run"]) == 0
    radio.assert_called_once_with(SEED)
    cli.authenticate.assert_not_called()
    assert not (home / ".playlistimporter").exists()
    output = capsys.readouterr()
    assert len(output.out.splitlines()) == 6
    assert "Recommendations came from YouTube Music" in output.err
    assert "No login, network requests" not in output.err


def test_noninteractive_url_preview_accepts_count_without_prompts(home, monkeypatch, radio, api, capsys):
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    assert cli.main(["--url", SEED, "--count", "4", "--dry-run"]) == 0
    assert len(capsys.readouterr().out.splitlines()) == 4
    cli.authenticate.assert_not_called()


def test_noninteractive_url_defaults_to_twenty(home, monkeypatch, radio, api, capsys):
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    assert cli.main(["--url", SEED, "--dry-run"]) == 0
    assert len(capsys.readouterr().out.splitlines()) == 20


def test_too_large_explicit_count_fails_without_saving_or_importing(home, radio, api):
    assert cli.main(["--url", SEED, "--count", "100"]) == 2
    cli.authenticate.assert_not_called()
    assert not (home / ".playlistimporter").exists()


@pytest.mark.parametrize("arguments", [
    ["songs.csv", "--url", SEED],
    ["songs.csv", "--count", "2"],
    ["--url", SEED, "--count", "0"],
    ["--url", SEED, "--count", "201"],
    ["--logout", "--url", SEED],
])
def test_invalid_combinations_fail_before_network(home, radio, api, arguments):
    assert cli.main(arguments) == 2
    radio.assert_not_called()
    cli.authenticate.assert_not_called()


def test_snapshot_failure_stops_before_auth_or_creation(home, monkeypatch, radio, api):
    answers(monkeypatch, "1", SEED, "3", "A playlist", "y")
    monkeypatch.setattr(cli, "save_song_list", Mock(side_effect=OSError("disk full")))
    assert cli.main([]) == 1
    cli.authenticate.assert_not_called()
    cli.YouTube.assert_not_called()


def test_snapshot_preserves_order_metadata_and_private_permissions(home):
    source = ImportFile([Track("fJ9rUzIMcZQ", 'Title, "quoted"\nsecond line', "日本語"), Track("YQHsXMglC9A", "Hello", "Adele")], 0)
    path = snapshots.save_song_list(source, home / "private")
    assert read_csvs([path]).tracks == source.tracks
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
        assert stat.S_IMODE(path.parent.parent.stat().st_mode) == 0o700


def test_failed_snapshot_is_removed(home, monkeypatch):
    monkeypatch.setattr(snapshots.os, "fsync", Mock(side_effect=OSError("disk full")))
    with pytest.raises(OSError):
        snapshots.save_song_list(ImportFile([Track("fJ9rUzIMcZQ")], 0), home / "private")
    assert not list((home / "private/imports").iterdir())


def test_partial_link_import_resumes_exact_selection_without_generating_again(home, monkeypatch, radio, api, capsys):
    answers(monkeypatch, "1", SEED, "4", "My discoveries", "y")
    api.add_video.side_effect = [None, ImporterError("quota exhausted")]
    assert cli.main([]) == 1
    snapshot = next((home / ".playlistimporter/imports").glob("*.csv"))
    output = capsys.readouterr()
    assert str(snapshot) in output.err and "Stopped after 1" in output.err
    api.reset_mock()
    api.add_video.side_effect = None
    api.video_ids.return_value = {"v0000000000"}
    radio.reset_mock()
    assert cli.main([str(snapshot), "--playlist", PLAYLIST, "--client-secrets", str(home / "Downloads/client_secret.json")]) == 0
    radio.assert_not_called()
    api.create_playlist.assert_not_called()
    assert [call.args[1] for call in api.add_video.call_args_list] == [f"v{i:010d}" for i in range(1, 4)]


@pytest.mark.skipif(os.name != "posix", reason="POSIX symlink permissions")
def test_snapshot_directory_cannot_point_elsewhere(home):
    parent = home / "private"
    parent.mkdir(mode=0o700)
    elsewhere = home / "elsewhere"
    elsewhere.mkdir()
    (parent / "imports").symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(ImporterError, match="symlink"):
        snapshots.save_song_list(ImportFile([Track("fJ9rUzIMcZQ")], 0), parent)
    assert not list(elsewhere.iterdir())
