from __future__ import annotations

import datetime as dt
import json
import os
import uuid

from cryptography.fernet import Fernet
from vercel.blob import sync as blob


USER_PREFIX = "telegram/users/"
AUDIT_PREFIX = "telegram/audit/"


def _cipher() -> Fernet:
    return Fernet(os.environ["TOKEN_ENCRYPTION_KEY"].encode())


def _path(user_id: int) -> str:
    return f"{USER_PREFIX}{user_id}.json.enc"


def _encode(value: dict[str, object]) -> bytes:
    return _cipher().encrypt(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode())


def _decode(value: bytes) -> dict[str, object]:
    return json.loads(_cipher().decrypt(value))


def get_user(user_id: int) -> dict[str, object] | None:
    try:
        return _decode(blob.get_blob(_path(user_id), access="private").body)
    except blob.BlobNotFoundError:
        return None


def save_user(user: dict[str, object]) -> None:
    user["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    blob.put_blob(
        _path(int(user["id"])),
        _encode(user),
        access="private",
        content_type="application/octet-stream",
        allow_overwrite=True,
        cache_control_max_age=0,
    )


def ensure_user(sender: dict[str, object]) -> dict[str, object]:
    user_id = int(sender["id"])
    user = get_user(user_id) or {
        "id": user_id,
        "status": "pending",
        "role": "user",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    user["username"] = str(sender.get("username") or "")
    user["first_name"] = str(sender.get("first_name") or "")
    user["last_name"] = str(sender.get("last_name") or "")
    if str(user_id) == os.environ.get("TELEGRAM_ADMIN_ID", ""):
        user["status"] = "approved"
        user["role"] = "admin"
        user["root_admin"] = True
    save_user(user)
    return user


def list_users() -> list[dict[str, object]]:
    users: list[dict[str, object]] = []
    for item in blob.query_blobs(prefix=USER_PREFIX, page_size=200):
        try:
            users.append(_decode(blob.get_blob(item.pathname, access="private").body))
        except (blob.BlobNotFoundError, ValueError):
            continue
    return sorted(users, key=lambda user: (str(user.get("status")), int(user["id"])))


def find_user(reference: str) -> dict[str, object] | None:
    normalized = reference.strip().removeprefix("@").casefold()
    if normalized.isdigit():
        return get_user(int(normalized))
    for user in list_users():
        if str(user.get("username", "")).casefold() == normalized:
            return user
    return None


def create_user_by_id(user_id: int) -> dict[str, object]:
    user = get_user(user_id) or {
        "id": user_id,
        "username": "",
        "first_name": "",
        "last_name": "",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    user["status"] = "approved"
    user["role"] = "user"
    save_user(user)
    return user


def audit(actor_id: int, action: str, target_id: int) -> None:
    event = {
        "actor_id": actor_id,
        "action": action,
        "target_id": target_id,
        "at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    pathname = f"{AUDIT_PREFIX}{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex}.json.enc"
    blob.put_blob(
        pathname,
        _encode(event),
        access="private",
        content_type="application/octet-stream",
        cache_control_max_age=0,
    )
