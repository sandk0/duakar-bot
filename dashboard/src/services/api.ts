import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  errors?: string[];
}

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: process.env.REACT_APP_API_BASE_URL || '/api/v1',
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Generic API methods
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.api.get(url, config);
    return response.data;
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.api.post(url, data, config);
    return response.data;
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.api.put(url, data, config);
    return response.data;
  }

  async patch<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.api.patch(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.api.delete(url, config);
    return response.data;
  }

  // Authentication
  async login(username: string, password: string) {
    return this.post('/auth/login', { username, password });
  }

  async logout() {
    return this.post('/auth/logout');
  }

  // Dashboard stats
  async getDashboardStats() {
    return this.get('/admin/stats');
  }

  // Users
  async getUsers(params?: any) {
    return this.get('/admin/users', { params });
  }

  async getUserById(id: number) {
    return this.get(`/admin/users/${id}`);
  }

  async updateUser(id: number, data: any) {
    return this.put(`/admin/users/${id}`, data);
  }

  async blockUser(id: number, reason: string) {
    return this.post(`/admin/users/${id}/block`, { reason });
  }

  async unblockUser(id: number) {
    return this.post(`/admin/users/${id}/unblock`);
  }

  // Subscriptions
  async getSubscriptions(params?: any) {
    return this.get('/admin/subscriptions', { params });
  }

  async getSubscriptionById(id: number) {
    return this.get(`/admin/subscriptions/${id}`);
  }

  async updateSubscription(id: number, data: any) {
    return this.patch(`/admin/subscriptions/${id}`, data);
  }

  async cancelSubscription(id: number) {
    return this.delete(`/admin/subscriptions/${id}`);
  }

  async extendSubscription(id: number, days: number) {
    return this.post(`/admin/subscriptions/${id}/extend`, { days });
  }

  // Payments
  async getPayments(params?: any) {
    return this.get('/admin/payments', { params });
  }

  async getPaymentById(id: number) {
    return this.get(`/admin/payments/${id}`);
  }

  async refundPayment(id: number, data: any) {
    return this.post(`/admin/payments/${id}/refund`, data);
  }

  // Settings
  async getSettings() {
    return this.get('/admin/settings');
  }

  async updateSetting(data: any) {
    return this.post('/admin/settings', data);
  }

  async toggleTestingMode(testingMode: boolean) {
    return this.post('/admin/toggle-testing-mode', { testing_mode: testingMode });
  }

  // Broadcast
  async createBroadcast(data: any) {
    return this.post('/admin/broadcast', data);
  }

  async getBroadcasts() {
    return this.get('/admin/broadcasts');
  }

  async getBroadcastById(id: number) {
    return this.get(`/admin/broadcasts/${id}`);
  }
}

export default new ApiService();