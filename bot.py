"""
bot.py  –  Main entry point for the Video Screenshot Bot.
Starts BOTH the Pyrogram bot and the aiohttp web server on port 8080.
"""
import asyncio
import logging
import os

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

from pyrogram import Client, idle
from pyrogram.types import BotCommand

from config import Config
from web_server import start_web_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class VideoBot(Client):
    def __init__(self):
        super().__init__(
            name="VideoScreenshotBot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            plugins=dict(root="handlers"),
            workers=8,
            sleep_threshold=60,
        )

    async def start(self):
        os.makedirs(Config.TEMP_DIR, exist_ok=True)
        await super().start()
        me = await self.get_me()
        logger.info("Bot started: @%s (id=%s)", me.username, me.id)

        await self.set_bot_commands(
            [
                BotCommand("start",    "Start the bot"),
                BotCommand("help",     "How to use"),
                BotCommand("about",    "About the bot"),
                BotCommand("settings", "Customize your settings"),
                BotCommand("cancel",   "Cancel current operation"),
                BotCommand("stats",    "Bot statistics (admin)"),
                BotCommand("broadcast","Broadcast message (admin)"),
                BotCommand("users",    "Total user count (admin)"),
            ]
        )
        logger.info("Bot commands registered.")

    async def stop(self, *args):
        await super().stop()
        logger.info("Bot stopped.")


async def main():
    # Start web server (port 8080) FIRST so Koyeb health checks pass immediately
    await start_web_server()

    bot = VideoBot()
    await bot.start()
    logger.info("Bot + web server running. Listening for messages…")
    await idle()
    await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
