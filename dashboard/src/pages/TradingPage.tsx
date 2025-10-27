import React, { useState, useEffect } from 'react';
import { Card, Button, Table, LoadingSpinner, Badge } from '../components/common';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../services/api';
import type { Order, TradingSignal } from '../types';

export const TradingPage: React.FC = () => {
  const [positions, setPositions] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [executingSignal, setExecutingSignal] = useState(false);
  const [signalForm, setSignalForm] = useState<TradingSignal>({
    action: 'OPEN_LONG',
    symbol: 'BTCUSDT',
    entry_price: undefined,
    stop_loss: undefined,
    take_profit: undefined,
    volume: 0.01,
    reason: '',
  });

  const { isConnected } = useWebSocket('positions', {
    onMessage: (message) => {
      if (message.type === 'position_update') {
        fetchPositions();
      }
    },
  });

  const fetchPositions = async () => {
    try {
      const data = await api.getPositions(0, 100);
      // Filter only OPEN positions
      const openPositions = data.positions.filter(p => p.status === 'OPEN');
      setPositions(openPositions);
    } catch (error) {
      console.error('Failed to fetch positions:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPositions();
    const interval = setInterval(fetchPositions, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const handleExecuteSignal = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setExecutingSignal(true);
      const result = await api.executeTradingSignal(signalForm);
      alert(
        `Signal executed!\nSuccessful: ${result.executed_count}\nFailed: ${result.failed_count}`
      );
      await fetchPositions();
    } catch (error) {
      console.error('Failed to execute signal:', error);
      alert('Failed to execute trading signal');
    } finally {
      setExecutingSignal(false);
    }
  };

  const handleCloseAll = async () => {
    if (!confirm('Are you sure you want to close all positions?')) {
      return;
    }
    try {
      await api.closeAllPositions();
      alert('Close all positions command sent');
      await fetchPositions();
    } catch (error) {
      console.error('Failed to close all positions:', error);
      alert('Failed to close all positions');
    }
  };

  const handleCloseSymbol = async (symbol: string) => {
    if (!confirm(`Are you sure you want to close all ${symbol} positions?`)) {
      return;
    }
    try {
      await api.closeAllPositions(symbol);
      alert(`Close ${symbol} positions command sent`);
      await fetchPositions();
    } catch (error) {
      console.error(`Failed to close ${symbol} positions:`, error);
      alert(`Failed to close ${symbol} positions`);
    }
  };

  const positionColumns = [
    {
      header: 'User ID',
      accessor: 'user_id' as keyof Order,
    },
    {
      header: 'Symbol',
      accessor: 'symbol' as keyof Order,
    },
    {
      header: 'Side',
      accessor: ((row: Order) => (
        <Badge variant={row.side === 'BUY' ? 'success' : 'danger'}>
          {row.side}
        </Badge>
      )) as any,
    },
    {
      header: 'Quantity',
      accessor: ((row: Order) => row.quantity?.toFixed(4) || '-') as any,
    },
    {
      header: 'Entry Price',
      accessor: ((row: Order) => row.entry_price?.toFixed(2) || '-') as any,
    },
    {
      header: 'Stop Loss',
      accessor: ((row: Order) => row.stop_loss?.toFixed(2) || '-') as any,
    },
    {
      header: 'Take Profit',
      accessor: ((row: Order) => row.take_profit?.toFixed(2) || '-') as any,
    },
    {
      header: 'Status',
      accessor: ((row: Order) => (
        <Badge variant="info">{row.status}</Badge>
      )) as any,
    },
    {
      header: 'Created At',
      accessor: ((row: Order) =>
        new Date(row.created_at).toLocaleString()
      ) as any,
    },
  ];

  // Calculate statistics
  const totalPositions = positions.length;
  const longPositions = positions.filter((p) => p.side === 'BUY').length;
  const shortPositions = positions.filter((p) => p.side === 'SELL').length;
  const uniqueSymbols = [...new Set(positions.map((p) => p.symbol))];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Trading</h1>
          <p className="text-gray-600 mt-1">
            Execute signals and monitor positions
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="danger" onClick={handleCloseAll}>
            Close All Positions
          </Button>
          <Button variant="secondary" onClick={fetchPositions}>
            Refresh
          </Button>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">
                Total Positions
              </p>
              <p className="text-2xl font-bold text-gray-900 mt-2">
                {totalPositions}
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
              <p className="text-sm font-medium text-gray-600">Long Positions</p>
              <p className="text-2xl font-bold text-green-600 mt-2">
                {longPositions}
              </p>
            </div>
            <div className="w-12 h-12 rounded-lg bg-green-50 text-green-600 flex items-center justify-center text-2xl">
              📈
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">
                Short Positions
              </p>
              <p className="text-2xl font-bold text-red-600 mt-2">
                {shortPositions}
              </p>
            </div>
            <div className="w-12 h-12 rounded-lg bg-red-50 text-red-600 flex items-center justify-center text-2xl">
              📉
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">
                Unique Symbols
              </p>
              <p className="text-2xl font-bold text-gray-900 mt-2">
                {uniqueSymbols.length}
              </p>
            </div>
            <div className="w-12 h-12 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center text-2xl">
              🎯
            </div>
          </div>
        </div>
      </div>

      {/* Signal Execution Form */}
      <Card title="Execute Trading Signal">
        <form onSubmit={handleExecuteSignal} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Action *
              </label>
              <select
                className="input"
                value={signalForm.action}
                onChange={(e) =>
                  setSignalForm({
                    ...signalForm,
                    action: e.target.value as TradingSignal['action'],
                  })
                }
                required
              >
                <option value="OPEN_LONG">Open Long</option>
                <option value="OPEN_SHORT">Open Short</option>
                <option value="CLOSE">Close Position</option>
                <option value="CLOSE_ALL">Close All</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Symbol *
              </label>
              <input
                type="text"
                className="input"
                value={signalForm.symbol}
                onChange={(e) =>
                  setSignalForm({ ...signalForm, symbol: e.target.value })
                }
                placeholder="e.g. BTCUSDT"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Volume
              </label>
              <input
                type="number"
                step="0.001"
                className="input"
                value={signalForm.volume}
                onChange={(e) =>
                  setSignalForm({
                    ...signalForm,
                    volume: parseFloat(e.target.value),
                  })
                }
                placeholder="0.01"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Entry Price
              </label>
              <input
                type="number"
                step="0.01"
                className="input"
                value={signalForm.entry_price || ''}
                onChange={(e) =>
                  setSignalForm({
                    ...signalForm,
                    entry_price: e.target.value
                      ? parseFloat(e.target.value)
                      : undefined,
                  })
                }
                placeholder="Market price"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Stop Loss
              </label>
              <input
                type="number"
                step="0.01"
                className="input"
                value={signalForm.stop_loss || ''}
                onChange={(e) =>
                  setSignalForm({
                    ...signalForm,
                    stop_loss: e.target.value
                      ? parseFloat(e.target.value)
                      : undefined,
                  })
                }
                placeholder="Optional"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Take Profit
              </label>
              <input
                type="number"
                step="0.01"
                className="input"
                value={signalForm.take_profit || ''}
                onChange={(e) =>
                  setSignalForm({
                    ...signalForm,
                    take_profit: e.target.value
                      ? parseFloat(e.target.value)
                      : undefined,
                  })
                }
                placeholder="Optional"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Reason (Optional)
            </label>
            <textarea
              className="input"
              rows={2}
              value={signalForm.reason}
              onChange={(e) =>
                setSignalForm({ ...signalForm, reason: e.target.value })
              }
              placeholder="Reason for this trade..."
            />
          </div>

          <Button
            type="submit"
            variant="primary"
            loading={executingSignal}
            disabled={executingSignal}
          >
            Execute Signal for All Users
          </Button>
        </form>
      </Card>

      {/* Open Positions */}
      <Card
        title="Open Positions"
        actions={
          <div className="flex gap-2">
            <Badge variant={isConnected ? 'success' : 'danger'}>
              {isConnected ? 'Live' : 'Offline'}
            </Badge>
          </div>
        }
      >
        {loading ? (
          <LoadingSpinner />
        ) : (
          <>
            {uniqueSymbols.length > 0 && (
              <div className="mb-4 flex flex-wrap gap-2">
                <span className="text-sm text-gray-600">Close by symbol:</span>
                {uniqueSymbols.map((symbol) => (
                  <Button
                    key={symbol}
                    size="sm"
                    variant="secondary"
                    onClick={() => handleCloseSymbol(symbol)}
                  >
                    Close {symbol}
                  </Button>
                ))}
              </div>
            )}
            <Table
              data={positions}
              columns={positionColumns}
              emptyMessage="No open positions"
            />
          </>
        )}
      </Card>
    </div>
  );
};
