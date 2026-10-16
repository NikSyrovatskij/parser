import aiosqlite
import json
import logging
import os
from typing import Optional

from .config import DEFAULT_DEVICE_PROFILE

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
                    subscription_url TEXT,
                    servers_json TEXT,
                    raw_content TEXT,
                    device_hwid TEXT,
                    device_model TEXT,
                    device_model_name TEXT,
                    device_os TEXT,
                    device_ver_os TEXT,
                    user_agent TEXT,
                    device_locale TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            # Автоматическая миграция: проверка и добавление отсутствующих колонок
            async with db.execute("PRAGMA table_info(users)") as cursor:
                existing_columns = [row[1] for row in await cursor.fetchall()]

            columns_to_add = {
                "device_hwid": "TEXT",
                "device_model": "TEXT",
                "device_model_name": "TEXT",
                "device_os": "TEXT",
                "device_ver_os": "TEXT",
                "user_agent": "TEXT",
                "device_locale": "TEXT",
            }
            for col_name, col_type in columns_to_add.items():
                if col_name not in existing_columns:
                    await db.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                    logger.info("Миграция БД: добавлена колонка %s", col_name)

            await db.commit()
            logger.info("Database initialized and migrated at %s", self.db_path)

    async def get_user_device_profile(self, user_id: int) -> dict:
        """Получить сохранённый профиль устройства пользователя или вернуть дефолтный."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT device_hwid, device_model, device_model_name,
                       device_os, device_ver_os, user_agent, device_locale
                FROM users WHERE user_id = ?
                """,
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return dict(DEFAULT_DEVICE_PROFILE)

        return {
            "hwid": row["device_hwid"] or DEFAULT_DEVICE_PROFILE["hwid"],
            "model": row["device_model"] or DEFAULT_DEVICE_PROFILE["model"],
            "model_name": row["device_model_name"] or DEFAULT_DEVICE_PROFILE["model_name"],
            "os": row["device_os"] or DEFAULT_DEVICE_PROFILE["os"],
            "ver_os": row["device_ver_os"] or DEFAULT_DEVICE_PROFILE["ver_os"],
            "user_agent": row["user_agent"] or DEFAULT_DEVICE_PROFILE["user_agent"],
            "locale": row["device_locale"] or DEFAULT_DEVICE_PROFILE["locale"],
            "real_ip": DEFAULT_DEVICE_PROFILE["real_ip"],
        }

    async def update_user_device_profile(self, user_id: int, **kwargs):
        """Обновить настройки профиля устройства (HWID, модель, ОС) пользователя."""
        async with aiosqlite.connect(self.db_path) as db:
            # Убеждаемся, что запись для user_id существует
            await db.execute(
                """
                INSERT INTO users (user_id, subscription_url, servers_json, raw_content)
                VALUES (?, '', '[]', '')
                ON CONFLICT(user_id) DO NOTHING;
                """,
                (user_id,),
            )

            fields_map = {
                "hwid": "device_hwid",
                "model": "device_model",
                "model_name": "device_model_name",
                "os": "device_os",
                "ver_os": "device_ver_os",
                "user_agent": "user_agent",
                "locale": "device_locale",
            }

            set_clauses = []
            values = []
            for arg_key, col_name in fields_map.items():
                if arg_key in kwargs:
                    set_clauses.append(f"{col_name} = ?")
                    values.append(kwargs[arg_key])

            if set_clauses:
                set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                values.append(user_id)
                sql = f"UPDATE users SET {', '.join(set_clauses)} WHERE user_id = ?"
                await db.execute(sql, tuple(values))
                await db.commit()

    async def get_user_subscription(self, user_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT user_id, subscription_url, servers_json, raw_content,
                       device_hwid, device_model, device_model_name,
                       device_os, device_ver_os, user_agent, device_locale,
                       updated_at
                FROM users WHERE user_id = ?
                """,
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row or not row["subscription_url"]:
                    return None
                return {
                    "user_id": row["user_id"],
                    "subscription_url": row["subscription_url"],
                    "servers": json.loads(row["servers_json"]) if row["servers_json"] else [],
                    "raw_content": row["raw_content"] or "",
                    "device": {
                        "hwid": row["device_hwid"] or DEFAULT_DEVICE_PROFILE["hwid"],
                        "model": row["device_model"] or DEFAULT_DEVICE_PROFILE["model"],
                        "model_name": row["device_model_name"] or DEFAULT_DEVICE_PROFILE["model_name"],
                        "os": row["device_os"] or DEFAULT_DEVICE_PROFILE["os"],
                        "ver_os": row["device_ver_os"] or DEFAULT_DEVICE_PROFILE["ver_os"],
                        "user_agent": row["user_agent"] or DEFAULT_DEVICE_PROFILE["user_agent"],
                        "locale": row["device_locale"] or DEFAULT_DEVICE_PROFILE["locale"],
                    },
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
