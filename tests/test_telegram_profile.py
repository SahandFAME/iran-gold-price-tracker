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


def test_start_restores_persistent_reply_menu(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    user = {"id": 123, "status": "approved", "role": "user"}
    monkeypatch.setattr(
        telegram_bot,
        "ensure_user",
        lambda sender: user,
    )
    monkeypatch.setattr(telegram_bot, "sync_bot_profile", lambda: False)
    monkeypatch.setattr(telegram_bot, "save_user", lambda value: None)
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
    assert sent[0]["reply_markup"]["keyboard"][0][0]["text"] == telegram_bot.REPORT_BUTTON
    assert user["prompt_message_id"] == 42


def test_report_removes_prompt_but_preserves_previous_reports(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    user = {
        "id": 123,
        "status": "approved",
        "role": "user",
        "prompt_message_id": 42,
        "ui_version": telegram_bot.UI_VERSION,
    }
    monkeypatch.setattr(telegram_bot, "ensure_user", lambda sender: user)
    monkeypatch.setattr(telegram_bot, "save_user", lambda value: None)
    monkeypatch.setattr(telegram_bot, "_report_text", lambda: "<b>REPORT</b>")
    monkeypatch.setattr(
        telegram_bot,
        "_api",
        lambda method, payload: calls.append((method, payload))
        or ({"ok": True, "result": {"message_id": 100}} if method == "sendMessage" else {"ok": True}),
    )

    telegram_bot._handle_callback(
        {
            "id": "callback-1",
            "from": {"id": 123},
            # This is an older report from the v2 interface and must survive.
            "message": {"message_id": 90, "chat": {"id": 123, "type": "private"}},
            "data": "nav:report",
        }
    )

    deleted_ids = [payload["message_id"] for method, payload in calls if method == "deleteMessage"]
    assert deleted_ids == [42]
    sent = [payload for method, payload in calls if method == "sendMessage"]
    assert len(sent) == 1
    assert sent[0]["text"] == "<b>REPORT</b>"
    assert "keyboard" in sent[0]["reply_markup"]
    assert "prompt_message_id" not in user


def test_user_list_replaces_previous_prompt(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    admin = {
        "id": 1,
        "status": "approved",
        "role": "admin",
        "root_admin": True,
        "prompt_message_id": 99,
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
        lambda method, payload: calls.append((method, payload))
        or ({"ok": True, "result": {"message_id": 100}} if method == "sendMessage" else {"ok": True}),
    )

    telegram_bot._handle_callback(
        {
            "id": "callback-2",
            "from": {"id": 1},
            "message": {"message_id": 99, "chat": {"id": 1, "type": "private"}},
            "data": "admin:users",
        }
    )

    deleted_ids = [payload["message_id"] for method, payload in calls if method == "deleteMessage"]
    assert deleted_ids == [99]
    sent = [payload for method, payload in calls if method == "sendMessage"]
    assert len(sent) == 1
    assert "کاربر ۱ از ۲" in sent[0]["text"]
    callbacks = sent[0]["reply_markup"]["inline_keyboard"]
    assert any(button["callback_data"] == "admin:users:2" for row in callbacks for button in row)
    assert admin["prompt_message_id"] == 100


def test_new_prompt_deletes_only_previous_prompt(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    user = {"id": 123, "status": "approved", "role": "user", "prompt_message_id": 12}
    monkeypatch.setattr(telegram_bot, "save_user", lambda value: None)

    def fake_api(method, payload):
        calls.append((method, payload))
        if method == "sendMessage":
            return {"ok": True, "result": {"message_id": 13}}
        return {"ok": True, "result": True}

    monkeypatch.setattr(telegram_bot, "_api", fake_api)
    telegram_bot._prompt(user, 123, "new prompt", telegram_bot._main_keyboard("user"))

    assert [method for method, _ in calls] == ["deleteMessage", "sendMessage"]
    assert user["prompt_message_id"] == 13


def test_v2_migration_forgets_panel_without_deleting_possible_report(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    user = {"id": 123, "status": "approved", "role": "user", "ui_version": 2, "panel_message_id": 77}
    monkeypatch.setattr(telegram_bot, "save_user", lambda value: None)
    monkeypatch.setattr(
        telegram_bot,
        "_api",
        lambda method, payload: calls.append((method, payload)) or {"ok": True},
    )

    telegram_bot._migrate_ui(user)

    assert calls == []
    assert "panel_message_id" not in user
    assert user["ui_version"] == telegram_bot.UI_VERSION


def test_report_text_contains_only_requested_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        telegram_bot,
        "get_report_data",
        lambda: {
            "tgju": {"available": True, "price_toman": 25_651_400},
            "workbook": {
                "date": "2026-11-01",
                "values": {
                    "D": 26_408_200,
                    "E": 20_304_774.867,
                    "F": 24_111_967.023,
                    "G": 29_676_267.105,
                    "H": 20_402_433.635,
                    "I": 18_547_666.941,
                    "K": 23_981_552.941,
                    "L": 25_129_213.846,
                },
            },
        },
    )

    text = telegram_bot._report_text()

    assert "<b>آخرین قیمت:</b> ۲۵,۶۵۱,۴۰۰ تومان" in text
    assert "قیمت آربیتراژی" in text
    assert "قیمت تعادلی جاری" in text
    assert "کران محاسباتی بالا" in text
    assert "کف محاسباتی" in text
    assert "قیمت حرکت چرخه ای" in text
    assert "محاسبات فایل اکسل" not in text
    assert "قیمت ثبت‌شده" not in text
    assert "ارزش حدودی مقطعی" not in text
    assert "میانگین ۸۵" not in text
