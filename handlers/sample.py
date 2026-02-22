"""
handlers/sample.py
Generate a sample video clip from the middle of the video.
"""
import logging
import time

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

from database import db
from utils.ffmpeg_utils import generate_sample
from utils.helpers import (
    check_force_sub,
    send_force_sub_message,
    progress_callback,
    cleanup,
)
from handlers.video import user_video_cache

logger = logging.getLogger(__name__)


@Client.on_callback_query(filters.regex("^sample$"))
async def sample_cb(client: Client, cb: CallbackQuery):
    user = cb.from_user

    missing = await check_force_sub(client, user.id)
    if missing:
        await cb.answer("Join channels first!", show_alert=True)
        return await send_force_sub_message(cb.message)

    cache = user_video_cache.get(user.id)
    if not cache:
        return await cb.answer("❌ No video found. Please send a video first.", show_alert=True)

    settings = await db.get_settings(user.id)
    duration  = int(settings.get("sample_duration", 30))
    watermark = settings.get("watermark_video", False)

    await cb.answer(f"🎬 Generating {duration}s sample…")
    status = await cb.message.edit_text(
        f"🎬 <b>Generating {duration}-second sample clip…</b>\n"
        f"(Cutting from middle of video)"
    )

    try:
        out_path = await generate_sample(
            cache["file_path"],
            duration=duration,
            watermark=watermark,
        )
    except Exception as e:
        logger.exception("Sample generation failed")
        return await status.edit_text(f"❌ Sample generation failed:\n<code>{e}</code>")

    await status.edit_text("📤 <b>Uploading sample video…</b>")

    try:
        start_time = time.time()
        await cb.message.reply_video(
            video=out_path,
            caption=(
                f"🎬 <b>Sample Video</b>\n"
                f"Duration: <code>{duration}s</code> | "
                f"Watermark: <code>{'ON' if watermark else 'OFF'}</code>"
            ),
            progress=progress_callback,
            progress_args=(status, "📤 <b>Uploading…</b>", start_time),
        )
    except Exception as e:
        logger.exception("Upload failed")
        await status.edit_text(f"❌ Upload error:\n<code>{e}</code>")
        return

    cleanup(out_path)
    await db.inc_samples()
    await status.delete()
