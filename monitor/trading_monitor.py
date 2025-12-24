"""
交易监控模块
负责监控交易记录、计算盈亏、生成报告等
"""

import time
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from config import config


@dataclass
class TradingSession:
    """交易会话数据类"""
    strategy: str  # 策略名称
    open_time: str  # 开仓时间
    open_price: float  # 开仓价格
    avg_close_price: float  # 平均平仓价格
    total_qty: int  # 交易数量
    profit: float  # 本次盈亏
    cumulative_profit: float  # 累计盈亏
    actual_wait: str  # 实际等待时间

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


@dataclass
class PositionInfo:
    """持仓信息数据类"""
    quantity: int  # 持仓数量
    avg_price: float  # 平均持仓价格
    side: str  # 持仓方向（多头/空头）
    unrealized_pnl: float  # 未实现盈亏
    market_price: float  # 当前市价


class TradingMonitor:
    """交易监控器"""

    def __init__(self, excel_file_path: str = None):
        self.excel_file_path = excel_file_path or config.EXCEL_FILE_PATH
        self.trading_sessions: List[TradingSession] = []
        self.cumulative_profit = 0.0
        self.start_time = datetime.now()
        self.total_trades = 0
        self.successful_trades = 0
        self.failed_trades = 0

    def record_trading_session(self, session: TradingSession):
        """
        记录交易会话

        Args:
            session: 交易会话数据
        """
        self.trading_sessions.append(session)
        self.cumulative_profit = session.cumulative_profit
        self.total_trades += 1

        if session.profit != 0:
            self.successful_trades += 1

        self.save_to_excel()
        self.print_session_summary(session)

    def save_to_excel(self):
        """保存交易记录到Excel文件"""
        try:
            if not self.trading_sessions:
                return

            # 转换为DataFrame
            df_data = [session.to_dict() for session in self.trading_sessions]
            df = pd.DataFrame(df_data)

            # 保存到Excel
            df.to_excel(self.excel_file_path, index=False)
            print(f"交易记录已保存到: {self.excel_file_path}")

        except Exception as e:
            print(f"保存Excel文件失败: {e}")

    def print_session_summary(self, session: TradingSession):
        """打印交易会话摘要"""
        print("-" * 40)
        print(f"交易结束 | 策略: {session.strategy}")
        print(f"开仓价格: {session.open_price:.4f}")
        print(f"平均平仓价: {session.avg_close_price:.4f}")
        print(f"交易数量: {session.total_qty}张")
        print(f"本次盈亏: {session.profit:.2f}")
        print(f"★ 累计总盈亏: {session.cumulative_profit:.2f}")
        print(f"实际用时: {session.actual_wait}")
        print("-" * 40)

    def get_position_info(self, current_market_price: float,
                         quantity: int, avg_price: float, side: str) -> PositionInfo:
        """
        计算持仓信息

        Args:
            current_market_price: 当前市价
            quantity: 持仓数量
            avg_price: 平均持仓价格
            side: 持仓方向

        Returns:
            持仓信息
        """
        if quantity == 0:
            return PositionInfo(0, 0, "无", 0, current_market_price)

        # 计算未实现盈亏
        if side == "多头":
            unrealized_pnl = (current_market_price - avg_price) * quantity * config.CONTRACT_MULTIPLIER
        else:  # 空头
            unrealized_pnl = (avg_price - current_market_price) * quantity * config.CONTRACT_MULTIPLIER

        return PositionInfo(
            quantity=quantity,
            avg_price=avg_price,
            side=side,
            unrealized_pnl=unrealized_pnl,
            market_price=current_market_price
        )

    def get_monitoring_stats(self) -> Dict:
        """获取监控统计信息"""
        running_time = datetime.now() - self.start_time

        # 计算胜率
        win_rate = (self.successful_trades / self.total_trades * 100) if self.total_trades > 0 else 0

        # 计算平均盈亏
        profits = [s.profit for s in self.trading_sessions if s.profit != 0]
        avg_profit = sum(profits) / len(profits) if profits else 0

        # 计算最大回撤
        max_drawdown = self._calculate_max_drawdown()

        return {
            'start_time': self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            'running_time': str(running_time).split('.')[0],
            'total_trades': self.total_trades,
            'successful_trades': self.successful_trades,
            'failed_trades': self.failed_trades,
            'win_rate': f"{win_rate:.2f}%",
            'avg_profit': f"{avg_profit:.2f}",
            'cumulative_profit': f"{self.cumulative_profit:.2f}",
            'max_drawdown': f"{max_drawdown:.2f}",
            'sessions_count': len(self.trading_sessions)
        }

    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        if len(self.trading_sessions) < 2:
            return 0.0

        # 提取累计利润序列
        profit_series = [s.cumulative_profit for s in self.trading_sessions]

        # 计算最大回撤
        max_profit = profit_series[0]
        max_drawdown = 0.0

        for profit in profit_series:
            if profit > max_profit:
                max_profit = profit
            else:
                drawdown = max_profit - profit
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        return max_drawdown

    def print_real_time_status(self, position_info: PositionInfo,
                             market_status: Dict, strategy_status: Dict):
        """打印实时状态信息"""
        status_msg = (
            f"\r[{market_status['timestamp']}] "
            f"卖:{market_status['ask']:.4f}({market_status['ask_change']:.2%}) | "
            f"买:{market_status['bid']:.4f}({market_status['bid_change']:.2%}) | "
            f"持仓:{position_info.quantity}张 | "
            f"未实现盈亏:{position_info.unrealized_pnl:.2f} | "
            f"总盈亏:{self.cumulative_profit:.2f}  "
        )
        print(status_msg, end="")

    def generate_daily_report(self) -> Dict:
        """生成每日交易报告"""
        if not self.trading_sessions:
            return {"message": "今日暂无交易记录"}

        # 按策略分组统计
        strategy_stats = {}
        for session in self.trading_sessions:
            if session.strategy not in strategy_stats:
                strategy_stats[session.strategy] = {
                    'count': 0,
                    'total_profit': 0,
                    'success_count': 0
                }

            stats = strategy_stats[session.strategy]
            stats['count'] += 1
            stats['total_profit'] += session.profit
            if session.profit > 0:
                stats['success_count'] += 1

        # 计算每小时交易量
        hourly_volume = {}
        for session in self.trading_sessions:
            try:
                hour = session.open_time.split(':')[0]
                if hour not in hourly_volume:
                    hourly_volume[hour] = 0
                hourly_volume[hour] += session.total_qty
            except:
                continue

        return {
            'date': datetime.now().strftime("%Y-%m-%d"),
            'summary': self.get_monitoring_stats(),
            'strategy_breakdown': strategy_stats,
            'hourly_volume': hourly_volume,
            'best_trade': max(self.trading_sessions, key=lambda x: x.profit),
            'worst_trade': min(self.trading_sessions, key=lambda x: x.profit)
        }

    def reset_monitor(self):
        """重置监控器"""
        self.trading_sessions.clear()
        self.cumulative_profit = 0.0
        self.start_time = datetime.now()
        self.total_trades = 0
        self.successful_trades = 0
        self.failed_trades = 0
        print("监控器已重置")