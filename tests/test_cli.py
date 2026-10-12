import os
import shlex
import subprocess
import sys
from unittest.mock import Mock

import pytest

from playlist_importer import cli
from playlist_importer.errors import ImporterError, PlaylistConflict

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
    monkeypatch.setattr(cli.time, "sleep", Mock())
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


def test_resume_command_works_without_activation_or_original_directory(monkeypatch, csv_file, tmp_path):
    monkeypatch.chdir(tmp_path)
    args = cli.parser().parse_args([
        csv_file.name, "--config-dir", "private login", "--client-secrets", "Google keys/client.json", "--reauth",
    ])
    expected = [
        sys.executable, "-m", "playlist_importer", str(csv_file), "--playlist", PLAYLIST,
        "--config-dir", str(tmp_path / "private login"), "--client-secrets", str(tmp_path / "Google keys/client.json"),
    ]
    escaped = subprocess.list2cmdline(expected) if os.name == "nt" else shlex.join(expected)
    assert cli.resume_command(args, PLAYLIST) == escaped


def test_conflict_saved_after_a_stale_read_does_not_repeat_write(csv_file, fake_youtube, capsys):
    fake_youtube.add_video.side_effect = [PlaylistConflict("conflict"), None]
    fake_youtube.video_ids.side_effect = [set(), {A}]
    assert cli.main([str(csv_file)]) == 0
    assert [call.args for call in fake_youtube.add_video.call_args_list] == [(PLAYLIST, A), (PLAYLIST, B)]
    assert [call.args[0] for call in cli.time.sleep.call_args_list] == [5, 2]
    output = capsys.readouterr()
    assert "Already saved" in output.err
    assert "Done. Added 1 videos; skipped 1 already present" in output.err


def test_conflict_retries_only_after_two_absent_checks(csv_file, fake_youtube, capsys):
    fake_youtube.add_video.side_effect = [PlaylistConflict("conflict"), None, None]
    fake_youtube.video_ids.return_value = set()
    assert cli.main([str(csv_file)]) == 0
    operations = [call[0] for call in fake_youtube.mock_calls if call[0] in {"add_video", "video_ids"}]
    assert operations == ["add_video", "video_ids", "video_ids", "add_video", "add_video"]
    assert [call.args for call in fake_youtube.add_video.call_args_list] == [(PLAYLIST, A), (PLAYLIST, A), (PLAYLIST, B)]
    fake_youtube.create_playlist.assert_called_once()
    assert "Done. Added 2" in capsys.readouterr().err


def test_persistent_conflict_stops_at_three_retries_and_keeps_resume(csv_file, fake_youtube, capsys):
    fake_youtube.add_video.side_effect = PlaylistConflict("conflict")
    assert cli.main([str(csv_file)]) == 1
    assert fake_youtube.add_video.call_count == 4
    assert all(call.args == (PLAYLIST, A) for call in fake_youtube.add_video.call_args_list)
    assert fake_youtube.video_ids.call_count == 6
    assert [call.args[0] for call in cli.time.sleep.call_args_list] == [5, 2, 10, 2, 20, 2]
    output = capsys.readouterr()
    assert f"list={PLAYLIST}" in output.out
    assert "stopped after 3 rounds" in output.err
    assert "Stopped after 0 confirmed" in output.err
    assert "Done." not in output.err
    fake_youtube.create_playlist.assert_called_once()


def test_reported_duplicate_is_polled_without_repeating_insertion(csv_file, fake_youtube, capsys):
    fake_youtube.add_video.side_effect = [PlaylistConflict("already saved", reported_duplicate=True), None]
    fake_youtube.video_ids.side_effect = [set(), set(), {A}]
    assert cli.main([str(csv_file)]) == 0
    assert [call.args for call in fake_youtube.add_video.call_args_list] == [(PLAYLIST, A), (PLAYLIST, B)]
    assert [call.args[0] for call in cli.time.sleep.call_args_list] == [5, 2, 10]
    assert "skipped 1 already present" in capsys.readouterr().err


def test_unverifiable_duplicate_stops_without_reinsertion(csv_file, fake_youtube, capsys):
    fake_youtube.add_video.side_effect = PlaylistConflict("already saved", reported_duplicate=True)
    assert cli.main([str(csv_file)]) == 1
    fake_youtube.add_video.assert_called_once_with(PLAYLIST, A)
    assert fake_youtube.video_ids.call_count == 6
    assert "Done." not in capsys.readouterr().err


def test_failed_recovery_read_stops_before_more_writes(csv_file, fake_youtube, capsys):
    fake_youtube.add_video.side_effect = PlaylistConflict("conflict")
    fake_youtube.video_ids.side_effect = ImporterError("quota exhausted")
    assert cli.main([str(csv_file)]) == 1
    fake_youtube.add_video.assert_called_once_with(PLAYLIST, A)
    assert "couldn't verify the playlist" in capsys.readouterr().err


@pytest.mark.parametrize("message", ["quota exhausted", "login rejected", "video not found", "request timed out"])
def test_non_conflict_errors_are_not_automatically_retried(csv_file, fake_youtube, message):
    fake_youtube.add_video.side_effect = ImporterError(message)
    assert cli.main([str(csv_file)]) == 1
    fake_youtube.add_video.assert_called_once_with(PLAYLIST, A)
    fake_youtube.video_ids.assert_not_called()
    cli.time.sleep.assert_not_called()


def test_permanent_error_on_retry_stops_recovery(csv_file, fake_youtube, capsys):
    fake_youtube.add_video.side_effect = [PlaylistConflict("conflict"), ImporterError("quota exhausted")]
    assert cli.main([str(csv_file)]) == 1
    assert fake_youtube.add_video.call_count == 2
    assert fake_youtube.video_ids.call_count == 2
    assert "quota exhausted" in capsys.readouterr().err


def test_ctrl_c_during_recovery_preserves_manual_resume(csv_file, fake_youtube, capsys):
    fake_youtube.add_video.side_effect = PlaylistConflict("conflict")
    cli.time.sleep.side_effect = KeyboardInterrupt
    assert cli.main([str(csv_file)]) == 130
    fake_youtube.add_video.assert_called_once_with(PLAYLIST, A)
    fake_youtube.video_ids.assert_not_called()
    output = capsys.readouterr()
    assert "To resume safely" in output.err
    assert "The playlist was kept" in output.err


def test_creation_conflict_is_never_retried(csv_file, fake_youtube, capsys):
    fake_youtube.create_playlist.side_effect = PlaylistConflict("conflict")
    assert cli.main([str(csv_file)]) == 1
    fake_youtube.create_playlist.assert_called_once()
    fake_youtube.add_video.assert_not_called()
    cli.time.sleep.assert_not_called()
    assert "Check your YouTube library" in capsys.readouterr().err
