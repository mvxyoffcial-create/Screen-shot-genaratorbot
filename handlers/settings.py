"""
handlers/settings.py  —  /settings inline panel
Includes custom watermark text: user taps button → sends their own text → saved.
"""
import logging

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import Config
from database import db
from utils.helpers import check_force_sub, send_force_sub_message

logger = logging.getLogger(__name__)

# Tracks users currently entering a custom watermark text
# user_id -> message_id of the settings msg (to edit it back after)
_wm_input_state: dict = {}


def _tick(val: bool) -> str:
    return "✅" if val else "☑️"


async def _settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    s = await db.get_settings(user_id)

    upload_mode  = s.get("upload_mode",    "tile")
    ss_mode      = s.get("screenshot_mode","even")
    sample_dur   = s.get("sample_duration", 30)
    wm_video     = s.get("watermark_video", False)
    wm_photo     = s.get("watermark_photo", False)
    wm_text      = s.get("watermark_text",  Config.WATERMARK_TEXT)

    return InlineKeyboardMarkup(
        [
            # ── Upload mode ──────────────────────────────────────────────────
            [InlineKeyboardButton("📸 Upload Mode", callback_data="noop")],
            [
                InlineKeyboardButton(
                    f"{'✅ ' if upload_mode == 'tile'     else ''}🖼 Tile Collage",
                    callback_data="set_upload_tile",
                ),
                InlineKeyboardButton(
                    f"{'✅ ' if upload_mode == 'separate' else ''}📎 Separate",
                    callback_data="set_upload_separate",
                ),
            ],
            # ── Screenshot mode ──────────────────────────────────────────────
            [InlineKeyboardButton("⚙️ Screenshot Mode", callback_data="noop")],
            [
                InlineKeyboardButton(
                    f"{'✅ ' if ss_mode == 'even'   else ''}📏 Even",
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
            # ── Watermark toggles ────────────────────────────────────────────
            [InlineKeyboardButton("💧 Watermark", callback_data="noop")],
            [
                InlineKeyboardButton(
                    f"{_tick(wm_video)} On Video",
                    callback_data="toggle_wm_video",
                ),
                InlineKeyboardButton(
                    f"{_tick(wm_photo)} On Photos",
                    callback_data="toggle_wm_photo",
                ),
            ],
            # ── Custom watermark text ────────────────────────────────────────
            [
                InlineKeyboardButton(
                    f"✏️ Watermark Text: {wm_text[:20]}{'…' if len(wm_text) > 20 else ''}",
                    callback_data="set_wm_text",
                )
            ],
            # ── Reset watermark to default ────────────────────────────────────
            [
                InlineKeyboardButton(
                    "🔄 Reset Watermark Text",
                    callback_data="reset_wm_text",
                )
            ],
            # ── Close ────────────────────────────────────────────────────────
            [InlineKeyboardButton("❌ Close", callback_data="close_settings")],
        ]
    )


async def _render_settings(user_id: int, cb: CallbackQuery) -> None:
    kb   = await _settings_keyboard(user_id)
    text = (
        "⚙️ <b>Your Settings</b>\n\n"
        "All changes save instantly.\n\n"
        "💧 <b>Watermark Text</b> — tap the button to set your own text "
        "(e.g. <code>@YourChannel</code> or your name)."
    )
    try:
        await cb.edit_message_text(text, reply_markup=kb)
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
        "⚙️ <b>Your Settings</b>\n\n"
        "All changes save instantly.\n\n"
        "💧 <b>Watermark Text</b> — tap the button to set your own text "
        "(e.g. <code>@YourChannel</code> or your name).",
        reply_markup=kb,
    )


# ── Upload mode ───────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex("^set_upload_(tile|separate)$"))
async def set_upload_mode(client: Client, cb: CallbackQuery):
    val = cb.matches[0].group(1)
    await db.update_setting(cb.from_user.id, "upload_mode", val)
    await cb.answer(f"Upload mode → {val}")
    await _render_settings(cb.from_user.id, cb)


# ── Screenshot mode ───────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex("^set_ss_(even|random)$"))
async def set_ss_mode(client: Client, cb: CallbackQuery):
    val = cb.matches[0].group(1)
    await db.update_setting(cb.from_user.id, "screenshot_mode", val)
    await cb.answer(f"Screenshot mode → {val}")
    await _render_settings(cb.from_user.id, cb)


# ── Sample duration ───────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^set_sample_(\d+)$"))
async def set_sample_duration(client: Client, cb: CallbackQuery):
    val = int(cb.matches[0].group(1))
    await db.update_setting(cb.from_user.id, "sample_duration", val)
    await cb.answer(f"Sample duration → {val}s")
    await _render_settings(cb.from_user.id, cb)


# ── Watermark toggles ─────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex("^toggle_wm_(video|photo)$"))
async def toggle_watermark(client: Client, cb: CallbackQuery):
    key_map = {"video": "watermark_video", "photo": "watermark_photo"}
    which   = cb.matches[0].group(1)
    db_key  = key_map[which]

    settings = await db.get_settings(cb.from_user.id)
    new_val  = not settings.get(db_key, False)

    await db.update_setting(cb.from_user.id, db_key, new_val)
    await cb.answer(f"Watermark on {which} → {'ON ✅' if new_val else 'OFF'}")
    await _render_settings(cb.from_user.id, cb)


# ── Custom watermark text: start input flow ───────────────────────────────────

@Client.on_callback_query(filters.regex("^set_wm_text$"))
async def set_wm_text_start(client: Client, cb: CallbackQuery):
    user = cb.from_user
    _wm_input_state[user.id] = cb.message.id   # remember settings msg id
    await cb.answer()

    settings = await db.get_settings(user.id)
    current  = settings.get("watermark_text", Config.WATERMARK_TEXT)

    await cb.message.edit_text(
        f"✏️ <b>Set Your Watermark Text</b>\n\n"
        f"Current: <code>{current}</code>\n\n"
        f"Send your new watermark text now.\n"
        f"Max <b>{Config.WATERMARK_MAX_LEN} characters</b>.\n\n"
        f"Examples:\n"
        f"  <code>@YourChannel</code>\n"
        f"  <code>Your Name</code>\n"
        f"  <code>© 2025 MyBrand</code>\n\n"
        f"Send /cancel to go back.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_wm_input")]]
        ),
    )


@Client.on_callback_query(filters.regex("^cancel_wm_input$"))
async def cancel_wm_input_cb(client: Client, cb: CallbackQuery):
    _wm_input_state.pop(cb.from_user.id, None)
    await cb.answer("Cancelled.")
    await _render_settings(cb.from_user.id, cb)


# ── Custom watermark text: receive the text ───────────────────────────────────

@Client.on_message(
    filters.private
    & filters.text
    & ~filters.command(["start", "help", "about", "settings", "cancel"])
)
async def wm_text_input(client: Client, message: Message):
    user = message.from_user
    if user.id not in _wm_input_state:
        return   # not waiting for watermark input — let other handlers deal

    _wm_input_state.pop(user.id)

    raw = message.text.strip()

    if len(raw) > Config.WATERMARK_MAX_LEN:
        return await message.reply_text(
            f"❌ Too long! Max <b>{Config.WATERMARK_MAX_LEN}</b> characters.\n"
            f"Your text: <b>{len(raw)}</b> chars. Try again with /settings."
        )

    await db.update_setting(user.id, "watermark_text", raw)

    kb = await _settings_keyboard(user.id)
    await message.reply_text(
        f"✅ <b>Watermark text updated!</b>\n\n"
        f"New watermark: <code>{raw}</code>\n\n"
        f"⚙️ <b>Your Settings</b>\n\n"
        "All changes save instantly.",
        reply_markup=kb,
    )


# ── Reset watermark to default ────────────────────────────────────────────────

@Client.on_callback_query(filters.regex("^reset_wm_text$"))
async def reset_wm_text(client: Client, cb: CallbackQuery):
    await db.update_setting(cb.from_user.id, "watermark_text", Config.WATERMARK_TEXT)
    await cb.answer(f"✅ Reset to {Config.WATERMARK_TEXT}")
    await _render_settings(cb.from_user.id, cb)


# ── Misc ──────────────────────────────────────────────────────────────────────

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
