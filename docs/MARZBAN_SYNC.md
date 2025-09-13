# 🔄 Синхронизация данных с Marzban

## Обзор

Система автоматической синхронизации данных между VPN Bot базой данных и Marzban API для обеспечения актуальности информации о подписках, статусе пользователей и использовании трафика.

## 🚀 Компоненты синхронизации

### 1. Синхронизация подписок (`sync_subscriptions_from_marzban`)
**Частота:** Каждые 2 часа  
**Функция:** Обновление данных о подписках из Marzban

**Выполняемые действия:**
- ✅ Проверка статуса пользователей в Marzban (active/expired/disabled)
- ✅ Обновление дат истечения подписок из Marzban API
- ✅ Синхронизация используемого трафика
- ✅ Автоматическое отключение истекших подписок
- ✅ Обновление времени последнего подключения

**Результат:**
```json
{
    "synced": 15,
    "errors": 2, 
    "total": 17
}
```

### 2. Синхронизация статуса пользователей (`sync_user_status_from_marzban`)
**Частота:** Каждый час в 30 минут  
**Функция:** Проверка и обновление статуса активности пользователей

**Выполняемые действия:**
- ✅ Проверка существования пользователя в Marzban
- ✅ Обновление статуса VPN конфигурации (active/inactive)
- ✅ Синхронизация данных о трафике
- ✅ Выявление пользователей, удаленных из Marzban

### 3. Очистка истекших пользователей (`cleanup_expired_marzban_users`)
**Частота:** Еженедельно по понедельникам в 01:00  
**Функция:** Освобождение ресурсов Marzban от истекших пользователей

**Выполняемые действия:**
- ✅ Поиск подписок, истекших более 7 дней назад
- ✅ Удаление пользователей из Marzban
- ✅ Обновление локальных записей в БД
- ✅ Логирование операций очистки

### 4. Сбор системной статистики (`get_marzban_system_stats`)
**Частота:** Каждые 15 минут  
**Функция:** Мониторинг состояния Marzban сервера

**Собираемые данные:**
- 📊 Версия Marzban
- 💾 Использование памяти (total/used)
- 💻 Загрузка CPU и количество ядер
- 👥 Количество пользователей (total/active)
- 📈 Пропускная способность (incoming/outgoing)
- ⚡ Скорость передачи данных

## 🔧 Конфигурация

### Очереди Celery
```python
task_routes = {
    'tasks.marzban_sync.*': {'queue': 'marzban'},
    # другие очереди...
}
```

### Расписание задач
```python
beat_schedule = {
    'sync-subscriptions-from-marzban': {
        'task': 'tasks.marzban_sync.sync_subscriptions_from_marzban',
        'schedule': crontab(minute=0, hour='*/2'),  # Каждые 2 часа
    },
    'sync-user-status-from-marzban': {
        'task': 'tasks.marzban_sync.sync_user_status_from_marzban',
        'schedule': crontab(minute=30),  # Каждый час в 30 минут
    },
    'cleanup-expired-marzban-users': {
        'task': 'tasks.marzban_sync.cleanup_expired_marzban_users',
        'schedule': crontab(minute=0, hour=1, day_of_week=1),  # Понедельник 01:00
    },
    'get-marzban-system-stats': {
        'task': 'tasks.marzban_sync.get_marzban_system_stats',
        'schedule': crontab(minute='*/15'),  # Каждые 15 минут
    }
}
```

## 📋 Логирование и мониторинг

### Примеры лог-сообщений
```
INFO: Marzban sync completed: 15 synced, 2 errors
INFO: Updating subscription end_date for user 12345: 2025-09-15 -> 2025-09-20
INFO: Marked VPN config inactive for missing user 67890
INFO: User status sync completed: 3 users updated
INFO: Cleaned up expired Marzban user for 11111
```

### Мониторинг через Flower
Доступен веб-интерфейс мониторинга задач: `http://localhost:5555`

## 🧪 Тестирование

### Ручной запуск синхронизации
```bash
# Синхронизация подписок
docker exec vpn_bot_worker python -c "
from tasks.marzban_sync import _sync_subscriptions_from_marzban
import asyncio
asyncio.run(_sync_subscriptions_from_marzban())
"

# Проверка статуса пользователей
docker exec vpn_bot_worker python -c "
from tasks.marzban_sync import _sync_user_status_from_marzban  
import asyncio
asyncio.run(_sync_user_status_from_marzban())
"

# Получение системной статистики
docker exec vpn_bot_worker python -c "
from tasks.marzban_sync import _get_marzban_system_stats
import asyncio
print(asyncio.run(_get_marzban_system_stats()))
"
```

### Запуск через Celery API
```bash
# Через Celery beat
docker exec vpn_bot_beat celery -A tasks.celery_app call tasks.marzban_sync.sync_subscriptions_from_marzban

# Через Flower API
curl -X POST "http://localhost:5555/api/task/apply/tasks.marzban_sync.sync_subscriptions_from_marzban"
```

## ⚠️ Важные особенности

### Обработка часовых поясов
- Marzban API возвращает timestamp в UTC
- PostgreSQL использует TIMESTAMP WITHOUT TIME ZONE  
- Выполняется конвертация: `datetime.fromtimestamp(ts, timezone.utc).replace(tzinfo=None)`

### Ограничение скорости запросов
- Между запросами к Marzban API добавляется задержка 0.05-0.1 сек
- Защита от перегрузки API при большом количестве пользователей

### Обработка ошибок
- Retry механизм в Marzban клиенте (3 попытки)
- Логирование всех ошибок с сохранением контекста
- Продолжение работы при ошибках отдельных пользователей

## 🔒 Безопасность

### Аутентификация
- Автоматическое обновление токенов доступа
- Безопасное хранение учетных данных в переменных окружения
- Таймауты для предотвращения зависания

### Изоляция задач
- Отдельная очередь `marzban` для изоляции задач синхронизации
- Ограничение времени выполнения задач (30 минут)
- Ограничение количества задач на процесс (100)

## 📈 Производительность

### Оптимизации
- Пакетная обработка пользователей
- Асинхронные запросы к API
- Эффективные SQL запросы с JOIN
- Кэширование токенов аутентификации

### Масштабирование
- Горизонтальное масштабирование воркеров Celery
- Раздельные очереди для разных типов задач
- Мониторинг производительности через Flower

## 🚀 Результат

Система синхронизации обеспечивает:
- ✅ **Актуальные данные**: Автоматическое обновление статуса подписок
- ✅ **Мониторинг**: Постоянный контроль состояния Marzban сервера
- ✅ **Оптимизация**: Очистка неиспользуемых ресурсов
- ✅ **Надежность**: Устойчивость к ошибкам и сбоям
- ✅ **Производительность**: Эффективное использование ресурсов