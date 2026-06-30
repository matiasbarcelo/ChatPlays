"""Look up streaming platform users for username validation."""

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

TWITCH_LOGIN_RE = re.compile(r"^[A-Za-z\d][A-Za-z\d_]{3,24}$", re.ASCII)

_app_token_cache = {"token": "", "expires_at": 0.0}
_USER_AGENT = "ChatPlays/1.0"


def _http_get_json(url: str, headers: dict | None = None) -> object:
    merged_headers = {"User-Agent": _USER_AGENT}
    if headers:
        merged_headers.update(headers)
    request = urllib.request.Request(url, headers=merged_headers)
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode())


def _get_app_access_token(client_id: str, client_secret: str) -> str:
    now = time.time()
    if _app_token_cache["token"] and _app_token_cache["expires_at"] > now + 60:
        return _app_token_cache["token"]

    body = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        }
    ).encode()
    request = urllib.request.Request(
        "https://id.twitch.tv/oauth2/token",
        data=body,
        method="POST",
        headers={"User-Agent": _USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        data = json.loads(response.read().decode())

    _app_token_cache["token"] = data["access_token"]
    _app_token_cache["expires_at"] = now + int(data.get("expires_in", 0))
    return _app_token_cache["token"]


def _lookup_helix(login: str) -> dict | None:
    client_id = os.environ.get("TWITCH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("TWITCH_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None

    token = _get_app_access_token(client_id, client_secret)
    url = "https://api.twitch.tv/helix/users?" + urllib.parse.urlencode({"login": login})
    data = _http_get_json(
        url,
        headers={
            "Client-ID": client_id,
            "Authorization": f"Bearer {token}",
        },
    )
    users = data.get("data") or []
    if not users:
        return {"found": False}

    user = users[0]
    return {
        "found": True,
        "login": user.get("login", login),
        "display_name": user.get("display_name", login),
        "profile_image_url": user.get("profile_image_url", ""),
    }


def _lookup_ivr(login: str) -> dict:
    url = "https://api.ivr.fi/v2/twitch/user?" + urllib.parse.urlencode({"login": login})
    data = _http_get_json(url)
    if not data:
        return {"found": False}

    user = data[0]
    return {
        "found": True,
        "login": user.get("login", login),
        "display_name": user.get("displayName", login),
        "profile_image_url": user.get("logo", ""),
    }


def lookup_streaming_user(platform: str, login: str) -> dict:
    login = login.strip()
    if not login:
        return {"found": False, "error": "empty"}
    if platform != "twitch":
        return {"found": False, "error": "unsupported_platform"}
    if not TWITCH_LOGIN_RE.match(login):
        return {"found": False, "error": "invalid_format"}

    try:
        helix_result = _lookup_helix(login)
        if helix_result is not None:
            return helix_result
        return _lookup_ivr(login)
    except urllib.error.HTTPError as exc:
        if exc.code == 400:
            return {"found": False, "error": "invalid_format"}
        return {"found": False, "error": "lookup_failed"}
    except Exception:
        return {"found": False, "error": "lookup_failed"}
