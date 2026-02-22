"""
handlers/screenshots.py
Handles screenshot generation callbacks and manual screenshot flow.
"""
import logging
import time

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from database import db
from utils.ffmpeg_utils import take_screenshots, make_tile_collage
from utils.helpers import check_force_sub, send_force_sub_message, cleanup
from handlers.video import user_video_cache

logger = logging.getLogger(__name__)

# Tracks users who are in "manual screenshots" mode
manual_ss_state: dict = {}   # user_id -> True


# ── Auto screenshot callbacks (ss_2 … ss_10) ──────────────────────────────────

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

    count     = int(cb.matches[0].group(1))
    settings  = await db.get_settings(user.id)
    mode      = settings.get("screenshot_mode", "even")
    upload_mode = settings.get("upload_mode", "tile")
    watermark   = settings.get("watermark_photo", False)

    await cb.answer(f"📸 Generating {count} screenshots…")
    status = await cb.message.edit_text(
        f"⚙️ <b>Generating {count} screenshots...</b>\n"
        f"Mode: <code>{mode}</code> | Watermark: <code>{'ON' if watermark else 'OFF'}</code>"
    )

    try:
        paths = await take_screenshots(
            cache["file_path"],
            count,
            mode=mode,
            watermark=watermark,
        )
    except Exception as e:
        logger.exception("Screenshot generation failed")
        return await status.edit_text(f"❌ Failed to generate screenshots:\n<code>{e}</code>")

    if not paths:
        return await status.edit_text("❌ No screenshots were generated.")

    await status.edit_text(f"📤 <b>Uploading {len(paths)} screenshot(s)…</b>")

    try:
        if upload_mode == "tile" and len(paths) > 1:
            # Make collage
            collage = await make_tile_collage(paths)
            await cb.message.reply_photo(
                photo=collage,
                caption=f"📸 <b>{count} Screenshots</b> | Mode: {mode}",
            )
            cleanup(collage)
        else:
            # Send separately as media group
            from pyrogram.types import InputMediaPhoto
            media_group = [
                InputMediaPhoto(p, caption=f"📸 Screenshot {i+1}/{len(paths)}" if i == 0 else "")
                for i, p in enumerate(paths)
            ]
            # Send in batches of 10 (Telegram limit)
            for batch_start in range(0, len(media_group), 10):
                batch = media_group[batch_start:batch_start + 10]
                await cb.message.reply_media_group(batch)
    except Exception as e:
        logger.exception("Upload failed")
        await status.edit_text(f"❌ Upload error: {e}")
        return

    cleanup(*paths)
    await db.inc_screenshots()
    await status.delete()


# ── Manual screenshots ─────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex("^manual_ss$"))
async def manual_ss_start(client: Client, cb: CallbackQuery):
    user = cb.from_user

    cache = user_video_cache.get(user.id)
    if not cache:
        return await cb.answer("❌ No video found. Please send a video first.", show_alert=True)

    manual_ss_state[user.id] = True
    await cb.answer()
    await cb.message.edit_text(
        "✏️ <b>Manual Screenshot Mode</b>\n\n"
        "Send timestamps one per line in any of these formats:\n"
        "<code>HH:MM:SS</code>  |  <code>MM:SS</code>  |  <code>SS</code>\n\n"
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


@Client.on_message(filters.private & filters.text & ~filters.command(["start","help","about","settings","cancel"]))
async def manual_ss_input(client: Client, message: Message):
    user = message.from_user
    if not manual_ss_state.get(user.id):
        return  # Not in manual mode – ignore

    cache = user_video_cache.get(user.id)
    if not cache:
        manual_ss_state.pop(user.id, None)
        return

    # Parse timestamps
    from utils.helpers import parse_time
    lines  = message.text.strip().splitlines()
    stamps = []
    bad    = []

    for line in lines:
        ts = parse_time(line.strip())
        if ts is not None:
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
    status = await message.reply_text(f"⚙️ <b>Extracting {len(stamps)} frames…</b>")

    settings  = await db.get_settings(user.id)
    watermark = settings.get("watermark_photo", False)

    paths = []
    try:
        from utils.ffmpeg_utils import _run, Config
        import os, uuid
        from pathlib import Path

        out_dir = Path(Config.TEMP_DIR) / str(uuid.uuid4())
        out_dir.mkdir(parents=True, exist_ok=True)

        for i, ts in enumerate(stamps):
            out_path = str(out_dir / f"manual_{i+1:03d}.png")
            cmd = [
                Config.FFMPEG_PATH,
                "-ss", ts,
                "-i", cache["file_path"],
                "-vframes", "1",
                "-q:v", "2",
                "-y", out_path,
            ]
            _, _, rc = await _run(cmd)
            if rc == 0 and os.path.isfile(out_path):
                if watermark:
                    from utils.ffmpeg_utils import _watermark_photo
                    out_path = await _watermark_photo(out_path, "@zerodev2")
                paths.append(out_path)

    except Exception as e:
        logger.exception("Manual SS failed")
        return await status.edit_text(f"❌ Error: {e}")

    if not paths:
        return await status.edit_text("❌ No frames extracted.")

    await status.edit_text(f"📤 <b>Uploading {len(paths)} screenshot(s)…</b>")

    upload_mode = settings.get("upload_mode", "tile")
    if upload_mode == "tile" and len(paths) > 1:
        collage = await make_tile_collage(paths)
        await message.reply_photo(collage, caption="📸 <b>Manual Screenshots</b>")
        cleanup(collage)
    else:
        from pyrogram.types import InputMediaPhoto
        media_group = [
            InputMediaPhoto(p, caption=f"📸 Frame at {stamps[i]}" if i == 0 else "")
            for i, p in enumerate(paths)
        ]
        for batch_start in range(0, len(media_group), 10):
            await message.reply_media_group(media_group[batch_start:batch_start + 10])

    cleanup(*paths)
    await db.inc_screenshots()
    await status.delete()
