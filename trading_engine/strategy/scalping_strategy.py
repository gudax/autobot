"""
Scalping Strategy - Main trading strategy integrating all analysis modules
"""

from typing import Optional, Dict, List, Any
from datetime import datetime

from config.strategy_config import StrategyConfig
from data.market_data import Candle, MarketDataCollector
from data.orderbook import OrderBook
from analysis.volume_analyzer import VolumeAnalyzer, VolumeSignal, SignalDirection
from analysis.orderbook_analyzer import OrderBookAnalyzer, OrderBookAnalysis
from analysis.chart_analyzer import ChartAnalyzer
from analysis.indicators import calculate_rsi, is_overbought, is_oversold
from strategy.signal_generator import SignalGenerator, TradingSignal, SignalAction
from strategy.risk_manager import RiskManager, Position
from utils.logger import get_logger
from utils.helpers import calculate_stop_loss, calculate_take_profit


logger = get_logger("scalping_strategy")


class ScalpingStrategy:
    """
    Main scalping strategy that combines:
    - Volume spike detection
    - Order book analysis
    - Chart pattern recognition
    - Risk management
    """

    def __init__(
        self,
        config: Optional[StrategyConfig] = None,
        initial_balance: float = 10000.0
    ):
        """
        Initialize Scalping Strategy

        Args:
            config: Strategy configuration
            initial_balance: Initial account balance
        """
        self.config = config or StrategyConfig()
        self.logger = logger

        # Initialize analyzers
        self.volume_analyzer = VolumeAnalyzer(self.config.volume)
        self.orderbook_analyzer = OrderBookAnalyzer(self.config.orderbook)
        self.chart_analyzer = ChartAnalyzer()

        # Initialize strategy components
        self.signal_generator = SignalGenerator()
        self.risk_manager = RiskManager(self.config.risk, initial_balance)

        # State
        self.current_positions: Dict[str, Position] = {}
        self.last_signals: Dict[str, VolumeSignal] = {}

    def analyze_market(
        self,
        symbol: str,
        candles: List[Candle],
        current_candle: Candle,
        orderbook: OrderBook
    ) -> Dict[str, Any]:
        """
        Perform complete market analysis

        Args:
            symbol: Trading symbol
            candles: Historical candles
            current_candle: Current candle
            orderbook: Current order book

        Returns:
            Dictionary with analysis results
        """
        # Volume analysis
        volume_signal = self.volume_analyzer.analyze(
            symbol,
            current_candle,
            ma_period=self.config.volume.ma_periods[0]
        )

        # Order book analysis
        orderbook_analysis = self.orderbook_analyzer.analyze(orderbook)

        # Chart analysis
        chart_analysis = self.chart_analyzer.analyze_price_action(candles)

        # Calculate RSI
        prices = [c.close for c in candles]
        rsi_values = calculate_rsi(prices, period=14) if len(prices) >= 15 else [50]
        current_rsi = rsi_values[-1] if rsi_values else 50

        return {
            "volume_signal": volume_signal,
            "orderbook_analysis": orderbook_analysis,
            "chart_analysis": chart_analysis,
            "rsi": current_rsi,
            "current_price": current_candle.close
        }

    def check_entry_conditions(
        self,
        symbol: str,
        analysis: Dict[str, Any]
    ) -> Optional[TradingSignal]:
        """
        Check if entry conditions are met

        Args:
            symbol: Trading symbol
            analysis: Market analysis results

        Returns:
            TradingSignal if conditions met, None otherwise
        """
        volume_signal: VolumeSignal = analysis["volume_signal"]
        orderbook_analysis: OrderBookAnalysis = analysis["orderbook_analysis"]
        chart_analysis: Dict[str, Any] = analysis["chart_analysis"]
        current_rsi: float = analysis["rsi"]
        current_price: float = analysis["current_price"]

        # Check if signal is neutral
        if volume_signal.direction == SignalDirection.NEUTRAL:
            return None

        # Check signal strength threshold
        if volume_signal.strength < self.config.scalping.min_signal_strength:
            self.logger.debug(
                "Signal strength below threshold",
                symbol=symbol,
                strength=volume_signal.strength,
                threshold=self.config.scalping.min_signal_strength
            )
            return None

        # Check volume spike requirement
        if self.config.scalping.volume_spike_required:
            if volume_signal.volume_ratio < self.config.volume.spike_threshold_medium:
                return None

        # Check order book imbalance requirement
        if self.config.scalping.orderbook_imbalance_required:
            if volume_signal.direction == SignalDirection.LONG:
                if orderbook_analysis.imbalance_ratio < self.config.orderbook.imbalance_threshold:
                    return None
            elif volume_signal.direction == SignalDirection.SHORT:
                if orderbook_analysis.imbalance_ratio > (1 - self.config.orderbook.imbalance_threshold):
                    return None

        # Check RSI conditions
        if self.config.scalping.use_rsi:
            if volume_signal.direction == SignalDirection.LONG:
                if is_overbought([current_rsi], self.config.scalping.rsi_overbought):
                    self.logger.debug("RSI overbought, skipping LONG signal", rsi=current_rsi)
                    return None
            elif volume_signal.direction == SignalDirection.SHORT:
                if is_oversold([current_rsi], self.config.scalping.rsi_oversold):
                    self.logger.debug("RSI oversold, skipping SHORT signal", rsi=current_rsi)
                    return None

        # Check order book favorability
        direction = "LONG" if volume_signal.direction == SignalDirection.LONG else "SHORT"
        favorability = self.orderbook_analyzer.is_favorable_for_entry(
            orderbook_analysis,
            direction
        )

        if not favorability["favorable"]:
            self.logger.debug(
                "Order book not favorable",
                symbol=symbol,
                direction=direction,
                score=favorability["score"]
            )
            return None

        # Calculate stop loss and take profit
        stop_loss = calculate_stop_loss(
            current_price,
            direction,
            self.config.scalping.stop_loss_percent / 100
        )

        take_profit = calculate_take_profit(
            current_price,
            direction,
            self.config.scalping.take_profit_percent / 100
        )

        # Calculate position size
        position_size = self.risk_manager.calculate_position_size(
            symbol,
            current_price,
            stop_loss
        )

        # Check if can open position
        can_open = self.risk_manager.can_open_position(
            symbol,
            direction,
            position_size,
            current_price
        )

        if not can_open["can_open"]:
            self.logger.info(
                "Cannot open position",
                symbol=symbol,
                reasons=can_open["reasons"]
            )
            return None

        # Calculate confidence
        confidence = self._calculate_overall_confidence(
            volume_signal,
            orderbook_analysis,
            chart_analysis,
            favorability
        )

        # Build reason
        reasons = [
            volume_signal.reason,
            f"OB pressure: {orderbook_analysis.pressure.value}",
            f"OB favorability: {favorability['score']:.2f}"
        ]

        if chart_analysis.get("trend"):
            reasons.append(f"Trend: {chart_analysis['trend']}")

        reason = " | ".join(reasons)

        # Generate signal
        signal = self.signal_generator.generate_entry_signal(
            symbol=symbol,
            direction=direction,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            quantity=position_size,
            confidence=confidence,
            reason=reason,
            metadata={
                "volume_signal_strength": volume_signal.strength,
                "orderbook_imbalance": orderbook_analysis.imbalance_ratio,
                "rsi": current_rsi
            }
        )

        return signal

    def check_exit_conditions(
        self,
        position: Position,
        current_price: float
    ) -> Optional[TradingSignal]:
        """
        Check if position should be closed

        Args:
            position: Open position
            current_price: Current market price

        Returns:
            TradingSignal if position should be closed, None otherwise
        """
        should_close = self.risk_manager.should_close_position(
            position,
            current_price,
            max_hold_time=self.config.scalping.max_hold_time_seconds
        )

        if should_close["should_close"]:
            signal = self.signal_generator.generate_exit_signal(
                symbol=position.symbol,
                exit_price=current_price,
                reason=" | ".join(should_close["reasons"])
            )
            return signal

        return None

    def process_signal(
        self,
        symbol: str,
        candles: List[Candle],
        current_candle: Candle,
        orderbook: OrderBook
    ) -> Optional[TradingSignal]:
        """
        Process market data and generate trading signal

        Args:
            symbol: Trading symbol
            candles: Historical candles
            current_candle: Current candle
            orderbook: Current order book

        Returns:
            TradingSignal or None
        """
        try:
            # Check if position exists
            if symbol in self.current_positions:
                # Check exit conditions
                position = self.current_positions[symbol]
                exit_signal = self.check_exit_conditions(position, current_candle.close)
                if exit_signal:
                    return exit_signal
                else:
                    # Hold position
                    return self.signal_generator.generate_hold_signal(
                        symbol,
                        "Position open, monitoring"
                    )

            # Analyze market
            analysis = self.analyze_market(symbol, candles, current_candle, orderbook)

            # Check entry conditions
            entry_signal = self.check_entry_conditions(symbol, analysis)

            if entry_signal:
                # Store signal
                self.last_signals[symbol] = analysis["volume_signal"]
                return entry_signal

            return None

        except Exception as e:
            self.logger.error("Error processing signal", symbol=symbol, error=str(e), exc_info=True)
            return None

    def execute_signal(self, signal: TradingSignal) -> bool:
        """
        Execute trading signal (simulation)

        Args:
            signal: Trading signal

        Returns:
            True if executed successfully
        """
        try:
            if signal.action == SignalAction.OPEN_LONG or signal.action == SignalAction.OPEN_SHORT:
                # Open position
                side = "LONG" if signal.action == SignalAction.OPEN_LONG else "SHORT"
                position = Position(
                    symbol=signal.symbol,
                    side=side,
                    entry_price=signal.entry_price,
                    quantity=signal.quantity,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    entry_time=datetime.utcnow(),
                    current_price=signal.entry_price
                )

                self.risk_manager.add_position(position)
                self.current_positions[signal.symbol] = position

                self.logger.info(
                    "Position opened",
                    symbol=signal.symbol,
                    side=side,
                    entry_price=signal.entry_price,
                    quantity=signal.quantity
                )

                return True

            elif signal.action == SignalAction.CLOSE:
                # Close position
                trade_result = self.risk_manager.close_position(
                    signal.symbol,
                    signal.entry_price,
                    signal.reason
                )

                if trade_result:
                    self.current_positions.pop(signal.symbol, None)
                    return True

            return False

        except Exception as e:
            self.logger.error("Error executing signal", signal=signal.to_dict(), error=str(e))
            return False

    def _calculate_overall_confidence(
        self,
        volume_signal: VolumeSignal,
        orderbook_analysis: OrderBookAnalysis,
        chart_analysis: Dict[str, Any],
        favorability: Dict[str, Any]
    ) -> float:
        """Calculate overall signal confidence"""
        confidence = 0.0

        # Volume signal contribution (40%)
        confidence += volume_signal.strength * 0.4

        # Order book favorability (30%)
        confidence += favorability["score"] * 0.3

        # Liquidity contribution (15%)
        confidence += orderbook_analysis.liquidity_score * 0.15

        # Trend alignment (15%)
        trend = chart_analysis.get("trend")
        if trend:
            direction = "LONG" if volume_signal.direction == SignalDirection.LONG else "SHORT"
            if (direction == "LONG" and trend == "UPTREND") or \
               (direction == "SHORT" and trend == "DOWNTREND"):
                confidence += 0.15

        return min(confidence, 1.0)

    def get_statistics(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        risk_stats = self.risk_manager.get_statistics()

        return {
            **risk_stats,
            "open_positions": len(self.current_positions),
            "tracked_symbols": len(self.last_signals)
        }

    def reset(self):
        """Reset strategy state"""
        self.current_positions.clear()
        self.last_signals.clear()
        self.logger.info("Strategy reset")
