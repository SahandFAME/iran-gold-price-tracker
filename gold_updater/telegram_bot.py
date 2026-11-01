from __future__ import annotations

import html

from .report import REPORT_FIELDS, get_report_data
from .telegram_api import telegram_api
from .telegram_profile import PENDING_START_MESSAGE, START_MESSAGE, sync_bot_profile
from .telegram_store import audit, create_user_by_id, ensure_user, find_user, get_user, list_users, save_user


REPORT_BUTTON = "📊 گزارش"
ADMIN_BUTTON = "⚙️ داشبورد مدیریت"
STATUS_LABELS = {"pending": "در انتظار تأیید", "approved": "فعال", "removed": "حذف‌شده"}
ROLE_LABELS = {"user": "کاربر", "admin": "مدیر"}
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
UI_VERSION = 5
MAIN_MENU_MESSAGE = "<b>منوی اصلی</b>\nگزینه موردنظر را انتخاب کنید:"


def _api(method: str, payload: dict[str, object]) -> dict[str, object]:
    return telegram_api(method, payload)


def _message_payload(
    chat_id: int,
    text: str,
    reply_markup: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return payload


def _send(chat_id: int, text: str, reply_markup: dict[str, object] | None = None) -> int:
    response = _api("sendMessage", _message_payload(chat_id, text, reply_markup))
    result = response.get("result")
    if not isinstance(result, dict) or "message_id" not in result:
        raise RuntimeError("Telegram sendMessage returned no message_id")
    return int(result["message_id"])


def _delete(chat_id: int, message_id: int | None) -> None:
    if not message_id:
        return
    try:
        _api("deleteMessage", {"chat_id": chat_id, "message_id": message_id})
    except RuntimeError:
        pass


def _answer(callback_id: str, text: str | None = None) -> None:
    payload: dict[str, object] = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    _api("answerCallbackQuery", payload)


def _edit_request_notification(
    chat_id: int,
    message_id: int | None,
    target: dict[str, object],
    decision: str,
    actor: dict[str, object] | None = None,
) -> None:
    if not message_id:
        return
    actor_text = f"\nمدیر: {html.escape(_display_name(actor))}" if actor else ""
    text = (
        "<b>درخواست دسترسی</b>\n\n"
        f"کاربر: <b>{html.escape(_display_name(target))}</b>\n"
        f"شناسه: <code>{target['id']}</code>\n\n"
        f"{decision}{actor_text}"
    )
    payload = _message_payload(chat_id, text, {"inline_keyboard": []})
    payload["message_id"] = message_id
    try:
        _api("editMessageText", payload)
    except RuntimeError:
        pass


def _notify_admins_of_request(requester: dict[str, object]) -> None:
    text = (
        "<b>درخواست دسترسی جدید</b>\n\n"
        f"کاربر: <b>{html.escape(_display_name(requester))}</b>\n"
        f"نام کاربری: "
        f"{html.escape('@' + str(requester['username'])) if requester.get('username') else 'ثبت نشده'}\n"
        f"شناسه: <code>{requester['id']}</code>"
    )
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ تأیید", "callback_data": f"request:approve:{requester['id']}"},
                {"text": "❌ رد", "callback_data": f"request:deny:{requester['id']}"},
            ]
        ]
    }
    try:
        admins = [item for item in list_users() if _admin(item)]
    except Exception as error:
        print(f"Unable to list admins for access request: {type(error).__name__}: {error}", flush=True)
        return
    for admin in admins:
        try:
            _send(int(admin["id"]), text, keyboard)
        except RuntimeError as error:
            print(f"Unable to notify Telegram admin {admin['id']}: {error}", flush=True)


def _migrate_ui(user: dict[str, object], chat_id: int) -> None:
    if user.get("ui_version") == UI_VERSION:
        return

    previous_version = int(user.get("ui_version") or 0)
    if previous_version == 3:
        # v3 tracked only non-report prompts, so it is safe to replace this
        # message when the next answer is sent.
        prompt_id = int(user.pop("prompt_message_id", 0) or 0)
        if prompt_id:
            user["answer_message_id"] = prompt_id
    else:
        user.pop("prompt_message_id", None)

    # A v2 panel may be a historical report, so never delete it during migration.
    user.pop("panel_message_id", None)
    del chat_id
    user["ui_version"] = UI_VERSION
    save_user(user)


def _clear_answer(user: dict[str, object], chat_id: int) -> None:
    answer_id = int(user.get("answer_message_id") or 0) or None
    _delete(chat_id, answer_id)
    if answer_id:
        user.pop("answer_message_id", None)
        save_user(user)


def _answer_message(
    user: dict[str, object],
    chat_id: int,
    text: str,
    reply_markup: dict[str, object] | None = None,
    *,
    message_id: int | None = None,
) -> None:
    del message_id  # Reports are untracked and must survive callbacks from them.
    _clear_answer(user, chat_id)
    user["answer_message_id"] = _send(chat_id, text, reply_markup)
    save_user(user)


def _main_keyboard(role: str) -> dict[str, object]:
    rows = [[{"text": REPORT_BUTTON}]]
    if role == "admin":
        rows.append([{"text": ADMIN_BUTTON}])
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


def _show_home(
    user: dict[str, object],
    chat_id: int,
    *,
    message_id: int | None = None,
    welcome: bool = False,
) -> None:
    text = START_MESSAGE if welcome else MAIN_MENU_MESSAGE
    _answer_message(user, chat_id, text, _main_keyboard(str(user["role"])), message_id=message_id)


def _admin_menu(
    user: dict[str, object],
    chat_id: int,
    *,
    message_id: int | None = None,
    notice: str | None = None,
) -> None:
    users = list_users()
    approved_count = sum(item.get("status") == "approved" for item in users)
    pending_count = sum(item.get("status") == "pending" for item in users)
    admin_count = sum(_admin(item) for item in users)
    removed_count = sum(item.get("status") == "removed" for item in users)
    prefix = f"{notice}\n\n" if notice else ""
    _answer_message(
        user,
        chat_id,
        (
            f"{prefix}<b>پنل مدیریت</b>\n\n"
            f"کاربران مجاز: {_fa_number(approved_count)}\n"
            f"درخواست‌های در انتظار: {_fa_number(pending_count)}\n"
            f"مدیران: {_fa_number(admin_count)}\n"
            f"دسترسی‌های لغوشده: {_fa_number(removed_count)}"
        ),
        {
            "inline_keyboard": [
                [
                    {"text": "✅ کاربران مجاز", "callback_data": "admin:approved"},
                    {"text": "⏳ درخواست‌های دسترسی", "callback_data": "admin:requests"},
                ],
                [
                    {"text": "👥 مدیریت کاربران و نقش‌ها", "callback_data": "admin:users"},
                    {"text": "➕ افزودن عضو", "callback_data": "admin:add"},
                ],
                [{"text": "🏠 بازگشت به منوی اصلی", "callback_data": "nav:home"}],
            ]
        },
        message_id=message_id,
    )


def _display_name(user: dict[str, object]) -> str:
    username = str(user.get("username") or "")
    name = " ".join(filter(None, (str(user.get("first_name") or ""), str(user.get("last_name") or ""))))
    return f"@{username}" if username else (name or str(user["id"]))


def _users_menu(
    actor: dict[str, object],
    chat_id: int,
    *,
    message_id: int | None = None,
    selected_id: int | None = None,
    status_filter: str | None = None,
) -> None:
    all_users = list_users()
    users = [item for item in all_users if item.get("status") == status_filter] if status_filter else all_users
    title = {
        "approved": "کاربران مجاز",
        "pending": "درخواست‌های دسترسی",
    }.get(status_filter, "مدیریت کاربران و نقش‌ها")
    callback_prefix = {
        "approved": "admin:approved",
        "pending": "admin:requests",
    }.get(status_filter, "admin:users")
    if not users:
        _answer_message(
            actor,
            chat_id,
            f"<b>{title}</b>\n\nموردی برای نمایش وجود ندارد.",
            {
                "inline_keyboard": [
                    [{"text": "↩️ بازگشت به مدیریت", "callback_data": "nav:admin"}],
                    [{"text": "🏠 منوی اصلی", "callback_data": "nav:home"}],
                ]
            },
            message_id=message_id,
        )
        return

    index = next((i for i, item in enumerate(users) if int(item["id"]) == selected_id), 0)
    target = users[index]
    status = str(target.get("status", "pending"))
    role = str(target.get("role", "user"))
    text = (
        f"<b>{title}</b>\n"
        f"کاربر {_fa_number(index + 1)} از {_fa_number(len(users))}\n\n"
        f"<b>{html.escape(_display_name(target))}</b>\n"
        f"شناسه: <code>{target['id']}</code>\n"
        f"وضعیت: {STATUS_LABELS.get(status, status)}\n"
        f"نقش: {ROLE_LABELS.get(role, role)}"
    )

    rows: list[list[dict[str, str]]] = []
    actions: list[dict[str, str]] = []
    if status == "pending":
        actions.append({"text": "✅ تأیید", "callback_data": f"user:approve:{target['id']}"})
        actions.append({"text": "❌ رد", "callback_data": f"user:deny:{target['id']}"})
    elif status == "removed":
        actions.append({"text": "✅ فعال‌سازی مجدد", "callback_data": f"user:approve:{target['id']}"})
    elif role == "user":
        actions.append({"text": "⬆️ ارتقا به مدیر", "callback_data": f"user:promote:{target['id']}"})
    elif not target.get("root_admin"):
        actions.append({"text": "⬇️ تنزل به کاربر", "callback_data": f"user:demote:{target['id']}"})
    if not target.get("root_admin") and status != "removed":
        actions.append({"text": "🗑 حذف دسترسی", "callback_data": f"user:remove:{target['id']}"})
    if actions:
        rows.append(actions)

    if len(users) > 1:
        previous_user = users[(index - 1) % len(users)]
        next_user = users[(index + 1) % len(users)]
        rows.append(
            [
                {"text": "◀️ قبلی", "callback_data": f"{callback_prefix}:{previous_user['id']}"},
                {"text": "بعدی ▶️", "callback_data": f"{callback_prefix}:{next_user['id']}"},
            ]
        )
    rows.extend(
        [
            [{"text": "↩️ بازگشت به مدیریت", "callback_data": "nav:admin"}],
            [{"text": "🏠 منوی اصلی", "callback_data": "nav:home"}],
        ]
    )
    _answer_message(actor, chat_id, text, {"inline_keyboard": rows}, message_id=message_id)


def _add_member_prompt(
    user: dict[str, object],
    chat_id: int,
    *,
    message_id: int | None = None,
    error: str | None = None,
) -> None:
    prefix = f"{error}\n\n" if error else ""
    _answer_message(
        user,
        chat_id,
        f"{prefix}<b>افزودن عضو</b>\n\nنام کاربری (با یا بدون @) یا شناسه عددی کاربر را ارسال کنید.",
        {
            "inline_keyboard": [
                [{"text": "↩️ انصراف و بازگشت", "callback_data": "admin:cancel_add"}],
                [{"text": "🏠 منوی اصلی", "callback_data": "nav:home"}],
            ]
        },
        message_id=message_id,
    )


def _fa_number(value: float | int) -> str:
    return f"{round(value):,}".translate(FA_DIGITS)


def _report_text() -> str:
    report = get_report_data()
    tgju = report["tgju"]
    workbook = report["workbook"]
    values = workbook["values"]
    lines = ["<b>گزارش تحلیلی طلای ۱۸ عیار</b>"]
    if tgju.get("available"):
        lines.extend(
            [
                "",
                f"<b>آخرین قیمت:</b> {_fa_number(tgju['price_toman'])} تومان",
            ]
        )
    else:
        lines.extend(["", "⚠️ دریافت قیمت لحظه‌ای TGJU موقتاً امکان‌پذیر نیست."])
    for column, label, explanation in REPORT_FIELDS:
        lines.extend(
            [
                "",
                f"<b>{label}:</b> {_fa_number(values[column])} تومان",
                explanation,
            ]
        )
    lines.extend(["", "<i>این گزارش صرفاً تحلیلی است و توصیه خرید یا فروش محسوب نمی‌شود.</i>"])
    return "\n".join(lines)


def _show_report(
    user: dict[str, object],
    chat_id: int,
    *,
    message_id: int | None = None,
) -> None:
    del message_id
    _clear_answer(user, chat_id)
    _send(chat_id, _report_text(), _main_keyboard(str(user["role"])))


def _approved(user: dict[str, object]) -> bool:
    return user.get("status") == "approved"


def _admin(user: dict[str, object]) -> bool:
    return _approved(user) and user.get("role") == "admin"


def _show_pending(
    user: dict[str, object],
    chat_id: int,
    *,
    message_id: int | None = None,
) -> None:
    _answer_message(user, chat_id, PENDING_START_MESSAGE, message_id=message_id)


def _notify_user_of_decision(target: dict[str, object], approved: bool) -> None:
    if approved:
        text = (
            "✅ <b>درخواست دسترسی شما تأیید شد.</b>\n\n"
            "اکنون می‌توانید از گزارش‌های ربات استفاده کنید."
        )
        keyboard = _main_keyboard(str(target.get("role", "user")))
    else:
        text = "❌ <b>درخواست دسترسی شما توسط مدیر رد شد.</b>"
        keyboard = {"remove_keyboard": True}
    try:
        _answer_message(target, int(target["id"]), text, keyboard)
    except RuntimeError as error:
        print(f"Unable to notify Telegram user {target['id']}: {error}", flush=True)


def _handle_message(message: dict[str, object]) -> None:
    sender = message.get("from") or {}
    chat = message.get("chat") or {}
    if not isinstance(sender, dict) or not isinstance(chat, dict) or chat.get("type") != "private":
        return
    chat_id = int(chat["id"])
    user = ensure_user(sender)
    text = str(message.get("text") or "").strip()
    is_start = text == "/start" or text.startswith("/start ")
    _migrate_ui(user, chat_id)

    if is_start:
        try:
            sync_bot_profile()
        except Exception as error:
            print(f"Telegram profile sync failed: {type(error).__name__}: {error}", flush=True)

    if not _approved(user):
        if is_start:
            if user.get("status") == "removed":
                user["status"] = "pending"
                user["role"] = "user"
                save_user(user)
            _notify_admins_of_request(user)
        _show_pending(user, chat_id)
        return

    if is_start:
        user.pop("pending_action", None)
        save_user(user)
        _show_home(user, chat_id, welcome=True)
        return

    if _admin(user) and user.get("pending_action") == "add_member" and text:
        target = find_user(text)
        if target is None and text.isdigit():
            target = create_user_by_id(int(text))
        elif target is not None:
            target["status"] = "approved"
            target.setdefault("role", "user")
            save_user(target)
        if target is None:
            _add_member_prompt(
                user,
                chat_id,
                error=(
                    "⚠️ این نام کاربری هنوز توسط ربات شناخته نشده است. از کاربر بخواهید یک‌بار "
                    "/start را ارسال کند، یا شناسه عددی او را وارد کنید."
                ),
            )
        else:
            user.pop("pending_action", None)
            save_user(user)
            audit(int(user["id"]), "approve", int(target["id"]))
            _admin_menu(
                user,
                chat_id,
                notice=f"✅ دسترسی {html.escape(_display_name(target))} با موفقیت فعال شد.",
            )
        return

    if text == REPORT_BUTTON or text == "/report":
        _show_report(user, chat_id)
    elif text == ADMIN_BUTTON or text == "/admin":
        if _admin(user):
            _admin_menu(user, chat_id)
        else:
            _answer_message(
                user,
                chat_id,
                "شما به بخش مدیریت دسترسی ندارید.",
                _main_keyboard(str(user["role"])),
            )
    elif text in {"منوی اصلی", "🏠 منوی اصلی"}:
        _show_home(user, chat_id)
    else:
        _show_home(user, chat_id)


def _handle_callback(callback: dict[str, object]) -> None:
    sender = callback.get("from") or {}
    message = callback.get("message") or {}
    chat = message.get("chat") if isinstance(message, dict) else {}
    if not isinstance(sender, dict) or not isinstance(chat, dict):
        return
    user = ensure_user(sender)
    _migrate_ui(user, int(chat["id"]))
    callback_id = str(callback["id"])
    chat_id = int(chat["id"])
    message_id = int(message.get("message_id") or 0) or None
    data = str(callback.get("data") or "")

    if not _approved(user):
        _answer(callback_id, "دسترسی شما هنوز تأیید نشده است.")
        _show_pending(user, chat_id, message_id=message_id)
        return

    if data == "nav:home":
        _answer(callback_id)
        user.pop("pending_action", None)
        save_user(user)
        _show_home(user, chat_id, message_id=message_id)
        return
    if data == "nav:report":
        _answer(callback_id)
        _show_report(user, chat_id, message_id=message_id)
        return
    if data == "nav:admin":
        if not _admin(user):
            _answer(callback_id, "دسترسی مدیریت ندارید.")
            return
        _answer(callback_id)
        user.pop("pending_action", None)
        save_user(user)
        _admin_menu(user, chat_id, message_id=message_id)
        return

    if not _admin(user):
        _answer(callback_id, "دسترسی مدیریت ندارید.")
        return

    if data.startswith("request:"):
        parts = data.split(":")
        if len(parts) != 3 or parts[1] not in {"approve", "deny"} or not parts[2].isdigit():
            _answer(callback_id, "درخواست نامعتبر است.")
            return
        action, target_id = parts[1], int(parts[2])
        target = get_user(target_id)
        if target is None:
            _answer(callback_id, "کاربر پیدا نشد.")
            return
        if target.get("status") != "pending":
            decision = "✅ قبلاً تأیید شده است." if target.get("status") == "approved" else "❌ قبلاً رد شده است."
            _answer(callback_id, "این درخواست قبلاً بررسی شده است.")
            _edit_request_notification(chat_id, message_id, target, decision)
            return
        approved = action == "approve"
        target["status"] = "approved" if approved else "removed"
        target["role"] = "user"
        save_user(target)
        audit(int(user["id"]), action, target_id)
        _answer(callback_id, "درخواست تأیید شد." if approved else "درخواست رد شد.")
        _edit_request_notification(
            chat_id,
            message_id,
            target,
            "✅ دسترسی تأیید شد." if approved else "❌ درخواست رد شد.",
            user,
        )
        _notify_user_of_decision(target, approved)
        return

    menu_filters = {
        "admin:users": None,
        "admin:approved": "approved",
        "admin:requests": "pending",
    }
    menu_prefix = next((prefix for prefix in menu_filters if data == prefix or data.startswith(prefix + ":")), None)
    if menu_prefix:
        selected_id: int | None = None
        parts = data.split(":")
        if len(parts) == 3 and parts[2].isdigit():
            selected_id = int(parts[2])
        _answer(callback_id)
        _users_menu(
            user,
            chat_id,
            message_id=message_id,
            selected_id=selected_id,
            status_filter=menu_filters[menu_prefix],
        )
        return
    if data == "admin:add":
        _answer(callback_id)
        user["pending_action"] = "add_member"
        save_user(user)
        _add_member_prompt(user, chat_id, message_id=message_id)
        return
    if data == "admin:cancel_add":
        _answer(callback_id)
        user.pop("pending_action", None)
        save_user(user)
        _admin_menu(user, chat_id, message_id=message_id)
        return

    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "user" or not parts[2].isdigit():
        _answer(callback_id, "درخواست نامعتبر است.")
        return
    action, target_id = parts[1], int(parts[2])
    target = get_user(target_id)
    if target is None:
        _answer(callback_id, "کاربر پیدا نشد.")
        return
    if target.get("root_admin") and action in {"demote", "remove", "deny"}:
        _answer(callback_id, "مدیر اصلی قابل حذف یا تنزل نیست.")
        return
    if action == "approve":
        target["status"] = "approved"
        target["role"] = "user"
    elif action == "promote":
        target["status"] = "approved"
        target["role"] = "admin"
    elif action == "demote":
        target["role"] = "user"
    elif action == "remove":
        target["status"] = "removed"
        target["role"] = "user"
    elif action == "deny":
        target["status"] = "removed"
        target["role"] = "user"
    else:
        _answer(callback_id, "عملیات نامعتبر است.")
        return
    save_user(target)
    audit(int(user["id"]), action, target_id)
    _answer(callback_id, "انجام شد.")
    if action in {"approve", "deny"}:
        _notify_user_of_decision(target, action == "approve")
    _users_menu(user, chat_id, message_id=message_id, selected_id=target_id)


def handle_update(update: dict[str, object]) -> None:
    message = update.get("message")
    callback = update.get("callback_query")
    if isinstance(message, dict):
        _handle_message(message)
    elif isinstance(callback, dict):
        _handle_callback(callback)
