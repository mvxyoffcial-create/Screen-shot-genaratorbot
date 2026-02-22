"""
utils/helpers.py  —  SPEED OPTIMISED
• check_force_sub  → all channels checked IN PARALLEL (asyncio.gather)
• progress_callback → throttled to 1 update/sec (avoids Telegram flood wait)
• fetch_random_wallpaper → short 5s timeout, returns fast
"""
import asyncio
import os
import shutil
import time
from typing import List, Optional

import aiohttp
from pyrogram import Client
from pyrogram.errors import UserNotParticipant, ChatAdminRequired
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import Config


# ─────────────────────────── force-sub (parallel) ─────────────────────────────

async def _check_one(client: Client, channel: str, user_id: int) -> Optional[str]:
    """Return channel username if user is NOT a member, else None."""
    try:
        member = await client.get_chat_member(channel, user_id)
        if member.status.value in ("left", "banned", "restricted"):
            return channel
        return None
    except UserNotParticipant:
        return channel
    except (ChatAdminRequired, Exception):
        return None   # Can't check → allow through


async def check_force_sub(client: Client, user_id: int) -> List[str]:
    """
    Check ALL channels IN PARALLEL.
    Returns list of channels the user hasn't joined.
    Empty list = all good.
    """
    results = await asyncio.gather(
        *[_check_one(client, ch, user_id) for ch in Config.FSUB_CHANNELS],
        return_exceptions=False,
    )
    return [ch for ch in results if ch is not None]


async def send_force_sub_message(message: Message) -> None:
    """Send the force-sub banner with join buttons."""
    buttons = [
        [InlineKeyboardButton(f"🔔 Join @{ch}", url=f"https://t.me/{ch}")]
        for ch in Config.FSUB_CHANNELS
    ]
    buttons.append(
        [InlineKeyboardButton("✅ I Joined – Try Again", callback_data="check_fsub")]
    )
    await message.reply_photo(
        photo=Config.FSUB_IMAGE,
        caption=(
            "<b>⚠️ Access Restricted!</b>\n\n"
            "You must join our channels to use this bot.\n\n"
            "🔔 Join <b>both channels</b> below, then tap ✅ <b>I Joined</b>."
        ),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ─────────────────────────── progress bar (throttled) ─────────────────────────

# Map: message_id → last_edit_timestamp
_last_edit: dict = {}
_THROTTLE_SEC = 1.5   # minimum seconds between progress edits


def _progress_bar(current: int, total: int, width: int = 20) -> str:
    filled = int(width * current / total) if total else 0
    return "█" * filled + "░" * (width - filled)


async def progress_callback(
    current: int,
    total: int,
    message: Message,
    action: str,
    start_time: float,
) -> None:
    """Throttled progress bar — edits at most once per 1.5 seconds."""
    msg_id = message.id
    now    = time.monotonic()

    # Skip if updated too recently  ← prevents FloodWait & slowdown
    if now - _last_edit.get(msg_id, 0) < _THROTTLE_SEC:
        return
    _last_edit[msg_id] = now

    elapsed = time.monotonic() - start_time
    speed   = current / elapsed if elapsed > 0 else 0
    eta     = (total - current) / speed if speed > 0 else 0
    pct     = current * 100 / total if total else 0
    bar     = _progress_bar(current, total)

    text = (
        f"{action}\n\n"
        f"<code>{bar}</code> {pct:.1f}%\n\n"
        f"📦 <b>Size:</b> {_human_size(current)} / {_human_size(total)}\n"
        f"⚡ <b>Speed:</b> {_human_size(int(speed))}/s\n"
        f"⏳ <b>ETA:</b> {_hms(eta)}"
    )
    try:
        await message.edit_text(text)
    except Exception:
        pass


# ─────────────────────────── size / time helpers ──────────────────────────────

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
    raw   = raw.strip()
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


# ─────────────────────────── wallpaper fetch (fast) ──────────────────────────

async def fetch_random_wallpaper() -> Optional[str]:
    """Fetch a random wallpaper URL. Fails fast (5s timeout)."""
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(Config.WALLPAPER_API) as resp:
                if resp.status != 200:
                    return None
                # Try JSON first
                try:
                    data = await resp.json(content_type=None)
                    for key in ("url", "image", "image_url", "link", "src"):
                        if key in data:
                            return data[key]
                except Exception:
                    pass
                # Fallback: plain URL text
                text = await resp.text()
                if text.strip().startswith("http"):
                    return text.strip()
    except Exception:
        pass
    return None
