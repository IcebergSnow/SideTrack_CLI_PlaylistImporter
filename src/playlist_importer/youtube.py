"""Small wrapper around the official YouTube Data API; no write retries."""

import requests
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession

from .errors import ImporterError

API_ROOT = "https://www.googleapis.com/youtube/v3/"
ERRORS = {
    "quotaExceeded": "YouTube API quota is exhausted. Wait for the project's daily reset or check its quota in Google Cloud, then resume.",
    "dailyLimitExceeded": "The API project's daily limit is exhausted. Check Google Cloud quota, then resume later.",
    "accessNotConfigured": "Enable YouTube Data API v3 in the OAuth client's Google Cloud project.",
    "youtubeSignupRequired": "This Google account needs a YouTube channel. Visit YouTube to create one, then try again.",
    "insufficientPermissions": "The login lacks YouTube write permission. Run again with --reauth.",
    "playlistItemsNotAccessible": "The signed-in YouTube channel cannot add songs to this playlist.",
    "playlistForbidden": "The signed-in YouTube channel cannot access this playlist.",
    "playlistNotFound": "The playlist wasn't found or isn't accessible to the signed-in channel.",
    "videoAlreadyInPlaylist": "YouTube reports this video is already in the playlist. Wait briefly, then resume into the same playlist to check existing videos.",
    "videoNotFound": "YouTube couldn't find this video. It may have been removed or made private.",
    "playlistContainsMaximumNumberOfVideos": "This playlist has reached YouTube's video limit.",
    "maxPlaylistExceeded": "The channel has reached YouTube's playlist creation limit.",
    "rateLimitExceeded": "YouTube is limiting requests. Wait before resuming the import.",
    "userRateLimitExceeded": "YouTube is limiting requests for this account. Wait before resuming.",
}


class YouTube:
    def __init__(self, credentials):
        self.session = AuthorizedSession(credentials, refresh_timeout=30)

    def close(self):
        self.session.close()

    def request(self, method: str, resource: str, *, params: dict, body: dict | None = None) -> dict:
        try:
            response = self.session.request(
                method, API_ROOT + resource, params=params, json=body,
                timeout=(10, 30), allow_redirects=False,
            )
        except (requests.RequestException, GoogleAuthError) as exc:
            raise ImporterError(
                "The request to Google failed. Check your connection and login. "
                "A write may already have succeeded; resume into the same playlist to check before adding again."
            ) from exc
        try:
            data = response.json()
        except ValueError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        if not 200 <= response.status_code < 300:
            error = data.get("error", {})
            details = error.get("errors", []) if isinstance(error, dict) else []
            reasons = [detail.get("reason") for detail in details if isinstance(detail, dict)] if isinstance(details, list) else []
            for reason in reasons:
                if isinstance(reason, str) and reason in ERRORS:
                    raise ImporterError(ERRORS[reason])
            if response.status_code == 401:
                raise ImporterError("Google rejected the login. Run again with --reauth.")
            if response.status_code == 409:
                raise ImporterError(
                    "YouTube reported a conflict (HTTP 409). Wait briefly, then resume into the same playlist "
                    "using the printed command. Existing videos will be checked before adding more."
                )
            raise ImporterError(f"YouTube API returned HTTP {response.status_code}. Check access and quota; a failed write may need reconciliation before retrying.")
        if not data:
            raise ImporterError("YouTube returned an invalid response. A write may have succeeded; check the playlist before retrying.")
        return data

    @staticmethod
    def items(result: dict) -> list[dict]:
        items = result.get("items")
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise ImporterError("YouTube returned an invalid list response. Stopped rather than assuming the playlist is empty.")
        return items

    def channel(self) -> dict:
        result = self.request("GET", "channels", params={"part": "snippet", "mine": "true"})
        items = self.items(result)
        if not items:
            raise ImporterError("No YouTube channel was found. Open YouTube with this account and create a channel, or sign in with --reauth.")
        if len(items) != 1 or not items[0].get("id"):
            raise ImporterError("Couldn't identify one YouTube channel. Sign in again with --reauth and choose the intended channel.")
        return items[0]

    def create_playlist(self, title: str) -> str:
        result = self.request("POST", "playlists", params={"part": "snippet,status"}, body={
            "snippet": {"title": title, "description": "Imported with PlaylistImporter."},
            "status": {"privacyStatus": "private"},
        })
        if not result.get("id"):
            raise ImporterError("YouTube didn't return a playlist ID. Check your YouTube library before creating another playlist.")
        return result["id"]

    def existing_playlist(self, identifier: str, channel_id: str) -> dict:
        result = self.request("GET", "playlists", params={"part": "snippet,status", "id": identifier})
        items = self.items(result)
        if not items:
            raise ImporterError("The playlist wasn't found. Check its URL and the signed-in YouTube channel.")
        playlist = items[0]
        if playlist.get("snippet", {}).get("channelId") != channel_id:
            raise ImporterError("This tool can only append to playlists owned by the signed-in YouTube channel.")
        return playlist

    def video_ids(self, identifier: str) -> set[str]:
        ids = set()
        page_token = None
        seen_tokens = set()
        while True:
            params = {"part": "contentDetails", "playlistId": identifier, "maxResults": 50}
            if page_token:
                params["pageToken"] = page_token
            result = self.request("GET", "playlistItems", params=params)
            for item in self.items(result):
                video = item.get("contentDetails", {}).get("videoId")
                if video:
                    ids.add(video)
            page_token = result.get("nextPageToken")
            if not page_token:
                return ids
            if page_token in seen_tokens or len(seen_tokens) >= 200:
                raise ImporterError("YouTube returned unexpected playlist pagination. Stopped before adding any songs.")
            seen_tokens.add(page_token)

    def add_video(self, identifier: str, video_id: str) -> None:
        result = self.request("POST", "playlistItems", params={"part": "snippet"}, body={
            "snippet": {"playlistId": identifier, "resourceId": {"kind": "youtube#video", "videoId": video_id}},
        })
        if not result.get("id"):
            raise ImporterError("YouTube didn't confirm the added video. Resume into the same playlist to reconcile it before retrying.")
