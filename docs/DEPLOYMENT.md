# Deployment Guide

## Системные требования

### Минимальные требования
- **CPU**: 2 ядра
- **RAM**: 4 GB
- **Дисковое пространство**: 20 GB SSD
- **ОС**: Ubuntu 20.04 LTS или новее
- **Docker**: 20.10+ и Docker Compose 2.0+

### Рекомендуемые требования (Production)
- **CPU**: 4 ядра
- **RAM**: 8 GB
- **Дисковое пространство**: 100 GB SSD
- **Сеть**: 100 Mbps

## Предварительная подготовка

### 1. Установка Docker и Docker Compose
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Перезагрузка для применения изменений
sudo reboot
```

### 2. Клонирование репозитория
```bash
git clone https://github.com/your-username/vpn-telegram-bot.git
cd vpn-telegram-bot
```

### 3. Настройка окружения
```bash
# Копирование файла конфигурации
cp .env.example .env

# Редактирование конфигурации
nano .env
```

## Конфигурация .env файла

### Обязательные параметры
```env
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token_from_botfather
BOT_USERNAME=your_bot_username
ADMIN_USER_IDS=123456789,987654321

# Database
DATABASE_URL=postgresql+asyncpg://vpn_user:secure_password@postgres:5432/vpn_bot

# Redis
REDIS_URL=redis://redis:6379/0

# Marzban VPN
MARZBAN_BASE_URL=http://your_marzban_server:8080
MARZBAN_USERNAME=admin
MARZBAN_PASSWORD=secure_marzban_password

# Payment Systems
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key

# Security
JWT_SECRET_KEY=your_very_long_random_secret_key_change_this_in_production
WEBHOOK_SECRET=your_webhook_secret_key

# Production settings
DEBUG=False
LOG_LEVEL=WARNING
TESTING_MODE=false
```

### Генерация секретных ключей
```bash
# Генерация JWT ключа
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))"

# Генерация webhook secret
python3 -c "import secrets; print('WEBHOOK_SECRET=' + secrets.token_urlsafe(32))"
```

## Развертывание

### 1. Сборка и запуск контейнеров
```bash
# Сборка образов
docker-compose build

# Запуск в фоновом режиме
docker-compose up -d

# Проверка статуса контейнеров
docker-compose ps
```

### 2. Инициализация базы данных
```bash
# Ожидание запуска PostgreSQL
sleep 30

# Применение миграций
docker-compose exec api alembic upgrade head

# Создание начальных данных
docker-compose exec api python -m scripts.init_data
```

### 3. Проверка работоспособности
```bash
# Проверка логов бота
docker-compose logs bot

# Проверка логов API
docker-compose logs api

# Проверка доступности API
curl http://localhost:8000/health

# Проверка доступности Grafana
curl http://localhost:3000/api/health
```

## SSL/TLS сертификаты

### Использование Certbot для Let's Encrypt
```bash
# Установка Certbot
sudo apt install certbot

# Получение сертификата
sudo certbot certonly --standalone -d your-domain.com -d api.your-domain.com

# Настройка автообновления
sudo crontab -e
# Добавить: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Nginx конфигурация
```nginx
# /etc/nginx/sites-available/vpn-bot
server {
    listen 80;
    server_name your-domain.com api.your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Production настройки Docker Compose

### docker-compose.prod.yml
```yaml
version: '3.9'

services:
  postgres:
    restart: always
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    environment:
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=${DB_NAME}

  redis:
    restart: always
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data

  bot:
    restart: always
    environment:
      - DEBUG=False
      - LOG_LEVEL=WARNING
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  api:
    restart: always
    environment:
      - DEBUG=False
      - LOG_LEVEL=WARNING
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  celery_worker:
    restart: always
    deploy:
      replicas: 2

  prometheus:
    restart: always
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

  grafana:
    restart: always
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_SECURITY_SECRET_KEY=${GRAFANA_SECRET_KEY}
      - GF_USERS_ALLOW_SIGN_UP=false
```

### Запуск в production режиме
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Мониторинг и логирование

### Настройка централизованного логирования
```bash
# Установка ELK Stack (опционально)
docker run -d --name elasticsearch \
  -p 9200:9200 -p 9300:9300 \
  -e "discovery.type=single-node" \
  elasticsearch:7.14.0

docker run -d --name kibana \
  -p 5601:5601 \
  --link elasticsearch:elasticsearch \
  kibana:7.14.0
```

### Настройка alerting в Prometheus
```yaml
# monitoring/alerts.yml
groups:
  - name: vpn_bot_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"

      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL is down"
```

## Backup и восстановление

### Настройка автоматического backup
```bash
#!/bin/bash
# scripts/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# Database backup
docker-compose exec -T postgres pg_dump -U ${DB_USER} -d ${DB_NAME} > ${BACKUP_DIR}/db_backup_${DATE}.sql

# Redis backup
docker-compose exec -T redis redis-cli BGSAVE
docker cp vpn_bot_redis:/data/dump.rdb ${BACKUP_DIR}/redis_backup_${DATE}.rdb

# Cleanup old backups (keep 30 days)
find ${BACKUP_DIR} -name "*.sql" -mtime +30 -delete
find ${BACKUP_DIR} -name "*.rdb" -mtime +30 -delete

echo "Backup completed: ${DATE}"
```

### Cron задача для backup
```bash
# Добавить в crontab
0 2 * * * /path/to/vpn-telegram-bot/scripts/backup.sh >> /var/log/backup.log 2>&1
```

## Обновление системы

### 1. Backup данных
```bash
./scripts/backup.sh
```

### 2. Получение обновлений
```bash
git pull origin main
```

### 3. Применение обновлений
```bash
# Пересборка образов
docker-compose build --no-cache

# Применение миграций
docker-compose exec api alembic upgrade head

# Перезапуск сервисов
docker-compose restart
```

### 4. Проверка работоспособности
```bash
# Проверка логов на ошибки
docker-compose logs --tail=50 bot
docker-compose logs --tail=50 api

# Проверка здоровья сервисов
curl http://localhost:8000/health
```

## Масштабирование

### Горизонтальное масштабирование
```yaml
# docker-compose.scale.yml
services:
  celery_worker:
    deploy:
      replicas: 4

  api:
    deploy:
      replicas: 3
```

### Load Balancer с Nginx
```nginx
upstream api_backend {
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
}

server {
    location / {
        proxy_pass http://api_backend;
    }
}
```

## Безопасность

### Firewall настройки
```bash
# UFW настройки
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Fail2Ban для защиты от брутфорса
```bash
# Установка Fail2Ban
sudo apt install fail2ban

# Конфигурация
sudo nano /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
```

## Troubleshooting

### Общие проблемы и решения

#### 1. Контейнер не запускается
```bash
# Проверка логов
docker-compose logs container_name

# Проверка ресурсов
docker stats

# Очистка системы
docker system prune -a
```

#### 2. Проблемы с базой данных
```bash
# Проверка подключения
docker-compose exec postgres psql -U vpn_user -d vpn_bot -c "SELECT 1;"

# Проверка миграций
docker-compose exec api alembic current
docker-compose exec api alembic history
```

#### 3. Проблемы с памятью
```bash
# Увеличение swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Логи и диагностика
```bash
# Реальное время логов
docker-compose logs -f bot

# Логи всех сервисов
docker-compose logs --tail=100

# Статистика контейнеров
docker-compose top

# Использование ресурсов
docker-compose exec api python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"
```