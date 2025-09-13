#!/bin/bash

# VPN Bot Deployment Script
set -e

echo "🚀 Starting VPN Bot deployment..."

# Configuration
REPO_URL="https://github.com/your-username/telegram-vpn-bot.git"
APP_DIR="/opt/vpn-bot"
BACKUP_DIR="/opt/backups"
SERVICE_USER="vpnbot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
        exit 1
    fi
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    apt-get update
    apt-get install -y \
        docker.io \
        docker-compose \
        git \
        curl \
        wget \
        htop \
        nginx \
        certbot \
        python3-certbot-nginx \
        fail2ban \
        ufw
    
    systemctl enable docker
    systemctl start docker
    
    log "System dependencies installed"
}

# Create service user
create_user() {
    if ! id "$SERVICE_USER" &>/dev/null; then
        log "Creating service user: $SERVICE_USER"
        useradd -r -s /bin/bash -d $APP_DIR $SERVICE_USER
        usermod -aG docker $SERVICE_USER
    else
        log "Service user $SERVICE_USER already exists"
    fi
}

# Setup directories
setup_directories() {
    log "Setting up directories..."
    
    mkdir -p $APP_DIR
    mkdir -p $BACKUP_DIR
    mkdir -p /var/log/vpn-bot
    
    chown -R $SERVICE_USER:$SERVICE_USER $APP_DIR
    chown -R $SERVICE_USER:$SERVICE_USER $BACKUP_DIR
    chown -R $SERVICE_USER:$SERVICE_USER /var/log/vpn-bot
    
    log "Directories created"
}

# Clone or update repository
setup_code() {
    log "Setting up application code..."
    
    if [ -d "$APP_DIR/.git" ]; then
        log "Updating existing repository..."
        cd $APP_DIR
        sudo -u $SERVICE_USER git pull origin main
    else
        log "Cloning repository..."
        sudo -u $SERVICE_USER git clone $REPO_URL $APP_DIR
        cd $APP_DIR
    fi
    
    # Copy environment file if it doesn't exist
    if [ ! -f "$APP_DIR/.env" ]; then
        log "Creating .env file from template..."
        sudo -u $SERVICE_USER cp .env.example .env
        warning "Please edit $APP_DIR/.env with your configuration"
    fi
    
    log "Code setup completed"
}

# Setup firewall
setup_firewall() {
    log "Configuring firewall..."
    
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    
    # SSH
    ufw allow 22/tcp
    
    # HTTP/HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Application ports
    ufw allow 8000/tcp  # API
    ufw allow 3000/tcp  # Grafana
    ufw allow 9090/tcp  # Prometheus
    ufw allow 5555/tcp  # Flower
    
    ufw --force enable
    
    log "Firewall configured"
}

# Setup SSL certificate
setup_ssl() {
    local domain=$1
    
    if [ -z "$domain" ]; then
        warning "No domain provided, skipping SSL setup"
        return
    fi
    
    log "Setting up SSL certificate for $domain..."
    
    # Create Nginx config
    cat > /etc/nginx/sites-available/vpn-bot << EOF
server {
    listen 80;
    server_name $domain;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    
    ln -sf /etc/nginx/sites-available/vpn-bot /etc/nginx/sites-enabled/
    nginx -t && systemctl reload nginx
    
    # Get SSL certificate
    certbot --nginx -d $domain --non-interactive --agree-tos --email admin@$domain
    
    log "SSL certificate configured"
}

# Setup systemd services
setup_services() {
    log "Setting up systemd services..."
    
    # VPN Bot service
    cat > /etc/systemd/system/vpn-bot.service << EOF
[Unit]
Description=VPN Bot Services
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=true
WorkingDirectory=$APP_DIR
User=$SERVICE_USER
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable vpn-bot.service
    
    log "Systemd services configured"
}

# Setup log rotation
setup_logrotate() {
    log "Setting up log rotation..."
    
    cat > /etc/logrotate.d/vpn-bot << EOF
/var/log/vpn-bot/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 $SERVICE_USER $SERVICE_USER
    postrotate
        /usr/bin/docker-compose -f $APP_DIR/docker-compose.yml restart > /dev/null 2>&1 || true
    endscript
}
EOF
    
    log "Log rotation configured"
}

# Setup backup cron job
setup_backup() {
    log "Setting up backup cron job..."
    
    cat > /etc/cron.d/vpn-bot-backup << EOF
# VPN Bot backup - daily at 2 AM
0 2 * * * $SERVICE_USER cd $APP_DIR && make backup > /var/log/vpn-bot/backup.log 2>&1
EOF
    
    log "Backup cron job configured"
}

# Build and start application
deploy_app() {
    log "Building and starting application..."
    
    cd $APP_DIR
    sudo -u $SERVICE_USER docker-compose build
    sudo -u $SERVICE_USER docker-compose up -d
    
    # Wait for services to start
    sleep 10
    
    # Run database setup
    sudo -u $SERVICE_USER docker-compose exec -T bot python scripts/setup_database.py
    
    log "Application deployed and started"
}

# Health check
health_check() {
    log "Performing health check..."
    
    cd $APP_DIR
    
    # Check if containers are running
    if ! sudo -u $SERVICE_USER docker-compose ps | grep -q "Up"; then
        error "Some containers are not running"
        sudo -u $SERVICE_USER docker-compose ps
        exit 1
    fi
    
    # Check API endpoint
    sleep 5
    if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
        warning "API health check failed"
    fi
    
    log "Health check completed"
}

# Main deployment function
main() {
    local domain=""
    local skip_deps=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --domain)
                domain="$2"
                shift 2
                ;;
            --skip-deps)
                skip_deps=true
                shift
                ;;
            *)
                echo "Unknown option $1"
                exit 1
                ;;
        esac
    done
    
    check_root
    
    if [ "$skip_deps" != true ]; then
        install_dependencies
    fi
    
    create_user
    setup_directories
    setup_code
    setup_firewall
    
    if [ -n "$domain" ]; then
        setup_ssl "$domain"
    fi
    
    setup_services
    setup_logrotate
    setup_backup
    deploy_app
    health_check
    
    log "🎉 Deployment completed successfully!"
    log ""
    log "Next steps:"
    log "1. Edit $APP_DIR/.env with your configuration"
    log "2. Create admin user: cd $APP_DIR && sudo -u $SERVICE_USER docker-compose exec bot python scripts/init_admin.py <your_telegram_id>"
    log "3. Access services:"
    log "   - API: http://localhost:8000/docs"
    log "   - Grafana: http://localhost:3000 (admin/admin)"
    log "   - Flower: http://localhost:5555"
    log "   - Prometheus: http://localhost:9090"
    log ""
    log "Logs: tail -f /var/log/vpn-bot/*.log"
    log "Control: systemctl {start|stop|restart} vpn-bot"
}

# Show usage if no arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 [--domain example.com] [--skip-deps]"
    echo ""
    echo "Options:"
    echo "  --domain     Domain name for SSL certificate"
    echo "  --skip-deps  Skip system dependencies installation"
    echo ""
    echo "Example:"
    echo "  $0 --domain vpn.example.com"
    exit 1
fi

main "$@"