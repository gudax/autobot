"""
Integration tests for Trading Engine
"""

import pytest
import asyncio
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.market_data import Candle, MarketDataCollector
from data.orderbook import OrderBook, OrderBookLevel
from analysis.volume_analyzer import VolumeAnalyzer
from analysis.orderbook_analyzer import OrderBookAnalyzer
from strategy.scalping_strategy import ScalpingStrategy
from execution.order_executor import OrderExecutor
from config.strategy_config import StrategyConfig


class TestIntegration:
    """Integration tests"""

    @pytest.fixture
    def sample_candles(self):
        """Create sample candles for testing"""
        candles = []
        base_price = 50000
        base_volume = 100

        for i in range(100):
            # Create uptrend with increasing volume
            candle = Candle(
                symbol="BTCUSD",
                timestamp=1234567890 + i * 60,
                open=base_price + i * 10,
                high=base_price + i * 10 + 50,
                low=base_price + i * 10 - 30,
                close=base_price + i * 10 + 20,
                volume=base_volume + i * 5,
                buy_volume=(base_volume + i * 5) * 0.6,
                sell_volume=(base_volume + i * 5) * 0.4,
                timeframe="1m"
            )
            candles.append(candle)

        return candles

    @pytest.fixture
    def sample_orderbook(self):
        """Create sample order book"""
        bids = [
            OrderBookLevel(price=50000, volume=2.0),
            OrderBookLevel(price=49990, volume=3.0),
            OrderBookLevel(price=49980, volume=2.5),
        ]

        asks = [
            OrderBookLevel(price=50010, volume=1.5),
            OrderBookLevel(price=50020, volume=2.0),
            OrderBookLevel(price=50030, volume=1.8),
        ]

        return OrderBook(
            symbol="BTCUSD",
            bids=bids,
            asks=asks
        )

    def test_volume_analyzer_integration(self, sample_candles):
        """Test volume analyzer with sample data"""
        analyzer = VolumeAnalyzer()

        # Add candles
        for candle in sample_candles[:-1]:
            analyzer.add_candle(candle)

        # Analyze last candle
        signal = analyzer.analyze("BTCUSD", sample_candles[-1])

        assert signal is not None
        assert signal.symbol == "BTCUSD"
        assert signal.volume_ratio > 0

    def test_orderbook_analyzer_integration(self, sample_orderbook):
        """Test order book analyzer"""
        analyzer = OrderBookAnalyzer()

        analysis = analyzer.analyze(sample_orderbook)

        assert analysis is not None
        assert analysis.symbol == "BTCUSD"
        assert 0 <= analysis.imbalance_ratio <= 1
        assert analysis.liquidity_score >= 0

    def test_strategy_integration(self, sample_candles, sample_orderbook):
        """Test strategy with sample data"""
        strategy = ScalpingStrategy(
            config=StrategyConfig(),
            initial_balance=10000.0
        )

        # Process signal
        signal = strategy.process_signal(
            "BTCUSD",
            sample_candles,
            sample_candles[-1],
            sample_orderbook
        )

        assert signal is not None

    @pytest.mark.asyncio
    async def test_order_executor_simulation(self, sample_candles):
        """Test order executor in simulation mode"""
        executor = OrderExecutor(
            token="test_token",
            trading_api_token="test_trading_token",
            simulation_mode=True
        )

        # Create strategy and get signal
        strategy = ScalpingStrategy(initial_balance=10000.0)

        # Create order book
        orderbook = OrderBook(
            symbol="BTCUSD",
            bids=[OrderBookLevel(price=50000, volume=2.0)],
            asks=[OrderBookLevel(price=50010, volume=1.5)]
        )

        signal = strategy.process_signal(
            "BTCUSD",
            sample_candles,
            sample_candles[-1],
            orderbook
        )

        if signal and signal.action.value != "HOLD":
            # Execute signal
            result = await executor.execute_signal(signal)

            assert result is not None
            if result.success:
                assert result.order_id is not None

        await executor.close()

    def test_end_to_end_workflow(self, sample_candles, sample_orderbook):
        """Test complete trading workflow"""
        # Initialize components
        strategy = ScalpingStrategy(
            config=StrategyConfig(),
            initial_balance=10000.0
        )

        # Process market data
        signal = strategy.process_signal(
            "BTCUSD",
            sample_candles,
            sample_candles[-1],
            sample_orderbook
        )

        # Signal should be generated
        assert signal is not None

        # If entry signal, execute it
        if signal.action.value in ["OPEN_LONG", "OPEN_SHORT"]:
            # Execute signal (simulation)
            success = strategy.execute_signal(signal)
            assert success

            # Position should be opened
            assert "BTCUSD" in strategy.current_positions

            # Get statistics
            stats = strategy.get_statistics()
            assert stats["open_positions"] == 1

    def test_risk_management_integration(self, sample_candles, sample_orderbook):
        """Test risk management in strategy"""
        strategy = ScalpingStrategy(initial_balance=1000.0)  # Small balance

        # Process multiple times to test position limits
        for _ in range(10):
            signal = strategy.process_signal(
                "BTCUSD",
                sample_candles,
                sample_candles[-1],
                sample_orderbook
            )

            if signal and signal.action.value in ["OPEN_LONG", "OPEN_SHORT"]:
                strategy.execute_signal(signal)

        # Should not exceed max positions
        assert len(strategy.current_positions) <= strategy.config.risk.max_total_positions

    def test_statistics_reporting(self, sample_candles, sample_orderbook):
        """Test statistics reporting"""
        strategy = ScalpingStrategy(initial_balance=10000.0)

        # Process signal
        signal = strategy.process_signal(
            "BTCUSD",
            sample_candles,
            sample_candles[-1],
            sample_orderbook
        )

        # Get statistics
        stats = strategy.get_statistics()

        assert "balance" in stats
        assert "total_pnl" in stats
        assert "win_rate" in stats
        assert "open_positions" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
