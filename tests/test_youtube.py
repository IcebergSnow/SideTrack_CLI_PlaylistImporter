from unittest.mock import Mock

import pytest
import requests

from playlist_importer.errors import ImporterError
from playlist_importer.youtube import API_ROOT, YouTube


def api_with(*responses):
    api = YouTube.__new__(YouTube)
    api.session = Mock()
    api.session.request.side_effect = [Mock(status_code=status, json=Mock(return_value=body)) for status, body in responses]
    return api


def test_private_creation_and_exact_video_id_insert():
    api = api_with((200, {"id": "PLtest123456789"}), (200, {"id": "item-id"}))
    identifier = api.create_playlist("My discoveries")
    api.add_video(identifier, "fJ9rUzIMcZQ")
    create, insert = api.session.request.call_args_list
    assert create.args == ("POST", API_ROOT + "playlists")
    assert create.kwargs["json"]["status"]["privacyStatus"] == "private"
    assert insert.kwargs["json"]["snippet"] == {
        "playlistId": identifier, "resourceId": {"kind": "youtube#video", "videoId": "fJ9rUzIMcZQ"},
    }
    assert create.kwargs["allow_redirects"] is False
    assert create.kwargs["timeout"] == (10, 30)


def test_resume_reads_every_page():
    api = api_with((200, {"items": [{"contentDetails": {"videoId": "first"}}], "nextPageToken": "page-two"}),
                   (200, {"items": [{"contentDetails": {"videoId": "second"}}]}))
    assert api.video_ids("playlist") == {"first", "second"}
    assert api.session.request.call_args.kwargs["params"]["pageToken"] == "page-two"


@pytest.mark.parametrize("body", [{}, {"items": None}, {"items": ["bad"]}, {"unexpected": "response"}])
def test_invalid_list_never_assumed_empty(body):
    api = api_with((200, body))
    with pytest.raises(ImporterError):
        api.video_ids("playlist")


def test_pagination_cycle_stops_before_writes():
    response = (200, {"items": [], "nextPageToken": "repeat"})
    api = api_with(response, response)
    with pytest.raises(ImporterError, match="pagination"):
        api.video_ids("playlist")
    assert api.session.request.call_count == 2


@pytest.mark.parametrize("reason,expected", [("quotaExceeded", "quota"), ("videoNotFound", "video"), ("youtubeSignupRequired", "channel"), ("accessNotConfigured", "Enable"), ("insufficientPermissions", "--reauth")])
def test_actionable_api_errors_no_response_leaks(reason, expected):
    api = api_with((403, {"error": {"message": "sensitive-test-token", "errors": [{"reason": reason}]}}))
    with pytest.raises(ImporterError, match=expected) as error:
        api.add_video("playlist", "video")
    assert "sensitive-test-token" not in str(error.value)
    assert api.session.request.call_count == 1


def test_uncertain_write_is_not_retried():
    api = api_with()
    api.session.request.side_effect = requests.Timeout("sensitive-test-token")
    with pytest.raises(ImporterError, match="may already have succeeded"):
        api.add_video("playlist", "video")
    assert api.session.request.call_count == 1


def test_different_owner_is_rejected():
    api = api_with((200, {"items": [{"snippet": {"channelId": "someone-else"}}]}))
    with pytest.raises(ImporterError, match="owned"):
        api.existing_playlist("playlist", "me")
