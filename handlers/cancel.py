"""
handlers/cancel.py
Global /cancel command to abort any ongoing multi-step flow.
"""
from pyrogram import Client, filters
from pyrogram.types import Message

from handlers.screenshots import manual_ss_state
from handlers.trim import trim_state


@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_handler(client: Client, message: Message):
    user_id = message.from_user.id
    cleared = False

    if user_id in manual_ss_state:
        manual_ss_state.pop(user_id)
        cleared = True

    if user_id in trim_state:
        trim_state.pop(user_id)
        cleared = True

    if cleared:
        await message.reply_text("❌ <b>Operation cancelled successfully.</b>")
    else:
        await message.reply_text("ℹ️ <b>Nothing to cancel.</b>")
