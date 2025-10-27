import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, Button, LoadingSpinner } from '../components/common';
import { api } from '../services/api';
import type { PerformanceMetrics, Trade } from '../types';

export const PerformancePage: React.FC = () => {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [period, setPeriod] = useState<'7d' | '30d' | '90d' | 'all'>('30d');
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [metricsData, tradesData] = await Promise.all([
        api.getPerformanceMetrics(period),
        api.getTrades(undefined, undefined, 0, 1000),
      ]);
      setMetrics(metricsData);
      setTrades(tradesData);
    } catch (error) {
      console.error('Failed to fetch performance data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [period]);

  if (loading) {
    return <LoadingSpinner size="lg" text="Loading performance data..." />;
  }

  if (!metrics) {
    return <div>No performance data available</div>;
  }

  // Prepare chart data - P&L over time
  const pnlData = trades
    .sort((a, b) => new Date(a.closed_at || 0).getTime() - new Date(b.closed_at || 0).getTime())
    .reduce((acc, trade, index) => {
      const prevTotal = index > 0 ? acc[index - 1].cumulative : 0;
      const cumulative = prevTotal + (trade.profit_loss || 0);
      acc.push({
        date: trade.closed_at
          ? new Date(trade.closed_at).toLocaleDateString()
          : '',
        pnl: trade.profit_loss || 0,
        cumulative,
      });
      return acc;
    }, [] as any[]);

  // Win/Loss distribution
  const winLossData = [
    { name: 'Winning', value: metrics.winning_trades, color: '#10b981' },
    { name: 'Losing', value: metrics.losing_trades, color: '#ef4444' },
  ];

  // Best and worst trades
  const sortedByPnL = [...trades].sort(
    (a, b) => (b.profit_loss || 0) - (a.profit_loss || 0)
  );
  const bestTrades = sortedByPnL.slice(0, 5);
  const worstTrades = sortedByPnL.slice(-5).reverse();

  // Symbol performance
  const symbolStats = trades.reduce((acc, trade) => {
    if (!acc[trade.symbol]) {
      acc[trade.symbol] = { symbol: trade.symbol, pnl: 0, count: 0 };
    }
    acc[trade.symbol].pnl += trade.profit_loss || 0;
    acc[trade.symbol].count += 1;
    return acc;
  }, {} as Record<string, { symbol: string; pnl: number; count: number }>);

  const symbolPerformance = Object.values(symbolStats)
    .sort((a, b) => b.pnl - a.pnl)
    .slice(0, 10);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Performance Analytics
          </h1>
          <p className="text-gray-600 mt-1">
            Analyze trading performance and metrics
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant={period === '7d' ? 'primary' : 'secondary'}
            onClick={() => setPeriod('7d')}
          >
            7 Days
          </Button>
          <Button
            size="sm"
            variant={period === '30d' ? 'primary' : 'secondary'}
            onClick={() => setPeriod('30d')}
          >
            30 Days
          </Button>
          <Button
            size="sm"
            variant={period === '90d' ? 'primary' : 'secondary'}
            onClick={() => setPeriod('90d')}
          >
            90 Days
          </Button>
          <Button
            size="sm"
            variant={period === 'all' ? 'primary' : 'secondary'}
            onClick={() => setPeriod('all')}
          >
            All Time
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Trades"
          value={metrics.total_trades}
          icon="📊"
          color="blue"
        />
        <StatCard
          title="Win Rate"
          value={`${(metrics.win_rate * 100).toFixed(1)}%`}
          icon="🎯"
          color="green"
        />
        <StatCard
          title="Total P&L"
          value={`$${metrics.total_profit_loss.toFixed(2)}`}
          icon={metrics.total_profit_loss >= 0 ? '📈' : '📉'}
          color={metrics.total_profit_loss >= 0 ? 'green' : 'red'}
        />
        <StatCard
          title="Avg Duration"
          value={`${Math.floor(metrics.average_duration_seconds / 60)}m`}
          icon="⏱️"
          color="purple"
        />
      </div>

      {/* Profit & Loss Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Avg Profit"
          value={`$${metrics.average_profit.toFixed(2)}`}
          icon="💰"
          color="green"
        />
        <StatCard
          title="Avg Loss"
          value={`$${metrics.average_loss.toFixed(2)}`}
          icon="💸"
          color="red"
        />
        <StatCard
          title="Best Trade"
          value={`$${metrics.best_trade.toFixed(2)}`}
          icon="🏆"
          color="green"
        />
        <StatCard
          title="Worst Trade"
          value={`$${metrics.worst_trade.toFixed(2)}`}
          icon="⚠️"
          color="red"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cumulative P&L Chart */}
        <Card title="Cumulative P&L Over Time">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={pnlData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="cumulative"
                stroke="#3b82f6"
                strokeWidth={2}
                name="Cumulative P&L"
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        {/* Win/Loss Distribution */}
        <Card title="Win/Loss Distribution">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={winLossData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value, percent }) =>
                  `${name}: ${value} (${(percent * 100).toFixed(0)}%)`
                }
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {winLossData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Symbol Performance Chart */}
      <Card title="Top 10 Symbols by P&L">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={symbolPerformance}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="symbol" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="pnl" fill="#3b82f6" name="P&L ($)" />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* Best & Worst Trades */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Best Trades */}
        <Card title="Top 5 Best Trades">
          <div className="space-y-3">
            {bestTrades.map((trade, index) => (
              <div
                key={trade.id}
                className="flex justify-between items-center p-3 bg-green-50 rounded-lg"
              >
                <div>
                  <div className="font-medium text-gray-900">
                    #{index + 1} - {trade.symbol}
                  </div>
                  <div className="text-sm text-gray-600">
                    {trade.side} | Qty: {trade.quantity?.toFixed(4)}
                  </div>
                  <div className="text-xs text-gray-500">
                    {trade.closed_at
                      ? new Date(trade.closed_at).toLocaleDateString()
                      : '-'}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold text-green-600">
                    ${(trade.profit_loss || 0).toFixed(2)}
                  </div>
                  <div className="text-sm text-green-600">
                    {(trade.profit_loss_percent || 0).toFixed(2)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Worst Trades */}
        <Card title="Top 5 Worst Trades">
          <div className="space-y-3">
            {worstTrades.map((trade, index) => (
              <div
                key={trade.id}
                className="flex justify-between items-center p-3 bg-red-50 rounded-lg"
              >
                <div>
                  <div className="font-medium text-gray-900">
                    #{index + 1} - {trade.symbol}
                  </div>
                  <div className="text-sm text-gray-600">
                    {trade.side} | Qty: {trade.quantity?.toFixed(4)}
                  </div>
                  <div className="text-xs text-gray-500">
                    {trade.closed_at
                      ? new Date(trade.closed_at).toLocaleDateString()
                      : '-'}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold text-red-600">
                    ${(trade.profit_loss || 0).toFixed(2)}
                  </div>
                  <div className="text-sm text-red-600">
                    {(trade.profit_loss_percent || 0).toFixed(2)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};

interface StatCardProps {
  title: string;
  value: string | number;
  icon: string;
  color: 'blue' | 'green' | 'purple' | 'red';
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color }) => {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    red: 'bg-red-50 text-red-600',
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-2">{value}</p>
        </div>
        <div
          className={`w-12 h-12 rounded-lg ${colorClasses[color]} flex items-center justify-center text-2xl`}
        >
          {icon}
        </div>
      </div>
    </div>
  );
};
