# ParserRIba Windows Remote Runner

Date: 2026-06-16

Эта инструкция описывает рабочую схему `Linux brain + Windows runner`.

- Linux-сервер/Hermes: код, архитектура, Graphify, Serena, Codex, non-GUI проверки.
- Windows-компьютер: реальный PySide6 launcher, Camoufox, ручная капча, визуальная проверка, Excel/JSON artifacts.

## Почему так

ParserRIba — Windows-focused desktop app. На Linux-сервере без нормального GUI можно проверять Python-код и архитектуру, но нельзя надёжно подтверждать:

- открытие Camoufox в пользовательском режиме;
- прохождение protected-store challenge;
- ручную капчу;
- поведение PySide6 launcher как у пользователя.

Поэтому Windows-машина становится operator/validation runner.

## Быстрый локальный запуск на Windows

Открой PowerShell в проекте:

```powershell
cd C:\tmp\ParserRIba-clean
```

Первичная настройка/проверка окружения:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_windows_remote_runner.ps1
```

Полная локальная проверка без реального сайта:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_windows_validation.ps1 -SetupVenv -RunPytest -ZipArtifacts
```

Реальная визуальная проверка с Camoufox/капчей:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_windows_validation.ps1 -RunVisualPyaterochka -ZipArtifacts
```

Результаты будут в:

```text
logs/windows_runner/<timestamp>/
logs/windows_runner/<timestamp>.zip
```

Zip можно отправить Hermes/разработчику.

## Ручная капча

Во время `-RunVisualPyaterochka`:

1. Camoufox открывается на Windows.
2. Если сайт показывает капчу/challenge, пользователь решает её вручную.
3. Когда каталог/товары видны в браузере, пользователь возвращается в PowerShell.
4. Скрипт/подпроцесс продолжает сбор диагностик.
5. Логи и отчёты складываются в `data/` и затем копируются в `logs/windows_runner/<timestamp>/artifacts/`.

Важно: капча не обходится внешним сервисом. Это операторский manual gate.

## Remote runner через SSH

Предпочтительная схема — **reverse SSH tunnel**. Она работает даже если Windows
за NAT/роутером: Windows сама подключается к Hermes VPS и открывает на VPS
локальный порт `127.0.0.1:2222`, ведущий обратно в Windows OpenSSH Server.

### 1. Первый запуск на Windows

Открой PowerShell в проекте:

```powershell
cd C:\tmp\ParserRIba-clean
```

Если OpenSSH Server ещё не включён, запусти PowerShell **от администратора**:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_hermes_reverse_tunnel.ps1 -InstallOpenSSH -OpenFirewall
```

Если OpenSSH Server уже включён, можно обычный PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_hermes_reverse_tunnel.ps1
```

Оставь это окно открытым. Пока оно открыто, Hermes на VPS может подключаться к
Windows командой:

```bash
ssh parserriba-windows
```

Если нужен запуск в фоне:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_hermes_reverse_tunnel.ps1 -Background
```

### 2. Проверка SSH с Linux-сервера

С Linux/Hermes:

```bash
ssh parserriba-windows "powershell -NoProfile -Command \"hostname; whoami\""
```

### 3. Запуск проверки удалённо

```bash
ssh parserriba-windows "cd C:\tmp\ParserRIba-clean; powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_windows_validation.ps1 -RunPytest -ZipArtifacts"
```

Визуальную проверку тоже можно стартовать удалённо, но браузер должен открыться
в активной пользовательской сессии Windows. Если OpenSSH запускает процесс в
service/session-0 без видимого рабочего стола, используем один из вариантов:

- запускать visual-команду вручную на Windows;
- использовать RustDesk/AnyDesk/RDP в активной сессии;
- сделать scheduled task `Run only when user is logged on`;
- использовать отдельный lightweight runner app в будущем.

## Что считать успешной проверкой

Минимальный PASS:

- `compileall` PASS;
- `architecture_check` PASS, warnings допустимы только известные legacy/long-file warnings;
- `agent_ops_check --scope all` PASS;
- `run_desktop_launcher.py --smoke` PASS;
- non-GUI tests PASS;
- для visual flow: Camoufox открылся, manual captcha решена, каталог/товары видны, artifacts появились в `data/`.

## Что отправлять Hermes после ручной проверки

1. Zip из `logs/windows_runner/<timestamp>.zip`.
2. Короткое описание:

```text
Camoufox открылся: да/нет
Капча была: да/нет
Капча решена: да/нет
Каталог виден: да/нет
Товары видны: да/нет
Excel/JSON создан: да/нет
Что пошло не так: ...
```

## Правила безопасности

- Не коммитить `.env`, прокси, cookies, browser profiles, `data/`, `logs/`, `profiles/`, `GeoLite2*.mmdb`.
- Не отправлять токены/прокси в чат.
- Не подключать captcha-solving/cloud browser/scraping API без явного решения.
- Windows runner — операторская машина, не публичный сервер. SSH открывать только в доверенной сети или через VPN.
