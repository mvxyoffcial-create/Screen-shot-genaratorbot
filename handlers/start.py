"""
handlers/start.py  —  SPEED OPTIMISED
• Welcome appears INSTANTLY — sticker deletes silently in background
• force-sub check + wallpaper fetched in PARALLEL (asyncio.gather)
• _full_name() fix for Pyrogram v2 (no .full_name attribute)
"""
import asyncio
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
from script import script
from utils.helpers import (
    check_force_sub,
    fetch_random_wallpaper,
    send_force_sub_message,
)

logger = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _full_name(user) -> str:
    """Pyrogram v2 has no .full_name — build it from first + last."""
    first = user.first_name or ""
    last  = user.last_name  or ""
    return f"{first} {last}".strip() or "User"


async def _delete_after(msg, delay: float = 2.0) -> None:
    """Silently delete a message after `delay` seconds (background task)."""
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass


def _welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📖 Help",  callback_data="help"),
                InlineKeyboardButton("ℹ️ About", callback_data="about"),
            ],
            [
                InlineKeyboardButton(
                    f"📢 Updates – @{Config.UPDATE_CHANNEL}",
                    url=f"https://t.me/{Config.UPDATE_CHANNEL}",
                )
            ],
        ]
    )


# ── /start ────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user = message.from_user

    # ── Run 3 things in PARALLEL: save user, fsub check, fetch wallpaper ─────
    _, missing, photo_url = await asyncio.gather(
        db.add_user(user.id, _full_name(user), user.username),
        check_force_sub(client, user.id),
        fetch_random_wallpaper(),
    )

    if missing:
        return await send_force_sub_message(message)

    caption  = script.START_TXT.format(user.mention)
    keyboard = _welcome_keyboard()

    # ── Send sticker AND welcome message at the SAME TIME ────────────────────
    if photo_url:
        welcome_coro = message.reply_photo(
            photo=photo_url, caption=caption, reply_markup=keyboard
        )
    else:
        welcome_coro = message.reply_text(caption, reply_markup=keyboard)

    sticker_msg, _ = await asyncio.gather(
        message.reply_sticker(Config.WELCOME_STICKER),
        welcome_coro,
    )

    # ── Delete sticker after 2s WITHOUT blocking anything ────────────────────
    asyncio.get_event_loop().create_task(_delete_after(sticker_msg, 2.0))


# ── /help ─────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("help") & filters.private)
async def help_cmd(client: Client, message: Message):
    missing = await check_force_sub(client, message.from_user.id)
    if missing:
        return await send_force_sub_message(message)
    await message.reply_text(
        script.HELP_TXT,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏠 Back", callback_data="start")]]
        ),
    )


# ── /about ────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("about") & filters.private)
async def about_cmd(client: Client, message: Message):
    missing = await check_force_sub(client, message.from_user.id)
    if missing:
        return await send_force_sub_message(message)
    await message.reply_text(
        script.ABOUT_TXT,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏠 Back", callback_data="start")]]
        ),
    )


# ── Callbacks: navigation & force-sub re-check ────────────────────────────────

@Client.on_callback_query(filters.regex("^(start|help|about|check_fsub)$"))
async def nav_callback(client: Client, cb: CallbackQuery):
    data = cb.data
    user = cb.from_user

    # ── Force-sub re-check ────────────────────────────────────────────────────
    if data == "check_fsub":
        missing = await check_force_sub(client, user.id)
        if missing:
            names = " and ".join(f"@{c}" for c in missing)
            return await cb.answer(f"❌ Still not joined: {names}", show_alert=True)

        await cb.answer("✅ Access granted! Welcome.", show_alert=True)
        try:
            await cb.message.delete()
        except Exception:
            pass

        photo_url = await fetch_random_wallpaper()
        caption   = script.START_TXT.format(user.mention)
        keyboard  = _welcome_keyboard()
        if photo_url:
            try:
                await cb.message.reply_photo(photo_url, caption=caption, reply_markup=keyboard)
                return
            except Exception:
                pass
        await cb.message.reply_text(caption, reply_markup=keyboard)
        return

    # ── Back to start ─────────────────────────────────────────────────────────
    if data == "start":
        photo_url = await fetch_random_wallpaper()
        caption   = script.START_TXT.format(user.mention)
        kb        = _welcome_keyboard()
        try:
            if photo_url and cb.message.photo:
                await cb.message.edit_caption(caption, reply_markup=kb)
            else:
                await cb.message.edit_text(caption, reply_markup=kb)
        except Exception:
            pass
        await cb.answer()
        return

    # ── Help ──────────────────────────────────────────────────────────────────
    if data == "help":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back", callback_data="start")]])
        try:
            await cb.message.edit_caption(script.HELP_TXT, reply_markup=kb)
        except Exception:
            await cb.message.edit_text(script.HELP_TXT, reply_markup=kb)
        await cb.answer()
        return

    # ── About ─────────────────────────────────────────────────────────────────
    if data == "about":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back", callback_data="start")]])
        try:
            await cb.message.edit_caption(script.ABOUT_TXT, reply_markup=kb)
        except Exception:
            await cb.message.edit_text(script.ABOUT_TXT, reply_markup=kb)
        await cb.answer()
        return

    await cb.answer()
