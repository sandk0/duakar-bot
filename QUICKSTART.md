# 🚀 Быстрый запуск VPN Telegram Bot

## Предварительные требования

- Python 3.11+
- Docker и Docker Compose
- PostgreSQL 15+ (или через Docker)
- Redis (или через Docker)
- Работающий Marzban сервер

## Шаг 1: Клонирование и настройка

```bash
git clone <your-repo-url>
cd telegram-bot

# Создание файла окружения
cp .env.example .env
```

## Шаг 2: Настройка .env файла

Отредактируйте `.env` файл и заполните обязательные параметры:

```env
# Telegram Bot
BOT_TOKEN=your_bot_token_from_botfather
BOT_USERNAME=your_bot_username

# Database
DATABASE_URL=postgresql+asyncpg://vpn_user:vpn_password@localhost:5432/vpn_bot
REDIS_URL=redis://localhost:6379/0

# Marzban
MARZBAN_API_URL=https://your-marzban-server.com/api
MARZBAN_ADMIN_USERNAME=admin
MARZBAN_ADMIN_PASSWORD=your_password

# Payment Systems (по крайней мере один)
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key

WATA_API_KEY=your_wata_api_key
WATA_SECRET_KEY=your_wata_secret_key

# Security
SECRET_KEY=your-secret-key-change-this
JWT_SECRET_KEY=your-jwt-secret-key
```

## Шаг 3: Запуск через Docker (Рекомендуется)

```bash
# Быстрый запуск (создаст .env и запустит все сервисы)
make setup

# Или пошагово:
make build
make up

# Просмотр логов
make logs
```

## Шаг 4: Инициализация базы данных

```bash
# Создание таблиц и начальных данных
make shell-bot
python scripts/setup_database.py
exit

# Создание администратора (замените на ваш Telegram ID)
make shell-bot
python scripts/init_admin.py 123456789 admin "Admin User"
exit
```

## Шаг 5: Проверка работы

```bash
# Проверка статуса сервисов
make status

# Проверка здоровья системы
make health

# Просмотр логов бота
make logs-bot
```

## Доступные сервисы

После запуска будут доступны:

- **Telegram Bot** - основной бот
- **API документация**: http://localhost:8000/docs
- **Grafana**: http://localhost:3000 (admin/admin) 
- **Prometheus**: http://localhost:9090
- **Flower (Celery)**: http://localhost:5555
- **Adminer (БД)**: http://localhost:8080

## Полезные команды

```bash
# Просмотр логов
make logs                # Все сервисы
make logs-bot           # Только бот
make logs-api           # Только API
make logs-worker        # Только Celery worker

# Управление
make restart            # Перезапуск всех сервисов
make down              # Остановка всех сервисов
make clean             # Полная очистка

# Разработка
make shell-bot         # Консоль в контейнере бота
make shell-db          # Консоль PostgreSQL
make redis-cli         # Redis CLI

# Бэкапы
make backup            # Создать бэкап БД
make backup-full       # Полный бэкап

# Мониторинг
make monitor           # Реальное время логи + статистика
make health            # Проверка здоровья сервисов
```

## Запуск без Docker (разработка)

```bash
# Установка зависимостей
pip install -r requirements.txt

# Настройка БД (если PostgreSQL уже запущен)
python scripts/setup_database.py

# Запуск бота
python -m bot.main

# В отдельных терминалах:
celery -A tasks.celery_app worker --loglevel=info
celery -A tasks.celery_app beat --loglevel=info
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## Продакшн развертывание

### Автоматическое развертывание

```bash
# На сервере (Ubuntu/Debian)
curl -sSL https://raw.githubusercontent.com/your-repo/main/scripts/deploy.sh | sudo bash -s -- --domain your-domain.com
```

### Ручное развертывание

```bash
# Клонирование на сервер
git clone <your-repo>
cd telegram-bot

# Настройка окружения
cp .env.example .env
# Отредактируйте .env

# Запуск в продакшне
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Настройка SSL (если нужен)
# Настройка Nginx
# Настройка файрвола
```

## Первоначальная настройка бота

1. **Создайте бота в BotFather**:
   - Откройте [@BotFather](https://t.me/botfather)
   - Используйте `/newbot`
   - Получите токен и username

2. **Настройте Marzban**:
   - Убедитесь, что API доступен
   - Создайте админа в Marzban
   - Получите данные для подключения

3. **Настройте платежные системы**:
   - YooKassa: создайте магазин и получите ключи
   - Wata: зарегистрируйтесь и получите API ключи

4. **Создайте администратора**:
   ```bash
   python scripts/init_admin.py YOUR_TELEGRAM_ID
   ```

5. **Протестируйте**:
   - Запустите бота: `/start`
   - Войдите в админку: `/admin`
   - Протестируйте оплату и VPN

## Решение проблем

### Бот не запускается
```bash
# Проверьте логи
make logs-bot

# Проверьте конфигурацию
cat .env

# Проверьте соединение с БД
make shell-db
```

### Ошибки платежей
```bash
# Проверьте настройки платежных систем в .env
# Проверьте логи API
make logs-api

# Проверьте webhook URL в настройках платежной системы
```

### Проблемы с Marzban
```bash
# Проверьте доступность API
curl -X GET "https://your-marzban.com/api/system" -H "Authorization: Bearer your-token"

# Проверьте логи бота для ошибок Marzban
make logs-bot | grep -i marzban
```

### Проблемы с контейнерами
```bash
# Проверьте статус
make status

# Перезапустите проблемный сервис
docker-compose restart bot

# Пересоберите при изменении кода
make build
make restart
```

## Полезные ссылки

- [Документация Marzban](https://github.com/Gozargah/Marzban)
- [YooKassa API](https://yookassa.ru/developers)
- [Aiogram документация](https://docs.aiogram.dev/)
- [Docker Compose](https://docs.docker.com/compose/)

## Поддержка

При возникновении проблем:

1. Проверьте логи: `make logs`
2. Проверьте статус: `make health` 
3. Изучите документацию
4. Создайте issue в репозитории