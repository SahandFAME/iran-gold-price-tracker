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


def test_start_keeps_user_message_and_shows_persistent_bottom_menu(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    user = {
        "id": 123,
        "status": "approved",
        "role": "user",
        "ui_version": telegram_bot.UI_VERSION,
    }
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
    assert sent[0]["reply_markup"]["is_persistent"] is True
    assert not [payload for method, payload in calls if method == "deleteMessage"]
    assert user["answer_message_id"] == 42


def test_report_removes_last_answer_but_preserves_previous_reports(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    user = {
        "id": 123,
        "status": "approved",
        "role": "user",
        "answer_message_id": 42,
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
    assert sent[0]["reply_markup"]["keyboard"][0][0]["text"] == telegram_bot.REPORT_BUTTON
    assert "answer_message_id" not in user


def test_user_list_replaces_previous_answer(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    admin = {
        "id": 1,
        "status": "approved",
        "role": "admin",
        "root_admin": True,
        "answer_message_id": 99,
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
    assert admin["answer_message_id"] == 100


def test_new_answer_deletes_only_previous_answer(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    user = {"id": 123, "status": "approved", "role": "user", "answer_message_id": 12}
    monkeypatch.setattr(telegram_bot, "save_user", lambda value: None)

    def fake_api(method, payload):
        calls.append((method, payload))
        if method == "sendMessage":
            return {"ok": True, "result": {"message_id": 13}}
        return {"ok": True, "result": True}

    monkeypatch.setattr(telegram_bot, "_api", fake_api)
    telegram_bot._answer_message(user, 123, "new answer", telegram_bot._main_keyboard("user"))

    assert [method for method, _ in calls] == ["deleteMessage", "sendMessage"]
    assert user["answer_message_id"] == 13


def test_v2_migration_forgets_panel_without_deleting_possible_report(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    user = {"id": 123, "status": "approved", "role": "user", "ui_version": 2, "panel_message_id": 77}
    monkeypatch.setattr(telegram_bot, "save_user", lambda value: None)
    monkeypatch.setattr(
        telegram_bot,
        "_api",
        lambda method, payload: calls.append((method, payload))
        or ({"ok": True, "result": {"message_id": 88}} if method == "sendMessage" else {"ok": True}),
    )

    telegram_bot._migrate_ui(user, 123)

    assert calls == []
    assert "panel_message_id" not in user
    assert user["ui_version"] == telegram_bot.UI_VERSION


def test_v3_migration_replaces_only_tracked_prompt(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    user = {"id": 123, "status": "approved", "role": "user", "ui_version": 3, "prompt_message_id": 77}
    monkeypatch.setattr(telegram_bot, "save_user", lambda value: None)
    monkeypatch.setattr(
        telegram_bot,
        "_api",
        lambda method, payload: calls.append((method, payload))
        or ({"ok": True, "result": {"message_id": 88}} if method == "sendMessage" else {"ok": True}),
    )

    telegram_bot._migrate_ui(user, 123)

    assert user["answer_message_id"] == 77
    assert "prompt_message_id" not in user
    assert calls == []


def test_admin_bottom_menu_contains_report_and_dashboard() -> None:
    keyboard = telegram_bot._main_keyboard("admin")

    assert keyboard == {
        "keyboard": [[{"text": telegram_bot.REPORT_BUTTON}], [{"text": telegram_bot.ADMIN_BUTTON}]],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def test_pending_start_notifies_every_admin_with_approval_buttons(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    requester = {
        "id": 22,
        "status": "pending",
        "role": "user",
        "username": "new_user",
        "first_name": "New",
        "ui_version": telegram_bot.UI_VERSION,
    }
    admins = [
        {"id": 1, "status": "approved", "role": "admin", "root_admin": True},
        {"id": 2, "status": "approved", "role": "admin"},
        requester,
    ]
    next_message_id = iter((101, 102, 103))
    monkeypatch.setattr(telegram_bot, "ensure_user", lambda sender: requester)
    monkeypatch.setattr(telegram_bot, "list_users", lambda: admins)
    monkeypatch.setattr(telegram_bot, "save_user", lambda value: None)
    monkeypatch.setattr(telegram_bot, "sync_bot_profile", lambda: False)
    monkeypatch.setattr(
        telegram_bot,
        "_api",
        lambda method, payload: calls.append((method, payload))
        or ({"ok": True, "result": {"message_id": next(next_message_id)}} if method == "sendMessage" else {"ok": True}),
    )

    telegram_bot._handle_message(
        {
            "from": {"id": 22, "username": "new_user", "first_name": "New"},
            "chat": {"id": 22, "type": "private"},
            "message_id": 7,
            "text": "/start",
        }
    )

    sent = [payload for method, payload in calls if method == "sendMessage"]
    assert [payload["chat_id"] for payload in sent] == [1, 2, 22]
    buttons = sent[0]["reply_markup"]["inline_keyboard"][0]
    assert [button["callback_data"] for button in buttons] == ["request:approve:22", "request:deny:22"]
    assert "درخواست دسترسی شما ثبت شد" in sent[2]["text"]


def test_main_menu_does_not_repeat_welcome_message(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    user = {"id": 1, "status": "approved", "role": "admin", "ui_version": telegram_bot.UI_VERSION}
    monkeypatch.setattr(telegram_bot, "ensure_user", lambda sender: user)
    monkeypatch.setattr(telegram_bot, "save_user", lambda value: None)
    monkeypatch.setattr(
        telegram_bot,
        "_api",
        lambda method, payload: calls.append((method, payload))
        or ({"ok": True, "result": {"message_id": 50}} if method == "sendMessage" else {"ok": True}),
    )

    telegram_bot._handle_message(
        {"from": {"id": 1}, "chat": {"id": 1, "type": "private"}, "message_id": 9, "text": "منوی اصلی"}
    )

    sent = [payload for method, payload in calls if method == "sendMessage"]
    assert sent[0]["text"] == telegram_bot.MAIN_MENU_MESSAGE
    assert sent[0]["text"] != telegram_profile.START_MESSAGE


def test_admin_dashboard_shows_relevant_counts_and_actions(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    admin = {"id": 1, "status": "approved", "role": "admin", "root_admin": True}
    users = [
        admin,
        {"id": 2, "status": "approved", "role": "user"},
        {"id": 3, "status": "pending", "role": "user"},
        {"id": 4, "status": "removed", "role": "user"},
    ]
    monkeypatch.setattr(telegram_bot, "list_users", lambda: users)
    monkeypatch.setattr(telegram_bot, "save_user", lambda value: None)
    monkeypatch.setattr(
        telegram_bot,
        "_api",
        lambda method, payload: calls.append((method, payload))
        or ({"ok": True, "result": {"message_id": 60}} if method == "sendMessage" else {"ok": True}),
    )

    telegram_bot._admin_menu(admin, 1)

    payload = next(payload for method, payload in calls if method == "sendMessage")
    assert "کاربران مجاز: ۲" in payload["text"]
    assert "درخواست‌های در انتظار: ۱" in payload["text"]
    assert "مدیران: ۱" in payload["text"]
    assert "دسترسی‌های لغوشده: ۱" in payload["text"]
    assert "مشاوران مالی" not in payload["text"]
    callbacks = [
        button["callback_data"]
        for row in payload["reply_markup"]["inline_keyboard"]
        for button in row
    ]
    assert callbacks == ["admin:approved", "admin:requests", "admin:users", "admin:add", "nav:home"]


def test_admin_can_approve_request_and_user_is_notified(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    saved: list[dict[str, object]] = []
    audits: list[tuple[int, str, int]] = []
    admin = {
        "id": 1,
        "status": "approved",
        "role": "admin",
        "root_admin": True,
        "ui_version": telegram_bot.UI_VERSION,
    }
    target = {
        "id": 22,
        "status": "pending",
        "role": "user",
        "username": "new_user",
        "answer_message_id": 44,
    }
    monkeypatch.setattr(telegram_bot, "ensure_user", lambda sender: admin)
    monkeypatch.setattr(telegram_bot, "get_user", lambda user_id: target)
    monkeypatch.setattr(telegram_bot, "save_user", lambda value: saved.append(dict(value)))
    monkeypatch.setattr(telegram_bot, "audit", lambda actor, action, target_id: audits.append((actor, action, target_id)))
    monkeypatch.setattr(
        telegram_bot,
        "_api",
        lambda method, payload: calls.append((method, payload))
        or ({"ok": True, "result": {"message_id": 70}} if method == "sendMessage" else {"ok": True}),
    )

    telegram_bot._handle_callback(
        {
            "id": "approve-1",
            "from": {"id": 1},
            "message": {"message_id": 55, "chat": {"id": 1, "type": "private"}},
            "data": "request:approve:22",
        }
    )

    assert target["status"] == "approved"
    assert audits == [(1, "approve", 22)]
    assert any(method == "editMessageText" and payload["message_id"] == 55 for method, payload in calls)
    assert any(
        method == "sendMessage"
        and payload["chat_id"] == 22
        and "درخواست دسترسی شما تأیید شد" in payload["text"]
        and "keyboard" in payload["reply_markup"]
        for method, payload in calls
    )
    assert any(method == "deleteMessage" and payload["message_id"] == 44 for method, payload in calls)


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
