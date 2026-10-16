import os
import secrets

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Простой резервный парсер .env без сторонних библиотек
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "bot.db"))

# Профиль устройства по умолчанию
DEFAULT_DEVICE_PROFILE = {
    "hwid": "74jf74nf8f4jr5je",
    "model": "ELP-NX1",
    "model_name": "Honor Magic 6 Pro",
    "os": "Android",
    "ver_os": "15",
    "user_agent": "Sing-box/1.8.29",
    "locale": "ru",
    "real_ip": "101.202.303.404",
}

# Популярные пресеты смартфонов для эмуляции
DEVICE_PRESETS = {
    "honor_magic6": {
        "title": "Honor Magic 6 Pro (Android 15)",
        "model": "ELP-NX1",
        "model_name": "Honor Magic 6 Pro",
        "os": "Android",
        "ver_os": "15",
        "user_agent": "Sing-box/1.8.29",
        "locale": "ru",
    },
    "samsung_s24": {
        "title": "Samsung Galaxy S24 Ultra (Android 15)",
        "model": "SM-S928B",
        "model_name": "Samsung Galaxy S24 Ultra",
        "os": "Android",
        "ver_os": "15",
        "user_agent": "Sing-box/1.8.29",
        "locale": "ru",
    },
    "pixel_8": {
        "title": "Google Pixel 8 Pro (Android 14)",
        "model": "Pixel 8 Pro",
        "model_name": "Google Pixel 8 Pro",
        "os": "Android",
        "ver_os": "14",
        "user_agent": "Sing-box/1.8.29",
        "locale": "ru",
    },
    "iphone_15": {
        "title": "Apple iPhone 15 Pro (iOS 18.0)",
        "model": "iPhone16,1",
        "model_name": "Apple iPhone 15 Pro",
        "os": "iOS",
        "ver_os": "18.0",
        "user_agent": "Sing-box/1.8.29",
        "locale": "ru",
    },
}


def generate_random_hwid(length: int = 16) -> str:
    """Генерирует случайный уникальный HWID (hex-строка из 16 или 32 символов)."""
    return secrets.token_hex(length // 2 if length % 2 == 0 else 8)


def build_headers_from_profile(profile: dict = None) -> dict:
    """Формирует HTTP-заголовки для отправки провайдеру подписки на основе профиля телефона."""
    if not profile:
        profile = DEFAULT_DEVICE_PROFILE

    hwid = profile.get("hwid") or DEFAULT_DEVICE_PROFILE["hwid"]
    model = profile.get("model") or DEFAULT_DEVICE_PROFILE["model"]
    os_name = profile.get("os") or DEFAULT_DEVICE_PROFILE["os"]
    ver_os = profile.get("ver_os") or DEFAULT_DEVICE_PROFILE["ver_os"]
    ua = profile.get("user_agent") or DEFAULT_DEVICE_PROFILE["user_agent"]
    locale = profile.get("locale") or DEFAULT_DEVICE_PROFILE["locale"]
    ip = profile.get("real_ip") or DEFAULT_DEVICE_PROFILE["real_ip"]

    return {
        "User-Agent": ua,
        "X-Device-Os": os_name,
        "X-Device-Locale": locale,
        "X-Device-Model": model,
        "X-Ver-Os": ver_os,
        "Accept-Encoding": "gzip",
        "Connection": "close",
        "X-Hwid": hwid,
        "X-Real-Ip": ip,
        "X-Forwarded-For": ip,
    }


# Для обратной совместимости
DEFAULT_HEADERS = build_headers_from_profile(DEFAULT_DEVICE_PROFILE)
