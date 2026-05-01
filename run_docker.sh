#!/bin/bash

# Скрипт для запуска парсера в Docker
# Использование: ./run_docker.sh [магазин] [категория]
# Пример: ./run_docker.sh pyaterochka ryba

SHOP=${1:-pyaterochka}
CATEGORY=${2:-ryba}

echo "🐳 Запуск парсера для магазина: $SHOP, категория: $CATEGORY"

# Сборка образа
docker-compose build

# Запуск парсера
docker-compose up --abort-on-container-exit --exit-code-from parserriba

# Остановка контейнеров
docker-compose down

echo "✅ Готово! Результаты в папке output/"
