from __future__ import annotations

import json
from pathlib import Path

from .telegram_api import telegram_api
from .telegram_store import get_profile_version, save_profile_version


PROFILE_VERSION = "2026-11-01-v1"
BOT_NAME = "دیدبان طلا و سکه | گزارش بازار"
BOT_SHORT_DESCRIPTION = "رصد روزانه قیمت طلا و سکه، همراه با گزارش‌ها و شاخص‌های تحلیلی بازار 📊"
BOT_DESCRIPTION = (
    "«دیدبان طلا و سکه» سامانه‌ای برای مشاهده و تحلیل قیمت طلا و مسکوکات است. "
    "آخرین قیمت طلای ۱۸ عیار، قیمت‌های محاسبه‌شده، شاخص آربیتراژ و توضیح هر شاخص را "
    "در قالب گزارشی ساده و کاربردی دریافت کنید.\n\n"
    "اطلاعات به‌صورت روزانه به‌روزرسانی می‌شوند و قیمت‌های ثبت‌شده هفته گذشته نیز با "
    "منبع قیمت بررسی خواهند شد. در نسخه‌های بعدی، قیمت سکه امامی، بهار آزادی و سایر "
    "نرخ‌های مهم بازار اضافه می‌شود."
)
START_MESSAGE = (
    "سلام، به <b>دیدبان طلا و سکه</b> خوش آمدید 👋\n\n"
    "اینجا می‌توانید آخرین قیمت طلای ۱۸ عیار، شاخص‌های تحلیلی و قیمت‌های محاسبه‌شده "
    "مانند «قیمت آربیتراژ» را همراه با توضیح مختصر مشاهده کنید.\n\n"
    "اطلاعات به‌صورت روزانه به‌روزرسانی و داده‌های هفته گذشته نیز برای شناسایی "
    "مغایرت‌ها بررسی می‌شوند.\n\n"
    "برای ادامه، گزینه «📊 گزارش» را انتخاب کنید.\n\n"
    "<i>⚠️ اطلاعات این ربات صرفاً جهت اطلاع‌رسانی و تحلیل بازار است و توصیه خرید یا "
    "فروش محسوب نمی‌شود.</i>"
)
PENDING_START_MESSAGE = (
    "سلام، به <b>دیدبان طلا و سکه</b> خوش آمدید 👋\n\n"
    "درخواست دسترسی شما ثبت شد. برای استفاده از گزارش‌های قیمت و شاخص‌های تحلیلی، "
    "یک مدیر باید حساب شما را تأیید کند."
)

AVATAR_PATH = Path(__file__).resolve().parents[1] / "assets" / "didban-tala-sekke-profile.jpg"


def sync_bot_profile(*, force: bool = False) -> bool:
    """Synchronize fixed public bot branding once per profile version."""

    if not force and get_profile_version() == PROFILE_VERSION:
        return False

    for language_code in ("", "fa"):
        telegram_api("setMyName", {"name": BOT_NAME, "language_code": language_code})
        telegram_api(
            "setMyShortDescription",
            {"short_description": BOT_SHORT_DESCRIPTION, "language_code": language_code},
        )
        telegram_api(
            "setMyDescription",
            {"description": BOT_DESCRIPTION, "language_code": language_code},
        )

    telegram_api(
        "setMyProfilePhoto",
        {
            "photo": json.dumps(
                {"type": "static", "photo": "attach://avatar"},
                separators=(",", ":"),
            )
        },
        files={"avatar": (AVATAR_PATH.name, AVATAR_PATH.read_bytes(), "image/jpeg")},
    )
    save_profile_version(PROFILE_VERSION)
    return True
