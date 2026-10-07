<?php
/**
 * Happ Proxy Subscription Converter
 * Для V2RayN / V2RayA
 */

// ================= НАСТРОЙКИ =================
// Ссылка подписки (можно передать через ?url= в запросе)
$subscriptionUrl = 'https://sub.ghostnode.bond/Ys2aEVL1zF1RJxKT';

// Заголовки, имитирующие мобильное приложение Happ
$headers = [
    // Если выдает json вместо vless, значение User-Agent должно быть Sing-box/1.8.29
    'User-Agent: Sing-box/1.8.29',
    'X-Device-Os: Android',
    'X-Device-Locale: ru',
    'X-Device-Model: ELP-NX1',
    'X-Ver-Os: 15',
    'Accept-Encoding: gzip',
    'Connection: close',
    // Эти два заголовка можно рандомизировать для обхода лимита устройств:
    'X-Hwid: 74jf74nf8f4jr5je',
    'X-Real-Ip: 101.202.303.404',
    'X-Forwarded-For: 101.202.303.404',
];

// Таймаут запроса (сек)
$timeout = 30;
// =============================================

  // Если существует кэшированная версия…
  if (file_exists("output.cache")) {
    if ((time() - '10800') < filemtime("output.cache")) {
    $file_cache = "output.cache";
    $file_cache_buffer = fopen ($file_cache,'r');
    $content_cache = fread( $file_cache_buffer, filesize( $file_cache ) );
    fclose($file_cache_buffer);
    header('Content-Type: text/plain; charset=utf-8');
    header('Cache-Control: no-cache, max-age=0');
    echo $content_cache;
    $cache_use="1";
    exit;
  }} 


//если нет кешированной версии то делаем запрос
if (@$cache_use!="1") {

// Инициализация cURL
$ch = curl_init();
curl_setopt_array($ch, [
    CURLOPT_URL            => $subscriptionUrl,
    CURLOPT_HTTPHEADER     => $headers,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_FOLLOWLOCATION => true,
    CURLOPT_SSL_VERIFYPEER => true,  // При проблемах с сертификатом можно поставить false
    CURLOPT_SSL_VERIFYHOST => 2,
    CURLOPT_TIMEOUT        => $timeout,
    CURLOPT_ENCODING       => '',    // Автоматическая обработка gzip
]);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$error = curl_error($ch);
curl_close($ch);

// Обработка ошибок
if ($error || $httpCode !== 200 || !$response) {
    http_response_code(502);
    die(json_encode([
        'error' => 'Failed to fetch subscription',
        'details' => $error ?: "HTTP $httpCode",
        'hint' => 'Проверьте ссылку, заголовки или попробуйте сменить HWID/IP'
    ], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}

// Декодируем Base64 (если нужно)
$decoded = base64_decode($response, true);
$output = $decoded ?: $response; // Если не Base64 — берём как есть

file_put_contents('output.cache', $output);

// Отдаём результат
header('Content-Type: text/plain; charset=utf-8');
header('Cache-Control: no-cache, max-age=0');
echo $output;

}

