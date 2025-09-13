import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert
} from '@mui/material';
import {
  People as PeopleIcon,
  Payment as PaymentIcon,
  Security as SecurityIcon,
  TrendingUp as TrendingUpIcon
} from '@mui/icons-material';
import apiService from '../services/api';

interface DashboardStats {
  users: {
    total_users: number;
    active_users: number;
    new_users_today: number;
  };
  subscriptions: {
    total_subscriptions: number;
    active_subscriptions: number;
  };
  payments: {
    total_revenue: number;
    revenue_today: number;
    successful_payments: number;
  };
  system: {
    database_size_mb: number;
  };
}

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
  subtitle?: string;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color, subtitle }) => {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Box
            sx={{
              backgroundColor: color,
              borderRadius: '50%',
              padding: 1,
              marginRight: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            {icon}
          </Box>
          <Typography variant="h6" component="div">
            {title}
          </Typography>
        </Box>
        <Typography variant="h4" component="div" sx={{ mb: 1 }}>
          {typeof value === 'number' ? value.toLocaleString() : value}
        </Typography>
        {subtitle && (
          <Typography variant="body2" color="text.secondary">
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      const response = await apiService.getDashboardStats();
      setStats(response.data);
      setError(null);
    } catch (err) {
      setError('Не удалось загрузить статистику');
      console.error('Error loading stats:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!stats) {
    return (
      <Alert severity="warning" sx={{ mb: 2 }}>
        Нет данных для отображения
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Dashboard
      </Typography>

      <Grid container spacing={3}>
        {/* Users Stats */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Всего пользователей"
            value={stats.users.total_users}
            icon={<PeopleIcon sx={{ color: 'white' }} />}
            color="#1976d2"
            subtitle={`Активных: ${stats.users.active_users}`}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Новые сегодня"
            value={stats.users.new_users_today}
            icon={<TrendingUpIcon sx={{ color: 'white' }} />}
            color="#2e7d32"
            subtitle="За сегодня"
          />
        </Grid>

        {/* Subscriptions */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Подписки"
            value={stats.subscriptions.active_subscriptions}
            icon={<SecurityIcon sx={{ color: 'white' }} />}
            color="#ed6c02"
            subtitle={`Всего: ${stats.subscriptions.total_subscriptions}`}
          />
        </Grid>

        {/* Revenue */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Выручка сегодня"
            value={`${stats.payments.revenue_today.toLocaleString()} ₽`}
            icon={<PaymentIcon sx={{ color: 'white' }} />}
            color="#9c27b0"
            subtitle={`Всего: ${stats.payments.total_revenue.toLocaleString()} ₽`}
          />
        </Grid>
      </Grid>

      {/* Additional metrics */}
      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Платежи
              </Typography>
              <Typography variant="body1">
                Успешных платежей: {stats.payments.successful_payments}
              </Typography>
              <Typography variant="body1">
                Общая выручка: {stats.payments.total_revenue.toLocaleString()} ₽
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Система
              </Typography>
              <Typography variant="body1">
                Размер БД: {stats.system.database_size_mb.toFixed(2)} MB
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;