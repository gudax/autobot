import React, { useState, useEffect } from 'react';
import { Card, Button, Table, LoadingSpinner, Badge } from '../components/common';
import { api } from '../services/api';
import type { Trade } from '../types';

export const TradesPage: React.FC = () => {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [filteredTrades, setFilteredTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [symbolFilter, setSymbolFilter] = useState('');
  const [sideFilter, setSideFilter] = useState<'ALL' | 'BUY' | 'SELL'>('ALL');
  const [profitFilter, setProfitFilter] = useState<'ALL' | 'PROFIT' | 'LOSS'>('ALL');

  const fetchTrades = async () => {
    try {
      setLoading(true);
      const data = await api.getTrades(undefined, undefined, 0, 1000);
      setTrades(data);
      setFilteredTrades(data);
    } catch (error) {
      console.error('Failed to fetch trades:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrades();
  }, []);

  // Apply filters whenever filters change
  useEffect(() => {
    let filtered = [...trades];

    // Symbol filter
    if (symbolFilter) {
      filtered = filtered.filter((t) =>
        t.symbol.toLowerCase().includes(symbolFilter.toLowerCase())
      );
    }

    // Side filter
    if (sideFilter !== 'ALL') {
      filtered = filtered.filter((t) => t.side === sideFilter);
    }

    // Profit/Loss filter
    if (profitFilter !== 'ALL') {
      if (profitFilter === 'PROFIT') {
        filtered = filtered.filter((t) => (t.profit_loss || 0) > 0);
      } else {
        filtered = filtered.filter((t) => (t.profit_loss || 0) < 0);
      }
    }

    setFilteredTrades(filtered);
  }, [trades, symbolFilter, sideFilter, profitFilter]);

  // Calculate statistics
  const totalTrades = filteredTrades.length;
  const winningTrades = filteredTrades.filter((t) => (t.profit_loss || 0) > 0).length;
  const losingTrades = filteredTrades.filter((t) => (t.profit_loss || 0) < 0).length;
  const totalPnL = filteredTrades.reduce((sum, t) => sum + (t.profit_loss || 0), 0);
  const winRate = totalTrades > 0 ? (winningTrades / totalTrades) * 100 : 0;
  const avgProfit =
    winningTrades > 0
      ? filteredTrades
          .filter((t) => (t.profit_loss || 0) > 0)
          .reduce((sum, t) => sum + (t.profit_loss || 0), 0) / winningTrades
      : 0;
  const avgLoss =
    losingTrades > 0
      ? filteredTrades
          .filter((t) => (t.profit_loss || 0) < 0)
          .reduce((sum, t) => sum + (t.profit_loss || 0), 0) / losingTrades
      : 0;

  const columns = [
    {
      header: 'ID',
      accessor: 'id' as keyof Trade,
    },
    {
      header: 'User ID',
      accessor: 'user_id' as keyof Trade,
    },
    {
      header: 'Symbol',
      accessor: 'symbol' as keyof Trade,
    },
    {
      header: 'Side',
      accessor: ((row: Trade) => (
        <Badge variant={row.side === 'BUY' ? 'success' : 'danger'}>
          {row.side}
        </Badge>
      )) as any,
    },
    {
      header: 'Quantity',
      accessor: ((row: Trade) => row.quantity?.toFixed(4) || '-') as any,
    },
    {
      header: 'Entry',
      accessor: ((row: Trade) => `$${row.entry_price?.toFixed(2) || '-'}`) as any,
    },
    {
      header: 'Exit',
      accessor: ((row: Trade) => `$${row.exit_price?.toFixed(2) || '-'}`) as any,
    },
    {
      header: 'P&L',
      accessor: ((row: Trade) => (
        <span
          className={
            (row.profit_loss || 0) >= 0
              ? 'text-green-600 font-semibold'
              : 'text-red-600 font-semibold'
          }
        >
          ${(row.profit_loss || 0).toFixed(2)}
        </span>
      )) as any,
    },
    {
      header: 'P&L %',
      accessor: ((row: Trade) => (
        <span
          className={
            (row.profit_loss_percent || 0) >= 0
              ? 'text-green-600'
              : 'text-red-600'
          }
        >
          {(row.profit_loss_percent || 0).toFixed(2)}%
        </span>
      )) as any,
    },
    {
      header: 'Duration',
      accessor: ((row: Trade) => {
        if (!row.duration_seconds) return '-';
        const hours = Math.floor(row.duration_seconds / 3600);
        const minutes = Math.floor((row.duration_seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
      }) as any,
    },
    {
      header: 'Executed At',
      accessor: ((row: Trade) =>
        row.executed_at ? new Date(row.executed_at).toLocaleString() : '-'
      ) as any,
    },
    {
      header: 'Closed At',
      accessor: ((row: Trade) =>
        row.closed_at ? new Date(row.closed_at).toLocaleString() : '-'
      ) as any,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Trade History</h1>
          <p className="text-gray-600 mt-1">
            View and analyze past trading activity
          </p>
        </div>
        <Button variant="secondary" onClick={fetchTrades}>
          Refresh
        </Button>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Trades</p>
              <p className="text-2xl font-bold text-gray-900 mt-2">
                {totalTrades}
              </p>
            </div>
            <div className="w-12 h-12 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center text-2xl">
              📊
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Win Rate</p>
              <p className="text-2xl font-bold text-gray-900 mt-2">
                {winRate.toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {winningTrades}W / {losingTrades}L
              </p>
            </div>
            <div className="w-12 h-12 rounded-lg bg-green-50 text-green-600 flex items-center justify-center text-2xl">
              🎯
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total P&L</p>
              <p
                className={`text-2xl font-bold mt-2 ${
                  totalPnL >= 0 ? 'text-green-600' : 'text-red-600'
                }`}
              >
                ${totalPnL.toFixed(2)}
              </p>
            </div>
            <div
              className={`w-12 h-12 rounded-lg ${
                totalPnL >= 0
                  ? 'bg-green-50 text-green-600'
                  : 'bg-red-50 text-red-600'
              } flex items-center justify-center text-2xl`}
            >
              {totalPnL >= 0 ? '📈' : '📉'}
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Avg Profit/Loss</p>
              <p className="text-sm font-semibold text-green-600 mt-2">
                ${avgProfit.toFixed(2)}
              </p>
              <p className="text-sm font-semibold text-red-600">
                ${avgLoss.toFixed(2)}
              </p>
            </div>
            <div className="w-12 h-12 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center text-2xl">
              💰
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <Card title="Filters">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Symbol
            </label>
            <input
              type="text"
              className="input"
              placeholder="Search by symbol..."
              value={symbolFilter}
              onChange={(e) => setSymbolFilter(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Side
            </label>
            <select
              className="input"
              value={sideFilter}
              onChange={(e) => setSideFilter(e.target.value as any)}
            >
              <option value="ALL">All</option>
              <option value="BUY">Buy (Long)</option>
              <option value="SELL">Sell (Short)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Result
            </label>
            <select
              className="input"
              value={profitFilter}
              onChange={(e) => setProfitFilter(e.target.value as any)}
            >
              <option value="ALL">All</option>
              <option value="PROFIT">Profitable Only</option>
              <option value="LOSS">Losses Only</option>
            </select>
          </div>
        </div>

        <div className="mt-4 flex gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              setSymbolFilter('');
              setSideFilter('ALL');
              setProfitFilter('ALL');
            }}
          >
            Clear Filters
          </Button>
          <span className="text-sm text-gray-600 flex items-center">
            Showing {filteredTrades.length} of {trades.length} trades
          </span>
        </div>
      </Card>

      {/* Trades Table */}
      <Card title="Trade History">
        {loading ? (
          <LoadingSpinner />
        ) : (
          <Table
            data={filteredTrades}
            columns={columns}
            emptyMessage="No trades found"
          />
        )}
      </Card>
    </div>
  );
};
