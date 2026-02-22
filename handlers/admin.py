"""
handlers/admin.py
Admin-only commands: /stats, /broadcast, /users
Admin user IDs are loaded from Config.ADMIN_IDS.
"""
import logging

from pyrogram import Client, filters
from pyrogram.types import Message

from config import Config
from database import db

logger = logging.getLogger(__name__)


def admin_filter(_, __, message: Message) -> bool:
    return message.from_user and message.from_user.id in Config.ADMIN_IDS


is_admin = filters.create(admin_filter)


# ── /stats ────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("stats") & filters.private & is_admin)
async def stats_cmd(client: Client, message: Message):
    stats = await db.get_stats()
    total = await db.total_users_count()

    text = (
        "📊 <b>Bot Statistics</b>\n\n"
        f"👥 <b>Total Users:</b> <code>{total}</code>\n"
        f"📸 <b>Screenshots Generated:</b> <code>{stats.get('screenshots_generated', 0)}</code>\n"
        f"🎬 <b>Samples Generated:</b> <code>{stats.get('samples_generated', 0)}</code>\n"
        f"✂️ <b>Trims Done:</b> <code>{stats.get('trims_done', 0)}</code>\n"
        f"📊 <b>Media Info Requests:</b> <code>{stats.get('media_info_requests', 0)}</code>\n"
        f"🖼 <b>Thumbnails Generated:</b> <code>{stats.get('thumbnails_generated', 0)}</code>\n"
    )
    await message.reply_text(text)


# ── /users ────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("users") & filters.private & is_admin)
async def users_cmd(client: Client, message: Message):
    total = await db.total_users_count()
    await message.reply_text(
        f"👥 <b>Total Registered Users:</b> <code>{total}</code>"
    )


# ── /broadcast ────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("broadcast") & filters.private & is_admin)
async def broadcast_cmd(client: Client, message: Message):
    # Usage: reply to a message with /broadcast
    if not message.reply_to_message:
        return await message.reply_text(
            "❗ <b>Reply to a message</b> with /broadcast to send it to all users."
        )

    status = await message.reply_text("📡 <b>Broadcasting…</b>")
    target = message.reply_to_message

    success = 0
    failed  = 0

    async for user in await db.get_all_users():
        try:
            await target.copy(user["_id"])
            success += 1
        except Exception as e:
            logger.warning("Broadcast failed for %s: %s", user["_id"], e)
            failed += 1

    await status.edit_text(
        f"✅ <b>Broadcast Complete!</b>\n\n"
        f"✔️ <b>Sent:</b> <code>{success}</code>\n"
        f"❌ <b>Failed:</b> <code>{failed}</code>"
    )
