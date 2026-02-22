"""
database.py  –  MongoDB interface via Motor (async)
Collections:
  users    – registered users
  settings – per-user settings
  stats    – global counters
"""
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.client   = AsyncIOMotorClient(Config.MONGO_URI)
        self.db       = self.client[Config.DB_NAME]
        self.users    = self.db["users"]
        self.settings = self.db["settings"]
        self.stats    = self.db["stats"]

    # ── users ─────────────────────────────────────────────────────────────────

    async def add_user(
        self,
        user_id: int,
        full_name: str,
        username: str | None = None,
    ) -> bool:
        """Insert user if new. Returns True if inserted."""
        if await self.users.find_one({"_id": user_id}):
            return False
        await self.users.insert_one(
            {
                "_id":       user_id,
                "full_name": full_name,
                "username":  username,
                "joined":    datetime.utcnow(),
            }
        )
        await self._inc("total_users")
        return True

    async def is_user_exist(self, user_id: int) -> bool:
        return bool(await self.users.find_one({"_id": user_id}))

    async def total_users_count(self) -> int:
        return await self.users.count_documents({})

    async def get_all_users(self):
        return self.users.find({})

    # ── settings ──────────────────────────────────────────────────────────────

    async def get_settings(self, user_id: int) -> dict:
        doc = await self.settings.find_one({"_id": user_id})
        if doc:
            doc.pop("_id", None)
            # Merge with defaults so new keys always present
            merged = dict(Config.DEFAULT_SETTINGS)
            merged.update(doc)
            return merged
        defaults = dict(Config.DEFAULT_SETTINGS)
        await self.settings.insert_one({"_id": user_id, **defaults})
        return defaults

    async def update_setting(self, user_id: int, key: str, value) -> None:
        await self.settings.update_one(
            {"_id": user_id},
            {"$set": {key: value}},
            upsert=True,
        )

    # ── stats ─────────────────────────────────────────────────────────────────

    async def _inc(self, key: str, amount: int = 1) -> None:
        await self.stats.update_one(
            {"_id": "global"},
            {"$inc": {key: amount}},
            upsert=True,
        )

    async def inc_screenshots(self) -> None:
        await self._inc("screenshots_generated")

    async def inc_samples(self) -> None:
        await self._inc("samples_generated")

    async def inc_trims(self) -> None:
        await self._inc("trims_done")

    async def inc_mediainfo(self) -> None:
        await self._inc("media_info_requests")

    async def inc_thumbnails(self) -> None:
        await self._inc("thumbnails_generated")

    async def get_stats(self) -> dict:
        doc = await self.stats.find_one({"_id": "global"}) or {}
        doc.pop("_id", None)
        return doc


db = Database()
