"""
handlers/settings.py
/settings command – full interactive inline settings panel.
"""
import logging

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from database import db
from utils.helpers import check_force_sub, send_force_sub_message

logger = logging.getLogger(__name__)


def _tick(val: bool) -> str:
    return "✅" if val else "☑️"


def _mode_label(val: str, option: str) -> str:
    return f"{'▶️ ' if val == option else ''}{option.title()}"


async def _settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    s = await db.get_settings(user_id)

    upload_mode   = s.get("upload_mode", "tile")
    ss_mode       = s.get("screenshot_mode", "even")
    sample_dur    = s.get("sample_duration", 30)
    wm_video      = s.get("watermark_video", False)
    wm_photo      = s.get("watermark_photo", False)

    return InlineKeyboardMarkup(
        [
            # ── Upload mode ──────────────────────────────────────────────────
            [InlineKeyboardButton("📸 Screenshot Upload Mode", callback_data="noop")],
            [
                InlineKeyboardButton(
                    f"{'✅ ' if upload_mode == 'tile' else ''}🖼 Tile Collage",
                    callback_data="set_upload_tile",
                ),
                InlineKeyboardButton(
                    f"{'✅ ' if upload_mode == 'separate' else ''}📎 Separate Photos",
                    callback_data="set_upload_separate",
                ),
            ],
            # ── Screenshot mode ──────────────────────────────────────────────
            [InlineKeyboardButton("⚙️ Screenshot Generation Mode", callback_data="noop")],
            [
                InlineKeyboardButton(
                    f"{'✅ ' if ss_mode == 'even' else ''}📏 Even",
                    callback_data="set_ss_even",
                ),
                InlineKeyboardButton(
                    f"{'✅ ' if ss_mode == 'random' else ''}🎲 Random",
                    callback_data="set_ss_random",
                ),
            ],
            # ── Sample duration ──────────────────────────────────────────────
            [InlineKeyboardButton(f"⏱ Sample Duration: {sample_dur}s", callback_data="noop")],
            [
                InlineKeyboardButton("15s", callback_data="set_sample_15"),
                InlineKeyboardButton("30s", callback_data="set_sample_30"),
                InlineKeyboardButton("45s", callback_data="set_sample_45"),
                InlineKeyboardButton("60s", callback_data="set_sample_60"),
            ],
            # ── Watermarks ───────────────────────────────────────────────────
            [InlineKeyboardButton("💧 Watermark Settings", callback_data="noop")],
            [
                InlineKeyboardButton(
                    f"{_tick(wm_video)} Watermark on Video",
                    callback_data="toggle_wm_video",
                ),
                InlineKeyboardButton(
                    f"{_tick(wm_photo)} Watermark on Photos",
                    callback_data="toggle_wm_photo",
                ),
            ],
            # ── Close ────────────────────────────────────────────────────────
            [InlineKeyboardButton("❌ Close", callback_data="close_settings")],
        ]
    )


async def _render_settings(user_id: int, obj) -> None:
    """Edit message in place with fresh settings keyboard."""
    kb   = await _settings_keyboard(user_id)
    text = "⚙️ <b>Your Settings</b>\n\nAll changes are saved instantly to your account."
    try:
        if hasattr(obj, "edit_message_text"):
            # CallbackQuery
            await obj.edit_message_text(text, reply_markup=kb)
        else:
            await obj.edit_text(text, reply_markup=kb)
    except Exception:
        pass


# ── /settings command ──────────────────────────────────────────────────────────

@Client.on_message(filters.command("settings") & filters.private)
async def settings_cmd(client: Client, message: Message):
    missing = await check_force_sub(client, message.from_user.id)
    if missing:
        return await send_force_sub_message(message)

    kb = await _settings_keyboard(message.from_user.id)
    await message.reply_text(
        "⚙️ <b>Your Settings</b>\n\nAll changes are saved instantly to your account.",
        reply_markup=kb,
    )


# ── Setting callbacks ──────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex("^set_upload_(tile|separate)$"))
async def set_upload_mode(client: Client, cb: CallbackQuery):
    val = cb.matches[0].group(1)
    await db.update_setting(cb.from_user.id, "upload_mode", val)
    await cb.answer(f"Upload mode → {val}")
    await _render_settings(cb.from_user.id, cb)


@Client.on_callback_query(filters.regex("^set_ss_(even|random)$"))
async def set_ss_mode(client: Client, cb: CallbackQuery):
    val = cb.matches[0].group(1)
    await db.update_setting(cb.from_user.id, "screenshot_mode", val)
    await cb.answer(f"Screenshot mode → {val}")
    await _render_settings(cb.from_user.id, cb)


@Client.on_callback_query(filters.regex(r"^set_sample_(\d+)$"))
async def set_sample_duration(client: Client, cb: CallbackQuery):
    val = int(cb.matches[0].group(1))
    await db.update_setting(cb.from_user.id, "sample_duration", val)
    await cb.answer(f"Sample duration → {val}s")
    await _render_settings(cb.from_user.id, cb)


@Client.on_callback_query(filters.regex("^toggle_wm_(video|photo)$"))
async def toggle_watermark(client: Client, cb: CallbackQuery):
    key_map = {"video": "watermark_video", "photo": "watermark_photo"}
    which   = cb.matches[0].group(1)
    db_key  = key_map[which]

    settings  = await db.get_settings(cb.from_user.id)
    current   = settings.get(db_key, False)
    new_val   = not current

    await db.update_setting(cb.from_user.id, db_key, new_val)
    await cb.answer(f"Watermark on {which} → {'ON' if new_val else 'OFF'}")
    await _render_settings(cb.from_user.id, cb)


@Client.on_callback_query(filters.regex("^close_settings$"))
async def close_settings(client: Client, cb: CallbackQuery):
    await cb.answer()
    try:
        await cb.message.delete()
    except Exception:
        pass


@Client.on_callback_query(filters.regex("^noop$"))
async def noop_cb(client: Client, cb: CallbackQuery):
    await cb.answer()
