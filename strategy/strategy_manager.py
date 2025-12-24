"""
策略管理器模块
统一管理所有交易策略，支持策略的启用/禁用、切换和状态追踪
"""

import threading
import time
from typing import Dict, List, Optional, Type, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import uuid

from database import get_database
from strategy.trading_strategy import (
    StrategyBase, TradingSignal, SignalType, 
    ArbitrageStrategy, VolatilityStrategy, 
    SpreadArbitrageStrategy, MeanReversionStrategy
)


class StrategyState(Enum):
    """策略状态枚举"""
    IDLE = "空闲"
    RUNNING = "运行中"
    PAUSED = "暂停"
    ERROR = "错误"


@dataclass
class StrategyRuntime:
    """策略运行时信息"""
    strategy: StrategyBase
    enabled: bool = False
    state: StrategyState = StrategyState.IDLE
    priority: int = 0
    signal_count: int = 0
    trade_count: int = 0
    last_signal_time: float = 0
    total_pnl: float = 0
    error_message: str = ""

    def reset_statistics(self):
        """重置统计信息"""
        self.signal_count = 0
        self.trade_count = 0
        self.last_signal_time = 0
        self.total_pnl = 0
        self.error_message = ""


class StrategyManager:
    """
    策略管理器
    管理所有交易策略的生命周期，包括注册、启用、禁用、切换等
    """

    def __init__(self):
        # 策略注册表: {strategy_name: StrategyRuntime}
        self._strategies: Dict[str, StrategyRuntime] = {}

        # 策略优先级队列（已启用的策略按优先级排序）
        self._enabled_strategies: List[str] = []

        # 当前活跃策略
        self._active_strategy: Optional[str] = None

        # 线程锁
        self._lock = threading.RLock()

        # 数据库
        self._db = get_database()

        # 回调函数
        self._on_signal_generated: Optional[Callable[[str, TradingSignal], None]] = None
        self._on_strategy_error: Optional[Callable[[str, str], None]] = None

        # 初始化数据库中的策略配置
        self._init_database_strategies()

    def _init_database_strategies(self):
        """从数据库初始化策略配置"""
        # 注册内置策略
        self.register_strategy(
            name="双向套利",
            strategy_class="ArbitrageStrategy",
            description="基于价格暴涨暴跌的双向套利策略",
            priority=1
        )

        self.register_strategy(
            name="波动率策略",
            strategy_class="VolatilityStrategy",
            description="基于隐含波动率和时间价值的期权策略",
            priority=2
        )

        self.register_strategy(
            name="价差套利",
            strategy_class="SpreadArbitrageStrategy",
            description="基于买卖价差收敛的套利策略",
            priority=3
        )

        self.register_strategy(
            name="均值回归",
            strategy_class="MeanReversionStrategy",
            description="基于价格均值回归的交易策略",
            priority=4
        )

        # 从数据库加载启用状态
        all_strategies = self._db.get_all_strategies()
        for strategy_info in all_strategies:
            name = strategy_info['strategy_name']
            if name in self._strategies:
                if strategy_info['enabled']:
                    self.enable_strategy(name, load_from_db=True)

    def register_strategy(self, name: str, strategy_class: str,
                          description: str = "", priority: int = 0,
                          strategy_instance: StrategyBase = None) -> bool:
        """
        注册策略

        Args:
            name: 策略名称
            strategy_class: 策略类名
            description: 策略描述
            priority: 优先级（数字越小优先级越高）
            strategy_instance: 策略实例（可选）

        Returns:
            是否成功
        """
        with self._lock:
            # 如果已存在，更新信息
            if name in self._strategies:
                runtime = self._strategies[name]
                runtime.priority = priority
            else:
                # 创建策略实例
                if strategy_instance is None:
                    # 动态导入策略类
                    try:
                        strategy_map = {
                            "ArbitrageStrategy": ArbitrageStrategy,
                            "VolatilityStrategy": VolatilityStrategy,
                            "SpreadArbitrageStrategy": SpreadArbitrageStrategy,
                            "MeanReversionStrategy": MeanReversionStrategy
                        }

                        if strategy_class in strategy_map:
                            strategy_instance = strategy_map[strategy_class]()
                        else:
                            # 默认使用ArbitrageStrategy
                            strategy_instance = ArbitrageStrategy()
                    except Exception as e:
                        print(f"创建策略实例失败: {e}")
                        return False

                runtime = StrategyRuntime(
                    strategy=strategy_instance,
                    enabled=False,
                    priority=priority
                )
                self._strategies[name] = runtime

            # 注册到数据库
            self._db.register_strategy(name, strategy_class, description, priority)

            # 重新排序启用策略列表
            self._sort_enabled_strategies()

            return True

    def enable_strategy(self, name: str, load_from_db: bool = False) -> bool:
        """
        启用策略

        Args:
            name: 策略名称
            load_from_db: 是否从数据库加载

        Returns:
            是否成功
        """
        with self._lock:
            if name not in self._strategies:
                return False

            runtime = self._strategies[name]

            # 重置策略状态
            runtime.enabled = True
            runtime.state = StrategyState.IDLE
            runtime.strategy.reset_strategy()

            # 添加到启用列表
            if name not in self._enabled_strategies:
                self._enabled_strategies.append(name)

            # 重新排序
            self._sort_enabled_strategies()

            # 更新数据库
            if not load_from_db:
                self._db.set_strategy_enabled(name, True)

            # 如果是第一个启用的策略，设为活跃策略
            if self._active_strategy is None:
                self._active_strategy = name

            return True

    def disable_strategy(self, name: str) -> bool:
        """
        禁用策略

        Args:
            name: 策略名称

        Returns:
            是否成功
        """
        with self._lock:
            if name not in self._strategies:
                return False

            runtime = self._strategies[name]
            runtime.enabled = False
            runtime.state = StrategyState.IDLE

            # 从启用列表移除
            if name in self._enabled_strategies:
                self._enabled_strategies.remove(name)

            # 更新数据库
            self._db.set_strategy_enabled(name, False)

            # 如果禁用的是活跃策略，切换到下一个
            if self._active_strategy == name:
                if self._enabled_strategies:
                    self._active_strategy = self._enabled_strategies[0]
                else:
                    self._active_strategy = None

            return True

    def enable_all_strategies(self) -> bool:
        """启用所有策略"""
        with self._lock:
            for name in self._strategies:
                self.enable_strategy(name)
            return True

    def disable_all_strategies(self) -> bool:
        """禁用所有策略"""
        with self._lock:
            # 清空启用列表
            self._enabled_strategies.clear()
            self._active_strategy = None

            # 更新所有策略状态
            for name, runtime in self._strategies.items():
                runtime.enabled = False
                runtime.state = StrategyState.IDLE
                runtime.strategy.reset_strategy()

            # 更新数据库
            self._db.disable_all_strategies()

            return True

    def is_strategy_enabled(self, name: str) -> bool:
        """检查策略是否启用"""
        with self._lock:
            runtime = self._strategies.get(name)
            return runtime is not None and runtime.enabled

    def get_enabled_strategies(self) -> List[str]:
        """获取所有启用的策略名称列表"""
        with self._lock:
            return self._enabled_strategies.copy()

    def get_all_strategies(self) -> List[Dict]:
        """获取所有策略信息"""
        with self._lock:
            result = []
            for name, runtime in self._strategies.items():
                # 确保所有值都不是None
                result.append({
                    'name': name or "未知策略",
                    'enabled': bool(runtime.enabled) if runtime.enabled is not None else False,
                    'state': runtime.state.value if runtime.state else "IDLE",
                    'priority': int(runtime.priority) if runtime.priority is not None else 0,
                    'signal_count': int(runtime.signal_count) if runtime.signal_count is not None else 0,
                    'trade_count': int(runtime.trade_count) if runtime.trade_count is not None else 0,
                    'total_pnl': float(runtime.total_pnl) if runtime.total_pnl is not None else 0.0
                })
            return result

    def get_strategy_parameter_config(self, strategy_name: str) -> Optional[Dict]:
        """获取指定策略的参数配置"""
        with self._lock:
            runtime = self._strategies.get(strategy_name)
            if runtime and runtime.strategy:
                try:
                    return runtime.strategy.get_parameter_config()
                except Exception as e:
                    print(f"获取策略 {strategy_name} 参数配置失败: {e}")
                    return None
            return None

    def update_strategy_parameters(self, strategy_name: str, **parameters) -> bool:
        """更新指定策略的参数"""
        with self._lock:
            runtime = self._strategies.get(strategy_name)
            if runtime and runtime.strategy:
                try:
                    runtime.strategy.update_parameters(**parameters)
                    # 保存到数据库
                    self._db.save_strategy_parameters(strategy_name, parameters)
                    print(f"策略 {strategy_name} 参数更新成功: {parameters}")
                    return True
                except Exception as e:
                    print(f"更新策略 {strategy_name} 参数失败: {e}")
                    return False
            return False

    def get_strategy_info(self, name: str) -> Optional[Dict]:
        """获取指定策略信息"""
        with self._lock:
            runtime = self._strategies.get(name)
            if runtime is None:
                return None

            # 获取策略状态
            strategy_status = runtime.strategy.get_strategy_status() if runtime.strategy else {}

            return {
                'name': name or "未知策略",
                'enabled': bool(runtime.enabled) if runtime.enabled is not None else False,
                'state': runtime.state.value if runtime.state else "IDLE",
                'priority': int(runtime.priority) if runtime.priority is not None else 0,
                'signal_count': int(runtime.signal_count) if runtime.signal_count is not None else 0,
                'trade_count': int(runtime.trade_count) if runtime.trade_count is not None else 0,
                'total_pnl': float(runtime.total_pnl) if runtime.total_pnl is not None else 0.0,
                'last_signal_time': float(runtime.last_signal_time) if runtime.last_signal_time is not None else 0.0,
                'strategy_status': strategy_status or {},
                'error_message': runtime.error_message or ""
            }

    def get_active_strategy(self) -> Optional[str]:
        """获取当前活跃策略"""
        with self._lock:
            return self._active_strategy

    def set_active_strategy(self, name: str) -> bool:
        """
        设置活跃策略

        Args:
            name: 策略名称

        Returns:
            是否成功
        """
        with self._lock:
            if name not in self._enabled_strategies:
                return False

            # 重置之前的活跃策略
            if self._active_strategy and self._active_strategy != name:
                old_runtime = self._strategies[self._active_strategy]
                old_runtime.state = StrategyState.IDLE

            # 设置新的活跃策略
            self._active_strategy = name
            runtime = self._strategies[name]
            runtime.state = StrategyState.RUNNING

            return True

    def analyze_market_data(self, market_data: Dict) -> Optional[TradingSignal]:
        """
        使用活跃策略分析市场数据

        Args:
            market_data: 市场数据

        Returns:
            交易信号或None
        """
        with self._lock:
            # 如果没有活跃策略或没有启用策略，返回None
            if not self._active_strategy:
                return None

            runtime = self._strategies.get(self._active_strategy)
            if not runtime or not runtime.enabled:
                return None

            try:
                # 使用策略分析市场数据
                signal = runtime.strategy.analyze_market_data(market_data)

                if signal:
                    runtime.signal_count += 1
                    runtime.last_signal_time = time.time()

                    # 触发回调
                    if self._on_signal_generated:
                        self._on_signal_generated(self._active_strategy, signal)

                return signal

            except Exception as e:
                runtime.state = StrategyState.ERROR
                runtime.error_message = str(e)

                if self._on_strategy_error:
                    self._on_strategy_error(self._active_strategy, str(e))

                return None

    def should_close_position(self, elapsed_time: float) -> Optional[TradingSignal]:
        """
        判断是否应该平仓

        Args:
            elapsed_time: 开仓后的经过时间（秒）

        Returns:
            平仓信号或None
        """
        with self._lock:
            if not self._active_strategy:
                return None

            runtime = self._strategies.get(self._active_strategy)
            if not runtime or not runtime.enabled:
                return None

            try:
                return runtime.strategy.should_close_position(elapsed_time)
            except Exception as e:
                runtime.state = StrategyState.ERROR
                runtime.error_message = str(e)
                return None

    def update_position(self, quantity: int, is_open: bool = True):
        """更新活跃策略的持仓信息"""
        with self._lock:
            if not self._active_strategy:
                return

            runtime = self._strategies.get(self._active_strategy)
            if runtime:
                runtime.strategy.update_position(quantity, is_open)
                if is_open:
                    runtime.trade_count += 1

    def update_pnl(self, pnl: float, strategy_name: str = None):
        """更新策略盈亏"""
        with self._lock:
            name = strategy_name or self._active_strategy
            if not name:
                return

            runtime = self._strategies.get(name)
            if runtime:
                runtime.total_pnl += pnl

    def update_strategy_parameters(self, name: str, **kwargs):
        """更新策略参数"""
        with self._lock:
            if name not in self._strategies:
                return False

            runtime = self._strategies[name]
            try:
                # 更新内存中的参数
                runtime.strategy.update_parameters(**kwargs)
                
                # 更新数据库中的参数
                self._db.update_strategy_parameters(name, kwargs)
                
                print(f"策略 {name} 参数更新成功: {kwargs}")
                return True
            except Exception as e:
                print(f"更新策略 {name} 参数失败: {e}")
                return False

    def get_strategy_parameter_config(self, name: str) -> Dict:
        """获取策略参数配置"""
        with self._lock:
            runtime = self._strategies.get(name)
            if runtime and runtime.strategy:
                return runtime.strategy.get_parameter_config()
            return {}

    def get_active_strategy_instance(self) -> Optional[StrategyBase]:
        """获取活跃策略的实例"""
        with self._lock:
            if not self._active_strategy:
                return None

            runtime = self._strategies.get(self._active_strategy)
            return runtime.strategy if runtime else None

    def get_strategy_instance(self, name: str) -> Optional[StrategyBase]:
        """获取指定策略的实例"""
        with self._lock:
            runtime = self._strategies.get(name)
            return runtime.strategy if runtime else None

    def reset_strategy(self, name: str):
        """重置策略状态"""
        with self._lock:
            if name not in self._strategies:
                return

            runtime = self._strategies[name]
            runtime.strategy.reset_strategy()
            runtime.reset_statistics()
            runtime.state = StrategyState.IDLE

    def reset_all_strategies(self):
        """重置所有策略状态"""
        with self._lock:
            for name, runtime in self._strategies.items():
                runtime.strategy.reset_strategy()
                runtime.reset_statistics()
                if runtime.enabled:
                    runtime.state = StrategyState.IDLE
                else:
                    runtime.state = StrategyState.IDLE

    def _sort_enabled_strategies(self):
        """按优先级排序启用策略列表"""
        self._enabled_strategies.sort(
            key=lambda name: self._strategies[name].priority
        )

    # ==================== 回调设置 ====================

    def set_signal_callback(self, callback: Callable[[str, TradingSignal], None]):
        """设置信号生成回调"""
        self._on_signal_generated = callback

    def set_error_callback(self, callback: Callable[[str, str], None]):
        """设置错误回调"""
        self._on_strategy_error = callback

    # ==================== 状态检查 ====================

    def has_enabled_strategies(self) -> bool:
        """检查是否有启用的策略"""
        with self._lock:
            return len(self._enabled_strategies) > 0

    def is_any_strategy_running(self) -> bool:
        """检查是否有策略正在运行"""
        with self._lock:
            for runtime in self._strategies.values():
                if runtime.state == StrategyState.RUNNING:
                    return True
            return False

    def get_strategy_state(self, name: str) -> StrategyState:
        """获取策略状态"""
        with self._lock:
            runtime = self._strategies.get(name)
            return runtime.state if runtime else StrategyState.IDLE

    def pause_strategy(self, name: str) -> bool:
        """暂停策略"""
        with self._lock:
            if name not in self._strategies:
                return False

            runtime = self._strategies[name]
            if runtime.state == StrategyState.RUNNING:
                runtime.state = StrategyState.PAUSED
                return True
            return False

    def resume_strategy(self, name: str) -> bool:
        """恢复策略"""
        with self._lock:
            if name not in self._strategies:
                return False

            runtime = self._strategies[name]
            if runtime.state == StrategyState.PAUSED:
                runtime.state = StrategyState.RUNNING
                return True
            return False


# 创建全局策略管理器实例
_manager_instance = None
_manager_lock = threading.Lock()


def get_strategy_manager() -> StrategyManager:
    """获取全局策略管理器实例（单例模式）"""
    global _manager_instance
    if _manager_instance is None:
        with _manager_lock:
            if _manager_instance is None:
                _manager_instance = StrategyManager()
    return _manager_instance
