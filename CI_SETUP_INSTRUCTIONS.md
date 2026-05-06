# 📋 Инструкция по настройке CI/CD

## Проблема
Ваш текущий токен GitHub (`ghp_...`) не имеет права `workflow`, поэтому автоматическая отправка файла `.github/workflows/ci.yml` блокируется сервером GitHub.

## Решение (2 варианта)

### Вариант 1: Обновить токен (Рекомендуется)
1. Зайдите на https://github.com/settings/tokens
2. Удалите старый токен или создайте новый
3. При создании выберите права:
   - ✅ `repo` (полный доступ к репозиторию)
   - ✅ **`workflow`** (обязательно для CI/CD!)
4. Скопируйте новый токен
5. В терминале выполните:
   ```bash
   git remote set-url origin https://<YOUR_USERNAME>:<NEW_TOKEN>@github.com/Lyti4/ParserRIba.git
   git push --force
   ```

### Вариант 2: Добавить файл вручную через веб-интерфейс
1. Зайдите в репозиторий: https://github.com/Lyti4/ParserRIba
2. Перейдите на вкладку "Actions" → "set up a workflow yourself"
3. Или создайте файл `.github/workflows/ci.yml` через интерфейс:
   - Нажмите "Add file" → "Create new file"
   - Имя файла: `.github/workflows/ci.yml`
   - Вставьте содержимое из файла `ci_template.yml` (см. ниже)
   - Нажмите "Commit changes"

## Содержимое файла ci.yml
Скопируйте этот код в файл `.github/workflows/ci.yml`:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ "проект-парсеров-цен-на-рыбу-253cc", "main" ]
  pull_request:
    branches: [ "main" ]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        playwright install chromium
    
    - name: Lint with flake8
      run: |
        pip install flake8
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
    
    - name: Run tests
      run: |
        pytest tests/ -v --tb=short

  docker-build:
    needs: lint-and-test
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: docker build -t parserriba:latest .
    
    - name: Test Docker image
      run: docker run --rm parserriba:latest python -c "print('Docker build successful')"
```

## Что уже работает без CI/CD
Все остальные компоненты проекта полностью готовы:
- ✅ Knowledge Base (6 магазинов)
- ✅ Парсеры (Pyaterochka, Magnit, Lenta, Auchan, Okey, Perekrestok)
- ✅ Стратегии и Политики
- ✅ Session Manager
- ✅ Docker и docker-compose
- ✅ Интеграционные тесты

Запуск локально:
```bash
docker-compose up --build
# или
pytest tests/ -v
```
