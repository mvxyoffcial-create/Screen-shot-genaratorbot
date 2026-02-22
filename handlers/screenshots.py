"""
handlers/screenshots.py
Auto screenshots (ss_2…ss_10) + manual screenshot flow.
Uses the user's own watermark_text from their settings.
"""
import logging
import os
import uuid
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)

from config import Config
from database import db
from utils.ffmpeg_utils import take_screenshots, make_tile_collage, _run
from utils.helpers import check_force_sub, send_force_sub_message, cleanup
from handlers.video import user_video_cache

logger = logging.getLogger(__name__)

# Users in manual-screenshot input mode
manual_ss_state: dict = {}   # user_id → True


# ── Auto screenshots (ss_2 … ss_10) ───────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^ss_(\d+)$"))
async def screenshot_count_cb(client: Client, cb: CallbackQuery):
    user = cb.from_user

    missing = await check_force_sub(client, user.id)
    if missing:
        await cb.answer("Join channels first!", show_alert=True)
        return await send_force_sub_message(cb.message)

    cache = user_video_cache.get(user.id)
    if not cache:
        return await cb.answer("❌ No video found. Please send a video first.", show_alert=True)

    count       = int(cb.matches[0].group(1))
    settings    = await db.get_settings(user.id)
    mode        = settings.get("screenshot_mode",  "even")
    upload_mode = settings.get("upload_mode",      "tile")
    watermark   = settings.get("watermark_photo",  False)
    wm_text     = settings.get("watermark_text",   Config.WATERMARK_TEXT)

    await cb.answer(f"📸 Generating {count} screenshots…")
    status = await cb.message.edit_text(
        f"⚙️ <b>Generating {count} screenshots…</b>\n"
        f"Mode: <code>{mode}</code> | "
        f"Watermark: <code>{'ON – ' + wm_text if watermark else 'OFF'}</code>"
    )

    try:
        paths = await take_screenshots(
            cache["file_path"],
            count,
            mode=mode,
            watermark=watermark,
            watermark_text=wm_text,
        )
    except Exception as e:
        logger.exception("Screenshot generation failed")
        return await status.edit_text(f"❌ Failed:\n<code>{e}</code>")

    if not paths:
        return await status.edit_text("❌ No screenshots were generated.")

    await status.edit_text(f"📤 <b>Uploading {len(paths)} screenshot(s)…</b>")

    try:
        if upload_mode == "tile" and len(paths) > 1:
            collage = await make_tile_collage(paths)
            await cb.message.reply_photo(
                photo=collage,
                caption=f"📸 <b>{count} Screenshots</b> | Mode: {mode}",
            )
            cleanup(collage)
        else:
            media_group = [
                InputMediaPhoto(
                    p,
                    caption=f"📸 Screenshot {i+1}/{len(paths)}" if i == 0 else "",
                )
                for i, p in enumerate(paths)
            ]
            for batch in range(0, len(media_group), 10):
                await cb.message.reply_media_group(media_group[batch:batch + 10])
    except Exception as e:
        logger.exception("Upload failed")
        await status.edit_text(f"❌ Upload error:\n<code>{e}</code>")
        return

    cleanup(*paths)
    await db.inc_screenshots()
    await status.delete()


# ── Manual screenshots ─────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex("^manual_ss$"))
async def manual_ss_start(client: Client, cb: CallbackQuery):
    cache = user_video_cache.get(cb.from_user.id)
    if not cache:
        return await cb.answer("❌ No video found. Please send a video first.", show_alert=True)

    manual_ss_state[cb.from_user.id] = True
    await cb.answer()
    await cb.message.edit_text(
        "✏️ <b>Manual Screenshot Mode</b>\n\n"
        "Send timestamps one per line:\n"
        "<code>HH:MM:SS</code>  |  <code>MM:SS</code>  |  <code>seconds</code>\n\n"
        "<b>Example:</b>\n"
        "<code>00:01:30\n00:05:00\n00:10:45</code>\n\n"
        "Send /cancel to abort.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_manual_ss")]]
        ),
    )


@Client.on_callback_query(filters.regex("^cancel_manual_ss$"))
async def cancel_manual_ss_cb(client: Client, cb: CallbackQuery):
    manual_ss_state.pop(cb.from_user.id, None)
    await cb.answer("Cancelled.")
    await cb.message.edit_text("❌ <b>Manual screenshot cancelled.</b>")


@Client.on_message(
    filters.private
    & filters.text
    & ~filters.command(["start", "help", "about", "settings", "cancel"])
)
async def manual_ss_input(client: Client, message: Message):
    user = message.from_user
    if not manual_ss_state.get(user.id):
        return

    cache = user_video_cache.get(user.id)
    if not cache:
        manual_ss_state.pop(user.id, None)
        return

    from utils.helpers import parse_time
    lines  = message.text.strip().splitlines()
    stamps, bad = [], []

    for line in lines:
        ts = parse_time(line.strip())
        if ts:
            stamps.append(ts)
        else:
            bad.append(line.strip())

    if bad:
        return await message.reply_text(
            f"❌ Could not parse: <code>{', '.join(bad)}</code>\n"
            "Use <code>HH:MM:SS</code>, <code>MM:SS</code>, or seconds."
        )
    if not stamps:
        return await message.reply_text("❌ No valid timestamps provided.")

    manual_ss_state.pop(user.id, None)

    settings    = await db.get_settings(user.id)
    watermark   = settings.get("watermark_photo", False)
    wm_text     = settings.get("watermark_text",  Config.WATERMARK_TEXT)
    upload_mode = settings.get("upload_mode",      "tile")

    status = await message.reply_text(f"⚙️ <b>Extracting {len(stamps)} frame(s)…</b>")

    out_dir = Path(Config.TEMP_DIR) / str(uuid.uuid4())
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []

    import asyncio
    async def _extract(i: int, ts: str):
        out_path = str(out_dir / f"manual_{i+1:03d}.png")
        cmd = [
            Config.FFMPEG_PATH,
            "-ss", ts,
            "-i", cache["file_path"],
            "-vframes", "1",
            "-q:v", "2",
            "-threads", "0",
            "-y", out_path,
        ]
        _, _, rc = await _run(cmd)
        if rc == 0 and os.path.isfile(out_path):
            if watermark:
                from utils.ffmpeg_utils import _watermark_photo
                return await _watermark_photo(out_path, wm_text)
            return out_path
        return None

    results = await asyncio.gather(*[_extract(i, ts) for i, ts in enumerate(stamps)])
    paths   = [p for p in results if p]

    if not paths:
        return await status.edit_text("❌ No frames extracted.")

    await status.edit_text(f"📤 <b>Uploading {len(paths)} screenshot(s)…</b>")

    try:
        if upload_mode == "tile" and len(paths) > 1:
            collage = await make_tile_collage(paths)
            await message.reply_photo(collage, caption="📸 <b>Manual Screenshots</b>")
            cleanup(collage)
        else:
            media_group = [
                InputMediaPhoto(
                    p,
                    caption=f"📸 Frame at <code>{stamps[i]}</code>" if i == 0 else "",
                )
                for i, p in enumerate(paths)
            ]
            for batch in range(0, len(media_group), 10):
                await message.reply_media_group(media_group[batch:batch + 10])
    except Exception as e:
        logger.exception("Upload failed")
        await status.edit_text(f"❌ Upload error:\n<code>{e}</code>")
        return

    cleanup(*paths)
    await db.inc_screenshots()
    await status.delete()
