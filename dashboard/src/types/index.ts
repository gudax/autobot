// User types
export interface User {
  id: number;
  email: string;
  broker_id: string;
  name?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Session types
export interface Session {
  session_id: number;
  user_id: number;
  trading_account_id?: string;
  login_at?: string;
  expires_at?: string;
  last_refresh_at?: string;
}

// Order types
export interface Order {
  id: number;
  user_id: number;
  account_id?: number;
  order_uuid?: string;
  symbol: string;
  side: string;
  order_type?: string;
  quantity?: number;
  entry_price?: number;
  stop_loss?: number;
  take_profit?: number;
  status: string;
  created_at: string;
  executed_at?: string;
  closed_at?: string;
}

// Trade types
export interface Trade {
  id: number;
  user_id: number;
  symbol: string;
  side: string;
  entry_price?: number;
  exit_price?: number;
  quantity?: number;
  profit_loss?: number;
  profit_loss_percent?: number;
  commission?: number;
  duration_seconds?: number;
  executed_at?: string;
  closed_at?: string;
}

// Dashboard types
export interface DashboardOverview {
  total_users: number;
  active_sessions: number;
  total_balance: number;
  total_equity: number;
  total_profit_loss: number;
  open_positions: number;
  total_trades_today: number;
  win_rate: number;
  average_profit: number;
}

export interface PerformanceMetrics {
  period: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_profit_loss: number;
  average_profit: number;
  average_loss: number;
  best_trade: number;
  worst_trade: number;
  average_duration_seconds: number;
}

// WebSocket message types
export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: string;
  error?: string;
}

export interface TradingSignal {
  action: 'OPEN_LONG' | 'OPEN_SHORT' | 'CLOSE' | 'CLOSE_ALL';
  symbol?: string;
  entry_price?: number;
  stop_loss?: number;
  take_profit?: number;
  volume?: number;
  strength?: number;
  volume_ratio?: number;
  orderbook_imbalance?: number;
  reason?: string;
}

// API Response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface LoginAllResponse {
  success: boolean;
  total_users: number;
  successful_logins: number;
  failed_logins: number;
  results: any[];
}

export interface ExecuteSignalResponse {
  success: boolean;
  executed_count: number;
  failed_count: number;
  total_volume?: number;
  execution_time_ms?: number;
  successful_orders: any[];
  failed_orders: any[];
  signal?: any;
  error?: string;
}
