"""
GUI交易系统集成类（重写版）
将原有的交易系统包装成适合GUI调用的形式，集成策略管理器
"""

import threading
import time
import uuid
from typing import Dict, Optional
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QThread

from utils import setup_driver
from auth import LoginManager
from data import MarketData
from strategy import get_strategy_manager, TradingSignal, SignalType
from execution import TradeExecutor
from monitor import TradingMonitor
from config import config
from database import get_database


class TradingThread(QThread):
    """交易系统工作线程"""

    # 定义信号
    market_data_updated = pyqtSignal(dict)
    trade_signal_generated = pyqtSignal(object)
    position_updated = pyqtSignal(dict)
    trade_executed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    status_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.is_connected = False

        # 交易系统组件
        self.driver = None
        self.login_manager = None
        self.market_data = None
        self.strategy_manager = None
        self.executor = None
        self.monitor = None
        self.db = None

        # 持仓状态
        self.current_position = 0
        self.open_position_info = None
        self.current_position_id = None
        self.position_open_time = None

        # 统计数据
        self.max_profit = 0.0
        self.max_loss = 0.0

    def initialize_components(self):
        """初始化交易系统组件"""
        try:
            # 初始化浏览器和登录
            from utils import setup_driver
            self.driver = setup_driver()

            # 初始化各个模块
            from auth import LoginManager
            from data import MarketData
            from execution import TradeExecutor
            from monitor import TradingMonitor
            from config import config

            self.login_manager = LoginManager(self.driver)
            self.market_data = MarketData(self.driver)
            self.strategy_manager = get_strategy_manager()
            self.executor = TradeExecutor(self.driver)
            self.monitor = TradingMonitor()
            self.db = get_database()

            # 执行登录
            if not self.login_manager.login():
                return False

            # 选择合约
            if not self.login_manager.select_contract():
                return False

            self.is_connected = True
            return True

        except Exception as e:
            self.error_occurred.emit(f"初始化失败: {e}")
            return False

    def run(self):
        """运行交易策略主循环"""
        if not self.is_connected:
            self.error_occurred.emit("交易系统未连接")
            return

        # 检查是否有启用的策略
        if not self.strategy_manager.has_enabled_strategies():
            self.error_occurred.emit("没有启用的策略，请先启用策略")
            return

        self.is_running = True
        self.status_changed.emit("策略运行中")

        try:
            while self.is_running:
                # 更新市场数据
                if self.market_data.update_price_history():
                    market_status = self.market_data.get_market_status()

                    # 发出市场数据更新信号
                    self.market_data_updated.emit(market_status)

                    # 检查是否准备好
                    if market_status['history_ready']:
                        # 使用策略管理器生成交易信号
                        signal = self.strategy_manager.analyze_market_data(market_status)

                        if signal and self.current_position == 0:
                            self.trade_signal_generated.emit(signal)
                            self.execute_open_trade(signal)

                    # 更新持仓信息
                    self.update_position_info(market_status)

                    # 检查是否需要平仓
                    if self.current_position > 0 and self.position_open_time:
                        elapsed = time.time() - self.position_open_time
                        close_signal = self.strategy_manager.should_close_position(elapsed)
                        if close_signal:
                            self.execute_close_trade(close_signal)

                time.sleep(config.INTERVAL)

        except Exception as e:
            self.error_occurred.emit(f"策略运行异常: {e}")
        finally:
            self.is_running = False
            self.status_changed.emit("策略已停止")

    def execute_open_trade(self, signal: TradingSignal):
        """执行开仓交易"""
        try:
            # 获取当前策略名称
            strategy_name = self.strategy_manager.get_active_strategy()
            if not strategy_name:
                strategy_name = "未知策略"

            # 生成交易ID
            trade_id = str(uuid.uuid4())[:8]

            # 执行交易
            open_record = self.executor.execute_with_signal(signal)
            if open_record and open_record.quantity > 0:
                self.current_position = open_record.quantity
                self.position_open_time = time.time()

                # 生成持仓ID
                self.current_position_id = f"{strategy_name}_{trade_id}"

                # 保存开仓信息
                self.open_position_info = {
                    'position_id': self.current_position_id,
                    'strategy_name': strategy_name,
                    'open_time': datetime.now().isoformat(),
                    'open_price': open_record.price,
                    'quantity': open_record.quantity,
                    'direction': '多头' if signal.signal_type == SignalType.BUY_TO_OPEN else '空头'
                }

                # 更新策略持仓
                self.strategy_manager.update_position(open_record.quantity, is_open=True)

                # 记录到数据库
                self._record_trade_to_db(signal, open_record, 'open')

                # 记录持仓到数据库
                self.db.open_position(self.open_position_info)

                # 发出交易执行信号
                trade_info = {
                    'trade_id': f"{strategy_name}_{int(time.time())}",
                    'strategy_name': strategy_name,
                    'signal_type': signal.signal_type.value,
                    'type': 'open',
                    'price': open_record.price,
                    'quantity': open_record.quantity,
                    'direction': '买入' if 'BUY' in signal.signal_type.name else '卖出',
                    'position_type': 'open',
                    'status': 'completed',
                    'reason': signal.reason,
                    'contract_code': config.TARGET_CONTRACT,
                    'timestamp': datetime.now().isoformat()
                }
                self.trade_executed.emit(trade_info)

                # 发出持仓更新信号
                position_info = {
                    'quantity': open_record.quantity,
                    'unrealized_pnl': 0,
                    'market_price': open_record.price,
                    'strategy_name': strategy_name,
                    'avg_price': open_record.price,
                    'side': self.open_position_info['direction'],
                    'open_time': self.open_position_info['open_time']
                }
                self.position_updated.emit(position_info)

        except Exception as e:
            self.error_occurred.emit(f"开仓执行异常: {e}")

    def execute_close_trade(self, signal: TradingSignal):
        """执行平仓交易"""
        try:
            if not self.open_position_info or self.current_position <= 0:
                return

            # 执行交易
            close_record = self.executor.execute_with_signal(signal)
            if close_record:
                # 计算盈亏
                open_price = self.open_position_info['open_price']
                close_price = close_record.price
                quantity = self.current_position
                direction = self.open_position_info['direction']

                if direction == '多头':
                    pnl = (close_price - open_price) * quantity * config.CONTRACT_MULTIPLIER
                else:
                    pnl = (open_price - close_price) * quantity * config.CONTRACT_MULTIPLIER

                # 更新策略盈亏
                self.strategy_manager.update_pnl(pnl)

                # 记录到数据库
                self._record_trade_to_db(signal, close_record, 'close', pnl)

                # 更新持仓记录
                hold_seconds = int(time.time() - self.position_open_time) if self.position_open_time else 0
                self.db.close_position(
                    self.current_position_id,
                    {
                        'close_time': datetime.now().isoformat(),
                        'close_price': close_price,
                        'pnl': pnl,
                        'hold_seconds': hold_seconds
                    }
                )

                # 获取策略名称
                strategy_name = self.open_position_info['strategy_name']

                # 发出交易执行信号
                trade_info = {
                    'trade_id': f"{strategy_name}_{int(time.time())}",
                    'strategy_name': strategy_name,
                    'signal_type': signal.signal_type.value,
                    'type': 'close',
                    'price': close_price,
                    'quantity': quantity,
                    'pnl': pnl,
                    'direction': '买入' if 'BUY' in signal.signal_type.name else '卖出',
                    'position_type': 'close',
                    'status': 'completed',
                    'reason': signal.reason,
                    'contract_code': config.TARGET_CONTRACT,
                    'timestamp': datetime.now().isoformat()
                }
                self.trade_executed.emit(trade_info)

                # 重置持仓状态
                self.current_position = 0
                self.open_position_info = None
                self.current_position_id = None
                self.position_open_time = None
                self.max_profit = 0.0
                self.max_loss = 0.0

                # 更新策略持仓
                self.strategy_manager.update_position(quantity, is_open=False)

                # 发出持仓更新信号
                position_info = {
                    'quantity': 0,
                    'unrealized_pnl': 0,
                    'market_price': close_price,
                    'strategy_name': strategy_name,
                    'pnl': pnl
                }
                self.position_updated.emit(position_info)

        except Exception as e:
            self.error_occurred.emit(f"平仓执行异常: {e}")

    def _record_trade_to_db(self, signal: TradingSignal, record, position_type: str, pnl: float = 0):
        """记录交易到数据库"""
        try:
            strategy_name = self.strategy_manager.get_active_strategy()
            if not strategy_name:
                strategy_name = "未知策略"

            trade_info = {
                'trade_id': f"{strategy_name}_{int(time.time())}",
                'strategy_name': strategy_name,
                'signal_type': signal.signal_type.value,
                'direction': '买入' if 'BUY' in signal.signal_type.name else '卖出',
                'position_type': position_type,
                'price': record.price,
                'quantity': record.quantity,
                'pnl': pnl,
                'status': 'completed',
                'reason': signal.reason,
                'contract_code': config.TARGET_CONTRACT,
                'timestamp': datetime.now().isoformat()
            }

            self.db.add_trade(trade_info)

        except Exception as e:
            print(f"记录交易到数据库失败: {e}")

    def update_position_info(self, market_status):
        """更新持仓信息"""
        position_info = {
            'quantity': self.current_position,
            'unrealized_pnl': 0,
            'market_price': market_status.get('mid_price', 0),
            'strategy_name': self.strategy_manager.get_active_strategy() or '--'
        }

        if self.open_position_info and self.current_position > 0:
            # 添加更多信息
            position_info['avg_price'] = self.open_position_info['open_price']
            position_info['side'] = self.open_position_info['direction']
            position_info['open_time'] = self.open_position_info['open_time']
            position_info['strategy_name'] = self.open_position_info['strategy_name']

            # 计算未实现盈亏
            avg_price = self.open_position_info['open_price']
            current_price = market_status.get('mid_price', 0)
            direction = self.open_position_info['direction']

            if direction == '多头':
                pnl = (current_price - avg_price) * self.current_position * config.CONTRACT_MULTIPLIER
            else:
                pnl = (avg_price - current_price) * self.current_position * config.CONTRACT_MULTIPLIER

            position_info['unrealized_pnl'] = pnl

            # 更新最大盈亏
            if pnl > self.max_profit:
                self.max_profit = pnl
            if pnl < self.max_loss:
                self.max_loss = pnl

            position_info['max_profit'] = self.max_profit
            position_info['max_loss'] = self.max_loss

            # 持仓秒数
            if self.position_open_time:
                position_info['hold_seconds'] = int(time.time() - self.position_open_time)

            # 最大持仓时间（从配置或策略获取）
            position_info['max_hold_time'] = config.MAX_HOLDING_TIME

        self.position_updated.emit(position_info)

    def stop(self):
        """停止交易线程"""
        self.is_running = False
        self.wait()


class TradingSystemGUI(QObject):
    """GUI交易系统集成类（重写版）"""

    # 定义信号
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)

    # 转发线程信号
    market_data_updated = pyqtSignal(dict)
    trade_signal_generated = pyqtSignal(object)
    position_updated = pyqtSignal(dict)
    trade_executed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.trading_thread = None
        self._is_connected = False
        self.strategy_manager = get_strategy_manager()

    def initialize(self) -> bool:
        """初始化交易系统"""
        try:
            # 创建交易线程
            self.trading_thread = TradingThread()

            # 连接信号
            self.trading_thread.market_data_updated.connect(self.market_data_updated)
            self.trading_thread.trade_signal_generated.connect(self.trade_signal_generated)
            self.trading_thread.position_updated.connect(self.position_updated)
            self.trading_thread.trade_executed.connect(self.trade_executed)
            self.trading_thread.error_occurred.connect(self.error)
            self.trading_thread.status_changed.connect(self.on_status_changed)

            # 初始化交易系统组件（在交易线程中）
            if self.trading_thread.initialize_components():
                self._is_connected = True
                self.connected.emit()
                return True
            else:
                return False

        except Exception as e:
            self.error.emit(f"初始化失败: {e}")
            return False

    def cleanup(self):
        """清理资源"""
        if self.trading_thread:
            self.trading_thread.stop()
            if self.trading_thread.driver:
                self.trading_thread.driver.quit()
            self._is_connected = False
            self.disconnected.emit()

    def start_strategy(self):
        """启动交易策略"""
        if self.trading_thread and self._is_connected:
            self.trading_thread.start()

    def stop_strategy(self):
        """停止交易策略"""
        if self.trading_thread:
            self.trading_thread.stop()

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._is_connected

    def update_strategy_parameters(self, params: Dict):
        """更新策略参数"""
        active_strategy = self.strategy_manager.get_active_strategy()
        if active_strategy:
            self.strategy_manager.update_strategy_parameters(active_strategy, **params)

    def execute_manual_trade(self, trade_params: Dict) -> bool:
        """执行手动交易
        
        Args:
            trade_params: 交易参数字典，包含:
                         - direction: 交易方向 ('买入'/'卖出')
                         - position: 开平仓 ('开仓'/'平仓')
                         - price_type: 价格类型 ('市价'/'限价')
                         - quantity: 交易数量
                         - limit_price: 限价 (可选)
        
        Returns:
            bool: 交易是否成功
        """
        try:
            if not self._is_connected:
                self.error.emit("未连接到交易系统")
                return False

            # 获取当前策略名称
            strategy_name = self.strategy_manager.get_active_strategy()
            if not strategy_name:
                strategy_name = "手动交易"

            # 解析交易参数
            direction = trade_params.get('direction', '买入')
            position = trade_params.get('position', '开仓')
            price_type = trade_params.get('price_type', '市价')
            quantity = trade_params.get('quantity', 0)
            limit_price = trade_params.get('limit_price')

            if quantity <= 0:
                self.error.emit("交易数量无效")
                return False

            # 创建交易信号
            if position == '开仓':
                if direction == '买入':
                    signal_type = SignalType.BUY_TO_OPEN
                else:
                    signal_type = SignalType.SELL_TO_OPEN
            else:  # 平仓
                if direction == '买入':
                    signal_type = SignalType.BUY_TO_CLOSE
                else:
                    signal_type = SignalType.SELL_TO_CLOSE

            # 创建信号
            signal = TradingSignal(
                signal_type=signal_type,
                quantity=quantity,
                price=limit_price if limit_price else 0.0,
                timestamp=datetime.now().strftime("%H:%M:%S"),
                confidence=1.0,
                reason="手动交易"
            )

            # 执行交易
            if position == '开仓':
                self.trading_thread.execute_open_trade(signal)
            else:
                self.trading_thread.execute_close_trade(signal)

            return True

        except Exception as e:
            self.error.emit(f"手动交易执行失败: {e}")
            return False

    def on_status_changed(self, status):
        """处理状态变更"""
        # 可以在这里处理状态变更逻辑
        pass
