# 🚀 Happ Subscription Converter & Telegram Bot

Универсальный инструмент и Telegram-бот для парсинга, расшифровки и конвертации подписок **Happ Proxy** в готовые конфигурации:
- **VLESS / Hysteria2** (быстрое копирование в 1 клик для V2RayN, Streisand, v2rayNG)
- **Clash Meta / Mihomo** (`.yaml`)
- **Sing-Box / Hiddify / NekoBox** (`.json`)

---

## ✨ Возможности

- 🔄 **Эмуляция клиента Happ**: автоматическая подстановка заголовков, обход лимитов, разархивирование Gzip и декодирование Base64.
- 📥 **Удобный ввод**: отправка ссылки `https://...` или `happ://add/https://...`.
- 📋 **Интерактивный список**:
  - Кнопки с реальными названиями серверов и флагами стран.
  - Постраничная навигация.
  - Быстрое копирование ссылок прямо в буфер обмена Telegram (в 1 клик).
- 📦 **Экспорт в Clash (YAML)**:
  - Выгрузка любого выбранного сервера в формате Clash.
  - Выгрузка полного профиля со всеми серверами разом.
- 🦊 **Экспорт в Sing-Box (JSON)**:
  - Выгрузка любого выбранного сервера в формате Sing-Box outbound.
  - Выгрузка полного профиля Sing-Box со всеми серверами и селектором.
- 📁 **Выгрузка в TXT**: скачивание всех сырых ссылок единым файлом для быстрого импорта.
- 🔄 **Обновление в 1 клик**: мгновенный повторный парсинг подписки от провайдера с обновлением локальной базы.
- 🐳 **Docker ready**: готов к быстрому деплою через Docker Compose.

---

## 🛠️ Быстрый старт (Docker)

### 1. Настройка окружения
Скопируйте пример файла конфигурации и укажите ваш токен бота (получить у [@BotFather](https://t.me/BotFather)):

```bash
cp .env.example .env
```

Отредактируйте `.env`:
```env
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuVWXyz
```

### 2. Запуск контейнера
```bash
docker compose up -d --build
```

### 3. Управление
```bash
# Просмотр логов:
docker compose logs -f

# Перезапуск:
docker compose restart

# Остановка:
docker compose down
```

---

## 📂 Структура проекта

```
.
├── bot/                       # Исходный код Telegram-бота
│   ├── config.py              # Конфигурация и HTTP-заголовки
│   ├── database.py            # Хранилище SQLite (aiosqlite)
│   ├── parser.py              # Парсинг и Base64-декодирование подписки
│   ├── converters.py          # Конвертер в Clash YAML и Sing-Box JSON
│   ├── keyboards.py           # Меню, пагинация и кнопки серверов
│   ├── handlers.py            # Обработчики сообщений и коллбэков
│   └── main.py                # Точка входа
├── docs/                      # Документация и справочные материалы
│   └── parser_happ_subscrition_to_vless_links.md
├── legacy_scripts/            # Автономные скрипты (PHP и Python CLI)
│   ├── happ_converter.php
│   ├── happ_converter.py
│   ├── debug_headers.php
│   └── .htaccess
├── data/                      # Данные базы SQLite (монтируется в Docker)
├── Dockerfile                 # Сборка образа Docker (Python 3.12-slim)
├── docker-compose.yml         # Конфигурация Docker Compose
├── requirements.txt           # Зависимости Python
├── .env.example               # Шаблон переменных окружения
├── .gitignore                 # Исключения Git (токены и кеши)
└── README.md                  # Документация проекта
```

---

## 🔒 Безопасность

- Файл `.env` с реальным токеном бота добавлен в `.gitignore` и никогда не попадает в публичный репозиторий.
- База данных SQLite сохраняется локально в директории `data/`.
