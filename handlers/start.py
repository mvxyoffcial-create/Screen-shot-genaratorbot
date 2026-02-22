"""
handlers/start.py
/start, /help, /about commands + force-sub callback.
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

# ── /start ────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user = message.from_user
    await db.add_user(user.id, user.full_name, user.username)

    # Force-sub check
    missing = await check_force_sub(client, user.id)
    if missing:
        return await send_force_sub_message(message)

    # 1. Send sticker
    sticker_msg = await message.reply_sticker(Config.WELCOME_STICKER)

    # 2. Auto-delete sticker after 2 seconds
    await asyncio.sleep(2)
    try:
        await sticker_msg.delete()
    except Exception:
        pass

    # 3. Build welcome keyboard
    keyboard = InlineKeyboardMarkup(
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

    # 4. Fetch welcome image
    photo_url = await fetch_random_wallpaper()
    caption   = script.START_TXT.format(user.mention)

    if photo_url:
        try:
            await message.reply_photo(
                photo=photo_url,
                caption=caption,
                reply_markup=keyboard,
            )
            return
        except Exception:
            pass

    # Fallback – plain text
    await message.reply_text(caption, reply_markup=keyboard)


# ── /help ─────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("help") & filters.private)
async def help_cmd(client: Client, message: Message):
    missing = await check_force_sub(client, message.from_user.id)
    if missing:
        return await send_force_sub_message(message)

    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 Back", callback_data="start")]]
    )
    await message.reply_text(script.HELP_TXT, reply_markup=kb)


# ── /about ────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("about") & filters.private)
async def about_cmd(client: Client, message: Message):
    missing = await check_force_sub(client, message.from_user.id)
    if missing:
        return await send_force_sub_message(message)

    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 Back", callback_data="start")]]
    )
    await message.reply_text(script.ABOUT_TXT, reply_markup=kb)


# ── Callback – navigation & force-sub re-check ────────────────────────────────

@Client.on_callback_query(filters.regex("^(start|help|about|check_fsub)$"))
async def nav_callback(client: Client, cb: CallbackQuery):
    data = cb.data
    user = cb.from_user

    if data == "check_fsub":
        missing = await check_force_sub(client, user.id)
        if missing:
            names = " and ".join(f"@{c}" for c in missing)
            return await cb.answer(
                f"❌ You still haven't joined: {names}", show_alert=True
            )
        await cb.answer("✅ Welcome! You may now use the bot.", show_alert=True)
        try:
            await cb.message.delete()
        except Exception:
            pass
        # Re-trigger /start flow
        await start_handler(client, cb.message)
        return

    if data == "start":
        photo_url = await fetch_random_wallpaper()
        caption   = script.START_TXT.format(user.mention)
        kb = InlineKeyboardMarkup(
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
        try:
            if photo_url and cb.message.photo:
                await cb.message.edit_caption(caption, reply_markup=kb)
            else:
                await cb.message.edit_text(caption, reply_markup=kb)
        except Exception:
            pass
        return

    if data == "help":
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏠 Back", callback_data="start")]]
        )
        try:
            await cb.message.edit_caption(script.HELP_TXT, reply_markup=kb)
        except Exception:
            await cb.message.edit_text(script.HELP_TXT, reply_markup=kb)
        return

    if data == "about":
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏠 Back", callback_data="start")]]
        )
        try:
            await cb.message.edit_caption(script.ABOUT_TXT, reply_markup=kb)
        except Exception:
            await cb.message.edit_text(script.ABOUT_TXT, reply_markup=kb)
        return

    await cb.answer()
