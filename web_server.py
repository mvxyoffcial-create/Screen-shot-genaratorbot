"""
web_server.py
Lightweight aiohttp web server on port 8080.
Required for platforms like Koyeb, Railway, Render that expect an HTTP port.
Routes:
  GET /          → 200 OK  (health check)
  GET /health    → JSON status
  GET /stats     → JSON bot stats from MongoDB
"""
import asyncio
import logging

from aiohttp import web

from config import Config

logger = logging.getLogger(__name__)


async def handle_root(request: web.Request) -> web.Response:
    return web.Response(
        text=(
            "🎬 Video Screenshot Bot is running!\n"
            f"Developer: @{Config.OWNER_USERNAME}\n"
            f"Updates: https://t.me/{Config.UPDATE_CHANNEL}"
        ),
        content_type="text/plain",
    )


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response(
        {
            "status":    "ok",
            "bot":       "VideoScreenshotBot",
            "developer": f"@{Config.OWNER_USERNAME}",
            "channel":   f"https://t.me/{Config.UPDATE_CHANNEL}",
        }
    )


async def handle_stats(request: web.Request) -> web.Response:
    try:
        from database import db
        stats = await db.get_stats()
        total = await db.total_users_count()
        return web.json_response(
            {
                "status":      "ok",
                "total_users": total,
                **stats,
            }
        )
    except Exception as e:
        return web.json_response({"status": "error", "detail": str(e)}, status=500)


async def start_web_server() -> None:
    """Start the aiohttp web server on port 8080."""
    app = web.Application()
    app.router.add_get("/",        handle_root)
    app.router.add_get("/health",  handle_health)
    app.router.add_get("/stats",   handle_stats)

    runner = web.AppRunner(app)
    await runner.setup()

    port = Config.PORT
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    logger.info("Web server running on http://0.0.0.0:%s", port)
