import React, { useState, useEffect } from 'react';
import { Card, Button, LoadingSpinner, Badge } from '../components/common';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../services/api';
import type { DashboardOverview, Trade } from '../types';

export const DashboardPage: React.FC = () => {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [todayTrades, setTodayTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [loginAllLoading, setLoginAllLoading] = useState(false);

  const { isConnected } = useWebSocket('dashboard', {
    onMessage: (message) => {
      if (message.type === 'dashboard_update') {
        setOverview(message.data);
      }
    },
  });

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [overviewData, tradesData] = await Promise.all([
        api.getDashboardOverview(),
        api.getTodayTrades(),
      ]);
      setOverview(overviewData);
      setTodayTrades(tradesData);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleLoginAll = async () => {
    try {
      setLoginAllLoading(true);
      const result = await api.loginAllUsers();
      alert(
        `Login completed: ${result.successful_logins}/${result.total_users} successful`
      );
      await fetchDashboardData();
    } catch (error) {
      console.error('Failed to login all users:', error);
      alert('Failed to login all users');
    } finally {
      setLoginAllLoading(false);
    }
  };

  const handleRefreshTokens = async () => {
    try {
      await api.refreshAllTokens();
      alert('All tokens refreshed successfully');
    } catch (error) {
      console.error('Failed to refresh tokens:', error);
      alert('Failed to refresh tokens');
    }
  };

  const handleCheckHealth = async () => {
    try {
      const result = await api.checkSessionHealth();
      alert(`Health check: ${result.healthy_sessions}/${result.total_sessions} healthy`);
    } catch (error) {
      console.error('Failed to check health:', error);
      alert('Failed to check health');
    }
  };

  if (loading) {
    return <LoadingSpinner size="lg" text="Loading dashboard..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Real-time overview of your trading operations
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={isConnected ? 'success' : 'danger'}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </Badge>
        </div>
      </div>

      {/* Quick Actions */}
      <Card title="Quick Actions">
        <div className="flex flex-wrap gap-3">
          <Button
            variant="primary"
            onClick={handleLoginAll}
            loading={loginAllLoading}
          >
            Login All Users
          </Button>
          <Button variant="secondary" onClick={handleRefreshTokens}>
            Refresh All Tokens
          </Button>
          <Button variant="secondary" onClick={handleCheckHealth}>
            Check Session Health
          </Button>
          <Button variant="secondary" onClick={fetchDashboardData}>
            Refresh Dashboard
          </Button>
        </div>
      </Card>

      {/* Overview Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Users"
          value={overview?.total_users || 0}
          icon="👥"
          color="blue"
        />
        <StatCard
          title="Active Sessions"
          value={overview?.active_sessions || 0}
          icon="🔌"
          color="green"
        />
        <StatCard
          title="Open Positions"
          value={overview?.open_positions || 0}
          icon="📊"
          color="purple"
        />
        <StatCard
          title="Trades Today"
          value={overview?.total_trades_today || 0}
          icon="📈"
          color="indigo"
        />
      </div>

      {/* Financial Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Balance"
          value={`$${(overview?.total_balance || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
          icon="💰"
          color="green"
        />
        <StatCard
          title="Total Equity"
          value={`$${(overview?.total_equity || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
          icon="💎"
          color="blue"
        />
        <StatCard
          title="Total P&L"
          value={`$${(overview?.total_profit_loss || 0).toLocaleString(undefined, { maximumFractionDigits: 2, signDisplay: 'always' })}`}
          icon={overview && overview.total_profit_loss >= 0 ? '📈' : '📉'}
          color={overview && overview.total_profit_loss >= 0 ? 'green' : 'red'}
        />
        <StatCard
          title="Win Rate"
          value={`${((overview?.win_rate || 0) * 100).toFixed(1)}%`}
          icon="🎯"
          color="purple"
        />
      </div>

      {/* Recent Trades */}
      <Card title="Today's Trades" actions={
        <span className="text-sm text-gray-600">
          {todayTrades.length} trades
        </span>
      }>
        {todayTrades.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No trades today</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Time
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Symbol
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Side
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Quantity
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    P&L
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {todayTrades.slice(0, 10).map((trade) => (
                  <tr key={trade.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {trade.executed_at
                        ? new Date(trade.executed_at).toLocaleTimeString()
                        : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {trade.symbol}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <Badge variant={trade.side === 'BUY' ? 'success' : 'danger'}>
                        {trade.side}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {trade.quantity?.toFixed(2) || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span
                        className={
                          (trade.profit_loss || 0) >= 0
                            ? 'text-green-600 font-medium'
                            : 'text-red-600 font-medium'
                        }
                      >
                        ${(trade.profit_loss || 0).toFixed(2)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};

interface StatCardProps {
  title: string;
  value: string | number;
  icon: string;
  color: 'blue' | 'green' | 'purple' | 'indigo' | 'red';
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color }) => {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    indigo: 'bg-indigo-50 text-indigo-600',
    red: 'bg-red-50 text-red-600',
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-2">{value}</p>
        </div>
        <div className={`w-12 h-12 rounded-lg ${colorClasses[color]} flex items-center justify-center text-2xl`}>
          {icon}
        </div>
      </div>
    </div>
  );
};
