"""
Main entry point for Trading Engine
"""

import asyncio
from typing import Optional, List
from config import settings, StrategyConfig
from utils.logger import setup_logger
from data.market_data import MarketDataCollector, Candle
from data.orderbook import OrderBook
from strategy.scalping_strategy import ScalpingStrategy
from execution.order_executor import OrderExecutor


logger = setup_logger(
    name="trading_engine",
    level=settings.log_level,
    log_file=settings.log_file
)


class TradingEngine:
    """Main Trading Engine orchestrator"""

    def __init__(
        self,
        token: Optional[str] = None,
        trading_api_token: Optional[str] = None,
        symbols: Optional[List[str]] = None,
        simulation_mode: bool = True
    ):
        """
        Initialize Trading Engine

        Args:
            token: Authentication token
            trading_api_token: Trading API token
            symbols: List of symbols to trade
            simulation_mode: Run in simulation mode
        """
        self.running = False
        self.logger = logger
        self.simulation_mode = simulation_mode

        # Trading symbols
        self.symbols = symbols or ["BTCUSD"]

        # Initialize components
        self.market_data_collector = None
        self.order_executor = None
        self.strategy = None

        # Tokens
        self.token = token
        self.trading_api_token = trading_api_token

        # Performance metrics
        self.cycles_processed = 0
        self.signals_generated = 0
        self.orders_executed = 0

    async def start(self):
        """Start the trading engine"""
        self.logger.info(
            "Starting Trading Engine",
            version="0.1.0",
            symbols=self.symbols,
            simulation_mode=self.simulation_mode
        )

        try:
            self.running = True

            # Initialize components
            await self._initialize_components()

            self.logger.info("Trading Engine started successfully")

            # Main loop
            while self.running:
                await self._process_cycle()
                await asyncio.sleep(settings.data_refresh_interval)

        except Exception as e:
            self.logger.error("Error in trading engine", error=str(e), exc_info=True)
            raise
        finally:
            await self.stop()

    async def _initialize_components(self):
        """Initialize trading components"""
        # Initialize strategy
        self.strategy = ScalpingStrategy(
            config=StrategyConfig(),
            initial_balance=10000.0
        )

        # Initialize market data collector (if tokens provided)
        if self.token and self.trading_api_token:
            self.market_data_collector = MarketDataCollector(
                token=self.token,
                trading_api_token=self.trading_api_token
            )

            # Initialize order executor
            self.order_executor = OrderExecutor(
                token=self.token,
                trading_api_token=self.trading_api_token,
                simulation_mode=self.simulation_mode
            )

        self.logger.info("Components initialized")

    async def _process_cycle(self):
        """Process one trading cycle"""
        try:
            self.cycles_processed += 1

            # Process each symbol
            for symbol in self.symbols:
                await self._process_symbol(symbol)

            # Log statistics periodically
            if self.cycles_processed % 60 == 0:  # Every 60 cycles
                self._log_statistics()

        except Exception as e:
            self.logger.error("Error in process cycle", error=str(e), exc_info=True)

    async def _process_symbol(self, symbol: str):
        """
        Process trading for single symbol

        Args:
            symbol: Trading symbol
        """
        try:
            # In simulation mode without API, skip
            if not self.market_data_collector:
                self.logger.debug("Skipping cycle (no market data collector)")
                return

            # Collect market data
            candles = await self.market_data_collector.get_candles(
                symbol=symbol,
                timeframe="1m",
                limit=100
            )

            if not candles or len(candles) < 2:
                self.logger.warning("Insufficient candle data", symbol=symbol)
                return

            current_candle = candles[-1]

            # Get order book (simulated for now)
            # In production, fetch real order book data
            orderbook = self._create_dummy_orderbook(symbol, current_candle.close)

            # Generate signal
            signal = self.strategy.process_signal(
                symbol,
                candles,
                current_candle,
                orderbook
            )

            if signal and signal.action.value != "HOLD":
                self.signals_generated += 1
                self.logger.info("Signal generated", signal=signal.to_dict())

                # Execute signal
                if self.order_executor:
                    result = await self.order_executor.execute_signal(signal)

                    if result.success:
                        self.orders_executed += 1
                        # Update strategy with execution result
                        self.strategy.execute_signal(signal)

        except Exception as e:
            self.logger.error("Error processing symbol", symbol=symbol, error=str(e))

    def _create_dummy_orderbook(self, symbol: str, price: float) -> OrderBook:
        """Create dummy order book for testing"""
        from data.orderbook import OrderBookLevel

        # Create simple order book around current price
        bids = [
            OrderBookLevel(price=price - 10, volume=1.0),
            OrderBookLevel(price=price - 20, volume=2.0),
            OrderBookLevel(price=price - 30, volume=1.5),
        ]

        asks = [
            OrderBookLevel(price=price + 10, volume=1.2),
            OrderBookLevel(price=price + 20, volume=1.8),
            OrderBookLevel(price=price + 30, volume=2.5),
        ]

        return OrderBook(
            symbol=symbol,
            bids=bids,
            asks=asks
        )

    def _log_statistics(self):
        """Log trading statistics"""
        strategy_stats = self.strategy.get_statistics()

        self.logger.info(
            "Trading Statistics",
            cycles=self.cycles_processed,
            signals_generated=self.signals_generated,
            orders_executed=self.orders_executed,
            **strategy_stats
        )

    async def stop(self):
        """Stop the trading engine"""
        self.logger.info("Stopping Trading Engine")
        self.running = False

        # Close connections
        if self.market_data_collector:
            await self.market_data_collector.close()

        if self.order_executor:
            await self.order_executor.close()

        # Log final statistics
        self._log_statistics()

        self.logger.info("Trading Engine stopped")


async def main():
    """Main entry point"""
    engine = TradingEngine()

    try:
        await engine.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        await engine.stop()
    except Exception as e:
        logger.error("Fatal error", error=str(e), exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
