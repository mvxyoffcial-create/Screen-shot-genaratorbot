"""
handlers/cancel.py
Global /cancel — aborts any active multi-step flow:
  manual screenshots, trim, and watermark text input.
"""
from pyrogram import Client, filters
from pyrogram.types import Message

from handlers.screenshots import manual_ss_state
from handlers.trim import trim_state
from handlers.settings import _wm_input_state


@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_handler(client: Client, message: Message):
    uid     = message.from_user.id
    cleared = False

    if uid in manual_ss_state:
        manual_ss_state.pop(uid)
        cleared = True

    if uid in trim_state:
        trim_state.pop(uid)
        cleared = True

    if uid in _wm_input_state:
        _wm_input_state.pop(uid)
        cleared = True

    if cleared:
        await message.reply_text("❌ <b>Operation cancelled.</b>")
    else:
        await message.reply_text("ℹ️ <b>Nothing to cancel.</b>")
