# 📘 Инструкция: Happ Proxy Subscription Converter  
*Парсинг подписки Happ Proxy для V2RayN / V2RayA / Clash / SingBox*

> ⚠️ **Важно**: Данный скрипт предназначен для образовательных целей. Используйте только с легальной подпиской и в соответствии с условиями вашего провайдера.

---

[Скачать happ_conventer.php](https://gist.githubusercontent.com/bubasik/af37247b71ca0b253161b48614aba61a/raw/06ee5d07292e3f1720873a26e7f925bc8932850f/happ_converter.php)

[Скачать debug_headers.php](https://gist.githubusercontent.com/bubasik/af37247b71ca0b253161b48614aba61a/raw/36dd37b101112dda93813019de29a408000a30b3/debug_headers.php)

## 📋 Оглавление

1. [Назначение](#-назначение)
2. [Требования](#-требования)
3. [Установка](#-установка)
4. [🔍 Перехват заголовков приложения (Debug)](#-перехват-заголовков-приложения-debug)
5. [Настройка скрипта](#-настройка-скрипта)
6. [Защита файлов (.htaccess)](#-защита-файлов-htaccess)
7. [Проверка работы](#-проверка-работы)
8. [Подключение в VPN-клиентах](#-подключение-в-vpn-клиентах)
9. [Обход лимита устройств](#-обход-лимита-устройств)
10. [Дополнительные конвертеры](#-дополнительные-конвертеры)
11. [Частые проблемы](#-частые-проблемы)
12. [Безопасность](#-безопасность)
13. [Файловая структура](#-файловая-структура)

---

## 🎯 Назначение

Скрипт `happ_converter.php` решает следующие задачи:

| Задача | Решение |
|--------|---------|
| 🔄 Эмуляция мобильного приложения | Подстановка заголовков `User-Agent: Happ/3.13.0` и других |
| 🔓 Обход проверки устройства | Использование кастомных `X-Hwid`, `X-Real-Ip` |
| 📦 Декодирование подписки | Автоматическое декодирование Base64 → список `vless://` |
| ⚡ Кеширование | Сохранение результата на 3 часа для ускорения загрузки |
| 🌐 Универсальность | Работает с V2RayN, V2RayA, Clash, SingBox |

---

## ⚙️ Требования

- **PHP 7.4+** с поддержкой расширений:
  - `curl` ✅
  - `mbstring` ✅
  - `json` ✅
- Веб-сервер: **Apache** (рекомендуется) или Nginx
- Права на запись в директорию скрипта (для `output.cache`)
- (Опционально) Модуль `mod_rewrite` для `.htaccess`

> 💡 Проверка наличия cURL в PHP:
> ```bash
> php -m | grep curl
> # или создай файл info.php с <?php phpinfo();
> ```

---

## 📁 Установка

### Шаг 1: Создай файл `happ_converter.php`

Скопируй код ниже в новый файл:

```php
<?php
/**
 * Happ Proxy Subscription Converter (Lite + Cache)
 * Для V2RayN / V2RayA
 * Версия: 1.2
 */

// ================= НАСТРОЙКИ =================
$subscriptionUrl = trim('https://subscription.web.tech/ТВОЯ_ССЫЛКА');

// Заголовки мобильного приложения Happ
$headers = [
    'User-Agent: Happ/3.13.0', //если выдает json вместо vless то значение User-Agent заменить на Sing-box/1.8.29
    'X-Device-Os: Android',
    'X-Device-Locale: ru',
    'X-Device-Model: ELP-NX1',  // ← Замени на свою модель
    'X-Ver-Os: 15',              // ← Замени на свою версию Android
    'Accept-Encoding: gzip',
    'Connection: close',
    'X-Hwid: 74jf74nf8f4jr5je',  // ← Уникальный ID устройства
    'X-Real-Ip: 101.202.303.404',
    'X-Forwarded-For: 101.202.303.404',
];

$timeout = 30;                    // Таймаут запроса (сек)
$cache_ttl = 10800;              // Время жизни кеша: 3 часа (в секундах)
$cache_file = __DIR__ . '/output.cache';
// =============================================

// ================= ПРОВЕРКА КЕША =================
if (file_exists($cache_file)) {
    if ((time() - filemtime($cache_file)) < $cache_ttl) {
        header('Content-Type: text/plain; charset=utf-8');
        header('Cache-Control: no-cache, max-age=0');
        header('X-Cache: HIT');
        echo file_get_contents($cache_file);
        exit;
    }
}

// ================= ЗАПРОС К СЕРВЕРУ HAPP =================
$ch = curl_init();
curl_setopt_array($ch, [
    CURLOPT_URL            => $subscriptionUrl,
    CURLOPT_HTTPHEADER     => $headers,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_FOLLOWLOCATION => true,
    CURLOPT_SSL_VERIFYPEER => true,
    CURLOPT_SSL_VERIFYHOST => 2,
    CURLOPT_TIMEOUT        => $timeout,
    CURLOPT_ENCODING       => '',  // Авто-обработка gzip
]);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$error = curl_error($ch);
curl_close($ch);

// Обработка ошибок
if ($error || $httpCode !== 200 || !$response) {
    // Фолбэк: если есть старый кеш — отдаём его
    if (file_exists($cache_file)) {
        header('Content-Type: text/plain; charset=utf-8');
        header('X-Cache: STALE');
        echo file_get_contents($cache_file);
        exit;
    }
    http_response_code(502);
    die("Error: " . ($error ?: "HTTP $httpCode"));
}

// Декодируем Base64 (если нужно)
$decoded = base64_decode($response, true);
$output = $decoded ?: $response;

// Сохраняем в кеш
file_put_contents($cache_file, $output, LOCK_EX);

// Отдаём результат
header('Content-Type: text/plain; charset=utf-8');
header('Cache-Control: no-cache, max-age=0');
header('X-Cache: MISS');
echo $output;
```

---

## 🔍 Перехват заголовков приложения (Debug)

> 🎯 **Зачем это нужно?**  
> Если провайдер обновил приложение и ваши заголовки устарели, или вы хотите использовать **свои уникальные параметры** (HWID, модель устройства) — нужно перехватить реальные заголовки, которые отправляет приложение Happ.

### Шаг 1: Создай файл `debug_headers.php`

Этот скрипт сохранит все входящие заголовки в файл `requests.log`:

```php
<?php
/**
 * Debug: Логирование входящих запросов от Happ App
 * Сохраняет все HTTP-заголовки в requests.log
 */

// Путь к файлу логов
define('LOG_OUTPUT', __DIR__ . '/requests.log');

// Формируем данные для записи
$data = sprintf(
    "[%s]\n%s %s %s\n\nHTTP HEADERS:\n",
    date('c'),
    $_SERVER['REQUEST_METHOD'],
    $_SERVER['REQUEST_URI'],
    $_SERVER['SERVER_PROTOCOL']
);

// Собираем все HTTP-заголовки
foreach ($_SERVER as $name => $value) {
    if (preg_match('/^HTTP_/',$name)) {
        // конвертируем HTTP_HEADER_NAME в Header-Name
        $name = strtr(substr($name,5),'_',' ');
        $name = ucwords(strtolower($name));
        $name = strtr($name,' ','-');
        
        // добавляем в список
        $data .= $name . ': ' . $value . "\n";
    }
}

$data .= "\nREQUEST BODY:\n" . file_get_contents('php://input') . "\n";

// Записываем в файл (с блокировкой)
file_put_contents(LOG_OUTPUT, $data, FILE_APPEND|LOCK_EX);

echo("OK!\n");
```

### Шаг 2: Настрой приложение Happ

1.  Открой настройки приложения Happ Proxy
2.  Найди раздел **Подписка** или **Subscription URL**
3.  Вставь ссылку на свой сервер:
    ```
    https://твой-сайт.ru/debug_headers.php
    ```
4.  Нажми **Обновить подписку** или **Sync**

### Шаг 3: Проверь файл `requests.log`

После обновления подписки в приложении, файл `requests.log` будет содержать что-то вроде:

```
[2026-03-15T10:30:45+00:00]
GET /debug_headers.php HTTP/1.1

HTTP HEADERS:
Host: твой-сайт.ru
User-Agent: Happ/3.13.0
X-Device-Os: Android
X-Real-Ip: 101.202.303.404
X-Device-Locale: ru
X-Device-Model: ELP-NX1
Connection: close
X-Hwid: 74jf74nf8f4jr5je
X-Ver-Os: 15
X-Forwarded-For: 101.202.303.404
Accept-Encoding: gzip

REQUEST BODY:
```

### Шаг 4: Скопируй заголовки в `happ_converter.php`

Возьми значения из `requests.log` и вставь в основной скрипт:

```php
$headers = [
    'User-Agent: Happ/3.13.0',           // ← из лога
    'X-Device-Os: Android',              // ← из лога
    'X-Device-Locale: ru',               // ← из лога
    'X-Device-Model: ELP-NX1',           // ← твоя модель
    'X-Ver-Os: 15',                      // ← твоя версия Android
    'Accept-Encoding: gzip',
    'Connection: close',
    'X-Hwid: 74jf74nf8f4jr5je',          // ← твой HWID
    'X-Real-Ip: 101.202.303.404',        // ← можно оставить или сгенерировать
    'X-Forwarded-For: 101.202.303.404',  // ← должен совпадать с X-Real-Ip
];
```

### 🔒 Важно: Удали debug-скрипт после использования!

```bash
# После того как скопировал заголовки:
rm debug_headers.php
rm requests.log  # или перемести в безопасное место
```

> ⚠️ **Не оставляй `debug_headers.php` на сервере!**  
> Через него можно получить информацию о твоих запросах и заголовках.

---

## ⚙️ Настройка скрипта

### Шаг 1: Замени ссылку подписки

```php
// ❌ Было:
$subscriptionUrl = trim('https://subscription.web.tech/ТВОЯ_ССЫЛКА');

// ✅ Стало (твоя реальная ссылка из happ://add/...):
$subscriptionUrl = trim('https://subscription.web.tech/qqwweeerrrttt45');
```

> 💡 Если у тебя ссылка в формате `happ://add/https://...`, убери префикс `happ://add/`.

### Шаг 2: Настрой заголовки

Используй данные из `requests.log` (см. раздел выше) или оставь дефолтные:

```php
$headers = [
    'User-Agent: Happ/3.13.0',
    'X-Device-Os: Android',
    'X-Device-Locale: ru',
    'X-Device-Model: ELP-NX1',   // твоя модель телефона
    'X-Ver-Os: 15',              // твоя версия Android
    'Accept-Encoding: gzip',
    'Connection: close',
    'X-Hwid: 74jf74nf8f4jr5je',  // уникальный идентификатор
    'X-Real-Ip: 101.202.303.404',
    'X-Forwarded-For: 101.202.303.404',
];
```

### Шаг 3: Настрой кеширование

```php
$cache_ttl = 10800;  // 3 часа в секундах
// Можно изменить:
// 1 час  = 3600
// 6 часов = 21600
// 12 часов = 43200
```

---

## 🔒 Защита файлов (.htaccess)

Для защиты кеш-файлов создай `.htaccess` в той же папке:

```apache
# 🔒 Запрет прямого доступа к служебным файлам
<FilesMatch "\.(cache|meta|log|tmp)$">
    Require all denied
</FilesMatch>

# Скрыть все файлы, начинающиеся с точки
<Files ~ "^\.">
    Require all denied
</Files>
<Files ".htaccess">
    Require all granted
</Files>

# Запрет листинга директории
Options -Indexes

# (Опционально) Защита самого скрипта от прямого вызова без параметров
<Files "happ_converter.php">
    <If "%{QUERY_STRING} == ''">
        Require all denied
    </If>
</Files>
```

> ⚠️ Для **Apache 2.2** замени `Require all denied` на `Deny from all`.

---

## 🧪 Проверка работы

### Тест через терминал (curl)

```bash
# 1️⃣ Первый запрос (кеш создается, X-Cache: MISS)
curl -i "https://твой-сайт.ru/happ_converter.php" | head -20

# Ожидаемый ответ:
# HTTP/1.1 200 OK
# Content-Type: text/plain; charset=utf-8
# X-Cache: MISS
# vless://uuid@ip:port?...
# vless://uuid@ip:port?...

# 2️⃣ Повторный запрос (кеш используется, X-Cache: HIT)
curl -i "https://твой-сайт.ru/happ_converter.php" | grep "X-Cache"
# Ответ: X-Cache: HIT

# 3️⃣ Проверка защиты .htaccess
curl -I "https://твой-сайт.ru/output.cache"
# Ответ: HTTP/1.1 403 Forbidden ✅

# 4️⃣ Проверка защиты requests.log
curl -I "https://твой-сайт.ru/requests.log"
# Ответ: HTTP/1.1 403 Forbidden ✅
```

### Тест через браузер

1. Открой: `https://твой-сайт.ru/happ_converter.php`
2. Должен увидеть список ссылок вида:
   ```
   vless://343e5f1c-a7b1-5c98-b215-d8e6104ffgt6@89.208.85.123:443?security=reality&type=xhttp&...
   ```
3. Если видишь `Error: Failed to fetch subscription` — проверь заголовки и ссылку.

---

## 🔗 Подключение в VPN-клиентах

### 📱 V2RayN (Windows / Android)

1. Открой **Подписки** → **Добавить подписку**
2. Вставь ссылку:
   ```
   https://твой-сайт.ru/happ_converter.php
   ```
3. Тип: **V2Ray / VLESS** (или **Raw**)
4. Нажми **Обновить** → серверы появятся в списке

### 💻 V2RayA (Linux / Docker)

1. Открой веб-интерфейс → **Subscriptions**
2. Нажми **Add Subscription**
3. URL:
   ```
   https://твой-сайт.ru/happ_converter.php
   ```
4. Label: `Happ Proxy`
5. Нажми **Update** → импортируй конфигурации

### 🧩 Clash Meta / Mihomo

> Требуется доработка скрипта для вывода в YAML-формате.  
> Пока можно использовать внешние конвертеры (см. раздел ниже).

### 🦊 SingBox / Hiddify

> Аналогично Clash — нужен JSON-вывод.  
> Временно: скопируй `vless://` ссылки вручную.

---

## 🔄 Обход лимита устройств

Провайдер считает устройства по заголовку `X-Hwid`. Чтобы подключить больше 3–5 устройств:

### Способ 1: Сгенерировать новый HWID

```php
// Вставь в скрипт или выполни отдельно:
echo bin2hex(random_bytes(16));  // 32 символа, например: a1b2c3d4e5f6...
```

### Способ 2: Передавать HWID через URL

1. В скрипте замени строку:
   ```php
   'X-Hwid: 74jf74nf8f4jr5je',
   ```
   на:
   ```php
   'X-Hwid: ' . ($_GET['hwid'] ?? '74jf74nf8f4jr5je'),
   ```

2. Теперь можно подключать с разным HWID:
   ```
   https://твой-сайт.ru/happ_converter.php?hwid=abc123def456...
   ```

> ⚠️ **Важно**: Не злоупотребляй! Если провайдер ведёт учёт по аккаунту, а не только по HWID, это может привести к блокировке.

---

## 🌐 Дополнительные конвертеры

Если нужен формат **Clash YAML** или **SingBox JSON**, используй внешние инструменты:

| Конвертер | Направление | Ссылка |
|-----------|-------------|--------|
| **vless-xtls-converter** | `vless://` → SingBox/Clash JSON | [🔗 Открыть](https://eikeidev.github.io/vless-xtls-converter/) |
| **amnezia_xkeen_converter** | JSON → `vless://` | [🔗 Открыть](https://sovenov.github.io/amnezia_xkeen_converter/) |
| **VlessLinker (GitHub)** | Мультиформат, открытый код | [🔗 Репозиторий](https://github.com/AS97GitHub/VlessLinker) |

> 💡 **Как использовать**:  
> 1. Скачай список `vless://` из нашего скрипта  
> 2. Вставь в конвертер  
> 3. Скачай готовый конфиг для нужного клиента

---

## ❓ Частые проблемы

| Проблема | Возможная причина | Решение |
|----------|------------------|---------|
| **Пустой ответ / 502** | Неверная ссылка, заголовки или блокировка | Проверь `$subscriptionUrl`, сравни заголовки с перехватом, временно поставь `CURLOPT_SSL_VERIFYPEER => false` |
| **Кеш не обновляется** | Файл `output.cache` заблокирован или нет прав | Удали файл вручную: `rm output.cache`, проверь права `chmod 666` |
| **Не декодируется Base64** | Сервер вернул plain text, а не Base64 | Добавь лог: `file_put_contents('debug.log', $response);` и проверь содержимое |
| **403 на .htaccess** | Модуль `mod_rewrite` выключен или `AllowOverride None` | Включи в конфиге Apache: `AllowOverride All`, перезагрузи сервер |
| **Слишком медленный ответ** | Таймаут мал или хостинг тормозит | Увеличь `$timeout = 60`, проверь скорость сервера |
| **Ссылки не импортируются в клиент** | Неподдерживаемый формат | Убедись, что в клиенте выбран тип **V2Ray / VLESS**, а не Trojan/VMess |

### 🐛 Отладка: включи логирование

Добавь в начало скрипта:
```php
error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('log_errors', 1);
ini_set('error_log', __DIR__ . '/error.log');
```

---

## 🔐 Безопасность

### ✅ Обязательно

- [ ] Не публикуй скрипт в публичном GitHub с реальными токенами
- [ ] Удали `requests.log` и `debug.log` после отладки
- [ ] **Удали `debug_headers.php` после перехвата заголовков!**
- [ ] Ограничь доступ к скрипту (если он в публичном доступе):

```php
// Простая базовая авторизация:
if (!isset($_SERVER['PHP_AUTH_USER']) || $_SERVER['PHP_AUTH_USER'] !== 'admin') {
    header('WWW-Authenticate: Basic realm="Happ Converter"');
    header('HTTP/1.0 401 Unauthorized');
    exit('Access denied');
}
```

- [ ] Регулярно обновляй заголовки, если Happ меняет версию приложения
- [ ] Используй HTTPS для домена, где размещён скрипт

### 🔁 Автообновление заголовков (опционально)

Если Happ часто обновляется, можно вынести заголовки в отдельный файл `config.php`:
```php
// config.php
return [
    'user_agent' => 'Happ/3.14.0',
    'device_model' => 'NEW-MODEL-2025',
    // ...
];

// В основном скрипте:
$config = require 'config.php';
$headers = [
    'User-Agent: ' . $config['user_agent'],
    // ...
];
```

---

## 📦 Файловая структура

```
/public_html/
├── happ_converter.php    # 🎯 Основной скрипт
├── debug_headers.php     # 🔍 Перехват заголовков (удалить после использования!)
├── .htaccess             # 🔒 Защита служебных файлов
├── output.cache          # 🗃️ Кеш подписки (создаётся автоматически)
├── requests.log          # 📋 Логи перехвата заголовков (удалить после использования!)
├── error.log             # 🐛 Логи ошибок (при включённой отладке)
├── config.php            # ⚙️ Вынесенные настройки (опционально)
└── README.md             # 📘 Эта инструкция
```

---

## 🔄 Обновление скрипта

1. Скачай новую версию `happ_converter.php`
2. Сохрани свои настройки (`$subscriptionUrl`, заголовки)
3. Замени файл на сервере
4. Очисти кеш: `rm output.cache`
5. Проверь работу: `curl -I https://твой-сайт.ru/happ_converter.php`

---

## 🆘 Поддержка и вопросы

Если что-то не работает:

1. Проверь логи: `tail -f error.log`
2. Протестируй запрос вручную:
   ```bash
   curl -v \
     -H "User-Agent: Happ/3.13.0" \
     -H "X-Hwid: твой_hwid" \
     "https://subscription.web.tech/твоя_ссылка"
   ```
3. Напиши в ответ:
   - Текст ошибки
   - Версию PHP (`php -v`)
   - Тип веб-сервера (Apache / Nginx)

---
