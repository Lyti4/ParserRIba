ParserRIba - быстрый старт
==========================

1. Запустите проверку:

   ParserRIba.exe --check-env

2. Посмотрите доступные магазины:

   ParserRIba.exe --list-stores

3. Для теста Пятерочки запустите:

   ParserRIba.exe --store pyaterochka --no-headless

   Или двойным кликом откройте:

   RUN_PYATEROCHKA_VISUAL.bat

   После проверки откройте отчеты:

   OPEN_REPORTS.bat

4. Если нужен прокси, сначала откройте:

   SETUP_ENV.bat

   Потом заполните .env:

   PARSER_PROXY=http://user:password@host:port
   PARSER_PROXIES=http://user:password@host1:port;http://user:password@host2:port

5. GeoIP:

   Если рядом с ParserRIba.exe лежит GeoLite2-City.mmdb, программа использует
   его автоматически. Без GeoIP программа тоже запускается, но Camoufox хуже
   согласует регион браузера.

Документация:

   docs\WINDOWS_QUICKSTART.md
   docs\INSTALLER_ROADMAP.md

Если программа не запускается, сначала отправьте разработчику вывод команды:

   ParserRIba.exe --check-env
