import os

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

# Заголовки эмуляции мобильного приложения / Sing-box для конвертера Happ
DEFAULT_HEADERS = {
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

