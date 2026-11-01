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


def test_start_sends_full_intro_and_keyboard(monkeypatch) -> None:
    sent: list[tuple[int, str, object]] = []
    monkeypatch.setattr(
        telegram_bot,
        "ensure_user",
        lambda sender: {"id": sender["id"], "status": "approved", "role": "user"},
    )
    monkeypatch.setattr(telegram_bot, "sync_bot_profile", lambda: False)
    monkeypatch.setattr(
        telegram_bot,
        "_send",
        lambda chat_id, text, reply_markup=None: sent.append((chat_id, text, reply_markup)),
    )

    telegram_bot._handle_message(
        {
            "from": {"id": 123},
            "chat": {"id": 123, "type": "private"},
            "text": "/start",
        }
    )

    assert sent[0][1] == telegram_profile.START_MESSAGE
    assert sent[0][2]["keyboard"][0][0]["text"] == telegram_bot.REPORT_BUTTON
