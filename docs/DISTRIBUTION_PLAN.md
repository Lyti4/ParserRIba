# ParserRIba distribution plan

Цель: пользователь скачивает архив или установщик, вводит прокси при
необходимости и запускает ParserRIba без ручной настройки проекта.

## Текущий статус

Готово:

- Python 3.11 окружение проверено.
- Camoufox запускается через общий launcher.
- GeoIP extra и `GeoLite2-City.mmdb` поддерживаются.
- Прокси задается через `.env`, секреты не попадают в git.
- Пятерочка имеет отдельный smoke-тест с JSON/HTML/PNG/Markdown отчетом.
- Есть `scripts/check_environment.py` для самодиагностики.

## Сборка portable-версии

На машине разработчика:

```powershell
cd /d C:\tmp\ParserRIba-clean
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1 -Clean
```

Результат:

```text
dist\ParserRIba\ParserRIba.exe
dist\ParserRIba-windows-x64.zip
```

Проверка:

```powershell
dist\ParserRIba\ParserRIba.exe --list-stores
dist\ParserRIba\ParserRIba.exe --check-env
```

## Что не включаем в git и portable-архив

- `.env` с прокси и паролями;
- `GeoLite2-City.mmdb`, если лицензия/размер мешают публикации;
- `.venv`, `.build-venv`;
- smoke-артефакты из `data/`;
- логи.

## Что нужно для первой публичной сборки

1. Проверить PyInstaller build на чистой Windows-машине.
2. Решить, поставляем ли Camoufox рядом с приложением или просим пользователя
   установить его отдельно.
3. Добавить GUI/launcher для ввода прокси и запуска проверок.
4. Добавить команду `doctor` в CLI, которая вызывает проверку окружения.
5. Подготовить Inno Setup или NSIS installer.

## Рекомендованный следующий этап

Сначала выпустить portable ZIP:

```text
ParserRIba-windows-x64.zip
```

Внутри:

- `ParserRIba.exe`;
- `knowledge_base/`;
- `config.yaml`;
- `.env.example`;
- `README_START_HERE.txt`;
- `RUN_PYATEROCHKA_VISUAL.bat`;
- `docs/PROJECT_REPORT.md`;
- `docs/WINDOWS_QUICKSTART.md`.

Если нужен GeoIP в portable-версии, положите `GeoLite2-City.mmdb` рядом с
`ParserRIba.exe` в папку `dist\ParserRIba\`.

После стабилизации Пятерочки и еще 1-2 магазинов делать полноценный установщик.
План установщика описан в `docs/INSTALLER_ROADMAP.md`.
