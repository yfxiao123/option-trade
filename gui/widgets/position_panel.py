"""
持仓监控面板（优化版）
显示当前持仓信息、实时盈亏和交易记录，增加策略名称和更多统计信息
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QGroupBox, QSplitter, QFormLayout, QPushButton,
                             QFrame, QProgressBar)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QBrush
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class PositionDetailWidget(QGroupBox):
    """持仓详情组件"""

    def __init__(self):
        super().__init__("持仓详情")
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        # 策略名称
        self.strategy_label = QLabel("--")
        self.strategy_label.setStyleSheet("font-size: 14px; color: #3498db; font-weight: bold;")
        layout.addRow("使用策略:", self.strategy_label)

        # 持仓数量
        self.quantity_label = QLabel("0")
        self.quantity_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        layout.addRow("持仓数量:", self.quantity_label)

        # 持仓均价
        self.avg_price_label = QLabel("0.0000")
        self.avg_price_label.setStyleSheet("font-size: 18px; color: #7f8c8d;")
        layout.addRow("开仓均价:", self.avg_price_label)

        # 当前市价
        self.market_price_label = QLabel("0.0000")
        self.market_price_label.setStyleSheet("font-size: 16px;")
        layout.addRow("当前市价:", self.market_price_label)

        # 持仓方向
        self.side_label = QLabel("无")
        self.side_label.setStyleSheet("font-size: 16px;")
        layout.addRow("持仓方向:", self.side_label)

        # 开仓时间
        self.open_time_label = QLabel("--:--:--")
        layout.addRow("开仓时间:", self.open_time_label)

        # 持仓时长
        self.hold_duration_label = QLabel("00:00:00")
        layout.addRow("持仓时长:", self.hold_duration_label)

    def update_position(self, position_info: Dict):
        """更新持仓详情"""
        # 策略名称
        strategy = position_info.get('strategy_name', '--')
        self.strategy_label.setText(strategy)

        # 持仓数量
        quantity = position_info.get('quantity', 0)
        self.quantity_label.setText(str(quantity))

        # 持仓均价
        avg_price = position_info.get('avg_price', 0)
        self.avg_price_label.setText(f"{avg_price:.4f}")

        # 当前市价
        market_price = position_info.get('market_price', 0)
        self.market_price_label.setText(f"{market_price:.4f}")

        # 持仓方向
        side = position_info.get('side', '无')
        self.side_label.setText(side)
        if side == "多头":
            self.side_label.setStyleSheet("color: #e74c3c; font-size: 16px; font-weight: bold;")  # 红色多头
        elif side == "空头":
            self.side_label.setStyleSheet("color: #27ae60; font-size: 16px; font-weight: bold;")  # 绿色空头
        else:
            self.side_label.setStyleSheet("color: #95a5a6; font-size: 16px;")

        # 开仓时间
        open_time = position_info.get('open_time', '')
        if open_time:
            try:
                dt = datetime.fromisoformat(open_time.replace('T', ' '))
                self.open_time_label.setText(dt.strftime("%H:%M:%S"))
            except:
                self.open_time_label.setText(open_time)

    def update_hold_duration(self, duration_str: str):
        """更新持仓时长"""
        self.hold_duration_label.setText(duration_str)


class PositionPnLWidget(QGroupBox):
    """持仓盈亏组件"""

    def __init__(self):
        super().__init__("盈亏分析")
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        # 未实现盈亏
        self.unrealized_pnl_label = QLabel("0.00")
        self.unrealized_pnl_label.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 8px;
            min-width: 150px;
        """)
        self.unrealized_pnl_label.setAlignment(Qt.AlignCenter)
        layout.addRow(self.unrealized_pnl_label)

        # 最大浮盈
        self.max_profit_label = QLabel("0.00")
        self.max_profit_label.setStyleSheet("font-size: 16px; color: #27ae60;")
        layout.addRow("最大浮盈:", self.max_profit_label)

        # 最大浮亏
        self.max_loss_label = QLabel("0.00")
        self.max_loss_label.setStyleSheet("font-size: 16px; color: #e74c3c;")
        layout.addRow("最大浮亏:", self.max_loss_label)

        # 盈亏率
        self.pnl_ratio_label = QLabel("0.00%")
        self.pnl_ratio_label.setStyleSheet("font-size: 14px;")
        layout.addRow("盈亏率:", self.pnl_ratio_label)

        # 预估平仓盈亏
        self.est_close_pnl_label = QLabel("0.00")
        self.est_close_pnl_label.setStyleSheet("font-size: 14px;")
        layout.addRow("预估平仓:", self.est_close_pnl_label)

    def update_pnl(self, position_info: Dict):
        """更新盈亏信息"""
        unrealized_pnl = position_info.get('unrealized_pnl', 0)
        max_profit = position_info.get('max_profit', 0)
        max_loss = position_info.get('max_loss', 0)

        # 更新未实现盈亏
        self.unrealized_pnl_label.setText(f"{unrealized_pnl:+.2f}")

        if unrealized_pnl > 0:
            self.unrealized_pnl_label.setStyleSheet("""
                font-size: 28px;
                font-weight: bold;
                color: #e74c3c;
                background-color: #fadbd8;
                padding: 15px;
                border-radius: 8px;
                min-width: 150px;
            """)  # 红色盈利
        elif unrealized_pnl < 0:
            self.unrealized_pnl_label.setStyleSheet("""
                font-size: 28px;
                font-weight: bold;
                color: #27ae60;
                background-color: #d5f4e6;
                padding: 15px;
                border-radius: 8px;
                min-width: 150px;
            """)  # 绿色亏损
        else:
            self.unrealized_pnl_label.setStyleSheet("""
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
                background-color: #ecf0f1;
                padding: 15px;
                border-radius: 8px;
                min-width: 150px;
            """)  # 无变化

        # 更新最大盈亏
        self.max_profit_label.setText(f"+{max_profit:.2f}")
        self.max_loss_label.setText(f"{max_loss:.2f}")

        # 计算盈亏率
        cost = position_info.get('avg_price', 0)
        if cost > 0:
            pnl_ratio = (unrealized_pnl / cost) * 100
            self.pnl_ratio_label.setText(f"{pnl_ratio:+.2f}%")

            if pnl_ratio > 0:
                self.pnl_ratio_label.setStyleSheet("font-size: 14px; color: #e74c3c; font-weight: bold;")
            elif pnl_ratio < 0:
                self.pnl_ratio_label.setStyleSheet("font-size: 14px; color: #27ae60; font-weight: bold;")
            else:
                self.pnl_ratio_label.setStyleSheet("font-size: 14px; color: #2c3e50;")
        else:
            self.pnl_ratio_label.setText("0.00%")
            self.pnl_ratio_label.setStyleSheet("font-size: 14px; color: #2c3e50;")

        # 预估平仓盈亏（考虑手续费）
        commission = position_info.get('commission', 0)
        est_close_pnl = unrealized_pnl - commission
        self.est_close_pnl_label.setText(f"{est_close_pnl:+.2f}")


class PositionWarningWidget(QGroupBox):
    """持仓预警组件"""

    def __init__(self):
        super().__init__("持仓预警")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 预警消息
        self.warning_label = QLabel("无预警")
        self.warning_label.setStyleSheet("""
            font-size: 14px;
            color: #27ae60;
            background-color: #d5f4e6;
            padding: 10px;
            border-radius: 5px;
            border-left: 4px solid #27ae60;
        """)
        self.warning_label.setWordWrap(True)
        layout.addWidget(self.warning_label)

        # 持仓时长进度条
        layout.addWidget(QLabel("持仓时长:"))

        self.duration_progress = QProgressBar()
        self.duration_progress.setRange(0, 100)
        self.duration_progress.setValue(0)
        self.duration_progress.setFormat("%v / %m 秒")
        layout.addWidget(self.duration_progress)

        # 止损预警线
        self.stop_loss_label = QLabel("止损线: --")
        self.stop_loss_label.setStyleSheet("color: #e74c3c;")
        layout.addWidget(self.stop_loss_label)

        # 止盈预警线
        self.take_profit_label = QLabel("止盈线: --")
        self.take_profit_label.setStyleSheet("color: #27ae60;")
        layout.addWidget(self.take_profit_label)

    def update_warning(self, position_info: Dict):
        """更新预警信息"""
        # 根据盈亏设置预警
        unrealized_pnl = position_info.get('unrealized_pnl', 0)
        stop_loss = position_info.get('stop_loss', 0)
        take_profit = position_info.get('take_profit', 0)

        # 设置止损止盈线
        if stop_loss != 0:
            self.stop_loss_label.setText(f"止损线: {stop_loss:.2f}")
        else:
            self.stop_loss_label.setText("止损线: --")

        if take_profit != 0:
            self.take_profit_label.setText(f"止盈线: {take_profit:.2f}")
        else:
            self.take_profit_label.setText("止盈线: --")

        # 预警判断
        warnings = []

        if stop_loss != 0 and unrealized_pnl <= stop_loss:
            warnings.append("⚠️ 触及止损线！")

        if take_profit != 0 and unrealized_pnl >= take_profit:
            warnings.append("✓ 触及止盈线！")

        # 持仓时长预警
        hold_seconds = position_info.get('hold_seconds', 0)
        max_hold_time = position_info.get('max_hold_time', 0)

        if max_hold_time > 0:
            self.duration_progress.setMaximum(max_hold_time)
            self.duration_progress.setValue(hold_seconds)

            ratio = hold_seconds / max_hold_time
            if ratio >= 0.9:
                warnings.append("⏰ 持仓时长接近上限！")
            elif ratio >= 1.0:
                warnings.append("🔴 持仓时长已超限！")
        else:
            self.duration_progress.setMaximum(100)
            self.duration_progress.setValue(0)

        # 更新预警显示
        if warnings:
            warning_text = " | ".join(warnings)
            self.warning_label.setText(warning_text)
            self.warning_label.setStyleSheet("""
                font-size: 14px;
                color: #e74c3c;
                background-color: #fadbd8;
                padding: 10px;
                border-radius: 5px;
                border-left: 4px solid #e74c3c;
            """)
        else:
            self.warning_label.setText("✓ 持仓正常")
            self.warning_label.setStyleSheet("""
                font-size: 14px;
                color: #27ae60;
                background-color: #d5f4e6;
                padding: 10px;
                border-radius: 5px;
                border-left: 4px solid #27ae60;
            """)


class PositionPanel(QWidget):
    """持仓监控主面板（优化版）"""

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_timer()
        self.open_time = None

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 标题
        title_layout = QHBoxLayout()
        title_label = QLabel("持仓监控")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 状态指示
        self.status_indicator = QLabel("无持仓")
        self.status_indicator.setStyleSheet("""
            font-size: 12px;
            color: white;
            background-color: #95a5a6;
            padding: 5px 10px;
            border-radius: 3px;
        """)
        title_layout.addWidget(self.status_indicator)

        layout.addLayout(title_layout)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # 左侧：持仓详情和预警
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        self.position_detail = PositionDetailWidget()
        left_layout.addWidget(self.position_detail)

        self.position_warning = PositionWarningWidget()
        left_layout.addWidget(self.position_warning)

        left_layout.addStretch()
        splitter.addWidget(left_widget)

        # 右侧：盈亏分析
        self.position_pnl = PositionPnLWidget()
        splitter.addWidget(self.position_pnl)

        # 设置分割比例
        splitter.setSizes([400, 300])

    def setup_timer(self):
        """设置定时刷新"""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_hold_duration)
        self.refresh_timer.start(1000)  # 每秒刷新一次

    def update_position(self, position_info: Dict):
        """更新持仓信息"""
        try:
            quantity = position_info.get('quantity', 0)

            # 更新状态指示
            if quantity > 0:
                self.status_indicator.setText("有持仓")
                self.status_indicator.setStyleSheet("""
                    font-size: 12px;
                    color: white;
                    background-color: #e74c3c;
                    padding: 5px 10px;
                    border-radius: 3px;
                """)

                # 记录开仓时间
                if position_info.get('open_time'):
                    self.open_time = position_info['open_time']
            else:
                self.status_indicator.setText("无持仓")
                self.status_indicator.setStyleSheet("""
                    font-size: 12px;
                    color: white;
                    background-color: #95a5a6;
                    padding: 5px 10px;
                    border-radius: 3px;
                """)
                self.open_time = None

            # 更新详情
            self.position_detail.update_position(position_info)

            # 更新盈亏
            self.position_pnl.update_pnl(position_info)

            # 更新预警
            self.position_warning.update_warning(position_info)

        except Exception as e:
            print(f"更新持仓信息失败: {e}")

    def _refresh_hold_duration(self):
        """刷新持仓时长"""
        if self.open_time:
            try:
                open_dt = datetime.fromisoformat(self.open_time.replace('T', ' '))
                duration = datetime.now() - open_dt

                hours = duration.seconds // 3600
                minutes = (duration.seconds % 3600) // 60
                seconds = duration.seconds % 60

                duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                self.position_detail.update_hold_duration(duration_str)

            except Exception as e:
                pass

    def clear_all_data(self):
        """清空所有数据"""
        # 重置详情
        self.position_detail.strategy_label.setText("--")
        self.position_detail.quantity_label.setText("0")
        self.position_detail.quantity_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        self.position_detail.avg_price_label.setText("0.0000")
        self.position_detail.market_price_label.setText("0.0000")
        self.position_detail.side_label.setText("无")
        self.position_detail.side_label.setStyleSheet("color: #95a5a6; font-size: 16px;")
        self.position_detail.open_time_label.setText("--:--:--")
        self.position_detail.hold_duration_label.setText("00:00:00")

        # 重置盈亏
        self.position_pnl.unrealized_pnl_label.setText("0.00")
        self.position_pnl.unrealized_pnl_label.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 8px;
            min-width: 150px;
        """)
        self.position_pnl.max_profit_label.setText("0.00")
        self.position_pnl.max_loss_label.setText("0.00")
        self.position_pnl.pnl_ratio_label.setText("0.00%")
        self.position_pnl.est_close_pnl_label.setText("0.00")

        # 重置预警
        self.position_warning.warning_label.setText("无预警")
        self.position_warning.warning_label.setStyleSheet("""
            font-size: 14px;
            color: #27ae60;
            background-color: #d5f4e6;
            padding: 10px;
            border-radius: 5px;
            border-left: 4px solid #27ae60;
        """)
        self.position_warning.duration_progress.setValue(0)
        self.position_warning.stop_loss_label.setText("止损线: --")
        self.position_warning.take_profit_label.setText("止盈线: --")

        # 重置状态
        self.status_indicator.setText("无持仓")
        self.status_indicator.setStyleSheet("""
            font-size: 12px;
            color: white;
            background-color: #95a5a6;
            padding: 5px 10px;
            border-radius: 3px;
        """)

        self.open_time = None
