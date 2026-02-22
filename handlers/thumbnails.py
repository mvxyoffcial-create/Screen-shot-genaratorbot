"""
handlers/thumbnails.py
Extract multiple thumbnails from the video.
"""
import logging

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)

from database import db
from utils.ffmpeg_utils import extract_thumbnails, make_tile_collage
from utils.helpers import check_force_sub, send_force_sub_message, cleanup
from handlers.video import user_video_cache

logger = logging.getLogger(__name__)


@Client.on_callback_query(filters.regex("^thumbnails$"))
async def thumbnails_cb(client: Client, cb: CallbackQuery):
    user = cb.from_user

    missing = await check_force_sub(client, user.id)
    if missing:
        await cb.answer("Join channels first!", show_alert=True)
        return await send_force_sub_message(cb.message)

    cache = user_video_cache.get(user.id)
    if not cache:
        return await cb.answer("❌ No video found. Please send a video first.", show_alert=True)

    # Ask how many thumbnails
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("1", callback_data="thumb_1"),
                InlineKeyboardButton("2", callback_data="thumb_2"),
                InlineKeyboardButton("4", callback_data="thumb_4"),
            ],
            [
                InlineKeyboardButton("6", callback_data="thumb_6"),
                InlineKeyboardButton("8", callback_data="thumb_8"),
                InlineKeyboardButton("10", callback_data="thumb_10"),
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="back_to_menu")],
        ]
    )
    await cb.answer()
    await cb.message.edit_text(
        "🖼 <b>Get Thumbnails</b>\n\nHow many thumbnails would you like?",
        reply_markup=kb,
    )


@Client.on_callback_query(filters.regex(r"^thumb_(\d+)$"))
async def do_thumbnails(client: Client, cb: CallbackQuery):
    user  = cb.from_user
    count = int(cb.matches[0].group(1))

    cache = user_video_cache.get(user.id)
    if not cache:
        return await cb.answer("❌ Session expired. Send a video again.", show_alert=True)

    await cb.answer(f"🖼 Extracting {count} thumbnail(s)…")
    status = await cb.message.edit_text(f"🖼 <b>Extracting {count} thumbnail(s)…</b>")

    try:
        paths = await extract_thumbnails(cache["file_path"], count=count)
    except Exception as e:
        logger.exception("Thumbnail extraction failed")
        return await status.edit_text(f"❌ Extraction failed:\n<code>{e}</code>")

    if not paths:
        return await status.edit_text("❌ No thumbnails extracted.")

    await status.edit_text(f"📤 <b>Uploading {len(paths)} thumbnail(s)…</b>")

    settings = await db.get_settings(user.id)
    upload_mode = settings.get("upload_mode", "tile")

    try:
        if upload_mode == "tile" and len(paths) > 1:
            collage = await make_tile_collage(paths)
            await cb.message.reply_photo(
                collage,
                caption=f"🖼 <b>{count} Thumbnails</b>",
            )
            cleanup(collage)
        else:
            media_group = [
                InputMediaPhoto(p, caption=f"🖼 Thumbnail {i+1}" if i == 0 else "")
                for i, p in enumerate(paths)
            ]
            for batch_start in range(0, len(media_group), 10):
                await cb.message.reply_media_group(media_group[batch_start:batch_start + 10])
    except Exception as e:
        logger.exception("Thumbnail upload failed")
        await status.edit_text(f"❌ Upload error:\n<code>{e}</code>")
        return

    cleanup(*paths)
    await db.inc_thumbnails()
    await status.delete()
