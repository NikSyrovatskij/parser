#!/usr/bin/env python3
"""
Happ Proxy Subscription Converter (Python version)
Парсинг подписки Happ Proxy в список vless / hysteria2 ссылок
"""

import sys
import os
import time
import base64
import gzip
import urllib.request
import urllib.error

# ================= НАСТРОЙКИ =================
SUBSCRIPTION_URL = "https://sub.ghostnode.bond/Ys2aEVL1zF1RJxKT"
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output.cache")
CACHE_TTL = 10800  # 3 часа в секундах

HEADERS = {
    # Sing-box/1.8.29 отдает Base64 со списком vless:// ссылок (Happ/3.13.0 отдает JSON)
    "User-Agent": "Sing-box/1.8.29",
    "X-Device-Os": "Android",
    "X-Device-Locale": "ru",
    "X-Device-Model": "ELP-NX1",
    "X-Ver-Os": "15",
    "Accept-Encoding": "gzip",
    "Connection": "close",
    "X-Hwid": "74jf74nf8f4jr5je",
    "X-Real-Ip": "101.202.303.404",
    "X-Forwarded-For": "101.202.303.404",
}
# =============================================


def fetch_subscription(force=False):
    # Проверка кеша
    if not force and os.path.exists(CACHE_FILE):
        file_age = time.time() - os.path.getmtime(CACHE_FILE)
        if file_age < CACHE_TTL:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            print("[X-Cache: HIT] Отдано из кеша:")
            return content

    req = urllib.request.Request(SUBSCRIPTION_URL, headers=HEADERS)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw_data = response.read()
            
            # Распаковка gzip если сжато
            if response.headers.get("Content-Encoding") == "gzip":
                raw_data = gzip.decompress(raw_data)
            
            # Пробуем раскодировать base64
            try:
                decoded = base64.b64decode(raw_data).decode("utf-8")
                # Проверяем, что раскодированное содержит протоколы vless:// или hysteria2://
                if "vless://" in decoded or "hysteria2://" in decoded:
                    content = decoded
                else:
                    content = raw_data.decode("utf-8", errors="replace")
            except Exception:
                content = raw_data.decode("utf-8", errors="replace")

            # Сохраняем в кеш
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                f.write(content)
            
            print("[X-Cache: MISS] Получено с сервера и сохранено в кеш:")
            return content

    except Exception as e:
        if os.path.exists(CACHE_FILE):
            print(f"[Warning] Ошибка запроса ({e}), отдаем устаревший кеш:", file=sys.stderr)
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return f.read()
        print(f"[Error] Не удалось получить подписку: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    force_update = "--force" in sys.argv
    result = fetch_subscription(force=force_update)
    print(result)

