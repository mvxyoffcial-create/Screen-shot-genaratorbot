"""
handlers/trim.py
Two-step trim flow: collect start time → end time → trim → upload.
"""
import logging
import os
import time

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from database import db
from utils.ffmpeg_utils import trim_video
from utils.helpers import (
    check_force_sub,
    send_force_sub_message,
    parse_time,
    progress_callback,
    cleanup,
)
from handlers.video import user_video_cache

logger = logging.getLogger(__name__)

# State: user_id -> {"step": "start"|"end", "start": str}
trim_state: dict = {}


@Client.on_callback_query(filters.regex("^trim$"))
async def trim_start_cb(client: Client, cb: CallbackQuery):
    user = cb.from_user

    cache = user_video_cache.get(user.id)
    if not cache:
        return await cb.answer("❌ No video found. Please send a video first.", show_alert=True)

    trim_state[user.id] = {"step": "start"}
    await cb.answer()
    await cb.message.edit_text(
        "✂️ <b>Trim Video – Step 1/2</b>\n\n"
        "Send the <b>start time</b>:\n"
        "<code>HH:MM:SS</code>  |  <code>MM:SS</code>  |  <code>seconds</code>\n\n"
        "Example: <code>00:01:30</code>",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_trim")]]
        ),
    )


@Client.on_callback_query(filters.regex("^cancel_trim$"))
async def cancel_trim_cb(client: Client, cb: CallbackQuery):
    trim_state.pop(cb.from_user.id, None)
    await cb.answer("Cancelled.")
    await cb.message.edit_text("❌ <b>Trim cancelled.</b>")


@Client.on_message(filters.private & filters.text & ~filters.command(["start","help","about","settings","cancel"]))
async def trim_input(client: Client, message: Message):
    user = message.from_user
    state = trim_state.get(user.id)
    if not state:
        return

    cache = user_video_cache.get(user.id)
    if not cache:
        trim_state.pop(user.id, None)
        return

    raw = message.text.strip()
    ts  = parse_time(raw)

    if ts is None:
        return await message.reply_text(
            "❌ Invalid time format. Use <code>HH:MM:SS</code>, <code>MM:SS</code> or seconds."
        )

    if state["step"] == "start":
        trim_state[user.id] = {"step": "end", "start": ts}
        await message.reply_text(
            f"✅ <b>Start time set:</b> <code>{ts}</code>\n\n"
            "✂️ <b>Step 2/2</b> – Now send the <b>end time</b>:\n"
            "<code>HH:MM:SS</code>  |  <code>MM:SS</code>  |  <code>seconds</code>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_trim")]]
            ),
        )
        return

    # End time received
    start_ts = state["start"]
    end_ts   = ts
    trim_state.pop(user.id, None)

    settings  = await db.get_settings(user.id)
    watermark = settings.get("watermark_video", False)

    status = await message.reply_text(
        f"✂️ <b>Trimming video…</b>\n"
        f"From <code>{start_ts}</code> to <code>{end_ts}</code>"
    )

    try:
        out_path = await trim_video(
            cache["file_path"],
            start=start_ts,
            end=end_ts,
            watermark=watermark,
        )
    except Exception as e:
        logger.exception("Trim failed")
        return await status.edit_text(f"❌ Trim failed:\n<code>{e}</code>")

    await status.edit_text("📤 <b>Uploading trimmed video…</b>")

    try:
        start_time = time.time()
        await message.reply_video(
            video=out_path,
            caption=(
                f"✂️ <b>Trimmed Video</b>\n"
                f"From: <code>{start_ts}</code>\n"
                f"To: <code>{end_ts}</code>"
            ),
            progress=progress_callback,
            progress_args=(status, "📤 <b>Uploading…</b>", start_time),
        )
    except Exception as e:
        logger.exception("Upload failed")
        await status.edit_text(f"❌ Upload error:\n<code>{e}</code>")
        return

    cleanup(out_path)
    await db.inc_trims()
    await status.delete()
