/**
 * Utility functions for formatting data
 */

/**
 * Format number as currency
 */
export const formatCurrency = (amount: number, currency: string = 'RUB'): string => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
};

/**
 * Format bytes to human readable format
 */
export const formatBytes = (bytes: number, decimals: number = 2): string => {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

/**
 * Format date to locale string
 */
export const formatDate = (date: string | Date): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return dateObj.toLocaleDateString('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
};

/**
 * Format datetime to locale string
 */
export const formatDateTime = (date: string | Date): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return dateObj.toLocaleDateString('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

/**
 * Format relative time (e.g., "2 hours ago")
 */
export const formatRelativeTime = (date: string | Date): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffInMs = now.getTime() - dateObj.getTime();
  const diffInMinutes = Math.floor(diffInMs / (1000 * 60));
  const diffInHours = Math.floor(diffInMinutes / 60);
  const diffInDays = Math.floor(diffInHours / 24);

  if (diffInMinutes < 1) {
    return 'только что';
  } else if (diffInMinutes < 60) {
    return `${diffInMinutes} мин. назад`;
  } else if (diffInHours < 24) {
    return `${diffInHours} ч. назад`;
  } else if (diffInDays < 7) {
    return `${diffInDays} дн. назад`;
  } else {
    return formatDate(dateObj);
  }
};

/**
 * Format subscription status
 */
export const formatSubscriptionStatus = (status: string): string => {
  const statusMap: Record<string, string> = {
    'active': 'Активна',
    'expired': 'Истекла',
    'cancelled': 'Отменена',
    'suspended': 'Приостановлена',
    'pending': 'В ожидании',
  };
  
  return statusMap[status] || status;
};

/**
 * Format payment status
 */
export const formatPaymentStatus = (status: string): string => {
  const statusMap: Record<string, string> = {
    'pending': 'В ожидании',
    'processing': 'Обработка',
    'completed': 'Завершен',
    'failed': 'Ошибка',
    'cancelled': 'Отменен',
    'refunded': 'Возвращен',
  };
  
  return statusMap[status] || status;
};

/**
 * Get status color for MUI components
 */
export const getStatusColor = (status: string): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
  const colorMap: Record<string, 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'> = {
    'active': 'success',
    'completed': 'success',
    'expired': 'warning',
    'failed': 'error',
    'cancelled': 'error',
    'suspended': 'warning',
    'pending': 'info',
    'processing': 'info',
    'refunded': 'warning',
  };
  
  return colorMap[status] || 'default';
};

/**
 * Format telegram ID with @
 */
export const formatTelegramId = (telegramId: number): string => {
  return `@${telegramId}`;
};

/**
 * Truncate text to specified length
 */
export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

/**
 * Format percentage
 */
export const formatPercentage = (value: number, decimals: number = 1): string => {
  return `${value.toFixed(decimals)}%`;
};

/**
 * Format number with locale
 */
export const formatNumber = (value: number): string => {
  return new Intl.NumberFormat('ru-RU').format(value);
};

/**
 * Format plan type
 */
export const formatPlanType = (planType: string): string => {
  const planMap: Record<string, string> = {
    'trial': 'Пробный',
    'monthly': 'Месячный',
    'quarterly': 'Квартальный',
    'yearly': 'Годовой',
    'lifetime': 'Пожизненный',
  };
  
  return planMap[planType] || planType;
};

/**
 * Calculate days remaining
 */
export const calculateDaysRemaining = (endDate: string | Date): number => {
  const end = typeof endDate === 'string' ? new Date(endDate) : endDate;
  const now = new Date();
  const diffInMs = end.getTime() - now.getTime();
  const diffInDays = Math.ceil(diffInMs / (1000 * 60 * 60 * 24));
  
  return Math.max(0, diffInDays);
};

/**
 * Format days remaining text
 */
export const formatDaysRemaining = (endDate: string | Date): string => {
  const daysLeft = calculateDaysRemaining(endDate);
  
  if (daysLeft === 0) {
    return 'Истекает сегодня';
  } else if (daysLeft === 1) {
    return 'Остался 1 день';
  } else if (daysLeft < 5) {
    return `Осталось ${daysLeft} дня`;
  } else {
    return `Осталось ${daysLeft} дней`;
  }
};