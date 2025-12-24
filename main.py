"""
期权交易自动化程序 - 重构版本
模块化架构的主程序入口
"""

import time
import threading
from utils import setup_driver
from auth import LoginManager
from data import MarketData
from strategy import TradingStrategy
from execution import TradeExecutor
from monitor import TradingMonitor, TradingSession
from config import config


class TradingSystem:
    """期权交易系统主类"""

    def __init__(self):
        self.driver = None
        self.login_manager = None
        self.market_data = None
        self.strategy = None
        self.executor = None
        self.monitor = None
        self.is_running = False
        self.current_position = 0
        self.open_position_info = None  # 存储开仓信息

    def initialize(self):
        """初始化系统组件"""
        print("正在初始化交易系统...")

        # 初始化浏览器驱动
        self.driver = setup_driver()

        # 初始化各模块
        self.login_manager = LoginManager(self.driver)
        self.market_data = MarketData(self.driver)
        self.strategy = TradingStrategy()
        self.executor = TradeExecutor(self.driver)
        self.monitor = TradingMonitor()

        print("系统初始化完成")

    def login_and_select_contract(self):
        """登录并选择合约"""
        try:
            # 登录
            print("正在登录...")
            if not self.login_manager.login():
                return False

            # 选择合约
            print(f"正在选择合约: {config.TARGET_CONTRACT}")
            if not self.login_manager.select_contract():
                return False

            print("登录和合约选择成功")
            return True

        except Exception as e:
            print(f"登录失败: {e}")
            return False

    def execute_trading_cycle(self, signal):
        """
        执行完整的交易周期（开仓 -> 平仓）

        Args:
            signal: 开仓信号
        """
        print(f"\n{'='*50}")
        print(f"开始执行交易周期: {signal}")
        print(f"{'='*50}")

        # 记录开仓开始时间
        cycle_start_time = time.time()
        open_price = signal.price
        open_qty = signal.quantity

        # === 阶段 1: 信号触发后的固定等待 ===
        print(f"1. [{signal.signal_type.value}] 信号触发，固定等待 {config.FIXED_DELAY_BEFORE_OPEN} 秒...")
        time.sleep(config.FIXED_DELAY_BEFORE_OPEN)

        # === 阶段 2: 执行开仓 ===
        print(f"2. 执行开仓操作...")
        open_record = self.executor.execute_with_signal(signal)

        if not open_record or open_record.quantity == 0:
            print(" [警告] 开仓未成交，退出交易周期")
            return

        # 更新策略持仓信息
        self.strategy.update_position(open_record.quantity, is_open=True)
        self.current_position = open_record.quantity

        # 存储开仓信息
        self.open_position_info = {
            'price': open_record.price,
            'quantity': open_record.quantity,
            'time': open_record.time_str,
            'signal_type': signal.signal_type.value
        }

        print(f"3. 开仓成交: {open_record}")

        # === 阶段 3: 动态延时 ===
        elapsed_time = time.time() - cycle_start_time
        wait_remaining = config.TARGET_INTERVAL_CLOSE - elapsed_time
        if wait_remaining < 0:
            wait_remaining = 0

        print(f"4. 动态等待平仓 (还需等待 {wait_remaining:.2f}s)...")
        time.sleep(wait_remaining)

        # === 阶段 4: 循环强制平仓 ===
        print(f"5. 开始平仓循环...")
        self._execute_close_cycle(cycle_start_time)

    def _execute_close_cycle(self, cycle_start_time):
        """执行平仓循环"""
        close_revenue = 0
        close_qty = 0
        last_known_signature = self.executor.last_known_signature

        while self.current_position > 0:
            # 生成平仓信号
            close_signal = self.strategy.should_close_position(
                time.time() - cycle_start_time
            )

            if close_signal:
                # 执行平仓
                close_record = self.executor.execute_with_signal(close_signal)

                if close_record and close_record.signature != last_known_signature:
                    filled_qty = close_record.quantity
                    print(f"      >> 平仓成交: {close_record}")

                    # 更新统计
                    self.current_position -= filled_qty
                    if self.current_position < 0:
                        self.current_position = 0

                    close_revenue += close_record.price * filled_qty
                    close_qty += filled_qty

                    # 更新策略持仓
                    self.strategy.update_position(filled_qty, is_open=False)

                    last_known_signature = close_record.signature

                else:
                    print("      >> 平仓未成交，重试...")
                    time.sleep(1)
            else:
                time.sleep(0.5)

        # === 阶段 5: 计算和记录交易结果 ===
        self._calculate_and_record(close_revenue, close_qty, cycle_start_time)

    def _calculate_and_record(self, close_revenue, close_qty, cycle_start_time):
        """计算并记录交易结果"""
        if not self.open_position_info or close_qty == 0:
            return

        # 计算平均平仓价
        avg_close_price = close_revenue / close_qty

        # 计算盈亏
        open_price = self.open_position_info['price']
        qty = self.open_position_info['quantity']

        if "买入开仓" in self.open_position_info['signal_type']:
            # 多头策略：卖出平仓
            profit = (avg_close_price - open_price) * qty * config.CONTRACT_MULTIPLIER
            strategy_name = "Bull (Buy->Sell)"
        else:
            # 空头策略：买入平仓
            profit = (open_price - avg_close_price) * qty * config.CONTRACT_MULTIPLIER
            strategy_name = "Bear (Sell->Buy)"

        # 创建交易会话记录
        session = TradingSession(
            strategy=strategy_name,
            open_time=self.open_position_info['time'],
            open_price=open_price,
            avg_close_price=avg_close_price,
            total_qty=qty,
            profit=profit,
            cumulative_profit=self.monitor.cumulative_profit + profit,
            actual_wait=f"{time.time() - cycle_start_time:.2f}s"
        )

        # 记录交易
        self.monitor.record_trading_session(session)

        # 清空开仓信息
        self.open_position_info = None

        # 清空价格历史
        self.market_data.clear_history()

    def run_strategy(self):
        """运行交易策略主循环"""
        print(f"\n>>> 启动双向套利策略")
        print(f"    - 信号阈值: {config.THRESHOLD:.2%}")
        print(f"    - 交易数量: {config.TRADE_QTY}张")
        print(f"    - 目标平仓间隔: {config.TARGET_INTERVAL_CLOSE}s")
        print(f"    - 价格监控间隔: {config.INTERVAL}s\n")

        self.is_running = True

        while self.is_running:
            try:
                # 更新市场数据
                if not self.market_data.update_price_history():
                    time.sleep(config.INTERVAL)
                    continue

                # 获取市场状态
                market_status = self.market_data.get_market_status()

                # 初始化期间
                if not market_status['history_ready']:
                    print(f"\r[{market_status['timestamp']}] "
                          f"初始化市场数据... {market_status['history_length']}/{config.HISTORY_LEN}",
                          end="")
                    time.sleep(config.INTERVAL)
                    continue

                # 生成交易信号
                signal = self.strategy.analyze_market_data(market_status)

                # 执行交易信号
                if signal and self.current_position == 0:
                    # 在新线程中执行交易周期，避免阻塞主循环
                    trading_thread = threading.Thread(
                        target=self.execute_trading_cycle,
                        args=(signal,)
                    )
                    trading_thread.daemon = True
                    trading_thread.start()

                # 打印实时状态
                position_info = self.monitor.get_position_info(
                    market_status.get('mid_price', 0),
                    self.current_position,
                    self.open_position_info['price'] if self.open_position_info else 0,
                    "多头" if self.open_position_info and "买入开仓" in self.open_position_info['signal_type'] else "空头"
                )

                self.monitor.print_real_time_status(
                    position_info, market_status, self.strategy.get_strategy_status()
                )

                time.sleep(config.INTERVAL)

            except KeyboardInterrupt:
                print("\n收到停止信号，正在退出...")
                self.is_running = False
                break
            except Exception as e:
                print(f"\n[错误] {e}")
                time.sleep(1)

    def run(self):
        """运行交易系统"""
        try:
            # 初始化
            self.initialize()

            # 登录
            if not self.login_and_select_contract():
                return

            # 运行策略
            self.run_strategy()

        except Exception as e:
            print(f"系统运行错误: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """清理资源"""
        if self.driver:
            print("正在关闭浏览器...")
            self.driver.quit()

        # 生成最终报告
        final_report = self.monitor.generate_daily_report()
        print("\n" + "="*50)
        print("每日交易报告")
        print("="*50)
        print(final_report)
        print("="*50)

        print("系统已退出")


def main():
    """主函数"""
    print("期权交易自动化程序 v2.0 (模块化版本)")
    print("="*50)

    # 创建并运行交易系统
    trading_system = TradingSystem()
    trading_system.run()


if __name__ == "__main__":
    main()