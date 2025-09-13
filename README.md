# 🚀 VPN Telegram Bot

**Профессиональное решение для управления VPN-сервисом через Telegram с современной веб-панелью администратора.**

Полнофункциональная система управления VPN подписками, интегрированная с Marzban API, включающая платежные системы, аналитику, мониторинг и автоматизацию.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-supported-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## ✨ Ключевые возможности

### 🤖 Telegram Bot
- **Полнофункциональный бот** с FSM состояниями и интерактивными клавиатурами
- **Регистрация и аутентификация** пользователей через Telegram
- **VPN конфигурации** с QR-кодами для быстрого подключения
- **Автоматические уведомления** об истечении подписки, платежах, обновлениях

### 💳 Платежная система
- **YooKassa** - основная платежная система (карты, СБП, электронные деньги)
- **Wata** - альтернативная платежная система
- **Автоматическая обработка** платежей и webhook'ов
- **Возврат средств** и управление спорными ситуациями

### 🔐 VPN управление
- **Интеграция с Marzban API v0.7.0** для управления VPN пользователями
- **Автоматическое создание** и настройка VPN аккаунтов
- **Мониторинг использования** трафика и статистики подключений
- **Многосерверная поддержка** (в планах)

### 👥 Маркетинговые инструменты
- **Реферальная программа** с автоматическим начислением бонусов
- **Система промокодов** (скидки, бонусные дни, бесплатный доступ)
- **Пробный период 7 дней** для новых пользователей
- **Массовые рассылки** и уведомления

### 📊 Аналитика и управление
- **React административная панель** с современным TypeScript интерфейсом
- **Подробная аналитика** доходов, пользователей, конверсий
- **Управление пользователями** и подписками
- **Prometheus + Grafana** для мониторинга системы

### 🛠 Техническая надежность
- **Микросервисная архитектура** на Docker контейнерах
- **Асинхронная обработка** на базе Python asyncio
- **Celery** для фоновых задач и автоматизации
- **PostgreSQL** с миграциями Alembic
- **Redis** для кэширования и очередей

## 📋 Системные требования

### Минимальные требования
- **Операционная система**: Ubuntu 20.04 LTS или новее
- **CPU**: 2 ядра
- **RAM**: 4 GB
- **Диск**: 20 GB SSD
- **Docker**: 20.10+ и Docker Compose 2.0+

### Рекомендуемые требования (Production)
- **CPU**: 4 ядра
- **RAM**: 8 GB  
- **Диск**: 100 GB SSD
- **Сеть**: 100 Mbps

### Программные зависимости
- **Python**: 3.11+
- **PostgreSQL**: 15+
- **Redis**: 7+
- **Node.js**: 18+ (для dashboard)
- **Marzban**: 0.7.0

## ⚡ Быстрый старт

### 1. Клонирование и настройка

```bash
# Клонируование репозитория
git clone https://github.com/your-username/vpn-telegram-bot.git
cd vpn-telegram-bot

# Копирование конфигурации
cp .env.example .env

# Редактирование конфигурации (обязательные поля)
nano .env
```

### 2. Обязательная конфигурация

Отредактируйте `.env` файл и заполните минимально необходимые поля:

```env
# Telegram Bot (получить у @BotFather)
BOT_TOKEN=your_bot_token_here
BOT_USERNAME=your_bot_username
ADMIN_USER_IDS=your_telegram_id

# База данных
DATABASE_URL=postgresql+asyncpg://vpn_user:secure_password@postgres:5432/vpn_bot

# Marzban VPN сервер
MARZBAN_BASE_URL=http://your_marzban_server:8080
MARZBAN_USERNAME=admin
MARZBAN_PASSWORD=your_marzban_password

# Платежные системы (хотя бы одна)
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key

# Безопасность (сгенерировать новые ключи!)
JWT_SECRET_KEY=your_very_long_random_secret_key_change_this
WEBHOOK_SECRET=your_webhook_secret_key
```

### 3. Генерация секретных ключей

```bash
# Генерация JWT секретного ключа
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))"

# Генерация webhook секрета
python3 -c "import secrets; print('WEBHOOK_SECRET=' + secrets.token_urlsafe(32))"
```

### 4. Запуск системы

```bash
# Запуск всех сервисов
docker-compose up -d

# Ожидание запуска базы данных
sleep 30

# Применение миграций базы данных
docker-compose exec api alembic upgrade head

# Проверка статуса всех контейнеров
docker-compose ps
```

### 5. Проверка работоспособности

```bash
# Проверка логов бота
docker-compose logs bot

# Проверка API
curl http://localhost:8000/health

# Проверка административной панели
curl http://localhost:3000
```

## 🛠 Детальная установка

### Разработка без Docker

```bash
# Установка Python зависимостей
pip install -r requirements.txt

# Установка и настройка PostgreSQL
sudo apt install postgresql postgresql-contrib
sudo -u postgres createuser -P vpn_user
sudo -u postgres createdb -O vpn_user vpn_bot

# Установка и запуск Redis
sudo apt install redis-server
sudo systemctl start redis-server

# Применение миграций
alembic upgrade head

# Запуск компонентов в отдельных терминалах
python -m bot.main                                    # Telegram bot
uvicorn api.main:app --reload --port 8000             # FastAPI API
celery -A tasks.celery_app worker --loglevel=info     # Celery worker
celery -A tasks.celery_app beat --loglevel=info       # Celery scheduler

# Запуск React dashboard (опционально)
cd dashboard
npm install
npm start
```

## 📁 Архитектура проекта

```
vpn-telegram-bot/
├── 🤖 bot/                     # Telegram Bot (aiogram)
│   ├── handlers/              # Обработчики команд и callback'ов
│   ├── keyboards/             # Inline и Reply клавиатуры
│   ├── middleware/            # Аутентификация, логирование, rate limiting
│   ├── states/               # FSM состояния для диалогов
│   └── utils/                # Вспомогательные функции
│
├── 🌐 api/                     # REST API (FastAPI)
│   ├── routes/               # Маршруты API endpoints
│   ├── schemas/              # Pydantic схемы валидации
│   ├── dependencies/         # Зависимости (auth, database)
│   └── middleware/           # CORS, rate limiting, логирование
│
├── 🗄️ database/               # База данных (PostgreSQL + SQLAlchemy)
│   ├── models/               # SQLAlchemy модели (User, Payment, VPN, etc.)
│   ├── migrations/           # Alembic миграции
│   └── repositories/         # Repository pattern для доступа к данным
│
├── ⚙️ services/               # Бизнес-логика и внешние интеграции
│   ├── marzban/              # Интеграция с Marzban VPN API
│   ├── payment/              # Платежные системы (YooKassa, Wata)
│   ├── notification/         # Telegram и Email уведомления
│   ├── analytics/            # Сбор и анализ статистики
│   └── stats/                # Мониторинг использования VPN
│
├── 🔄 tasks/                  # Фоновые задачи (Celery)
│   ├── payment_tasks.py      # Обработка платежей
│   ├── notification_tasks.py # Отправка уведомлений
│   ├── usage_tasks.py        # Синхронизация статистики VPN
│   └── maintenance_tasks.py  # Очистка и резервное копирование
│
├── 📊 dashboard/              # Административная панель (React)
│   ├── src/components/       # React компоненты
│   ├── src/pages/           # Страницы админ-панели
│   ├── src/services/        # API клиенты
│   └── src/types/           # TypeScript типы
│
├── 🐳 docker/                 # Контейнеризация
│   ├── Dockerfile.bot        # Образ для Telegram бота
│   ├── Dockerfile.api        # Образ для FastAPI
│   ├── Dockerfile.worker     # Образ для Celery worker
│   └── .dockerignore         # Исключения для Docker
│
├── 📈 monitoring/             # Мониторинг системы
│   ├── prometheus.yml        # Конфигурация Prometheus
│   ├── alerts.yml           # Правила алертов
│   └── grafana-dashboard.json # Дашборд Grafana
│
├── 🧪 tests/                  # Тестирование
│   ├── unit/                # Юнит тесты
│   ├── integration/         # Интеграционные тесты
│   ├── fixtures/            # Фикстуры для тестов
│   └── conftest.py          # Настройки pytest
│
├── 📚 docs/                   # Документация
│   ├── ARCHITECTURE.md       # Архитектурное описание
│   ├── API.md               # Документация REST API
│   ├── BOT_COMMANDS.md      # Команды Telegram бота
│   ├── DATABASE.md          # Схема базы данных
│   ├── DEPLOYMENT.md        # Руководство по развертыванию
│   └── ROADMAP.md           # План развития проекта
│
├── 🔧 scripts/                # Вспомогательные скрипты
│   ├── init_data.py         # Инициализация тестовых данных
│   ├── backup.sh           # Резервное копирование
│   └── deploy.sh           # Деплой в production
│
├── docker-compose.yml        # Оркестрация для разработки
├── docker-compose.prod.yml   # Production конфигурация
├── requirements.txt          # Python зависимости
├── alembic.ini              # Настройки миграций
├── Makefile                 # Automation команды
├── .env.example             # Пример конфигурации
├── CHANGELOG.md             # История изменений
└── README.md                # Документация проекта
```

### Основные компоненты

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| **Telegram Bot** | aiogram 3.x | Пользовательский интерфейс |
| **REST API** | FastAPI | Административные операции |
| **Database** | PostgreSQL + SQLAlchemy | Хранение данных |
| **Cache/Queue** | Redis + Celery | Кэширование и фоновые задачи |
| **Frontend** | React + TypeScript | Веб-панель администратора |
| **Monitoring** | Prometheus + Grafana | Мониторинг системы |
| **VPN API** | Marzban Integration | Управление VPN аккаунтами |

## 🔧 Конфигурация и интеграции

### 🤖 Создание Telegram бота

```bash
# 1. Напишите @BotFather в Telegram
# 2. Отправьте команду /newbot
# 3. Следуйте инструкциям для создания бота
# 4. Сохраните токен бота в .env файл

BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxyz
BOT_USERNAME=your_vpn_bot
```

### 🔐 Настройка Marzban VPN

```bash
# Убедитесь, что Marzban API доступен и работает
curl http://your_marzban_server:8080/api/docs

# Создайте администратора в Marzban веб-интерфейсе
# Укажите данные в .env:
MARZBAN_BASE_URL=http://your_marzban_server:8080
MARZBAN_USERNAME=admin
MARZBAN_PASSWORD=your_secure_password
```

### 💳 Настройка платежных систем

#### YooKassa (Рекомендуется)
```bash
# 1. Зарегистрируйтесь на https://yookassa.ru
# 2. Создайте магазин и пройдите модерацию  
# 3. Получите shop_id и secret_key в личном кабинете
# 4. Укажите в .env:
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
YOOKASSA_WEBHOOK_URL=https://yourdomain.com/api/v1/payments/webhooks/yookassa
```

#### Wata (Альтернатива)
```bash
# 1. Зарегистрируйтесь на https://wata.pro
# 2. Получите API ключи в личном кабинете
# 3. Укажите в .env:
WATA_API_KEY=your_api_key
WATA_SECRET_KEY=your_secret_key
WATA_WEBHOOK_URL=https://yourdomain.com/api/v1/payments/webhooks/wata
```

### 📧 Email уведомления (опционально)

```env
# SMTP настройки для отправки email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=noreply@yourdomain.com
```

## 📊 Мониторинг и администрирование

### Веб-интерфейсы системы

| Сервис | URL | Описание |
|--------|-----|----------|
| **FastAPI Docs** | http://localhost:8000/docs | Swagger документация API |
| **Admin Panel** | http://localhost:3000 | React административная панель |
| **Grafana** | http://localhost:3000 | Дашборды и графики метрик |
| **Prometheus** | http://localhost:9090 | Сбор и просмотр метрик |
| **Flower** | http://localhost:5555 | Мониторинг Celery задач |

### Доступ к административной панели

```bash
# Логин в Grafana
Username: admin
Password: [указан в GRAFANA_ADMIN_PASSWORD]

# API аутентификация  
# Получение JWT токена через POST /api/v1/auth/login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "your_admin_password"}'
```

## 🚀 Production развертывание

### Быстрое развертывание

```bash
# Клонирование и настройка
git clone https://github.com/your-username/vpn-telegram-bot.git
cd vpn-telegram-bot

# Настройка production конфигурации
cp .env.example .env
nano .env  # Заполните все production значения

# Запуск в production режиме
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Применение миграций
docker-compose exec api alembic upgrade head
```

### SSL и домены

```bash
# Установка Certbot для Let's Encrypt
sudo apt install certbot

# Получение SSL сертификата
sudo certbot certonly --standalone -d yourdomain.com -d api.yourdomain.com

# Настройка Nginx reverse proxy
sudo nano /etc/nginx/sites-available/vpn-bot
# [конфигурация из docs/DEPLOYMENT.md]
```

### Мониторинг в production

```bash
# Настройка алертов в Prometheus
# Файл: monitoring/alerts.yml содержит правила для:
# - Высокая нагрузка на сервер
# - Ошибки в приложении  
# - Недоступность базы данных
# - Проблемы с платежами

# Настройка уведомлений (Slack, Telegram, Email)
# В Grafana можно настроить каналы уведомлений
```

## 📱 Использование бота

### Основные команды пользователя

| Команда | Описание |
|---------|----------|
| `/start` | Регистрация и главное меню |
| `/profile` | Информация о профиле и подписке |
| `/subscription` | Управление подписками |
| `/config` | Получение VPN конфигурации |
| `/usage` | Статистика использования VPN |
| `/referral` | Реферальная программа |
| `/trial` | Активация пробного периода |
| `/support` | Обращение в техподдержку |
| `/help` | Справка по командам |

### Административные команды

| Команда | Описание | Доступ |
|---------|----------|---------|
| `/admin` | Административное меню | Только админы |
| `/stats` | Системная статистика | Только админы |
| `/broadcast` | Массовая рассылка | Только админы |
| `/user_info <id>` | Информация о пользователе | Только админы |

## 🛡️ Безопасность

### Рекомендации по безопасности

```bash
# 1. Используйте сильные пароли
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. Регулярно обновляйте зависимости
pip list --outdated
docker-compose pull

# 3. Настройте firewall
sudo ufw enable
sudo ufw allow 22,80,443/tcp

# 4. Мониторьте логи безопасности
docker-compose logs --tail=100 | grep ERROR
```

### Резервное копирование

```bash
# Автоматическое резервное копирование (настройка cron)
0 2 * * * /path/to/vpn-telegram-bot/scripts/backup.sh

# Ручное резервное копирование
./scripts/backup.sh

# Восстановление из резервной копии
docker-compose exec -T postgres psql -U vpn_user -d vpn_bot < backup_file.sql
```

## 📚 Документация

Подробная документация доступна в директории [`docs/`](./docs/):

- 📖 [**Архитектура системы**](./docs/ARCHITECTURE.md) - Техническое описание компонентов
- 🌐 [**API документация**](./docs/API.md) - Полное описание REST API endpoints  
- 🤖 [**Команды бота**](./docs/BOT_COMMANDS.md) - Подробное описание команд Telegram бота
- 🗄️ [**База данных**](./docs/DATABASE.md) - Схема БД, модели, миграции
- 🚀 [**Развертывание**](./docs/DEPLOYMENT.md) - Детальное руководство по установке
- 🗺️ [**Roadmap**](./docs/ROADMAP.md) - План развития проекта

## 🔧 Makefile команды

```bash
# Управление Docker окружением
make up              # Запуск всех сервисов
make down            # Остановка всех сервисов  
make logs            # Просмотр логов
make restart         # Перезапуск сервисов

# База данных
make migrate         # Применение миграций
make migrate-create  # Создание новой миграции
make db-backup       # Резервное копирование БД

# Разработка
make test           # Запуск тестов
make lint           # Проверка кода линтерами
make format         # Форматирование кода

# Production
make deploy         # Развертывание в production
make ssl-setup      # Настройка SSL сертификатов
```

## 🐛 Troubleshooting

### Частые проблемы

```bash
# Проблема: Контейнер не запускается
docker-compose logs container_name
docker system prune -a  # Очистка Docker

# Проблема: Бот не отвечает
docker-compose exec bot python -c "import asyncio; asyncio.run(bot.get_me())"

# Проблема: Ошибки подключения к БД
docker-compose exec postgres psql -U vpn_user -d vpn_bot -c "SELECT 1;"

# Проблема: Недостаточно памяти
sudo swapon --show  # Проверка swap
docker stats        # Использование ресурсов

# Проблема: SSL сертификаты
sudo certbot certificates  # Проверка сертификатов
sudo nginx -t              # Проверка конфигурации Nginx
```

## 📄 Лицензия

MIT License - см. [LICENSE](LICENSE) файл для деталей.

## 🤝 Поддержка

- 📧 **Email**: support@example.com
- 💬 **Telegram**: @your_support_bot  
- 🐛 **Issues**: [GitHub Issues](https://github.com/your-username/vpn-telegram-bot/issues)
- 📚 **Wiki**: [GitHub Wiki](https://github.com/your-username/vpn-telegram-bot/wiki)

## 🌟 Contributing

Приветствуются вклады в развитие проекта! См. [CONTRIBUTING.md](CONTRIBUTING.md) для деталей.

---

**⚡ Готовы начать?** Следуйте [быстрому старту](#-быстрый-старт) для запуска системы за 5 минут!