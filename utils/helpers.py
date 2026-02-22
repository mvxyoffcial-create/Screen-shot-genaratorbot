"""
utils/helpers.py
Shared utility functions: progress bar, force-sub check, time parsing, cleanup.
"""
import asyncio
import math
import os
import shutil
import time
from pathlib import Path
from typing import List, Optional

import aiohttp
from pyrogram import Client
from pyrogram.errors import UserNotParticipant, ChatAdminRequired
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import Config


# ─────────────────────────── force-sub ────────────────────────────────────────

async def check_force_sub(client: Client, user_id: int) -> List[str]:
    """
    Returns list of channel usernames the user has NOT joined.
    Empty list = all good.
    """
    not_joined = []
    for ch in Config.FSUB_CHANNELS:
        try:
            member = await client.get_chat_member(ch, user_id)
            if member.status.value in ("left", "banned", "restricted"):
                not_joined.append(ch)
        except UserNotParticipant:
            not_joined.append(ch)
        except ChatAdminRequired:
            # Bot not admin – skip check for this channel
            pass
        except Exception:
            pass
    return not_joined


async def send_force_sub_message(message: Message) -> None:
    """Send the force-sub image with join buttons."""
    buttons = []
    for ch in Config.FSUB_CHANNELS:
        buttons.append(
            [InlineKeyboardButton(f"🔔 Join @{ch}", url=f"https://t.me/{ch}")]
        )
    buttons.append(
        [InlineKeyboardButton("✅ I Joined – Try Again", callback_data="check_fsub")]
    )
    markup = InlineKeyboardMarkup(buttons)

    await message.reply_photo(
        photo=Config.FSUB_IMAGE,
        caption=(
            "<b>⚠️ Access Restricted!</b>\n\n"
            "You must join our channels to use this bot.\n\n"
            "🔔 Please join <b>both channels</b> below and tap "
            "<b>✅ I Joined</b> to continue."
        ),
        reply_markup=markup,
    )


# ─────────────────────────── progress bar ─────────────────────────────────────

def _progress_bar(current: int, total: int, width: int = 20) -> str:
    filled = int(width * current / total) if total else 0
    bar    = "█" * filled + "░" * (width - filled)
    return bar


async def progress_callback(
    current: int,
    total: int,
    message: Message,
    action: str,
    start_time: float,
) -> None:
    """Edit `message` with a live progress bar."""
    now     = time.time()
    elapsed = now - start_time
    speed   = current / elapsed if elapsed > 0 else 0
    eta     = (total - current) / speed if speed > 0 else 0
    pct     = current * 100 / total if total else 0
    bar     = _progress_bar(current, total)

    cur_str   = _human_size(current)
    tot_str   = _human_size(total)
    spd_str   = _human_size(int(speed)) + "/s"
    eta_str   = _hms(eta)

    text = (
        f"{action}\n\n"
        f"<code>{bar}</code> {pct:.1f}%\n\n"
        f"📦 <b>Size:</b> {cur_str} / {tot_str}\n"
        f"⚡ <b>Speed:</b> {spd_str}\n"
        f"⏳ <b>ETA:</b> {eta_str}"
    )

    try:
        await message.edit_text(text)
    except Exception:
        pass


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} TB"


def _hms(seconds: float) -> str:
    seconds = int(seconds)
    h, rem  = divmod(seconds, 3600)
    m, s    = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ─────────────────────────── time parsing ─────────────────────────────────────

def parse_time(raw: str) -> Optional[str]:
    """
    Accept HH:MM:SS, MM:SS, or raw seconds and return HH:MM:SS string.
    Returns None if invalid.
    """
    raw = raw.strip()
    parts = raw.split(":")
    try:
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
        elif len(parts) == 2:
            h = 0
            m, s = int(parts[0]), float(parts[1])
        else:
            total = float(parts[0])
            h = int(total // 3600)
            m = int((total % 3600) // 60)
            s = total % 60
        return f"{h:02d}:{m:02d}:{s:05.2f}"
    except Exception:
        return None


# ─────────────────────────── cleanup ─────────────────────────────────────────

def cleanup(*paths: str) -> None:
    """Remove files or directories."""
    for p in paths:
        if not p:
            continue
        try:
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            elif os.path.isfile(p):
                os.remove(p)
        except Exception:
            pass


# ─────────────────────────── wallpaper fetch ──────────────────────────────────

async def fetch_random_wallpaper() -> Optional[str]:
    """Fetch a random wallpaper URL from the anime API."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(Config.WALLPAPER_API, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    # Try common response keys
                    for key in ("url", "image", "image_url", "link"):
                        if key in data:
                            return data[key]
                    # If response is direct URL string
                    text = await resp.text()
                    if text.startswith("http"):
                        return text.strip()
    except Exception:
        pass
    return None
