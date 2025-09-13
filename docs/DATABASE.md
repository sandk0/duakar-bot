# Database Documentation

## Обзор базы данных

Проект использует PostgreSQL 15+ как основную базу данных с SQLAlchemy 2.0 ORM и Alembic для миграций.

## Схема базы данных

### Таблица: users
Основная таблица пользователей системы.

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    phone_number VARCHAR(20),
    email VARCHAR(255),
    language_code VARCHAR(5) DEFAULT 'ru',
    status VARCHAR(20) DEFAULT 'active',
    trial_used BOOLEAN DEFAULT FALSE,
    referral_code VARCHAR(10) UNIQUE,
    referred_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_referral_code ON users(referral_code);
CREATE INDEX idx_users_status ON users(status);
```

**Поля:**
- `id`: Уникальный идентификатор пользователя
- `telegram_id`: ID пользователя в Telegram
- `username`: Имя пользователя в Telegram (@username)
- `first_name`, `last_name`: Имя и фамилия
- `phone_number`: Номер телефона
- `email`: Адрес электронной почты
- `language_code`: Код языка (ru, en)
- `status`: Статус пользователя (active, blocked, deleted)
- `trial_used`: Использован ли пробный период
- `referral_code`: Реферальный код пользователя
- `referred_by`: Кем был приглашен (FK на users.id)

### Таблица: subscriptions
Подписки пользователей.

```sql
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id INTEGER NOT NULL REFERENCES pricing_plans(id),
    status VARCHAR(20) DEFAULT 'pending',
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    auto_renew BOOLEAN DEFAULT FALSE,
    payment_id INTEGER REFERENCES payments(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_end_date ON subscriptions(end_date);
```

**Статусы подписок:**
- `pending`: Ожидает оплаты
- `active`: Активная подписка
- `expired`: Истекшая подписка
- `cancelled`: Отмененная подписка

### Таблица: pricing_plans
Тарифные планы.

```sql
CREATE TABLE pricing_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'RUB',
    duration_days INTEGER NOT NULL,
    type VARCHAR(20) DEFAULT 'regular',
    is_active BOOLEAN DEFAULT TRUE,
    features JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Типы планов:**
- `trial`: Пробный период
- `regular`: Обычный план
- `premium`: Премиум план

### Таблица: payments
Платежи пользователей.

```sql
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    plan_id INTEGER REFERENCES pricing_plans(id),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'RUB',
    status VARCHAR(20) DEFAULT 'pending',
    system VARCHAR(20) NOT NULL,
    external_id VARCHAR(255),
    payment_url TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_payments_user_id ON payments(user_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_external_id ON payments(external_id);
```

**Платежные системы:**
- `yookassa`: ЮKassa
- `wata`: Wata
- `manual`: Ручное зачисление

**Статусы платежей:**
- `pending`: Ожидает оплаты
- `processing`: Обрабатывается
- `completed`: Завершен успешно
- `failed`: Ошибка оплаты
- `cancelled`: Отменен
- `refunded`: Возврат средств

### Таблица: vpn_configs
VPN конфигурации пользователей.

```sql
CREATE TABLE vpn_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    marzban_user_id VARCHAR(255),
    config_data TEXT,
    qr_code_data TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_vpn_configs_user_id ON vpn_configs(user_id);
CREATE INDEX idx_vpn_configs_marzban_user_id ON vpn_configs(marzban_user_id);
```

### Таблица: usage_stats
Статистика использования VPN.

```sql
CREATE TABLE usage_stats (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    bytes_uploaded BIGINT DEFAULT 0,
    bytes_downloaded BIGINT DEFAULT 0,
    connections_count INTEGER DEFAULT 0,
    unique_ips TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_usage_stats_user_date ON usage_stats(user_id, date);
CREATE INDEX idx_usage_stats_date ON usage_stats(date);
```

### Таблица: promo_codes
Промокоды.

```sql
CREATE TABLE promo_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    type VARCHAR(20) NOT NULL,
    discount_percent INTEGER,
    discount_amount DECIMAL(10,2),
    bonus_days INTEGER,
    usage_limit INTEGER,
    usage_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_promo_codes_code ON promo_codes(code);
CREATE INDEX idx_promo_codes_active ON promo_codes(is_active);
```

**Типы промокодов:**
- `discount`: Скидка на оплату
- `bonus_days`: Дополнительные дни
- `free_trial`: Бесплатный пробный период

### Таблица: promo_usage
Использование промокодов.

```sql
CREATE TABLE promo_usage (
    id SERIAL PRIMARY KEY,
    promo_code_id INTEGER NOT NULL REFERENCES promo_codes(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    payment_id INTEGER REFERENCES payments(id),
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_promo_usage_unique ON promo_usage(promo_code_id, user_id);
```

### Таблица: referral_stats
Статистика рефералов.

```sql
CREATE TABLE referral_stats (
    id SERIAL PRIMARY KEY,
    referrer_id INTEGER NOT NULL REFERENCES users(id),
    referred_id INTEGER NOT NULL REFERENCES users(id),
    bonus_days_granted INTEGER DEFAULT 0,
    bonus_granted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_referral_stats_referrer ON referral_stats(referrer_id);
CREATE INDEX idx_referral_stats_referred ON referral_stats(referred_id);
```

### Таблица: action_logs
Логи действий пользователей.

```sql
CREATE TABLE action_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_action_logs_user_id ON action_logs(user_id);
CREATE INDEX idx_action_logs_action ON action_logs(action);
CREATE INDEX idx_action_logs_created_at ON action_logs(created_at);
```

### Таблица: system_settings
Системные настройки.

```sql
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    type VARCHAR(20) DEFAULT 'string',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Таблица: faq_items
Часто задаваемые вопросы.

```sql
CREATE TABLE faq_items (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(50),
    order_index INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_faq_category ON faq_items(category);
CREATE INDEX idx_faq_order ON faq_items(order_index);
```

### Таблица: broadcast_messages
Сообщения рассылки.

```sql
CREATE TABLE broadcast_messages (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    target_users JSONB,
    status VARCHAR(20) DEFAULT 'draft',
    sent_count INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 0,
    scheduled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP
);

CREATE INDEX idx_broadcast_status ON broadcast_messages(status);
CREATE INDEX idx_broadcast_scheduled ON broadcast_messages(scheduled_at);
```

## Миграции Alembic

### Настройка
Файл `alembic.ini` содержит конфигурацию для миграций.

### Команды миграций
```bash
# Создание новой миграции
alembic revision --autogenerate -m "Add new table"

# Применение миграций
alembic upgrade head

# Откат миграции
alembic downgrade -1

# История миграций
alembic history

# Текущая версия
alembic current
```

### Структура директории миграций
```
database/migrations/
├── alembic/
│   └── versions/
│       ├── 001_initial_migration.py
│       ├── 002_add_referral_system.py
│       └── 003_add_promo_codes.py
├── env.py
└── script.py.mako
```

## Индексы для производительности

### Часто используемые запросы
```sql
-- Поиск активных подписок
CREATE INDEX idx_subscriptions_active ON subscriptions(user_id) 
WHERE status = 'active';

-- Статистика по дням
CREATE INDEX idx_usage_stats_date_range ON usage_stats(user_id, date) 
WHERE date >= CURRENT_DATE - INTERVAL '30 days';

-- Поиск по промокодам
CREATE INDEX idx_promo_codes_active_valid ON promo_codes(code) 
WHERE is_active = true AND (expires_at IS NULL OR expires_at > NOW());
```

## Backup и восстановление

### Автоматический backup
```bash
# Создание backup
pg_dump -h localhost -U vpn_user -d vpn_bot > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановление из backup
psql -h localhost -U vpn_user -d vpn_bot < backup_file.sql
```

### Настройка автоматического backup в cron
```bash
# Ежедневный backup в 2:00
0 2 * * * /usr/bin/pg_dump -h localhost -U vpn_user -d vpn_bot > /backups/vpn_bot_$(date +\%Y\%m\%d).sql
```

## Мониторинг производительности

### Полезные запросы для мониторинга
```sql
-- Активные подключения
SELECT count(*) FROM pg_stat_activity WHERE datname = 'vpn_bot';

-- Размер базы данных
SELECT pg_size_pretty(pg_database_size('vpn_bot'));

-- Самые медленные запросы
SELECT query, mean_time, calls FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 10;

-- Статистика по таблицам
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del 
FROM pg_stat_user_tables;
```

## Оптимизация

### Настройки PostgreSQL
```ini
# postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
wal_buffers = 16MB
checkpoint_completion_target = 0.9
random_page_cost = 1.1
```

### Партиционирование
Для таблиц с большим объемом данных (например, `usage_stats`) рекомендуется использовать партиционирование по дате.