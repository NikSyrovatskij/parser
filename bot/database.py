import aiosqlite
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    subscription_url TEXT NOT NULL,
                    servers_json TEXT NOT NULL,
                    raw_content TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            await db.commit()
            logger.info("Database initialized at %s", self.db_path)

    async def get_user_subscription(self, user_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT user_id, subscription_url, servers_json, raw_content, updated_at FROM users WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                return {
                    "user_id": row["user_id"],
                    "subscription_url": row["subscription_url"],
                    "servers": json.loads(row["servers_json"]),
                    "raw_content": row["raw_content"],
                    "updated_at": row["updated_at"],
                }

    async def save_user_subscription(
        self, user_id: int, subscription_url: str, servers: list[dict], raw_content: str
    ):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, subscription_url, servers_json, raw_content, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    subscription_url = excluded.subscription_url,
                    servers_json = excluded.servers_json,
                    raw_content = excluded.raw_content,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (user_id, subscription_url, json.dumps(servers, ensure_ascii=False), raw_content),
            )
            await db.commit()

