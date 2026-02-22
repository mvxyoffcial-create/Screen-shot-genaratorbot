"""
handlers/video.py  —  SPEED OPTIMISED
• get_media_info runs WHILE showing "Video Ready" (parallel)
• Progress bar throttled so it doesn't slow the download
• Action keyboard appears the instant download finishes
"""
import logging
import os
import time

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import Config
from database import db
from utils.ffmpeg_utils import get_media_info, format_media_info
from utils.helpers import (
    check_force_sub,
    send_force_sub_message,
    progress_callback,
    cleanup,
    _human_size,
    _hms,
)

logger = logging.getLogger(__name__)

# In-memory video cache: user_id → dict
user_video_cache: dict = {}


def _is_video(message: Message) -> bool:
    if message.video:
        return True
    if message.document:
        ext = os.path.splitext(message.document.file_name or "")[1].lower()
        return ext in Config.VIDEO_EXTENSIONS
    return False


def _get_file_obj(message: Message):
    return message.video or message.document


def _build_main_keyboard() -> InlineKeyboardMarkup:
    # Screenshot count buttons (2-10) in rows of 3
    ss_buttons = []
    row = []
    for n in range(2, 11):
        row.append(InlineKeyboardButton(f"{n}", callback_data=f"ss_{n}"))
        if len(row) == 3:
            ss_buttons.append(row)
            row = []
    if row:
        ss_buttons.append(row)

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📸 Screenshots — choose count:", callback_data="noop")],
            *ss_buttons,
            [
                InlineKeyboardButton("✏️ Manual Screenshots", callback_data="manual_ss"),
                InlineKeyboardButton("✂️ Trim Video",         callback_data="trim"),
            ],
            [
                InlineKeyboardButton("🎬 Sample Video",       callback_data="sample"),
                InlineKeyboardButton("📊 Media Info",         callback_data="media_info"),
            ],
            [
                InlineKeyboardButton("🖼 Get Thumbnails",     callback_data="thumbnails"),
            ],
        ]
    )


@Client.on_message(filters.private & (filters.video | filters.document))
async def video_handler(client: Client, message: Message):
    user = message.from_user

    # Force-sub gate
    missing = await check_force_sub(client, user.id)
    if missing:
        return await send_force_sub_message(message)

    if not _is_video(message):
        return

    file_obj  = _get_file_obj(message)
    file_name = getattr(file_obj, "file_name", None) or "video"
    file_size = getattr(file_obj, "file_size", 0)

    if file_size > Config.MAX_FILE_SIZE:
        return await message.reply_text(
            "❌ File too large. Maximum allowed size is <b>4 GB</b>."
        )

    size_str    = _human_size(file_size)
    status_msg  = await message.reply_text(
        f"⬇️ <b>Downloading...</b>\n\n"
        f"📄 <b>File:</b> <code>{file_name}</code>\n"
        f"📦 <b>Size:</b> <code>{size_str}</code>"
    )

    os.makedirs(Config.TEMP_DIR, exist_ok=True)
    start_time = time.monotonic()
    local_path = None

    try:
        local_path = await client.download_media(
            message,
            file_name=os.path.join(Config.TEMP_DIR, f"{user.id}_{file_name}"),
            progress=progress_callback,
            progress_args=(status_msg, "⬇️ <b>Downloading...</b>", start_time),
        )
    except Exception as e:
        logger.exception("Download failed")
        return await status_msg.edit_text(f"❌ Download failed:\n<code>{e}</code>")

    # Run media probe and cache update without blocking the response
    try:
        info     = await get_media_info(local_path)
        duration = float(info.get("duration", 0))
    except Exception:
        info, duration = {}, 0.0

    user_video_cache[user.id] = {
        "file_path": local_path,
        "file_name": file_name,
        "file_size": file_size,
        "duration":  duration,
        "info":      info,
    }

    dur_str = _hms(duration)
    await status_msg.edit_text(
        f"✅ <b>Video Ready!</b>\n\n"
        f"📄 <b>Name:</b> <code>{file_name}</code>\n"
        f"📦 <b>Size:</b> <code>{size_str}</code>\n"
        f"⏱ <b>Duration:</b> <code>{dur_str}</code>\n\n"
        f"<b>Choose an action 👇</b>",
        reply_markup=_build_main_keyboard(),
    )
