ParserRIba - быстрый старт
==========================

1. Запустите проверку:

   ParserRIba.exe --check-env

2. Посмотрите доступные магазины:

   ParserRIba.exe --list-stores

3. Для теста Пятерочки запустите:

   ParserRIba.exe --store pyaterochka --no-headless

4. Если нужен прокси, скопируйте файл .env.example в .env и заполните:

   PARSER_PROXY=http://user:password@host:port
   PARSER_PROXIES=http://user:password@host1:port;http://user:password@host2:port

5. GeoIP:

   Если рядом с ParserRIba.exe лежит GeoLite2-City.mmdb, программа использует
   его автоматически. Без GeoIP программа тоже запускается, но Camoufox хуже
   согласует регион браузера.

Документация:

   docs\WINDOWS_QUICKSTART.md
   docs\DISTRIBUTION_PLAN.md

Если программа не запускается, сначала отправьте разработчику вывод команды:

   ParserRIba.exe --check-env
