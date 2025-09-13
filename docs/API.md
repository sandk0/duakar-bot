# API Documentation

## Базовая информация

- **Base URL**: `http://localhost:8000/api/v1`
- **Аутентификация**: JWT Bearer токен
- **Content-Type**: `application/json`

## Аутентификация

### POST /auth/login
Вход в систему для администраторов.

**Request:**
```json
{
  "username": "admin",
  "password": "password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### POST /auth/refresh
Обновление JWT токена.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "access_token": "new_jwt_token",
  "token_type": "bearer",
  "expires_in": 86400
}
```

## Пользователи

### GET /users
Получение списка пользователей с пагинацией.

**Query Parameters:**
- `skip`: Количество пропускаемых записей (default: 0)
- `limit`: Количество записей на страницу (default: 50)
- `search`: Поиск по имени/телеграм ID
- `status`: Фильтр по статусу ('active', 'blocked', 'trial')

**Response:**
```json
{
  "users": [
    {
      "id": 1,
      "telegram_id": 123456789,
      "username": "john_doe",
      "first_name": "John",
      "last_name": "Doe",
      "phone_number": "+1234567890",
      "email": "john@example.com",
      "status": "active",
      "trial_used": false,
      "referral_code": "JOHN123",
      "referred_by": null,
      "created_at": "2024-01-01T00:00:00Z",
      "last_activity": "2024-01-15T12:30:00Z"
    }
  ],
  "total": 150,
  "skip": 0,
  "limit": 50
}
```

### GET /users/{user_id}
Получение информации о конкретном пользователе.

**Response:**
```json
{
  "id": 1,
  "telegram_id": 123456789,
  "username": "john_doe",
  "subscription": {
    "id": 1,
    "plan_id": 1,
    "status": "active",
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-02-01T00:00:00Z"
  },
  "vpn_config": {
    "id": 1,
    "config_data": "encrypted_config",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  },
  "usage_stats": {
    "total_data_gb": 15.5,
    "days_active": 10,
    "last_activity": "2024-01-15T12:30:00Z"
  }
}
```

### PUT /users/{user_id}/status
Изменение статуса пользователя.

**Request:**
```json
{
  "status": "blocked",
  "reason": "Violation of terms"
}
```

### DELETE /users/{user_id}
Удаление пользователя (мягкое удаление).

## Подписки

### GET /subscriptions
Получение списка подписок.

**Query Parameters:**
- `skip`, `limit`: Пагинация
- `status`: Фильтр по статусу
- `plan_id`: Фильтр по тарифному плану
- `user_id`: Фильтр по пользователю

**Response:**
```json
{
  "subscriptions": [
    {
      "id": 1,
      "user_id": 1,
      "plan_id": 1,
      "status": "active",
      "start_date": "2024-01-01T00:00:00Z",
      "end_date": "2024-02-01T00:00:00Z",
      "auto_renew": true,
      "payment_id": 1,
      "user": {
        "id": 1,
        "username": "john_doe"
      },
      "plan": {
        "id": 1,
        "name": "Monthly",
        "price": 299,
        "duration_days": 30
      }
    }
  ],
  "total": 100
}
```

### POST /subscriptions
Создание новой подписки.

**Request:**
```json
{
  "user_id": 1,
  "plan_id": 1,
  "auto_renew": true
}
```

### PUT /subscriptions/{subscription_id}
Обновление подписки.

**Request:**
```json
{
  "status": "cancelled",
  "auto_renew": false
}
```

## Платежи

### GET /payments
Получение списка платежей.

**Query Parameters:**
- `skip`, `limit`: Пагинация
- `status`: Фильтр по статусу
- `system`: Фильтр по платежной системе ('yookassa', 'wata')
- `user_id`: Фильтр по пользователю
- `date_from`, `date_to`: Фильтр по дате

**Response:**
```json
{
  "payments": [
    {
      "id": 1,
      "user_id": 1,
      "amount": 299.0,
      "currency": "RUB",
      "status": "completed",
      "system": "yookassa",
      "external_id": "2c85a3f4-0000-50ba-9000-0b0a009c0000",
      "created_at": "2024-01-01T00:00:00Z",
      "completed_at": "2024-01-01T00:01:30Z",
      "user": {
        "id": 1,
        "username": "john_doe"
      }
    }
  ],
  "total": 250
}
```

### GET /payments/{payment_id}
Детальная информация о платеже.

### POST /payments/refund
Возврат платежа.

**Request:**
```json
{
  "payment_id": 1,
  "amount": 299.0,
  "reason": "User request"
}
```

## Аналитика

### GET /analytics/overview
Общая статистика системы.

**Response:**
```json
{
  "users": {
    "total": 1500,
    "active": 1200,
    "new_today": 15,
    "new_this_week": 85
  },
  "subscriptions": {
    "active": 950,
    "expired": 150,
    "revenue_today": 5970.0,
    "revenue_this_month": 125400.0
  },
  "usage": {
    "total_data_gb": 15400.5,
    "avg_per_user_gb": 12.8,
    "peak_concurrent_users": 450
  },
  "payments": {
    "success_rate": 0.94,
    "total_today": 25,
    "failed_today": 2
  }
}
```

### GET /analytics/revenue
Аналитика доходов.

**Query Parameters:**
- `period`: 'day', 'week', 'month', 'year'
- `date_from`, `date_to`: Период

**Response:**
```json
{
  "period": "month",
  "data": [
    {
      "date": "2024-01-01",
      "revenue": 8970.0,
      "transactions": 30,
      "new_subscriptions": 25
    }
  ],
  "total_revenue": 125400.0,
  "avg_revenue_per_day": 4046.77
}
```

### GET /analytics/users
Аналитика пользователей.

**Response:**
```json
{
  "registrations": [
    {
      "date": "2024-01-01",
      "count": 15
    }
  ],
  "activity": [
    {
      "date": "2024-01-01",
      "active_users": 450
    }
  ],
  "retention": {
    "day_1": 0.85,
    "day_7": 0.62,
    "day_30": 0.45
  }
}
```

## VPN Конфигурации

### GET /vpn/configs
Список VPN конфигураций.

### POST /vpn/configs/{user_id}/regenerate
Перегенерация конфигурации для пользователя.

### PUT /vpn/configs/{config_id}/status
Изменение статуса конфигурации.

## Промокоды

### GET /promos
Список промокодов.

### POST /promos
Создание промокода.

**Request:**
```json
{
  "code": "WINTER2024",
  "type": "discount",
  "discount_percent": 20,
  "discount_amount": null,
  "bonus_days": null,
  "usage_limit": 100,
  "expires_at": "2024-03-01T00:00:00Z"
}
```

### PUT /promos/{promo_id}
Обновление промокода.

### DELETE /promos/{promo_id}
Деактивация промокода.

## Системные настройки

### GET /settings
Получение системных настроек.

### PUT /settings
Обновление системных настроек.

**Request:**
```json
{
  "trial_days": 7,
  "max_trial_users": 10000,
  "referral_bonus_days": 7,
  "maintenance_mode": false,
  "min_referrals_for_bonus": 1
}
```

## Уведомления

### POST /notifications/broadcast
Массовая рассылка уведомлений.

**Request:**
```json
{
  "user_ids": [1, 2, 3],
  "title": "Системное обслуживание",
  "message": "Сегодня в 22:00 будет проведено техническое обслуживание",
  "channels": ["telegram", "email"]
}
```

## Webhooks

### POST /webhooks/yookassa
Webhook для обработки платежей YooKassa.

### POST /webhooks/wata
Webhook для обработки платежей Wata.

## Коды ошибок

- `200` - Успешно
- `201` - Создано
- `400` - Неверный запрос
- `401` - Не авторизован
- `403` - Доступ запрещен
- `404` - Не найдено
- `422` - Ошибка валидации
- `429` - Превышен лимит запросов
- `500` - Внутренняя ошибка сервера

## Rate Limiting

- **Общий лимит**: 1000 запросов в час
- **Аутентификация**: 5 попыток в минуту
- **Аналитика**: 100 запросов в минуту