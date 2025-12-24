"""
交易策略模块
提供多策略的实现，接收行情数据并生成交易信号
"""

import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
from config import config


class SignalType(Enum):
    """交易信号类型枚举"""
    NO_SIGNAL = "无信号"
    BUY_TO_OPEN = "买入开仓"
    SELL_TO_OPEN = "卖出开仓"
    BUY_TO_CLOSE = "买入平仓"
    SELL_TO_CLOSE = "卖出平仓"

@dataclass
class TradingSignal:
    """交易信号数据类"""
    signal_type: SignalType
    quantity: int
    price: float
    timestamp: str
    confidence: float = 1.0
    reason: str = ""
    deviation: float = 0.0  # 触发时的偏离度（用于均值回归策略）

    def __str__(self):
        if self.deviation != 0:
            return f"{self.signal_type.value} {self.quantity}张 @ {self.price:.4f} (偏离: {self.deviation:.2%})"
        else:
            return f"{self.signal_type.value} {self.quantity}张 @ {self.price:.4f} (置信度: {self.confidence:.2f})"


class StrategyBase(ABC):
    """策略基类，定义统一接口"""

    def __init__(self):
        self.current_position = 0  # 当前持仓数量
        self.last_signal_time = None
        self.last_signal = None
        self.trade_qty = config.TRADE_QTY

    @abstractmethod
    def analyze_market_data(self, market_data: Dict) -> Optional[TradingSignal]:
        """
        分析市场数据并生成交易信号

        Args:
            market_data: 市场数据字典

        Returns:
            TradingSignal或None如果没有信号
        """
        pass

    @abstractmethod
    def should_close_position(self, elapsed_time: float) -> Optional[TradingSignal]:
        """
        判断是否应该平仓

        Args:
            elapsed_time: 开仓后的经过时间（秒）

        Returns:
            平仓信号或None
        """
        pass

    def update_position(self, quantity: int, is_open: bool = True):
        """更新持仓信息"""
        if is_open:
            self.current_position += quantity
        else:
            self.current_position -= quantity
            if self.current_position < 0:
                self.current_position = 0

    def reset_strategy(self):
        """重置策略状态"""
        self.current_position = 0
        self.last_signal_time = None
        self.last_signal = None

    def get_strategy_status(self) -> Dict:
        """获取策略状态信息"""
        return {
            'current_position': self.current_position,
            'last_signal': self.last_signal.__dict__ if self.last_signal else None,
            'last_signal_time': self.last_signal_time,
            'trade_qty': self.trade_qty
        }

    def update_parameters(self, **kwargs):
        """更新策略参数"""
        if 'trade_qty' in kwargs:
            self.trade_qty = kwargs['trade_qty']

    def get_parameter_config(self) -> Dict:
        """获取策略参数配置（用于GUI参数面板）"""
        return {
            'trade_qty': {
                'name': '交易数量',
                'type': 'int',
                'default': 1,
                'min': 1,
                'max': 100,
                'step': 1,
                'description': '每次交易的合约数量'
            }
        }


class ArbitrageStrategy(StrategyBase):
    """双向套利策略实现 (原 TradingStrategy)"""

    def __init__(self):
        super().__init__()
        self.threshold = config.THRESHOLD
        self.signal_cooldown = 1.0  # 信号冷却时间（秒）

    def analyze_market_data(self, market_data: Dict) -> Optional[TradingSignal]:
        # 检查市场数据是否有效
        if not market_data.get('bid') or not market_data.get('ask'):
            return None

        # 检查价格历史是否准备就绪
        if not market_data.get('history_ready', False):
            return None

        # 检查是否有持仓（有持仓时不产生新信号）
        if self.current_position > 0:
            return None

        # 获取价格变化
        bid_change = market_data.get('bid_change', 0)
        ask_change = market_data.get('ask_change', 0)

        current_time = time.time()

        # 检查信号冷却时间
        if self.last_signal_time and (current_time - self.last_signal_time) < self.signal_cooldown:
            return None

        # 生成信号
        signal = None

        # 暴涨信号：卖价上涨超过阈值 -> 买入开仓
        if ask_change > self.threshold:
            signal = TradingSignal(
                signal_type=SignalType.BUY_TO_OPEN,
                quantity=self.trade_qty,
                price=market_data['ask'],
                timestamp=market_data['timestamp'],
                reason=f"卖价上涨 {ask_change:.2%} 超过阈值 {self.threshold:.2%}"
            )
            print(f"\n\n[!!!] 暴涨信号触发: {signal}")

        # 暴跌信号：买价下跌超过阈值 -> 卖出开仓
        elif bid_change < -self.threshold:
            signal = TradingSignal(
                signal_type=SignalType.SELL_TO_OPEN,
                quantity=self.trade_qty,
                price=market_data['bid'],
                timestamp=market_data['timestamp'],
                reason=f"买价下跌 {bid_change:.2%} 超过阈值 {self.threshold:.2%}"
            )
            print(f"\n\n[!!!] 暴跌信号触发: {signal}")

        if signal:
            self.last_signal = signal
            self.last_signal_time = current_time

        return signal

    def should_close_position(self, elapsed_time: float) -> Optional[TradingSignal]:
        if self.current_position <= 0:
            return None

        # 检查是否达到目标平仓时间
        if elapsed_time >= config.TARGET_INTERVAL_CLOSE:
            # 根据持仓方向生成平仓信号
            if self.last_signal and self.last_signal.signal_type == SignalType.BUY_TO_OPEN:
                return TradingSignal(
                    signal_type=SignalType.SELL_TO_CLOSE,
                    quantity=self.current_position,
                    price=0,  # 市价平仓，价格为0表示使用市价
                    timestamp=time.strftime("%H:%M:%S"),
                    reason=f"达到目标平仓时间 {config.TARGET_INTERVAL_CLOSE}s"
                )
            elif self.last_signal and self.last_signal.signal_type == SignalType.SELL_TO_OPEN:
                return TradingSignal(
                    signal_type=SignalType.BUY_TO_CLOSE,
                    quantity=self.current_position,
                    price=0,
                    timestamp=time.strftime("%H:%M:%S"),
                    reason=f"达到目标平仓时间 {config.TARGET_INTERVAL_CLOSE}s"
                )

        return None

    def get_strategy_status(self) -> Dict:
        status = super().get_strategy_status()
        status.update({
            'threshold': self.threshold,
            'signal_cooldown': self.signal_cooldown
        })
        return status

    def update_parameters(self, **kwargs):
        super().update_parameters(**kwargs)
        if 'threshold' in kwargs:
            self.threshold = kwargs['threshold']
            print(f"更新阈值: {self.threshold}")
        if 'signal_cooldown' in kwargs:
            self.signal_cooldown = kwargs['signal_cooldown']
            print(f"更新信号冷却时间: {self.signal_cooldown}s")

    def get_parameter_config(self) -> Dict:
        """获取策略参数配置（用于GUI参数面板）"""
        config = super().get_parameter_config()
        config.update({
            'threshold': {
                'name': '价格变化阈值',
                'type': 'float',
                'default': 0.01,
                'min': 0.001,
                'max': 0.1,
                'step': 0.001,
                'description': '触发交易信号的价格变化百分比阈值'
            },
            'signal_cooldown': {
                'name': '信号冷却时间',
                'type': 'float',
                'default': 1.0,
                'min': 0.1,
                'max': 60.0,
                'step': 0.1,
                'description': '两次交易信号之间的最小间隔时间（秒）'
            }
        })
        return config


class VolatilityStrategy(StrategyBase):
    """期权交易策略实现（基于波动率与时间价值的双向策略）"""

    def __init__(self):
        super().__init__()
        self.threshold = config.THRESHOLD  # 波动率变化阈值
        self.signal_cooldown = 1.0  # 信号冷却时间（秒）
        # 期权特有参数
        self.iv_upper_threshold = config.IV_UPPER_THRESHOLD  # 隐含波动率上限
        self.iv_lower_threshold = config.IV_LOWER_THRESHOLD  # 隐含波动率下限
        self.time_value_ratio = config.TIME_VALUE_RATIO  # 时间价值占比阈值
        
        # 实时数据缓存
        self.current_iv = 0
        self.current_time_value = 0
        self.open_time_value = 0

    def analyze_market_data(self, market_data: Dict) -> Optional[TradingSignal]:
        # 检查市场数据有效性（期权特有字段）
        required_fields = ['bid', 'ask', 'iv', 'iv_change', 'time_value', 'days_to_expiry', 'history_ready']
        if not all(field in market_data for field in required_fields):
            return None

        # 检查价格历史是否准备就绪
        if not market_data.get('history_ready', False):
            return None

        # 更新实时数据缓存
        self.current_iv = market_data['iv']
        self.current_time_value = market_data['time_value']

        # 检查是否有持仓（有持仓时不产生新信号）
        if self.current_position > 0:
            return None

        # 获取期权关键数据
        iv = market_data['iv']
        iv_change = market_data['iv_change']
        time_value = market_data['time_value']
        premium = (market_data['bid'] + market_data['ask']) / 2
        time_value_ratio = time_value / premium if premium != 0 else 0
        days_to_expiry = market_data['days_to_expiry']

        current_time = time.time()

        # 检查信号冷却时间
        if self.last_signal_time and (current_time - self.last_signal_time) < self.signal_cooldown:
            return None

        # 生成信号
        signal = None

        # 低波动率买入策略
        if (iv < self.iv_lower_threshold and
                iv_change > -self.threshold and
                time_value_ratio < self.time_value_ratio and
                days_to_expiry > 10):

            if market_data.get('underlying_trend') == 'up':
                signal = TradingSignal(
                    signal_type=SignalType.BUY_TO_OPEN,
                    quantity=self.trade_qty,
                    price=market_data['ask'],
                    timestamp=market_data['timestamp'],
                    reason=f"低波动率买入看涨期权（IV: {iv:.2f}, 时间价值占比: {time_value_ratio:.2%}）"
                )
            elif market_data.get('underlying_trend') == 'down':
                signal = TradingSignal(
                    signal_type=SignalType.BUY_TO_OPEN,
                    quantity=self.trade_qty,
                    price=market_data['ask'],
                    timestamp=market_data['timestamp'],
                    reason=f"低波动率买入看跌期权（IV: {iv:.2f}, 时间价值占比: {time_value_ratio:.2%}）"
                )

        # 高波动率卖出策略
        elif (iv > self.iv_upper_threshold and
              iv_change < self.threshold and
              days_to_expiry > 5):

            if market_data.get('underlying_trend') == 'down':
                signal = TradingSignal(
                    signal_type=SignalType.SELL_TO_OPEN,
                    quantity=self.trade_qty,
                    price=market_data['bid'],
                    timestamp=market_data['timestamp'],
                    reason=f"高波动率卖出看涨期权（IV: {iv:.2f}, 时间价值占比: {time_value_ratio:.2%}）"
                )
            elif market_data.get('underlying_trend') == 'up':
                signal = TradingSignal(
                    signal_type=SignalType.SELL_TO_OPEN,
                    quantity=self.trade_qty,
                    price=market_data['bid'],
                    timestamp=market_data['timestamp'],
                    reason=f"高波动率卖出看跌期权（IV: {iv:.2f}, 时间价值占比: {time_value_ratio:.2%}）"
                )

        if signal:
            self.last_signal = signal
            self.last_signal_time = current_time
            self.open_time_value = self.current_time_value
            print(f"\n\n[!!!] 波动率信号触发: {signal}")

        return signal

    def should_close_position(self, elapsed_time: float) -> Optional[TradingSignal]:
        if self.current_position <= 0 or not self.last_signal:
            return None

        # 1. 买入开仓的平仓条件
        if self.last_signal.signal_type == SignalType.BUY_TO_OPEN:
            # 波动率回归
            if self.current_iv >= self.iv_lower_threshold + (self.iv_upper_threshold - self.iv_lower_threshold) * 0.5:
                return TradingSignal(
                    signal_type=SignalType.SELL_TO_CLOSE,
                    quantity=self.current_position,
                    price=0,
                    timestamp=time.strftime("%H:%M:%S"),
                    reason=f"波动率回归（当前IV: {self.current_iv:.2f}）"
                )
            # 时间价值衰减达标
            if self.open_time_value > 0 and (self.open_time_value - self.current_time_value) / self.open_time_value > 0.5:
                return TradingSignal(
                    signal_type=SignalType.SELL_TO_CLOSE,
                    quantity=self.current_position,
                    price=0,
                    timestamp=time.strftime("%H:%M:%S"),
                    reason=f"时间价值衰减超过50%"
                )

        # 2. 卖出开仓的平仓条件
        elif self.last_signal.signal_type == SignalType.SELL_TO_OPEN:
            # 波动率从高位回落
            if self.current_iv <= self.iv_upper_threshold - (self.iv_upper_threshold - self.iv_lower_threshold) * 0.3:
                return TradingSignal(
                    signal_type=SignalType.BUY_TO_CLOSE,
                    quantity=self.current_position,
                    price=0,
                    timestamp=time.strftime("%H:%M:%S"),
                    reason=f"波动率回落（当前IV: {self.current_iv:.2f}）"
                )
            # 达到最大持仓时间
            if elapsed_time >= config.MAX_HOLDING_TIME:
                return TradingSignal(
                    signal_type=SignalType.BUY_TO_CLOSE,
                    quantity=self.current_position,
                    price=0,
                    timestamp=time.strftime("%H:%M:%S"),
                    reason=f"达到最大持仓时间 {config.MAX_HOLDING_TIME}s"
                )

        return None

    def get_strategy_status(self) -> Dict:
        status = super().get_strategy_status()
        status.update({
            'iv_upper_threshold': self.iv_upper_threshold,
            'iv_lower_threshold': self.iv_lower_threshold,
            'time_value_ratio': self.time_value_ratio,
            'current_iv': self.current_iv
        })
        return status

    def update_parameters(self, **kwargs):
        super().update_parameters(**kwargs)
        if 'iv_upper_threshold' in kwargs:
            self.iv_upper_threshold = kwargs['iv_upper_threshold']
        if 'iv_lower_threshold' in kwargs:
            self.iv_lower_threshold = kwargs['iv_lower_threshold']
        if 'time_value_ratio' in kwargs:
            self.time_value_ratio = kwargs['time_value_ratio']

    def get_parameter_config(self) -> Dict:
        """获取策略参数配置"""
        config = super().get_parameter_config()
        config.update({
            'iv_upper_threshold': {
                'name': 'IV 上限',
                'type': 'float',
                'default': 0.35,
                'min': 0.1,
                'max': 1.0,
                'step': 0.01,
                'description': '隐含波动率上限，超过此值触发卖出开仓'
            },
            'iv_lower_threshold': {
                'name': 'IV 下限',
                'type': 'float',
                'default': 0.15,
                'min': 0.05,
                'max': 0.5,
                'step': 0.01,
                'description': '隐含波动率下限，低于此值触发买入开仓'
            },
            'time_value_ratio': {
                'name': '时间价值占比',
                'type': 'float',
                'default': 0.8,
                'min': 0.1,
                'max': 1.0,
                'step': 0.05,
                'description': '期权时间价值占总溢价的最小比例'
            }
        })
        return config

class SpreadArbitrageStrategy(StrategyBase):
    """价差套利策略实现 (原 spread_arbitrage_module.py 中的 TradingStrategy)"""

    def __init__(self):
        super().__init__()
        self.threshold = config.THRESHOLD
        self.signal_cooldown = 1.0
        self.spread_threshold_open = 0.002  # 开仓价差阈值
        self.spread_threshold_close = 0.0005  # 平仓价差阈值
        self.min_hold_time = 5  # 最小持仓时间（秒）
        self.max_hold_time = 300  # 最大持仓时间（秒）
        self.trade_qty = config.TRADE_QTY
        
        # 价格历史数据
        self.bid_prices = []
        self.ask_prices = []
        self.position_info = {}
        self.last_signal_time = None
        self.entry_time = None
        self.relative_spread = 0.0
        self.spread_history = []

    def analyze_market_data(self, market_data: Dict) -> Optional[TradingSignal]:
        """分析市场数据并生成交易信号"""
        # 检查市场数据是否有效
        if not market_data.get('bid') or not market_data.get('ask'):
            return None

        # 检查价格历史是否准备就绪
        if not market_data.get('history_ready', False):
            return None

        # 检查是否有持仓（有持仓时不产生新信号）
        if self.current_position > 0:
            return None

        # 获取当前价格
        current_bid = market_data['bid']
        current_ask = market_data['ask']

        # 更新价格历史
        self.bid_prices.append(current_bid)
        self.ask_prices.append(current_ask)

        # 保持固定长度的价格历史
        max_history = 100
        if len(self.bid_prices) > max_history:
            self.bid_prices = self.bid_prices[-max_history:]
        if len(self.ask_prices) > max_history:
            self.ask_prices = self.ask_prices[-max_history:]

        # 检查信号冷却时间
        current_time = time.time()
        if self.last_signal_time and (current_time - self.last_signal_time) < self.signal_cooldown:
            return None

        # 计算相对价差
        self.relative_spread = self._calculate_relative_spread()
        
        # 平滑价差以减少噪音
        smoothed_spread = self._smooth_spread(self.relative_spread)
        
        # 检查开仓信号
        signal = self._check_open_signal(current_bid, current_ask, smoothed_spread)
        
        if signal:
            self.last_signal = signal
            self.last_signal_time = current_time
            print(f"\n[价差套利] 信号触发: {signal}")
        
        return signal

    def should_close_position(self, elapsed_time: float) -> Optional[TradingSignal]:
        """判断是否应该平仓"""
        if self.current_position <= 0:
            return None

        # 检查最小持仓时间
        if elapsed_time < self.min_hold_time:
            return None

        # 计算当前价差
        current_spread = self.relative_spread
        
        # 检查平仓条件
        signal = None
        
        # 价差收敛平仓
        if abs(current_spread) < self.spread_threshold_close:
            if self.last_signal.signal_type == SignalType.BUY_TO_OPEN:
                signal = TradingSignal(
                    signal_type=SignalType.SELL_TO_CLOSE,
                    quantity=self.current_position,
                    price=0,  # 市价平仓
                    timestamp=time.strftime("%H:%M:%S"),
                    reason=f"价差收敛平仓 (价差: {current_spread:.4f})"
                )
            elif self.last_signal.signal_type == SignalType.SELL_TO_OPEN:
                signal = TradingSignal(
                    signal_type=SignalType.BUY_TO_CLOSE,
                    quantity=self.current_position,
                    price=0,
                    timestamp=time.strftime("%H:%M:%S"),
                    reason=f"价差收敛平仓 (价差: {current_spread:.4f})"
                )
        
        # 超时平仓
        elif elapsed_time > self.max_hold_time:
            if self.last_signal.signal_type == SignalType.BUY_TO_OPEN:
                signal = TradingSignal(
                    signal_type=SignalType.SELL_TO_CLOSE,
                    quantity=self.current_position,
                    price=0,
                    timestamp=time.strftime("%H:%M:%S"),
                    reason=f"超时平仓 (持仓时间: {elapsed_time:.1f}s)"
                )
            elif self.last_signal.signal_type == SignalType.SELL_TO_OPEN:
                signal = TradingSignal(
                    signal_type=SignalType.BUY_TO_CLOSE,
                    quantity=self.current_position,
                    price=0,
                    timestamp=time.strftime("%H:%M:%S"),
                    reason=f"超时平仓 (持仓时间: {elapsed_time:.1f}s)"
                )
        
        return signal

    def _calculate_relative_spread(self) -> float:
        """计算相对价差"""
        if len(self.bid_prices) < 2 or len(self.ask_prices) < 2:
            return 0.0
        
        # 使用最新的买卖价计算相对价差
        current_mid = (self.bid_prices[-1] + self.ask_prices[-1]) / 2
        if current_mid == 0:
            return 0.0
        
        relative_spread = (self.ask_prices[-1] - self.bid_prices[-1]) / current_mid
        return relative_spread

    def _smooth_spread(self, spread: float, window: int = 5) -> float:
        """平滑价差数据"""
        self.spread_history.append(spread)
        
        # 保持固定长度的历史
        if len(self.spread_history) > window:
            self.spread_history = self.spread_history[-window:]
        
        # 计算移动平均
        if len(self.spread_history) > 0:
            return sum(self.spread_history) / len(self.spread_history)
        return spread

    def _check_open_signal(self, bid: float, ask: float, spread: float) -> Optional[TradingSignal]:
        """检查开仓信号"""
        signal = None
        
        # 价差过大时卖出开仓（认为价格被高估）
        if spread > self.spread_threshold_open:
            signal = TradingSignal(
                signal_type=SignalType.SELL_TO_OPEN,
                quantity=self.trade_qty,
                price=bid,
                timestamp=time.strftime("%H:%M:%S"),
                reason=f"价差过大卖出开仓 (价差: {spread:.4f})"
            )
        
        # 价差过小时买入开仓（认为价格被低估）
        elif spread < -self.spread_threshold_open:
            signal = TradingSignal(
                signal_type=SignalType.BUY_TO_OPEN,
                quantity=self.trade_qty,
                price=ask,
                timestamp=time.strftime("%H:%M:%S"),
                reason=f"价差过小买入开仓 (价差: {spread:.4f})"
            )
        
        return signal

    def get_strategy_status(self) -> Dict:
        """获取策略状态信息"""
        status = super().get_strategy_status()
        status.update({
            'threshold': self.threshold,
            'signal_cooldown': self.signal_cooldown,
            'spread_threshold_open': self.spread_threshold_open,
            'spread_threshold_close': self.spread_threshold_close,
            'min_hold_time': self.min_hold_time,
            'max_hold_time': self.max_hold_time,
            'relative_spread': self.relative_spread,
            'position_info': self.position_info
        })
        return status

    def update_parameters(self, **kwargs):
        """更新策略参数"""
        super().update_parameters(**kwargs)
        if 'spread_threshold_open' in kwargs:
            self.spread_threshold_open = kwargs['spread_threshold_open']
        if 'spread_threshold_close' in kwargs:
            self.spread_threshold_close = kwargs['spread_threshold_close']
        if 'min_hold_time' in kwargs:
            self.min_hold_time = kwargs['min_hold_time']
        if 'max_hold_time' in kwargs:
            self.max_hold_time = kwargs['max_hold_time']

    def get_parameter_config(self) -> Dict:
        """获取策略参数配置"""
        config = super().get_parameter_config()
        config.update({
            'spread_threshold_open': {
                'name': '开仓价差阈值',
                'type': 'float',
                'default': 0.002,
                'min': 0.0001,
                'max': 0.01,
                'step': 0.0001,
                'description': '触发开仓的相对价差百分比阈值'
            },
            'spread_threshold_close': {
                'name': '平仓价差阈值',
                'type': 'float',
                'default': 0.0005,
                'min': 0.0,
                'max': 0.005,
                'step': 0.0001,
                'description': '触发平仓的相对价差百分比阈值'
            },
            'min_hold_time': {
                'name': '最小持仓时间',
                'type': 'int',
                'default': 5,
                'min': 1,
                'max': 60,
                'step': 1,
                'suffix': 's',
                'description': '开仓后的最小等待平仓时间（秒）'
            },
            'max_hold_time': {
                'name': '最大持仓时间',
                'type': 'int',
                'default': 300,
                'min': 30,
                'max': 3600,
                'step': 30,
                'suffix': 's',
                'description': '开仓后的强制平仓时间限制（秒）'
            }
        })
        return config


class MeanReversionStrategy(StrategyBase):
    """均值回归策略实现 (原 strategy_mean_reversion.py)"""

    def __init__(self):
        super().__init__()
        self.window_size = 20  # 移动平均窗口大小
        self.threshold = 0.003  # 偏离度触发阈值 (0.3%)
        self.stop_loss_pct = 0.01  # 止损百分比 (1%)
        self.reversion_target = 0.0005  # 回归目标阈值 (0.05%)
        self.trade_qty = config.TRADE_QTY
        self.signal_cooldown = 1.0  # 信号冷却时间（秒）
        self.contract_multiplier = 10000  # 合约乘数
        
        # 价格历史队列
        import collections
        self.price_queue = collections.deque(maxlen=self.window_size)
        
        # 持仓信息
        self.position_direction = ""  # "Long" 或 "Short"
        self.entry_price = 0.0
        self.entry_avg = 0.0
        self.entry_deviation = 0.0
        self.entry_time = ""
        
        # 策略状态
        self.moving_average = 0.0
        self.current_deviation = 0.0
        self.is_warming_up = True
        
        # 统计信息
        self.cumulative_profit = 0.0
        self.trade_count = 0

    def analyze_market_data(self, market_data: Dict) -> Optional[TradingSignal]:
        """分析市场数据并生成开仓信号"""
        # 检查市场数据是否有效
        mid_price = market_data.get('mid')
        if not mid_price:
            return None

        # 更新价格并计算指标
        result = self._update_price(mid_price, market_data.get('timestamp', ''))
        
        # 预热阶段不产生信号
        if result['warming_up']:
            return None
        
        # 已有持仓时不产生新的开仓信号
        if self.current_position > 0:
            return None
        
        # 检查信号冷却时间
        current_time = time.time()
        if self.last_signal_time and (current_time - self.last_signal_time) < self.signal_cooldown:
            return None
        
        signal = None
        deviation = self.current_deviation
        
        # 价格低于均值，做多回归
        if deviation < -self.threshold:
            signal = TradingSignal(
                signal_type=SignalType.BUY_TO_OPEN,
                quantity=self.trade_qty,
                price=market_data.get('ask', mid_price),
                timestamp=market_data.get('timestamp', time.strftime("%H:%M:%S")),
                confidence=min(abs(deviation) / self.threshold, 2.0),  # 偏离越大置信度越高
                reason=f"价格低于均值 {deviation*100:.2f}%，触发做多信号",
                deviation=deviation
            )
            print(f"\n[均值回归] 做多信号触发: {signal}")
        
        # 价格高于均值，做空回归
        elif deviation > self.threshold:
            signal = TradingSignal(
                signal_type=SignalType.SELL_TO_OPEN,
                quantity=self.trade_qty,
                price=market_data.get('bid', mid_price),
                timestamp=market_data.get('timestamp', time.strftime("%H:%M:%S")),
                confidence=min(abs(deviation) / self.threshold, 2.0),
                reason=f"价格高于均值 {deviation*100:.2f}%，触发做空信号",
                deviation=deviation
            )
            print(f"\n[均值回归] 做空信号触发: {signal}")
        
        if signal:
            self.last_signal = signal
            self.last_signal_time = current_time
        
        return signal

    def should_close_position(self, elapsed_time: float) -> Optional[TradingSignal]:
        """判断是否应该平仓"""
        if self.current_position <= 0:
            return None

        # 获取当前价格（需要从外部传入）
        # 这里假设能通过某种方式获取当前价格，实际使用时需要调整
        current_mid = 0.0  # 占位符，实际使用时需要从市场数据获取
        
        # 计算当前偏离度
        current_deviation = (current_mid - self.moving_average) / self.moving_average if self.moving_average > 0 else 0
        
        # 计算持仓盈亏比例
        if self.position_direction == "Long":
            pnl_ratio = (current_mid - self.entry_price) / self.entry_price
        else:
            pnl_ratio = (self.entry_price - current_mid) / self.entry_price
        
        exit_reason = None
        signal_type = None
        
        # 判断离场条件
        # 1. 回归均值 (偏离度小于目标阈值)
        if abs(current_deviation) < self.reversion_target:
            exit_reason = "回归均值"
        # 2. 止损
        elif pnl_ratio < -self.stop_loss_pct:
            exit_reason = "止损离场"
        
        if exit_reason:
            # 根据持仓方向确定平仓类型
            if self.position_direction == "Long":
                signal_type = SignalType.SELL_TO_CLOSE
            else:
                signal_type = SignalType.BUY_TO_CLOSE
            
            return TradingSignal(
                signal_type=signal_type,
                quantity=self.current_position,
                price=current_mid,
                timestamp=time.strftime("%H:%M:%S"),
                reason=exit_reason,
                deviation=current_deviation
            )
        
        return None

    def _update_price(self, mid_price: float, timestamp: str) -> Dict:
        """更新价格数据并计算指标"""
        self.price_queue.append(mid_price)
        
        # 检查是否完成预热
        if len(self.price_queue) < self.window_size:
            self.is_warming_up = True
            return {
                'warming_up': True,
                'progress': len(self.price_queue),
                'target': self.window_size,
                'moving_average': 0,
                'deviation': 0
            }
        
        self.is_warming_up = False
        
        # 计算移动平均
        self.moving_average = sum(self.price_queue) / self.window_size
        
        # 计算偏离度
        self.current_deviation = (mid_price - self.moving_average) / self.moving_average
        
        return {
            'warming_up': False,
            'progress': self.window_size,
            'target': self.window_size,
            'moving_average': self.moving_average,
            'deviation': self.current_deviation,
            'deviation_pct': self.current_deviation * 100
        }

    def get_strategy_status(self) -> Dict:
        """获取策略状态信息"""
        status = super().get_strategy_status()
        status.update({
            'strategy_name': '均值回归策略',
            'window_size': self.window_size,
            'threshold': self.threshold,
            'stop_loss_pct': self.stop_loss_pct,
            'reversion_target': self.reversion_target,
            'is_warming_up': self.is_warming_up,
            'warmup_progress': len(self.price_queue),
            'moving_average': self.moving_average,
            'current_deviation': self.current_deviation,
            'position_direction': self.position_direction,
            'entry_price': self.entry_price,
            'cumulative_profit': self.cumulative_profit,
            'trade_count': self.trade_count
        })
        return status

    def update_parameters(self, **kwargs):
        """更新策略参数"""
        super().update_parameters(**kwargs)
        if 'window_size' in kwargs:
            new_size = kwargs['window_size']
            self.window_size = new_size
            # 需要创建新的队列以适应新的窗口大小
            import collections
            old_prices = list(self.price_queue)
            self.price_queue = collections.deque(old_prices[-new_size:], maxlen=new_size)
            print(f"更新移动窗口: {new_size}")

        if 'threshold' in kwargs:
            self.threshold = kwargs['threshold']
            print(f"更新偏离阈值: {self.threshold:.2%}")

        if 'stop_loss_pct' in kwargs:
            self.stop_loss_pct = kwargs['stop_loss_pct']
            print(f"更新止损百分比: {self.stop_loss_pct:.2%}")

        if 'reversion_target' in kwargs:
            self.reversion_target = kwargs['reversion_target']
            print(f"更新回归目标: {self.reversion_target:.2%}")

    def get_parameter_config(self) -> Dict:
        """获取策略参数配置"""
        config = super().get_parameter_config()
        config.update({
            'window_size': {
                'name': '移动平均窗口',
                'type': 'int',
                'default': 20,
                'min': 5,
                'max': 200,
                'step': 1,
                'description': '计算移动平均的价格历史窗口大小'
            },
            'threshold': {
                'name': '偏离度阈值',
                'type': 'float',
                'default': 0.003,
                'min': 0.001,
                'max': 0.02,
                'step': 0.0001,
                'description': '触发开仓信号的价格偏离均值阈值（百分比）'
            },
            'stop_loss_pct': {
                'name': '止损百分比',
                'type': 'float',
                'default': 0.01,
                'min': 0.001,
                'max': 0.05,
                'step': 0.001,
                'description': '价格反向运行触发止损的比例'
            },
            'reversion_target': {
                'name': '回归目标',
                'type': 'float',
                'default': 0.0005,
                'min': 0.0,
                'max': 0.002,
                'step': 0.0001,
                'description': '平仓目标：价格偏离均值小于此阈值时平仓'
            }
        })
        return config

# 为了保持向后兼容，保留 TradingStrategy 名称指向 ArbitrageStrategy
TradingStrategy = ArbitrageStrategy