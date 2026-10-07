# 🚀 Happ Subscription Converter & Telegram Bot

Универсальный инструмент и Telegram-бот для парсинга, расшифровки и конвертации подписок **Happ Proxy** в готовые конфигурации:
- **VLESS / Hysteria2** (быстрое копирование в 1 клик для V2RayN, Streisand, v2rayNG)
- **Clash Meta / Mihomo** (`.yaml`)
- **Sing-Box / Hiddify / NekoBox** (`.json`)

🔗 **Репозиторий проекта:** [https://github.com/NikSyrovatskij/parser.git](https://github.com/NikSyrovatskij/parser.git)

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
- 🐳 **Docker ready**: автоматический запуск в изолированном контейнере с автоперезапуском.

---

## 🖥️ Пошаговая установка на сервер VPS (Ubuntu / Debian)

Ниже подробная инструкция по развертыванию бота на чистом сервере VPS с нуля.

### Шаг 1. Подключитесь к вашему VPS по SSH
В терминале на вашем компьютере выполните:
```bash
ssh root@IP_ВАШЕГО_СЕРВЕРА
```

---

### Шаг 2. Обновите систему и установите Docker
Выполните команду для обновления пакетов и автоматической установки Docker:

```bash
apt update && apt upgrade -y
apt install -y curl git docker.io docker-compose-v2
# или если используете официальный скрипт Docker:
# curl -fsSL https://get.docker.com | sh
```

Проверьте, что Docker и Compose установлены:
```bash
docker --version
docker compose version
```

---

### Шаг 3. Клонируйте репозиторий с GitHub
```bash
git clone https://github.com/NikSyrovatskij/parser.git
cd parser
```

---

### Шаг 4. Настройте токен бота (.env)
1. Создайте нового бота через [@BotFather](https://t.me/BotFather) в Telegram (команда `/newbot`) и скопируйте выданный токен.
2. Создайте файл `.env` из примера:
```bash
cp .env.example .env
```
3. Откройте файл `.env` в редакторе:
```bash
nano .env
```
Вставьте ваш токен в строку:
```env
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuVWXyz
```
*(Для сохранения в nano нажмите `Ctrl + O`, затем `Enter`, для выхода `Ctrl + X`)*.

---

### Шаг 5. Запустите бота через Docker Compose
Выполните сборку и запуск контейнера в фоновом режиме:

```bash
docker compose up -d --build
```

---

### Шаг 6. Проверьте работу бота
Посмотрите логи работающего контейнера:
```bash
docker compose logs -f
```
В логах появится сообщение:
```text
[INFO] happ_bot: 🚀 Бот запускается...
[INFO] aiogram.dispatcher: Run polling for bot @ИмяВашегоБота
```
*(Для выхода из просмотра логов нажмите `Ctrl + C`, контейнер продолжит работать в фоне)*.

Теперь откройте вашего бота в Telegram и отправьте команду `/start`!

---

## 🔄 Полезные команды на VPS

### Управление контейнером
```bash
# Просмотр статуса контейнера:
docker compose ps

# Просмотр логов:
docker compose logs -f

# Перезапуск бота:
docker compose restart

# Остановка бота:
docker compose down
```

### Обновление бота до последней версии с GitHub
Если вы внесли изменения в репозиторий на GitHub, обновите бота на VPS двумя командами:
```bash
git pull
docker compose up -d --build
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

- Файл `.env` с реальным токеном бота добавлен в `.gitignore` и **никогда не попадает** в публичный репозиторий GitHub.
- База данных SQLite сохраняется на хосте в смонтированной директории `data/`, поэтому при перезапуске или обновлении контейнера все данные пользователей и серверов сохраняются.
