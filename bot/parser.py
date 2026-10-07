import asyncio
import base64
import gzip
import logging
import urllib.parse
import urllib.request
import urllib.error
from typing import Tuple, List, Dict

from .config import DEFAULT_HEADERS

logger = logging.getLogger(__name__)

SUPPORTED_PROTOCOLS = ("vless://", "hysteria2://", "vmess://", "trojan://", "ss://", "tuic://", "wireguard://")


def clean_subscription_url(raw_url: str) -> str:
    url = raw_url.strip()
    if url.startswith("happ://add/"):
        url = url[len("happ://add/"):].strip()
    
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Ссылка должна начинаться с http://, https:// или happ://add/https://")
    if not parsed.netloc:
        raise ValueError("Некорректный адрес сервера в ссылке.")
    return url


def _fetch_sync(url: str) -> bytes:
    req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content_encoding = resp.headers.get("Content-Encoding", "").lower()
            data = resp.read()
            if "gzip" in content_encoding or data.startswith(b"\x1f\x8b"):
                try:
                    data = gzip.decompress(data)
                except Exception:
                    pass
            return data
    except urllib.error.HTTPError as e:
        raise ValueError(f"Сервер подписки ответил кодом {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise ValueError(f"Ошибка сети при запросе подписки: {e.reason}")
    except Exception as e:
        raise ValueError(f"Не удалось получить подписку: {e}")


async def fetch_and_parse_subscription(url: str) -> Tuple[List[Dict], str]:
    clean_url = clean_subscription_url(url)
    
    raw_bytes = await asyncio.to_thread(_fetch_sync, clean_url)

    text_content = ""
    # Попытка Base64 декодирования
    try:
        decoded_bytes = base64.b64decode(raw_bytes, validate=False)
        decoded_str = decoded_bytes.decode("utf-8", errors="replace")
        if any(proto in decoded_str for proto in SUPPORTED_PROTOCOLS):
            text_content = decoded_str
    except Exception:
        pass

    # Если не base64, декодируем как utf-8
    if not text_content:
        text_content = raw_bytes.decode("utf-8", errors="replace")

    lines = [line.strip() for line in text_content.splitlines() if line.strip()]
    servers = []
    
    idx = 0
    for line in lines:
        matched_proto = None
        for proto in SUPPORTED_PROTOCOLS:
            if line.startswith(proto):
                matched_proto = proto[:-3]  # e.g. "vless" from "vless://"
                break
        
        if not matched_proto:
            continue

        # Извлекаем название из хэша #...
        parts = line.split("#", 1)
        if len(parts) > 1 and parts[1].strip():
            title = urllib.parse.unquote(parts[1].strip())
        else:
            title = f"Сервер {idx + 1}"

        servers.append({
            "id": idx,
            "title": title,
            "proto": matched_proto,
            "link": line,
        })
        idx += 1

    if not servers:
        raise ValueError(
            "В ответе подписки не найдено поддерживаемых ссылок (vless/hysteria2).\n"
            "Проверьте правильность ссылки подписки."
        )

    return servers, text_content

