import axios, { AxiosInstance } from 'axios';
import type {
  User,
  Session,
  Order,
  Trade,
  DashboardOverview,
  PerformanceMetrics,
  TradingSignal,
  LoginAllResponse,
  ExecuteSignalResponse,
} from '@/types';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add any auth tokens here if needed
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // ========== USER ENDPOINTS ==========

  async getUsers(): Promise<User[]> {
    const response = await this.client.get('/api/v1/users/');
    return response.data;
  }

  async getUser(userId: number): Promise<User> {
    const response = await this.client.get(`/api/v1/users/${userId}`);
    return response.data;
  }

  async createUser(userData: {
    email: string;
    password: string;
    broker_id: string;
    name?: string;
  }): Promise<User> {
    const response = await this.client.post('/api/v1/users/', userData);
    return response.data;
  }

  async updateUser(
    userId: number,
    userData: Partial<User>
  ): Promise<User> {
    const response = await this.client.put(`/api/v1/users/${userId}`, userData);
    return response.data;
  }

  async deleteUser(userId: number): Promise<void> {
    await this.client.delete(`/api/v1/users/${userId}`);
  }

  async loginUser(userId: number): Promise<any> {
    const response = await this.client.post(`/api/v1/users/${userId}/login`);
    return response.data;
  }

  async logoutUser(userId: number): Promise<void> {
    await this.client.post(`/api/v1/users/${userId}/logout`);
  }

  async loginAllUsers(): Promise<LoginAllResponse> {
    const response = await this.client.post('/api/v1/users/login-all');
    return response.data;
  }

  // ========== SESSION ENDPOINTS ==========

  async getSessions(): Promise<{ total: number; sessions: Session[] }> {
    const response = await this.client.get('/api/v1/sessions/');
    return response.data;
  }

  async getSession(sessionId: number): Promise<Session> {
    const response = await this.client.get(`/api/v1/sessions/${sessionId}`);
    return response.data;
  }

  async refreshAllTokens(): Promise<any> {
    const response = await this.client.post('/api/v1/sessions/refresh-all');
    return response.data;
  }

  async closeSession(sessionId: number): Promise<void> {
    await this.client.delete(`/api/v1/sessions/${sessionId}`);
  }

  async checkSessionHealth(): Promise<any> {
    const response = await this.client.get('/api/v1/sessions/health/check');
    return response.data;
  }

  // ========== TRADING ENDPOINTS ==========

  async executeTradingSignal(signal: TradingSignal): Promise<ExecuteSignalResponse> {
    const response = await this.client.post('/api/v1/trading/signal', signal);
    return response.data;
  }

  async getPositions(
    skip = 0,
    limit = 100
  ): Promise<{ total: number; positions: Order[] }> {
    const response = await this.client.get('/api/v1/trading/positions', {
      params: { skip, limit },
    });
    return response.data;
  }

  async getUserPositions(
    userId: number,
    statusFilter = 'OPEN',
    skip = 0,
    limit = 100
  ): Promise<{ total: number; positions: Order[] }> {
    const response = await this.client.get(`/api/v1/trading/positions/user/${userId}`, {
      params: { status_filter: statusFilter, skip, limit },
    });
    return response.data;
  }

  async closeAllPositions(symbol?: string): Promise<any> {
    const response = await this.client.post('/api/v1/trading/close-all', {
      symbol,
    });
    return response.data;
  }

  async getOrders(
    statusFilter?: string,
    symbol?: string,
    skip = 0,
    limit = 100
  ): Promise<Order[]> {
    const response = await this.client.get('/api/v1/trading/orders', {
      params: { status_filter: statusFilter, symbol, skip, limit },
    });
    return response.data;
  }

  async getTrades(
    userId?: number,
    symbol?: string,
    skip = 0,
    limit = 100
  ): Promise<Trade[]> {
    const response = await this.client.get('/api/v1/trading/trades', {
      params: { user_id: userId, symbol, skip, limit },
    });
    return response.data;
  }

  async getTodayTrades(): Promise<Trade[]> {
    const response = await this.client.get('/api/v1/trading/trades/today');
    return response.data;
  }

  // ========== DASHBOARD ENDPOINTS ==========

  async getDashboardOverview(): Promise<DashboardOverview> {
    const response = await this.client.get('/api/v1/dashboard/overview');
    return response.data;
  }

  async getPerformanceMetrics(period = '30d'): Promise<PerformanceMetrics> {
    const response = await this.client.get('/api/v1/dashboard/performance', {
      params: { period },
    });
    return response.data;
  }

  async getUsersDashboard(): Promise<any> {
    const response = await this.client.get('/api/v1/dashboard/users');
    return response.data;
  }
}

// Export singleton instance
export const api = new ApiClient();
