# ParserRIba: быстрый запуск на Windows

Эта инструкция рассчитана на обычный запуск проекта на Windows без VPN на весь
компьютер. Для сайтов вроде `5ka.ru` лучше использовать прокси только внутри
парсера.

## 1. Python

Рекомендуемый вариант:

```powershell
py install --target="C:\Python311" 3.11
C:\Python311\python.exe --version
```

## 2. Виртуальная среда

```powershell
cd /d C:\tmp\ParserRIba-clean
C:\Python311\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 3. Локальные настройки

Скопируйте пример:

```powershell
copy .env.example .env
```

В `.env` можно указать:

```text
PARSER_PROXY=http://login:password@host:port
PARSER_PROXIES=http://login:password@host1:port;http://login:password@host2:port
PARSER_ATTEMPTS=3
PARSER_GEOIP=1
```

Не коммитьте `.env`: там могут быть логины и пароли.
`PARSER_PROXIES` используется для ротации при повторных попытках.
Скрипты `check_environment.py`, `smoke_pyaterochka_camoufox.py` и парсер
Пятерочки читают `.env` автоматически.

## 4. GeoIP

GeoIP нужен, чтобы Camoufox согласовывал геолокацию браузера с прокси.

```powershell
.\.venv\Scripts\python.exe download_geoip.py
```

Файл `GeoLite2-City.mmdb` большой и локальный, он не добавляется в Git.
Для portable-сборки положите этот файл рядом с `ParserRIba.exe`.

## 5. Проверка окружения

```powershell
.\.venv\Scripts\python.exe scripts\check_environment.py
```

То же самое можно запустить через главный вход программы:

```powershell
.\.venv\Scripts\python.exe main.py --check-env
```

Скрипт проверит:

- Python;
- зависимости;
- локальный Camoufox;
- `camoufox[geoip]`;
- GeoIP базу;
- прокси, если задан `PARSER_PROXY`.

## 6. Smoke-тест Пятерочки

```powershell
.\.venv\Scripts\python.exe scripts\smoke_pyaterochka_camoufox.py --category "Рыба" --attempts 3 --no-headless
```

Результаты сохраняются в `data/`:

- `pyaterochka_camoufox_smoke.json`;
- `pyaterochka_camoufox_smoke.html`;
- `pyaterochka_camoufox_smoke.png`.

Если сайт вернул антибот-страницу, в JSON будет:

```json
{
  "blocked": true,
  "block_reason": "pyaterochka_antibot_redirect"
}
```

## 7. Запуск основного CLI

```powershell
.\.venv\Scripts\python.exe main.py --list-stores
.\.venv\Scripts\python.exe main.py --store pyaterochka --no-headless
```

## 8. Тесты

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Обычный запуск тестов не ходит в живые сайты сетей. Для отдельной проверки
доступности магазинов включите live smoke-тесты:

```powershell
$env:RUN_NETWORK_SMOKE="1"
.\.venv\Scripts\python.exe -m pytest tests\test_parsers_smoke.py -q
Remove-Item Env:\RUN_NETWORK_SMOKE
```

## Важные правила

- Не включайте VPN на весь компьютер, если из-за него отваливается Codex или Git.
- Используйте residential/mobile RU proxy через `PARSER_PROXY`.
- Не храните прокси в коде, только в `.env`.
- Если `5ka.ru` возвращает `/xpvnsulc/`, это антибот, а не ошибка селекторов.
