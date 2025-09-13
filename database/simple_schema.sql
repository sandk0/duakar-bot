-- Simple schema for VPN Bot
-- This can be executed directly in PostgreSQL

-- Create users table
CREATE TABLE IF NOT EXISTS users (
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

-- Create pricing plans table
CREATE TABLE IF NOT EXISTS pricing_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'RUB',
    duration_days INTEGER NOT NULL,
    plan_type VARCHAR(20) DEFAULT 'regular',
    is_active BOOLEAN DEFAULT TRUE,
    features TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id INTEGER NOT NULL REFERENCES pricing_plans(id),
    status VARCHAR(20) DEFAULT 'pending',
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    auto_renew BOOLEAN DEFAULT FALSE,
    payment_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create payments table  
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    plan_id INTEGER REFERENCES pricing_plans(id),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'RUB',
    status VARCHAR(20) DEFAULT 'pending',
    system VARCHAR(20) NOT NULL,
    external_id VARCHAR(255),
    payment_url TEXT,
    payment_metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Create VPN configs table
CREATE TABLE IF NOT EXISTS vpn_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    marzban_user_id VARCHAR(255),
    config_data TEXT,
    qr_code_data TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_end_date ON subscriptions(end_date);
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_external_id ON payments(external_id);
CREATE INDEX IF NOT EXISTS idx_vpn_configs_user_id ON vpn_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_vpn_configs_marzban_user_id ON vpn_configs(marzban_user_id);

-- Insert default pricing plans
INSERT INTO pricing_plans (name, description, price, duration_days, plan_type) VALUES
('Месячная подписка', 'Доступ к VPN на 1 месяц', 200.00, 30, 'regular'),
('Квартальная подписка', 'Доступ к VPN на 3 месяца', 500.00, 90, 'regular'),
('Годовая подписка', 'Доступ к VPN на 12 месяцев', 2000.00, 365, 'regular'),
('Пробный период', 'Бесплатный доступ на 7 дней', 0.00, 7, 'trial')
ON CONFLICT DO NOTHING;

-- Create alembic version table for compatibility
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Insert initial version
INSERT INTO alembic_version (version_num) VALUES ('001_initial_migration') ON CONFLICT DO NOTHING;