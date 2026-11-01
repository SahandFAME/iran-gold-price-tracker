from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from cryptography.fernet import Fernet
from vercel.blob import sync as blob


DEVICE_ENDPOINT = "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode"
TOKEN_ENDPOINT = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
SCOPES = "offline_access Files.ReadWrite User.Read openid profile email"
DEVICE_BLOB = "oauth/microsoft-device.json.enc"
TOKEN_BLOB = "oauth/microsoft-token.json.enc"


def _cipher() -> Fernet:
    return Fernet(os.environ["TOKEN_ENCRYPTION_KEY"].encode())


def _store_json(pathname: str, value: dict[str, object]) -> None:
    encrypted = _cipher().encrypt(json.dumps(value, separators=(",", ":")).encode())
    blob.put_blob(
        pathname,
        encrypted,
        access="private",
        content_type="application/octet-stream",
        allow_overwrite=True,
        cache_control_max_age=0,
    )


def _load_json(pathname: str) -> dict[str, object]:
    result = blob.get_blob(pathname, access="private")
    return json.loads(_cipher().decrypt(result.body))


def _post_form(url: str, fields: dict[str, str]) -> tuple[int, dict[str, object]]:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(fields).encode(),
        method="POST",
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        try:
            payload = json.loads(error.read())
        except (ValueError, json.JSONDecodeError):
            payload = {"error": "http_error"}
        return error.code, payload


def start_device_authorization() -> dict[str, object]:
    status, response = _post_form(
        DEVICE_ENDPOINT,
        {"client_id": os.environ["MS_CLIENT_ID"], "scope": SCOPES},
    )
    if status != 200 or "device_code" not in response:
        raise RuntimeError(f"Microsoft device authorization failed: {response.get('error', status)}")

    _store_json(
        DEVICE_BLOB,
        {
            "device_code": response["device_code"],
            "expires_at": int(time.time()) + int(response["expires_in"]),
            "interval": int(response.get("interval", 5)),
        },
    )
    return {
        "verification_uri": response["verification_uri"],
        "user_code": response["user_code"],
        "expires_in": response["expires_in"],
        "message": response.get("message"),
    }


def complete_device_authorization() -> dict[str, object]:
    device = _load_json(DEVICE_BLOB)
    if int(device["expires_at"]) <= int(time.time()):
        return {"authorized": False, "status": "expired_token"}

    status, response = _post_form(
        TOKEN_ENDPOINT,
        {
            "client_id": os.environ["MS_CLIENT_ID"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": str(device["device_code"]),
        },
    )
    if status != 200:
        oauth_error = str(response.get("error", "authorization_failed"))
        if oauth_error in {"authorization_pending", "slow_down", "authorization_declined", "expired_token"}:
            return {"authorized": False, "status": oauth_error}
        raise RuntimeError(f"Microsoft authorization failed: {oauth_error}")

    _store_token_response(response)
    return {"authorized": True, "status": "authorized"}


def _store_token_response(response: dict[str, object], previous_refresh_token: str | None = None) -> None:
    refresh_token = str(response.get("refresh_token") or previous_refresh_token or "")
    if not refresh_token:
        raise RuntimeError("Microsoft did not return a refresh token")
    _store_json(
        TOKEN_BLOB,
        {
            "access_token": response["access_token"],
            "refresh_token": refresh_token,
            "expires_at": int(time.time()) + int(response.get("expires_in", 3600)),
        },
    )


def get_access_token() -> str:
    token = _load_json(TOKEN_BLOB)
    if int(token.get("expires_at", 0)) > int(time.time()) + 300:
        return str(token["access_token"])

    refresh_token = str(token["refresh_token"])
    status, response = _post_form(
        TOKEN_ENDPOINT,
        {
            "client_id": os.environ["MS_CLIENT_ID"],
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": SCOPES,
        },
    )
    if status != 200:
        raise RuntimeError(f"Microsoft token refresh failed: {response.get('error', status)}")
    _store_token_response(response, previous_refresh_token=refresh_token)
    return str(response["access_token"])
