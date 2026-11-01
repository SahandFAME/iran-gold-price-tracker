from __future__ import annotations

import html
import os

import httpx

from .report import REPORT_FIELDS, get_report_data
from .telegram_store import audit, create_user_by_id, ensure_user, find_user, get_user, list_users, save_user


REPORT_BUTTON = "📊 گزارش"
ADMIN_BUTTON = "⚙️ داشبورد مدیریت"
STATUS_LABELS = {"pending": "در انتظار تأیید", "approved": "فعال", "removed": "حذف‌شده"}
ROLE_LABELS = {"user": "کاربر", "admin": "مدیر"}
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _api(method: str, payload: dict[str, object]) -> dict[str, object]:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    response = httpx.post(
        f"https://api.telegram.org/bot{token}/{method}",
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram {method} failed")
    return result


def _send(chat_id: int, text: str, reply_markup: dict[str, object] | None = None) -> None:
    payload: dict[str, object] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    _api("sendMessage", payload)


def _answer(callback_id: str, text: str | None = None) -> None:
    payload: dict[str, object] = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    _api("answerCallbackQuery", payload)


def _main_keyboard(role: str) -> dict[str, object]:
    keyboard = [[{"text": REPORT_BUTTON}]]
    if role == "admin":
        keyboard.append([{"text": ADMIN_BUTTON}])
    return {"keyboard": keyboard, "resize_keyboard": True, "is_persistent": True}


def _admin_menu(chat_id: int) -> None:
    _send(
        chat_id,
        "<b>داشبورد مدیریت</b>\nگزینه موردنظر را انتخاب کنید:",
        {
            "inline_keyboard": [
                [{"text": "👥 فهرست کاربران", "callback_data": "admin:users"}],
                [{"text": "➕ افزودن عضو", "callback_data": "admin:add"}],
            ]
        },
    )


def _display_name(user: dict[str, object]) -> str:
    username = str(user.get("username") or "")
    name = " ".join(filter(None, (str(user.get("first_name") or ""), str(user.get("last_name") or ""))))
    return f"@{username}" if username else (name or str(user["id"]))


def _users_menu(chat_id: int) -> None:
    users = list_users()
    if not users:
        _send(chat_id, "هنوز کاربری ثبت نشده است.")
        return
    for user in users:
        status = str(user.get("status", "pending"))
        role = str(user.get("role", "user"))
        text = (
            f"<b>{html.escape(_display_name(user))}</b>\n"
            f"شناسه: <code>{user['id']}</code>\n"
            f"وضعیت: {STATUS_LABELS.get(status, status)}\n"
            f"نقش: {ROLE_LABELS.get(role, role)}"
        )
        actions: list[dict[str, str]] = []
        if status != "approved":
            actions.append({"text": "✅ تأیید", "callback_data": f"user:approve:{user['id']}"})
        elif role == "user":
            actions.append({"text": "⬆️ ارتقا به مدیر", "callback_data": f"user:promote:{user['id']}"})
        elif not user.get("root_admin"):
            actions.append({"text": "⬇️ تنزل به کاربر", "callback_data": f"user:demote:{user['id']}"})
        if not user.get("root_admin") and status != "removed":
            actions.append({"text": "🗑 حذف دسترسی", "callback_data": f"user:remove:{user['id']}"})
        _send(chat_id, text, {"inline_keyboard": [actions]} if actions else None)


def _fa_number(value: float | int) -> str:
    return f"{round(value):,}".translate(FA_DIGITS)


def _fa_date(value: str) -> str:
    return value.replace("-", "/").translate(FA_DIGITS)


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
                "<b>آخرین بیشترین قیمت TGJU</b>",
                f"{_fa_number(tgju['price_toman'])} تومان",
                f"تاریخ انتشار: {_fa_date(str(tgju['date']))}",
            ]
        )
    else:
        lines.extend(["", "⚠️ دریافت قیمت لحظه‌ای TGJU موقتاً امکان‌پذیر نیست."])
    lines.extend(
        [
            "",
            f"<b>محاسبات فایل اکسل — {_fa_date(str(workbook['date']))}</b>",
            f"قیمت ثبت‌شده: {_fa_number(values['D'])} تومان",
        ]
    )
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


def _approved(user: dict[str, object]) -> bool:
    return user.get("status") == "approved"


def _admin(user: dict[str, object]) -> bool:
    return _approved(user) and user.get("role") == "admin"


def _handle_message(message: dict[str, object]) -> None:
    sender = message.get("from") or {}
    chat = message.get("chat") or {}
    if not isinstance(sender, dict) or not isinstance(chat, dict) or chat.get("type") != "private":
        return
    chat_id = int(chat["id"])
    user = ensure_user(sender)
    text = str(message.get("text") or "").strip()

    if not _approved(user):
        _send(chat_id, "درخواست شما ثبت شد. برای استفاده از ربات باید یک مدیر دسترسی شما را تأیید کند.")
        return

    if _admin(user) and user.get("pending_action") == "add_member" and text:
        user.pop("pending_action", None)
        save_user(user)
        target = find_user(text)
        if target is None and text.isdigit():
            target = create_user_by_id(int(text))
        elif target is not None:
            target["status"] = "approved"
            target.setdefault("role", "user")
            save_user(target)
        if target is None:
            _send(
                chat_id,
                "این نام کاربری هنوز توسط ربات شناخته نشده است. از کاربر بخواهید یک‌بار /start را ارسال کند، یا شناسه عددی او را وارد کنید.",
            )
        else:
            audit(int(user["id"]), "approve", int(target["id"]))
            _send(chat_id, f"دسترسی {html.escape(_display_name(target))} با موفقیت فعال شد.")
        return

    if text == REPORT_BUTTON or text == "/report":
        _send(chat_id, "در حال آماده‌سازی گزارش…")
        _send(chat_id, _report_text(), _main_keyboard(str(user["role"])))
    elif text == ADMIN_BUTTON or text == "/admin":
        if _admin(user):
            _admin_menu(chat_id)
        else:
            _send(chat_id, "شما به بخش مدیریت دسترسی ندارید.", _main_keyboard(str(user["role"])))
    else:
        _send(
            chat_id,
            "خوش آمدید. برای مشاهده آخرین قیمت و محاسبات فایل، «گزارش» را انتخاب کنید.",
            _main_keyboard(str(user["role"])),
        )


def _handle_callback(callback: dict[str, object]) -> None:
    sender = callback.get("from") or {}
    message = callback.get("message") or {}
    chat = message.get("chat") if isinstance(message, dict) else {}
    if not isinstance(sender, dict) or not isinstance(chat, dict):
        return
    user = ensure_user(sender)
    callback_id = str(callback["id"])
    chat_id = int(chat["id"])
    if not _admin(user):
        _answer(callback_id, "دسترسی مدیریت ندارید.")
        return

    data = str(callback.get("data") or "")
    if data == "admin:users":
        _answer(callback_id)
        _users_menu(chat_id)
        return
    if data == "admin:add":
        user["pending_action"] = "add_member"
        save_user(user)
        _answer(callback_id)
        _send(
            chat_id,
            "نام کاربری (با یا بدون @) یا شناسه عددی کاربر را ارسال کنید.",
            {"force_reply": True, "input_field_placeholder": "@username یا 123456789"},
        )
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
    if target.get("root_admin") and action in {"demote", "remove"}:
        _answer(callback_id, "مدیر اصلی قابل حذف یا تنزل نیست.")
        return
    if action == "approve":
        target["status"] = "approved"
        target.setdefault("role", "user")
    elif action == "promote":
        target["status"] = "approved"
        target["role"] = "admin"
    elif action == "demote":
        target["role"] = "user"
    elif action == "remove":
        target["status"] = "removed"
        target["role"] = "user"
    else:
        _answer(callback_id, "عملیات نامعتبر است.")
        return
    save_user(target)
    audit(int(user["id"]), action, target_id)
    _answer(callback_id, "انجام شد.")
    _users_menu(chat_id)


def handle_update(update: dict[str, object]) -> None:
    message = update.get("message")
    callback = update.get("callback_query")
    if isinstance(message, dict):
        _handle_message(message)
    elif isinstance(callback, dict):
        _handle_callback(callback)
