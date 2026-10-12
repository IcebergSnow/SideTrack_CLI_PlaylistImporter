from unittest.mock import Mock

import pytest

from playlist_importer import cli
from playlist_importer.errors import ImporterError

A = "fJ9rUzIMcZQ"
B = "YQHsXMglC9A"
PLAYLIST = "PLtest1234567890"


@pytest.fixture
def csv_file(tmp_path):
    path = tmp_path / "my songs.csv"
    path.write_text(f"title,artist,url\nSong one,Artist,https://youtu.be/{A}\nSong two,Artist,https://youtu.be/{B}\nSame video,Artist,https://youtu.be/{A}\n")
    return path


@pytest.fixture
def fake_youtube(monkeypatch):
    api = Mock()
    api.channel.return_value = {"id": "my-channel", "snippet": {"title": "My Channel"}}
    api.create_playlist.return_value = PLAYLIST
    api.existing_playlist.return_value = {"snippet": {"title": "Existing"}, "status": {"privacyStatus": "private"}}
    api.video_ids.return_value = set()
    monkeypatch.setattr(cli, "authenticate", Mock(return_value=object()))
    monkeypatch.setattr(cli, "YouTube", Mock(return_value=api))
    return api


def test_dry_run_never_authenticates_or_writes(monkeypatch, csv_file, tmp_path, capsys):
    monkeypatch.setattr(cli, "authenticate", lambda *args: pytest.fail("auth called"))
    directory = tmp_path / "must-not-exist"
    assert cli.main([str(csv_file), "--dry-run", "--config-dir", str(directory)]) == 0
    output = capsys.readouterr()
    assert A in output.out and B in output.out
    assert "2 unique videos" in output.err and "150 units" in output.err
    assert not directory.exists()


def test_full_import_outputs_link_and_order(csv_file, fake_youtube, capsys):
    assert cli.main([str(csv_file), "--name", "Discoveries"]) == 0
    fake_youtube.create_playlist.assert_called_once_with("Discoveries")
    assert [call.args for call in fake_youtube.add_video.call_args_list] == [(PLAYLIST, A), (PLAYLIST, B)]
    output = capsys.readouterr()
    assert output.out.strip() == f"https://www.youtube.com/playlist?list={PLAYLIST}"
    assert "Done. Added 2" in output.err
    fake_youtube.close.assert_called_once()


def test_resume_skips_existing_ids_and_never_creates_another_playlist(csv_file, fake_youtube, capsys):
    fake_youtube.video_ids.return_value = {A}
    assert cli.main([str(csv_file), "--playlist", f"https://youtube.com/playlist?list={PLAYLIST}"]) == 0
    fake_youtube.create_playlist.assert_not_called()
    fake_youtube.add_video.assert_called_once_with(PLAYLIST, B)
    assert "skipping 1 already present" in capsys.readouterr().err


def test_partial_failure_keeps_link_and_resume_command(csv_file, fake_youtube, capsys):
    fake_youtube.add_video.side_effect = [None, ImporterError("quota exhausted")]
    assert cli.main([str(csv_file)]) == 1
    output = capsys.readouterr()
    assert f"list={PLAYLIST}" in output.out
    assert "Stopped after 1 confirmed" in output.err and f"--playlist {PLAYLIST}" in output.err
    assert B in output.err and "quota exhausted" in output.err
    assert "Done." not in output.err
    fake_youtube.close.assert_called_once()


def test_creation_timeout_does_not_claim_a_link(csv_file, fake_youtube, capsys):
    fake_youtube.create_playlist.side_effect = ImporterError("connection failed")
    assert cli.main([str(csv_file)]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert "Check your YouTube library" in output.err
    fake_youtube.add_video.assert_not_called()


def test_cancelled_import_preserves_resume_instructions(csv_file, fake_youtube, capsys):
    fake_youtube.add_video.side_effect = KeyboardInterrupt
    assert cli.main([str(csv_file)]) == 130
    assert "Stopped after 0 confirmed" in capsys.readouterr().err


def test_bad_second_file_prevents_any_auth_or_writes(csv_file, tmp_path, fake_youtube):
    bad = tmp_path / "bad.csv"
    bad.write_text("title\nNo URL\n")
    assert cli.main([str(csv_file), str(bad)]) == 2
    cli.authenticate.assert_not_called()
    fake_youtube.create_playlist.assert_not_called()


def test_missing_credentials_is_actionable(csv_file, tmp_path, capsys):
    assert cli.main([str(csv_file), "--client-secrets", str(tmp_path / "missing.json")]) == 1
    output = capsys.readouterr()
    assert "Desktop OAuth" in output.err and "Traceback" not in output.err


def test_terminal_escape_sequences_are_removed():
    assert "\x1b" not in cli.safe_text("song\x1b[2J\nname")


@pytest.mark.parametrize("name", ["", " " * 3, "x" * 151, "title\x1b[2J"])
def test_invalid_title_prevents_auth(csv_file, fake_youtube, name):
    assert cli.main([str(csv_file), "--name", name]) == 2
    cli.authenticate.assert_not_called()


def test_empty_resume_makes_no_writes(csv_file, fake_youtube):
    fake_youtube.video_ids.return_value = {A, B}
    assert cli.main([str(csv_file), "--playlist", PLAYLIST]) == 0
    fake_youtube.add_video.assert_not_called()
    fake_youtube.create_playlist.assert_not_called()
