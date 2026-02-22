"""
handlers/media_info.py
Show detailed media information via ffprobe.
"""
import logging

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from database import db
from utils.ffmpeg_utils import format_media_info
from utils.helpers import check_force_sub, send_force_sub_message
from handlers.video import user_video_cache

logger = logging.getLogger(__name__)


@Client.on_callback_query(filters.regex("^media_info$"))
async def media_info_cb(client: Client, cb: CallbackQuery):
    user = cb.from_user

    missing = await check_force_sub(client, user.id)
    if missing:
        await cb.answer("Join channels first!", show_alert=True)
        return await send_force_sub_message(cb.message)

    cache = user_video_cache.get(user.id)
    if not cache:
        return await cb.answer("❌ No video found. Please send a video first.", show_alert=True)

    await cb.answer()

    info     = cache.get("info", {})
    if not info:
        from utils.ffmpeg_utils import get_media_info
        try:
            info = await get_media_info(cache["file_path"])
            cache["info"] = info
        except Exception as e:
            return await cb.message.edit_text(f"❌ Failed to read media info:\n<code>{e}</code>")

    text = format_media_info(info, cache.get("file_name", "video"))

    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_menu")]]
    )
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except Exception:
        await cb.message.reply_text(text, reply_markup=kb)

    await db.inc_mediainfo()


@Client.on_callback_query(filters.regex("^back_to_menu$"))
async def back_to_menu(client: Client, cb: CallbackQuery):
    from handlers.video import _build_main_keyboard, user_video_cache, _human_size, _hms
    cache = user_video_cache.get(cb.from_user.id)
    if not cache:
        return await cb.answer("Session expired. Send a video again.", show_alert=True)

    size_str = _human_size(cache.get("file_size", 0))
    dur_str  = _hms(cache.get("duration", 0))

    await cb.message.edit_text(
        f"✅ <b>Video Ready!</b>\n\n"
        f"📄 <b>Name:</b> <code>{cache.get('file_name', 'video')}</code>\n"
        f"📦 <b>Size:</b> <code>{size_str}</code>\n"
        f"⏱ <b>Duration:</b> <code>{dur_str}</code>\n\n"
        f"<b>Choose an action below 👇</b>",
        reply_markup=_build_main_keyboard(),
    )
    await cb.answer()
