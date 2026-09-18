# ParserRIba: быстрый запуск на Windows

Date: 2026-06-01

Эта инструкция описывает текущий launcher-first путь. Старый `main.py` и
`parsers/` не являются runtime; удалённый legacy-код доступен через историю git.

## 1. Перейти в проект

```powershell
cd /d C:\tmp\ParserRIba-clean
```

## 2. Создать виртуальную среду

```powershell
C:\Python311\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 3. Настроить локальный `.env`

```powershell
copy .env.example .env
```

В `.env` можно указать прокси:

```text
PARSER_PROXY=http://login:password@host:port
PARSER_PROXIES=http://login:password@host1:port;http://login:password@host2:port
PARSER_ATTEMPTS=3
PARSER_GEOIP=1
```

Не коммитьте `.env`: там могут быть логины, пароли и другие локальные
секреты.

## 4. GeoIP

GeoIP нужен, чтобы Camoufox согласовывал геолокацию браузера с прокси.

```powershell
.\.venv\Scripts\python.exe download_geoip.py
```

Файл `GeoLite2-City.mmdb` локальный и не добавляется в Git.

## 5. Проверить окружение

```powershell
.\.venv\Scripts\python.exe scripts\check_environment.py
```

## 6. Запустить лаунчер

```powershell
.\.venv\Scripts\python.exe scripts\run_desktop_launcher.py
```

Текущий рабочий сценарий:

1. открыть вкладку `Исследование`;
2. ввести URL магазина;
3. нажать `Исследование`;
4. выбрать разделы во вкладке `Каталог`;
5. собрать товары;
6. отобрать товары и фильтры во вкладке `Товары`;
7. выбрать столбцы и собрать Excel во вкладке `Отчёт`.

## 7. Smoke-проверка лаунчера

```powershell
.\.venv\Scripts\python.exe scripts\run_desktop_launcher.py --smoke
```

## 8. Ручная Pyaterochka-проверка

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pyaterochka_visual.ps1
```

Результаты и диагностические файлы пишутся в `data/` и не коммитятся.

## 9. Тесты и проверки

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q models utils scripts tests stores launcher
.\.venv\Scripts\python.exe scripts\architecture_check.py
```

## 10. Windows runner для Hermes/Linux-разработки

Если код готовится на Linux-сервере, а реальный браузер/капча проверяются на
Windows, используйте runner-скрипты:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_windows_remote_runner.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_windows_validation.ps1 -SetupVenv -RunPytest -ZipArtifacts
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_windows_validation.ps1 -RunVisualPyaterochka -ZipArtifacts
```

Подробно: `docs\WINDOWS_REMOTE_RUNNER.md`.

## Важные правила

- Не коммитьте `.env`, прокси, cookies, browser profiles, `data/`, `logs/`,
  `profiles/`, `build/`, `dist/`, `GeoLite2*.mmdb`.
- Не добавляйте платные scraping/captcha/browser/cloud/LLM сервисы без явного
  согласия.
- Основной пользовательский путь теперь лаунчер, а не старый CLI.
