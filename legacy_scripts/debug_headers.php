// Path to store all incoming requests
define('LOG_OUTPUT', __DIR__ . '/requests.log');

$data = sprintf(
    "[%s]\n%s %s %s\n\nHTTP HEADERS:\n",
    date('c'),
    $_SERVER['REQUEST_METHOD'],
    $_SERVER['REQUEST_URI'],
    $_SERVER['SERVER_PROTOCOL']
);

foreach ($_SERVER as $name => $value) {
    if (preg_match('/^HTTP_/',$name)) {
        // convert HTTP_HEADER_NAME to Header-Name
        $name = strtr(substr($name,5),'_',' ');
        $name = ucwords(strtolower($name));
        $name = strtr($name,' ','-');

        // add to list
        $data .= $name . ': ' . $value . "\n";
    }
}

$data .= "\nREQUEST BODY:\n" . file_get_contents('php://input') . "\n";

file_put_contents(LOG_OUTPUT, $data, FILE_APPEND|LOCK_EX);

echo("OK!\n");