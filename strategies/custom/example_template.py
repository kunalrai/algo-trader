"""
Example Custom Trading Strategy Template

This is a template for creating custom trading strategies.
Copy this file and implement your own trading logic.

REQUIREMENTS:
1. Your strategy class MUST inherit from BaseStrategy
2. Implement all three required methods:
   - get_required_timeframes()
   - get_required_indicators()
   - analyze(data, current_price)
3. Return signals in the correct format

USAGE:
1. Copy this template and rename it (e.g., my_strategy.py)
2. Rename the class (e.g., MyCustomStrategy)
3. Implement your trading logic in the analyze() method
4. Upload via the dashboard UI
"""

from strategies.base_strategy import BaseStrategy
from typing import Dict, List


class ExampleCustomStrategy(BaseStrategy):
    """
    Example custom strategy demonstrating the required structure

    This example implements a simple Bollinger Bands mean reversion strategy.
    Replace this logic with your own trading strategy.
    """

    def __init__(self, period: int = 20, std_dev: float = 2.0, min_strength: float = 0.65):
        """
        Initialize the strategy with custom parameters

        Args:
            period: Bollinger Bands period (default: 20)
            std_dev: Standard deviation multiplier (default: 2.0)
            min_strength: Minimum signal strength to generate trades (default: 0.65)
        """
        super().__init__()
        self.period = period
        self.std_dev = std_dev
        self.min_strength = min_strength

    def get_required_timeframes(self) -> List[str]:
        """
        Return the list of timeframes your strategy needs

        Available timeframes: '1m', '5m', '15m', '30m', '1h', '4h', '1d'

        Returns:
            List of timeframe strings
        """
        return ['5m', '1h', '4h']

    def get_required_indicators(self) -> List[str]:
        """
        Return the list of indicators your strategy needs

        Available indicators:
        - EMAs: 'ema_9', 'ema_21', 'ema_50', 'ema_200'
        - MACD: 'macd', 'macd_signal', 'macd_hist'
        - RSI: 'rsi'
        - Bollinger Bands: 'bollinger_upper', 'bollinger_middle', 'bollinger_lower'
        - ATR: 'atr'

        Returns:
            List of indicator strings
        """
        return ['bollinger_upper', 'bollinger_middle', 'bollinger_lower', 'rsi', 'ema_9', 'ema_21']

    def analyze(self, data: Dict, current_price: float) -> Dict:
        """
        Analyze market data and generate trading signal

        This is where you implement your custom trading logic.

        Args:
            data: Dictionary of timeframe data with indicators
                  Format: {
                      '5m': DataFrame with OHLCV + indicators,
                      '1h': DataFrame with OHLCV + indicators,
                      '4h': DataFrame with OHLCV + indicators
                  }
            current_price: Current market price

        Returns:
            Signal dictionary with required fields:
            {
                'action': str,        # 'long', 'short', or 'flat'
                'strength': float,    # 0.0 to 1.0
                'confidence': float,  # 0.0 to 1.0
                'reasons': List[str], # Human-readable reasons
                'indicators': Dict,   # Indicator values used
                'metadata': Dict      # Any additional data
            }
        """
        # Validate data availability
        if not self.validate_data(data, self.get_required_timeframes()):
            return self._flat_signal("Insufficient data")

        try:
            # Get the primary timeframe data (5m in this example)
            df_5m = data.get('5m')
            df_1h = data.get('1h')

            if df_5m is None or df_5m.empty:
                return self._flat_signal("No 5m data available")

            # Get latest values from the dataframe
            latest = df_5m.iloc[-1]

            # Extract Bollinger Bands values
            bb_upper = latest.get('bollinger_upper', 0)
            bb_middle = latest.get('bollinger_middle', 0)
            bb_lower = latest.get('bollinger_lower', 0)
            rsi = latest.get('RSI', 50)

            # Extract EMA values for trend confirmation
            ema_9 = latest.get('EMA_9', 0)
            ema_21 = latest.get('EMA_21', 0)

            # Initialize signal components
            action = 'flat'
            strength = 0.0
            confidence = 0.0
            reasons = []

            # Example Strategy Logic: Bollinger Bands Mean Reversion

            # Long signal: Price touches lower band + oversold RSI
            if current_price <= bb_lower and rsi < 40:
                action = 'long'

                # Calculate strength based on how oversold
                rsi_strength = max(0, (40 - rsi) / 40)  # Stronger when more oversold
                bb_distance = (bb_middle - current_price) / (bb_middle - bb_lower)
                strength = (rsi_strength + bb_distance) / 2

                # Higher confidence if trend is bullish (EMA 9 > EMA 21)
                if ema_9 > ema_21:
                    confidence = 0.8
                    reasons.append("5m: Bullish trend confirmation (EMA 9 > EMA 21)")
                else:
                    confidence = 0.6
                    reasons.append("5m: Counter-trend setup")

                reasons.append(f"5m: Price at lower Bollinger Band (${current_price:.2f} vs ${bb_lower:.2f})")
                reasons.append(f"5m: RSI oversold ({rsi:.1f})")

            # Short signal: Price touches upper band + overbought RSI
            elif current_price >= bb_upper and rsi > 60:
                action = 'short'

                # Calculate strength based on how overbought
                rsi_strength = max(0, (rsi - 60) / 40)  # Stronger when more overbought
                bb_distance = (current_price - bb_middle) / (bb_upper - bb_middle)
                strength = (rsi_strength + bb_distance) / 2

                # Higher confidence if trend is bearish (EMA 9 < EMA 21)
                if ema_9 < ema_21:
                    confidence = 0.8
                    reasons.append("5m: Bearish trend confirmation (EMA 9 < EMA 21)")
                else:
                    confidence = 0.6
                    reasons.append("5m: Counter-trend setup")

                reasons.append(f"5m: Price at upper Bollinger Band (${current_price:.2f} vs ${bb_upper:.2f})")
                reasons.append(f"5m: RSI overbought ({rsi:.1f})")

            else:
                # No signal
                reasons.append("5m: Price within Bollinger Bands, no extreme RSI")

            # Multi-timeframe confirmation (optional but recommended)
            if action != 'flat' and df_1h is not None and not df_1h.empty:
                latest_1h = df_1h.iloc[-1]
                rsi_1h = latest_1h.get('RSI', 50)

                if action == 'long' and rsi_1h < 50:
                    strength += 0.1
                    confidence = min(1.0, confidence + 0.1)
                    reasons.append(f"1h: RSI confirms oversold condition ({rsi_1h:.1f})")
                elif action == 'short' and rsi_1h > 50:
                    strength += 0.1
                    confidence = min(1.0, confidence + 0.1)
                    reasons.append(f"1h: RSI confirms overbought condition ({rsi_1h:.1f})")

            # Ensure strength and confidence are within bounds
            strength = min(1.0, max(0.0, strength))
            confidence = min(1.0, max(0.0, confidence))

            # Only return signal if strength meets minimum threshold
            if strength < self.min_strength:
                action = 'flat'
                reasons = [f"Signal strength too weak ({strength:.2f} < {self.min_strength})"]

            # Build the signal dictionary
            return {
                'action': action,
                'strength': strength,
                'confidence': confidence,
                'reasons': reasons,
                'indicators': {
                    'bb_upper': bb_upper,
                    'bb_middle': bb_middle,
                    'bb_lower': bb_lower,
                    'rsi': rsi,
                    'ema_9': ema_9,
                    'ema_21': ema_21,
                    'current_price': current_price
                },
                'metadata': {
                    'strategy': 'Bollinger Bands Mean Reversion',
                    'period': self.period,
                    'std_dev': self.std_dev
                }
            }

        except Exception as e:
            # Always handle errors gracefully
            return self._flat_signal(f"Analysis error: {str(e)}")

    def _flat_signal(self, reason: str) -> Dict:
        """
        Helper method to return a flat (no trade) signal

        Args:
            reason: Reason for no signal

        Returns:
            Flat signal dictionary
        """
        return {
            'action': 'flat',
            'strength': 0.0,
            'confidence': 0.0,
            'reasons': [reason],
            'indicators': {},
            'metadata': {}
        }
