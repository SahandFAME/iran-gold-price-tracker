from __future__ import annotations

from gold_updater import telegram_bot, telegram_profile


def test_profile_fields_fit_telegram_limits() -> None:
    assert len(telegram_profile.BOT_NAME) <= 64
    assert len(telegram_profile.BOT_SHORT_DESCRIPTION) <= 120
    assert len(telegram_profile.BOT_DESCRIPTION) <= 512


def test_profile_sync_is_versioned(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object], object]] = []
    monkeypatch.setattr(telegram_profile, "get_profile_version", lambda: telegram_profile.PROFILE_VERSION)
    monkeypatch.setattr(
        telegram_profile,
        "telegram_api",
        lambda method, payload, files=None: calls.append((method, payload, files)),
    )

    assert telegram_profile.sync_bot_profile() is False
    assert calls == []


def test_profile_sync_sets_text_and_first_avatar(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object], object]] = []
    saved: list[str] = []
    monkeypatch.setattr(telegram_profile, "get_profile_version", lambda: None)
    monkeypatch.setattr(telegram_profile, "save_profile_version", saved.append)
    monkeypatch.setattr(
        telegram_profile,
        "telegram_api",
        lambda method, payload, files=None: calls.append((method, payload, files)) or {"ok": True},
    )

    assert telegram_profile.sync_bot_profile() is True
    assert [call[0] for call in calls].count("setMyName") == 2
    assert [call[0] for call in calls].count("setMyDescription") == 2
    assert [call[0] for call in calls].count("setMyShortDescription") == 2
    photo_call = calls[-1]
    assert photo_call[0] == "setMyProfilePhoto"
    avatar = photo_call[2]["avatar"]
    assert avatar[0] == "didban-tala-sekke-profile.jpg"
    assert avatar[1].startswith(b"\xff\xd8\xff")
    assert avatar[2] == "image/jpeg"
    assert saved == [telegram_profile.PROFILE_VERSION]


def test_start_sends_one_inline_panel(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    user = {"id": 123, "status": "approved", "role": "user"}
    monkeypatch.setattr(
        telegram_bot,
        "ensure_user",
        lambda sender: user,
    )
    monkeypatch.setattr(telegram_bot, "sync_bot_profile", lambda: False)
    monkeypatch.setattr(telegram_bot, "save_user", lambda value: None)
    monkeypatch.setattr(telegram_bot, "_remove_legacy_keyboard", lambda value, chat_id: None)
    monkeypatch.setattr(
        telegram_bot,
        "_api",
        lambda method, payload: calls.append((method, payload))
        or ({"ok": True, "result": {"message_id": 42}} if method == "sendMessage" else {"ok": True}),
    )

    telegram_bot._handle_message(
        {
            "from": {"id": 123},
            "chat": {"id": 123, "type": "private"},
            "message_id": 7,
            "text": "/start",
        }
    )

    sent = [payload for method, payload in calls if method == "sendMessage"]
    assert len(sent) == 1
    assert sent[0]["text"] == telegram_profile.START_MESSAGE
    assert sent[0]["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == "nav:report"
    assert user["panel_message_id"] == 42


def test_report_button_edits_existing_panel_without_new_message(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    user = {
        "id": 123,
        "status": "approved",
        "role": "user",
        "panel_message_id": 42,
        "ui_version": telegram_bot.UI_VERSION,
    }
    monkeypatch.setattr(telegram_bot, "ensure_user", lambda sender: user)
    monkeypatch.setattr(telegram_bot, "save_user", lambda value: None)
    monkeypatch.setattr(telegram_bot, "_report_text", lambda: "<b>REPORT</b>")
    monkeypatch.setattr(
        telegram_bot,
        "_api",
        lambda method, payload: calls.append((method, payload)) or {"ok": True, "result": True},
    )

    telegram_bot._handle_callback(
        {
            "id": "callback-1",
            "from": {"id": 123},
            "message": {"message_id": 42, "chat": {"id": 123, "type": "private"}},
            "data": "nav:report",
        }
    )

    assert not [call for call in calls if call[0] == "sendMessage"]
    edits = [payload for method, payload in calls if method == "editMessageText"]
    assert len(edits) == 1
    assert edits[0]["message_id"] == 42
    assert edits[0]["text"] == "<b>REPORT</b>"
    callbacks = edits[0]["reply_markup"]["inline_keyboard"]
    assert any(button["callback_data"] == "nav:home" for row in callbacks for button in row)


def test_user_list_is_paginated_in_same_panel(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    admin = {
        "id": 1,
        "status": "approved",
        "role": "admin",
        "root_admin": True,
        "panel_message_id": 99,
        "ui_version": telegram_bot.UI_VERSION,
    }
    users = [
        admin,
        {"id": 2, "status": "pending", "role": "user", "username": "new_user"},
    ]
    monkeypatch.setattr(telegram_bot, "ensure_user", lambda sender: admin)
    monkeypatch.setattr(telegram_bot, "list_users", lambda: users)
    monkeypatch.setattr(telegram_bot, "save_user", lambda value: None)
    monkeypatch.setattr(
        telegram_bot,
        "_api",
        lambda method, payload: calls.append((method, payload)) or {"ok": True, "result": True},
    )

    telegram_bot._handle_callback(
        {
            "id": "callback-2",
            "from": {"id": 1},
            "message": {"message_id": 99, "chat": {"id": 1, "type": "private"}},
            "data": "admin:users",
        }
    )

    edits = [payload for method, payload in calls if method == "editMessageText"]
    assert len(edits) == 1
    assert "کاربر ۱ از ۲" in edits[0]["text"]
    callbacks = edits[0]["reply_markup"]["inline_keyboard"]
    assert any(button["callback_data"] == "admin:users:2" for row in callbacks for button in row)
    assert not [call for call in calls if call[0] == "sendMessage"]


def test_stale_panel_is_deleted_before_replacement(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    user = {"id": 123, "status": "approved", "role": "user", "panel_message_id": 12}
    monkeypatch.setattr(telegram_bot, "save_user", lambda value: None)

    def fake_api(method, payload):
        calls.append((method, payload))
        if method == "editMessageText":
            raise RuntimeError("message to edit not found")
        if method == "sendMessage":
            return {"ok": True, "result": {"message_id": 13}}
        return {"ok": True, "result": True}

    monkeypatch.setattr(telegram_bot, "_api", fake_api)
    telegram_bot._panel(user, 123, "new panel", telegram_bot._main_keyboard("user"))

    assert [method for method, _ in calls] == ["editMessageText", "deleteMessage", "sendMessage"]
    assert user["panel_message_id"] == 13


def test_legacy_keyboard_cleanup_message_is_immediately_deleted(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    user = {"id": 123, "status": "approved", "role": "user"}
    monkeypatch.setattr(telegram_bot, "save_user", lambda value: None)
    monkeypatch.setattr(
        telegram_bot,
        "_api",
        lambda method, payload: calls.append((method, payload))
        or ({"ok": True, "result": {"message_id": 77}} if method == "sendMessage" else {"ok": True}),
    )

    telegram_bot._remove_legacy_keyboard(user, 123)

    assert [method for method, _ in calls] == ["sendMessage", "deleteMessage"]
    assert calls[0][1]["reply_markup"] == {"remove_keyboard": True}
    assert user["ui_version"] == telegram_bot.UI_VERSION
