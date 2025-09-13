# Техническое задание на разработку Telegram-бота для VPN-сервиса

## Общее описание проекта
Разработать Telegram-бота для управления подписками VPN-сервиса на базе Marzban с поддержкой протокола VLESS. Бот должен обеспечивать полный цикл работы с клиентами: от регистрации и оплаты до выдачи конфигураций и технической поддержки.

## Технологический стек

### Backend
- **Язык**: Python 3.11+
- **Фреймворк бота**: aiogram 3.x
- **База данных**: PostgreSQL 15+
- **Кеширование**: Redis
- **Очереди задач**: Celery + Redis/RabbitMQ
- **API**: FastAPI (для веб-дашборда)
- **ORM**: SQLAlchemy 2.0 / Tortoise ORM
- **Миграции БД**: Alembic

### Мониторинг и логирование
- **Метрики**: Prometheus + Grafana
- **Логирование**: Python logging + ELK Stack (опционально)
- **APM**: Sentry для отслеживания ошибок

### Деплой
- **Контейнеризация**: Docker + docker-compose
- **Reverse proxy**: Nginx/Traefik
- **CI/CD**: GitHub Actions / GitLab CI

## Архитектура системы

### Компоненты системы

1. **Telegram Bot Service** - основной сервис бота
2. **Payment Service** - сервис обработки платежей
3. **Marzban Integration Service** - интеграция с VPN-сервером
4. **Notification Service** - сервис уведомлений
5. **Admin Dashboard API** - API для веб-дашборда
6. **Background Tasks Worker** - Celery воркеры для фоновых задач
7. **Web Dashboard** - веб-интерфейс администратора

### База данных

#### Основные таблицы

```sql
-- Пользователи
users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    language_code VARCHAR(10) DEFAULT 'ru',
    referrer_id BIGINT REFERENCES users(id),
    is_blocked BOOLEAN DEFAULT FALSE,
    block_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
)

-- Подписки
subscriptions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    plan_type VARCHAR(50), -- monthly, quarterly, yearly
    status VARCHAR(50), -- active, expired, cancelled, trial
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    auto_renewal BOOLEAN DEFAULT TRUE,
    is_trial BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
)

-- Платежи
payments (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    subscription_id BIGINT REFERENCES subscriptions(id),
    amount DECIMAL(10,2),
    currency VARCHAR(10) DEFAULT 'RUB',
    payment_method VARCHAR(50), -- sbp, card, yoomoney
    payment_system VARCHAR(50), -- wata, yookassa
    status VARCHAR(50), -- pending, success, failed
    external_payment_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
)

-- VPN конфигурации
vpn_configs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    marzban_user_id VARCHAR(255),
    config_url TEXT,
    device_id VARCHAR(255),
    last_device_info TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP
)

-- Статистика использования
usage_stats (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    date DATE,
    bytes_uploaded BIGINT DEFAULT 0,
    bytes_downloaded BIGINT DEFAULT 0,
    connections_count INT DEFAULT 0,
    unique_ips TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
)

-- Промокоды
promo_codes (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    type VARCHAR(50), -- percent, fixed, days
    value DECIMAL(10,2),
    max_uses INT,
    current_uses INT DEFAULT 0,
    valid_from TIMESTAMP,
    valid_until TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
)

-- Реферальная статистика
referral_stats (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    referral_count INT DEFAULT 0,
    bonus_days_earned INT DEFAULT 0,
    bonus_days_used INT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
)

-- Тарифные планы
pricing_plans (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100),
    duration_days INT,
    price DECIMAL(10,2),
    discount_percent DECIMAL(5,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    features JSONB,
    created_at TIMESTAMP DEFAULT NOW()
)

-- FAQ
faq_items (
    id BIGSERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(100),
    order_index INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
)

-- Настройки системы
system_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
)

-- Логи действий
action_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    action_type VARCHAR(100),
    action_data JSONB,
    ip_address INET,
    created_at TIMESTAMP DEFAULT NOW()
)
```

## Функциональные требования

### 1. Пользовательский интерфейс бота

#### Главное меню
- 💳 Моя подписка
- 🔑 Получить конфиг
- 💰 Оплатить/Продлить
- 👥 Реферальная программа
- ❓ FAQ / Помощь
- ⚙️ Настройки
- 📊 Статистика использования

#### Процесс регистрации
1. Пользователь запускает бота командой /start
2. Автоматическая регистрация по Telegram ID
3. Проверка на реферальную ссылку
4. Предложение триального периода (7 дней)
5. Генерация VPN конфигурации через Marzban API
6. Отправка конфига и инструкций

### 2. Управление подписками

#### Тарифные планы
- **1 месяц** - базовая цена
- **3 месяца** - скидка X%
- **12 месяцев** - скидка Y%

*Цены и скидки настраиваются через админ-панель*

#### Триальный период
- Длительность: 7 дней
- Полный функционал без ограничений
- Один раз на пользователя
- Автоматическое напоминание об окончании

#### Автопродление
- Включено по умолчанию
- Попытка списания в день окончания
- При неудаче - повторная попытка через 24 часа
- После двух неудач - отключение подписки
- Уведомления на каждом этапе

### 3. Платежная система

#### Поддерживаемые методы оплаты
- **СБП** (Система быстрых платежей)
- **Банковские карты**

#### Интеграции с платежными системами
- wata.pro
- YooMoney/ЮKassa
- Возможность добавления других систем

#### Процесс оплаты
1. Выбор тарифного плана
2. Применение промокода (опционально)
3. Выбор способа оплаты
4. Переход на платежную страницу
5. Обработка webhook от платежной системы
6. Активация/продление подписки
7. Отправка уведомления и чека

### 4. VPN функционал

#### Интеграция с Marzban
- Использование Marzban API v0.7.0
- Автоматическое создание пользователей
- Генерация VLESS конфигураций
- Мониторинг статуса серверов
- Получение статистики трафика

#### Управление конфигурациями
- Один конфиг на пользователя
- Ограничение на одно устройство
- Возможность сброса и перевыпуска
- QR-код для быстрой настройки

#### Инструкции по установке
- iOS (Shadowrocket, Streisand)
- Android (v2rayNG, Clash)
- Windows (v2rayN, Clash for Windows)
- macOS (ClashX, V2RayX)
- Пошаговые инструкции с скриншотами

### 5. Реферальная система

#### Механика
- Реферер получает: X дней бесплатной подписки
- Реферал получает: Y дней бонуса к первой оплате
- Начисление после первой оплаты реферала
- Уникальная реферальная ссылка для каждого

#### Статистика
- Количество приглашенных
- Количество активных рефералов
- Заработанные бонусные дни

### 6. Система уведомлений

#### Типы уведомлений
- **За 3 дня до окончания** - первое напоминание
- **За 2 дня до окончания** - второе напоминание  
- **За 1 день до окончания** - последнее напоминание
- **Успешная оплата** - подтверждение
- **Неудачная оплата** - информирование
- **Проблемы с VPN** - техническое уведомление
- **Новости и акции** - маркетинговые рассылки

#### Реализация через Celery
- Планировщик задач (Celery Beat)
- Очередь отправки уведомлений
- Retry механизм при сбоях
- Батчинг для массовых рассылок

### 7. Администраторская панель

#### Функционал в боте
- Просмотр статистики пользователей
- Управление подписками
- Блокировка/разблокировка пользователей
- Создание и управление промокодами
- Массовые рассылки
- Управление FAQ
- Настройка цен и тарифов

#### Веб-дашборд

##### Технологии фронтенда
- React/Vue.js + TypeScript
- Ant Design / Material-UI
- Chart.js для графиков
- WebSocket для real-time обновлений

##### Разделы дашборда

**1. Главная страница**
- Ключевые метрики (DAU, MAU, Revenue)
- Графики роста пользователей
- Статус VPN серверов
- Последние платежи

**2. Пользователи**
- Таблица с фильтрами и поиском
- Детальная информация по клику
- История платежей и использования
- Управление подпиской
- Экспорт в CSV/Excel

**3. Финансы**
- График доходов
- Разбивка по тарифам
- Конверсия триал → платная подписка
- LTV, ARPU, Churn rate

**4. VPN серверы**
- Мониторинг нагрузки
- Количество активных подключений
- Использование трафика
- Управление серверами

**5. Маркетинг**
- Управление промокодами
- Реферальная статистика
- Создание рассылок
- A/B тестирование

**6. Настройки**
- Тарифные планы
- Платежные системы
- Тексты сообщений
- FAQ управление

### 8. Промокоды

#### Типы промокодов
- Процентная скидка
- Фиксированная скидка
- Дополнительные дни

#### Параметры
- Одноразовые/многоразовые
- Срок действия
- Ограничение по использованиям
- Применимость к тарифам

### 9. FAQ и поддержка

#### FAQ в боте
- Категоризированные вопросы
- Быстрый поиск
- Редактирование через админку

#### Поддержка
- Кнопка "Связаться с поддержкой"
- Отображение username саппорта
- Автодиагностика проблем

### 10. Автодиагностика

#### Проверки
- Статус подписки
- Валидность конфигурации
- Доступность VPN серверов
- Проверка подключения

#### Рекомендации
- Автоматические советы по решению
- Ссылки на соответствующие FAQ
- Эскалация в поддержку при необходимости

## Нефункциональные требования

### Производительность
- Поддержка 1000+ активных пользователей
- Время ответа бота < 2 секунд
- Обработка 100+ платежей/час

### Масштабируемость
- Горизонтальное масштабирование воркеров
- Поддержка множественных VPN серверов
- Балансировка нагрузки между серверами
- Database connection pooling

### Безопасность
- Rate limiting (10 запросов/минута на пользователя)
- Валидация всех входных данных
- Шифрование чувствительных данных в БД
- HTTPS для всех внешних соединений
- Защита от SQL инъекций через ORM
- Регулярные бэкапы БД

### Надежность
- Graceful shutdown
- Retry механизмы для внешних API
- Circuit breaker для платежных систем
- Health checks для всех сервисов
- Автовосстановление при сбоях

### Мониторинг

#### Метрики Prometheus
- Количество активных пользователей
- Успешность платежей
- Время ответа API
- Использование ресурсов
- Ошибки и исключения

#### Дашборды Grafana
- Общая статистика системы
- Финансовые показатели
- Технические метрики
- Алерты и уведомления

### Логирование
- Структурированные логи (JSON)
- Уровни: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Ротация логов через 30 дней
- Централизованное хранение

### Резервное копирование
- Автоматические бэкапы БД еженедельно
- Хранение бэкапов 30 дней
- Тестирование восстановления
- Offsite копии критических данных

## API Endpoints (FastAPI)

### Аутентификация
- `POST /api/auth/login` - вход для админов
- `POST /api/auth/refresh` - обновление токена
- `POST /api/auth/logout` - выход

### Пользователи
- `GET /api/users` - список пользователей
- `GET /api/users/{id}` - детали пользователя
- `PUT /api/users/{id}` - обновление пользователя
- `POST /api/users/{id}/block` - блокировка
- `POST /api/users/{id}/unblock` - разблокировка

### Подписки
- `GET /api/subscriptions` - список подписок
- `GET /api/subscriptions/{id}` - детали подписки
- `PUT /api/subscriptions/{id}` - изменение подписки
- `POST /api/subscriptions/{id}/cancel` - отмена

### Платежи
- `GET /api/payments` - история платежей
- `GET /api/payments/{id}` - детали платежа
- `POST /api/payments/webhook/{provider}` - webhook endpoint

### Статистика
- `GET /api/stats/overview` - общая статистика
- `GET /api/stats/revenue` - финансовая статистика
- `GET /api/stats/users` - статистика пользователей
- `GET /api/stats/usage` - статистика использования

### Промокоды
- `GET /api/promo` - список промокодов
- `POST /api/promo` - создание промокода
- `PUT /api/promo/{id}` - изменение
- `DELETE /api/promo/{id}` - удаление

### Рассылки
- `POST /api/broadcast` - создание рассылки
- `GET /api/broadcast/history` - история рассылок

### Настройки
- `GET /api/settings` - получение настроек
- `PUT /api/settings` - обновление настроек

## Структура проекта

```
telegram-vpn-bot/
├── bot/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── handlers/
│   │   ├── start.py
│   │   ├── subscription.py
│   │   ├── payment.py
│   │   ├── referral.py
│   │   ├── settings.py
│   │   ├── admin.py
│   │   └── support.py
│   ├── keyboards/
│   │   ├── user.py
│   │   └── admin.py
│   ├── middleware/
│   │   ├── auth.py
│   │   ├── throttling.py
│   │   └── logging.py
│   ├── states/
│   │   └── user.py
│   └── utils/
│       ├── messages.py
│       └── validators.py
├── services/
│   ├── payment/
│   │   ├── base.py
│   │   ├── wata.py
│   │   ├── yookassa.py
│   │   └── manager.py
│   ├── marzban/
│   │   ├── client.py
│   │   ├── models.py
│   │   └── utils.py
│   ├── notification/
│   │   ├── sender.py
│   │   └── templates.py
│   └── stats/
│       └── collector.py
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── auth.py
│   ├── dependencies.py
│   ├── routers/
│   │   ├── users.py
│   │   ├── subscriptions.py
│   │   ├── payments.py
│   │   ├── stats.py
│   │   └── settings.py
│   └── schemas/
│       ├── user.py
│       ├── subscription.py
│       └── payment.py
├── database/
│   ├── __init__.py
│   ├── connection.py
│   ├── models/
│   │   ├── user.py
│   │   ├── subscription.py
│   │   ├── payment.py
│   │   └── stats.py
│   └── migrations/
│       └── alembic/
├── tasks/
│   ├── __init__.py
│   ├── celery_app.py
│   ├── notifications.py
│   ├── payments.py
│   ├── stats.py
│   └── backup.py
├── dashboard/
│   ├── package.json
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── utils/
│   └── public/
├── docker/
│   ├── Dockerfile.bot
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   └── Dockerfile.dashboard
├── configs/
│   ├── bot.yaml
│   ├── api.yaml
│   ├── celery.yaml
│   └── nginx.conf
├── scripts/
│   ├── backup.sh
│   ├── deploy.sh
│   └── migrate.sh
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── requirements.txt
├── package.json
├── Makefile
└── README.md
```

## Переменные окружения (.env)

```env
# Telegram
BOT_TOKEN=
BOT_USERNAME=

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/vpn_bot
REDIS_URL=redis://localhost:6379/0

# Marzban
MARZBAN_API_URL=https://vpn.example.com/api
MARZBAN_API_TOKEN=
MARZBAN_ADMIN_USERNAME=
MARZBAN_ADMIN_PASSWORD=

# Payment Systems
WATA_API_KEY=
WATA_SECRET_KEY=
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=

# Security
SECRET_KEY=
JWT_SECRET_KEY=
ENCRYPTION_KEY=

# Monitoring
SENTRY_DSN=
PROMETHEUS_PORT=9090
GRAFANA_ADMIN_PASSWORD=

# Other
SUPPORT_USERNAME=@support
TIMEZONE=Europe/Moscow
DEBUG=False
```

## Этапы разработки

### Этап 1: Базовая инфраструктура (1 неделя)
- Настройка проекта и окружения
- Базовая структура БД
- Docker конфигурация
- CI/CD pipeline

### Этап 2: Ядро бота (2 недели)
- Регистрация и авторизация
- Основные handlers
- Интеграция с Marzban API
- Базовое управление подписками

### Этап 3: Платежная система (2 недели)
- Интеграция платежных систем
- Обработка webhooks
- Автопродление
- История платежей

### Этап 4: Расширенный функционал (2 недели)
- Реферальная система
- Промокоды
- FAQ
- Автодиагностика

### Этап 5: Админ-панель в боте (1 неделя)
- Команды администратора
- Управление пользователями
- Рассылки
- Статистика

### Этап 6: Веб-дашборд (2 недели)
- FastAPI backend
- React frontend
- Real-time обновления
- Графики и метрики

### Этап 7: Фоновые задачи (1 неделя)
- Celery workers
- Уведомления
- Сбор статистики
- Резервное копирование

### Этап 8: Мониторинг и оптимизация (1 неделя)
- Prometheus + Grafana
- Логирование
- Performance tuning
- Load testing

### Этап 9: Тестирование и документация (1 неделя)
- Unit тесты
- Integration тесты
- API документация
- Deployment guide

### Этап 10: Запуск и поддержка
- Production deployment
- Мониторинг
- Исправление багов
- Итеративные улучшения

## Критерии успешности проекта

1. **Технические метрики**
   - Uptime > 99.9%
   - Время ответа < 2 сек
   - Успешность платежей > 95%

2. **Бизнес метрики**
   - Конверсия trial → paid > 30%
   - Churn rate < 10% в месяц
   - LTV/CAC > 3

3. **Пользовательские метрики**
   - Успешная активация > 90%
   - Обращений в поддержку < 5%
   - Оценка удовлетворенности > 4.5/5

## Риски и митигация

1. **Блокировка Telegram бота**
   - Резервные боты
   - Web-версия личного кабинета

2. **Проблемы с платежами**
   - Множественные платежные системы
   - Криптовалютные платежи как backup

3. **Перегрузка VPN серверов**
   - Автомасштабирование
   - Балансировка нагрузки
   - Мониторинг и алерты

4. **Утечка данных**
   - Шифрование БД
   - Регулярные security audits
   - Минимизация хранимых данных

## Дополнительные возможности для будущего развития

1. **Мультиязычность** - поддержка английского и других языков
2. **Корпоративные тарифы** - специальные условия для команд
3. **Выбор локации сервера** - возможность выбора страны
4. **Семейные подписки** - несколько устройств на аккаунт
5. **VPN для роутера** - инструкции и поддержка
6. **Партнерская программа** - для блогеров и influencers
7. **White-label решение** - брендирование для партнеров
8. **API для интеграций** - публичный API для разработчиков
9. **Мобильные приложения** - нативные iOS/Android клиенты
10. **Умная маршрутизация** - split tunneling и правила

---

*Этот промпт содержит полное техническое задание для разработки Telegram-бота VPN-сервиса. Документ может быть использован как для самостоятельной разработки, так и для постановки задачи команде разработчиков.*