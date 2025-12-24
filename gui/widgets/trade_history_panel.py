"""
交易历史面板
从数据库加载并展示交易记录，支持筛选和导出功能
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QGroupBox, QPushButton, QDateEdit, QComboBox,
                             QLineEdit, QCheckBox, QFileDialog, QMessageBox,
                             QMenu, QAction, QInputDialog, QDialog, QFormLayout,
                             QSpinBox, QProgressBar, QSplitter, QTextEdit)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QColor, QBrush
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from database import get_database


class TradeFilterWidget(QGroupBox):
    """交易筛选组件"""

    # 定义信号
    filter_changed = pyqtSignal(dict)

    def __init__(self):
        super().__init__("筛选条件")
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        # 日期范围
        date_layout = QHBoxLayout()

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        date_layout.addWidget(QLabel("起始日期:"))
        date_layout.addWidget(self.start_date)

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        date_layout.addWidget(QLabel("结束日期:"))
        date_layout.addWidget(self.end_date)

        layout.addRow(date_layout)

        # 策略筛选
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem("全部策略", "")
        self.strategy_combo.currentIndexChanged.connect(self._on_filter_changed)
        layout.addRow("策略:", self.strategy_combo)

        # 信号类型筛选
        self.signal_type_combo = QComboBox()
        self.signal_type_combo.addItem("全部类型", "")
        self.signal_type_combo.addItem("买入开仓", "BUY_TO_OPEN")
        self.signal_type_combo.addItem("卖出开仓", "SELL_TO_OPEN")
        self.signal_type_combo.addItem("买入平仓", "BUY_TO_CLOSE")
        self.signal_type_combo.addItem("卖出平仓", "SELL_TO_CLOSE")
        self.signal_type_combo.currentIndexChanged.connect(self._on_filter_changed)
        layout.addRow("信号类型:", self.signal_type_combo)

        # 状态筛选
        self.status_combo = QComboBox()
        self.status_combo.addItem("全部状态", "")
        self.status_combo.addItem("已完成", "completed")
        self.status_combo.addItem("待成交", "pending")
        self.status_combo.addItem("已取消", "cancelled")
        self.status_combo.currentIndexChanged.connect(self._on_filter_changed)
        layout.addRow("状态:", self.status_combo)

        # 限制数量
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(10, 10000)
        self.limit_spin.setValue(500)
        self.limit_spin.setSuffix(" 条")
        self.limit_spin.valueChanged.connect(self._on_filter_changed)
        layout.addRow("显示数量:", self.limit_spin)

        # 应用筛选按钮
        self.apply_btn = QPushButton("应用筛选")
        self.apply_btn.clicked.connect(self._on_filter_changed)
        layout.addRow(self.apply_btn)

        # 重置按钮
        self.reset_btn = QPushButton("重置")
        self.reset_btn.clicked.connect(self._reset_filters)
        layout.addRow(self.reset_btn)

    def _on_filter_changed(self):
        """筛选条件变化"""
        filters = self.get_filters()
        self.filter_changed.emit(filters)

    def _reset_filters(self):
        """重置筛选条件"""
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.end_date.setDate(QDate.currentDate())
        self.strategy_combo.setCurrentIndex(0)
        self.signal_type_combo.setCurrentIndex(0)
        self.status_combo.setCurrentIndex(0)
        self.limit_spin.setValue(500)

    def get_filters(self) -> Dict:
        """获取当前筛选条件"""
        return {
            'start_date': self.start_date.date().toString("yyyy-MM-dd"),
            'end_date': self.end_date.date().toString("yyyy-MM-dd"),
            'strategy_name': self.strategy_combo.currentData(),
            'signal_type': self.signal_type_combo.currentData(),
            'status': self.status_combo.currentData(),
            'limit': self.limit_spin.value()
        }

    def update_strategy_list(self, strategies: List[str]):
        """更新策略列表"""
        current_text = self.strategy_combo.currentText()
        self.strategy_combo.clear()
        self.strategy_combo.addItem("全部策略", "")

        for strategy in strategies:
            self.strategy_combo.addItem(strategy, strategy)

        # 恢复之前的选择
        index = self.strategy_combo.findText(current_text)
        if index >= 0:
            self.strategy_combo.setCurrentIndex(index)


class TradeStatisticsWidget(QGroupBox):
    """交易统计组件"""

    def __init__(self):
        super().__init__("统计信息")
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        # 总交易次数
        self.total_trades_label = QLabel("0")
        self.total_trades_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addRow("总交易次数:", self.total_trades_label)

        # 总盈亏
        self.total_pnl_label = QLabel("0.00")
        self.total_pnl_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #27ae60;")
        layout.addRow("总盈亏:", self.total_pnl_label)

        # 胜率
        self.win_rate_label = QLabel("0.00%")
        self.win_rate_label.setStyleSheet("font-size: 14px;")
        layout.addRow("胜率:", self.win_rate_label)

        # 最大盈利
        self.max_profit_label = QLabel("0.00")
        self.max_profit_label.setStyleSheet("color: #27ae60;")
        layout.addRow("最大盈利:", self.max_profit_label)

        # 最大亏损
        self.max_loss_label = QLabel("0.00")
        self.max_loss_label.setStyleSheet("color: #e74c3c;")
        layout.addRow("最大亏损:", self.max_loss_label)

    def update_statistics(self, trades: List[Dict]):
        """更新统计信息"""
        if not trades:
            self.total_trades_label.setText("0")
            self.total_pnl_label.setText("0.00")
            self.win_rate_label.setText("0.00%")
            self.max_profit_label.setText("0.00")
            self.max_loss_label.setText("0.00")
            return

        total_trades = len(trades)
        total_pnl = sum(t.get('pnl', 0) for t in trades)

        # 计算胜率（只统计有盈亏的交易）
        close_trades = [t for t in trades if t.get('pnl', 0) != 0]
        win_count = sum(1 for t in close_trades if t.get('pnl', 0) > 0)
        win_rate = win_count / len(close_trades) if close_trades else 0

        # 最大盈利和亏损
        pnls = [t.get('pnl', 0) for t in close_trades]
        max_profit = max(pnls) if pnls else 0
        max_loss = min(pnls) if pnls else 0

        # 更新显示
        self.total_trades_label.setText(str(total_trades))

        self.total_pnl_label.setText(f"{total_pnl:.2f}")
        if total_pnl > 0:
            self.total_pnl_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #27ae60;")
        elif total_pnl < 0:
            self.total_pnl_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c;")
        else:
            self.total_pnl_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")

        self.win_rate_label.setText(f"{win_rate:.2%}")
        self.max_profit_label.setText(f"{max_profit:.2f}")
        self.max_loss_label.setText(f"{max_loss:.2f}")


class TradeTableWidget(QTableWidget):
    """交易表格组件"""

    # 定义信号
    trade_selected = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.trades_data = []

    def init_ui(self):
        """初始化表格"""
        # 设置列
        self.setColumnCount(12)
        self.setHorizontalHeaderLabels([
            "时间", "策略", "信号类型", "方向", "开平仓",
            "价格", "数量", "盈亏", "状态", "原因", "合约", "ID"
        ])

        # 设置列宽
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 时间
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 策略
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 信号类型
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 方向
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 开平仓
        header.setSectionResizeMode(5, QHeaderView.Stretch)           # 价格
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 数量
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # 盈亏
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # 状态
        header.setSectionResizeMode(9, QHeaderView.Stretch)           # 原因
        header.setSectionResizeMode(10, QHeaderView.ResizeToContents) # 合约
        header.setSectionResizeMode(11, QHeaderView.ResizeToContents) # ID

        # 设置表格属性
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSortingEnabled(True)

        # 连接选择事件
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def load_trades(self, trades: List[Dict]):
        """加载交易数据"""
        self.trades_data = trades
        self.setRowCount(0)

        for trade in trades:
            self._add_trade_row(trade)

    def _add_trade_row(self, trade: Dict):
        """添加交易行"""
        row = self.rowCount()
        self.insertRow(row)

        # 格式化时间
        timestamp = trade.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('T', ' '))
                time_str = dt.strftime("%m-%d %H:%M:%S")
            except:
                time_str = timestamp[:19]
        else:
            time_str = '--'

        # 设置单元格内容
        self.setItem(row, 0, QTableWidgetItem(time_str))
        self.setItem(row, 1, QTableWidgetItem(trade.get('strategy_name', '--')))
        self.setItem(row, 2, QTableWidgetItem(self._get_signal_type_name(trade.get('signal_type', ''))))
        self.setItem(row, 3, QTableWidgetItem(trade.get('direction', '--')))
        self.setItem(row, 4, QTableWidgetItem(trade.get('position_type', '--')))
        self.setItem(row, 5, QTableWidgetItem(f"{trade.get('price', 0):.4f}"))
        self.setItem(row, 6, QTableWidgetItem(str(trade.get('quantity', 0))))

        # 盈亏（带颜色）
        pnl = trade.get('pnl', 0)
        pnl_item = QTableWidgetItem(f"{pnl:.2f}")
        if pnl > 0:
            pnl_item.setForeground(QBrush(QColor("#27ae60")))
        elif pnl < 0:
            pnl_item.setForeground(QBrush(QColor("#e74c3c")))
        self.setItem(row, 7, pnl_item)

        # 状态（带颜色）
        status = trade.get('status', 'completed')
        status_item = QTableWidgetItem(self._get_status_name(status))
        if status == 'completed':
            status_item.setForeground(QBrush(QColor("#27ae60")))
        elif status == 'pending':
            status_item.setForeground(QBrush(QColor("#f39c12")))
        elif status == 'cancelled':
            status_item.setForeground(QBrush(QColor("#e74c3c")))
        self.setItem(row, 8, status_item)

        self.setItem(row, 9, QTableWidgetItem(trade.get('reason', '')[:50]))  # 截断长文本
        self.setItem(row, 10, QTableWidgetItem(trade.get('contract_code', '--')))
        self.setItem(row, 11, QTableWidgetItem(str(trade.get('id', ''))))

    def _get_signal_type_name(self, signal_type: str) -> str:
        """获取信号类型中文名"""
        mapping = {
            'BUY_TO_OPEN': '买入开仓',
            'SELL_TO_OPEN': '卖出开仓',
            'BUY_TO_CLOSE': '买入平仓',
            'SELL_TO_CLOSE': '卖出平仓',
            'NO_SIGNAL': '无信号'
        }
        return mapping.get(signal_type, signal_type)

    def _get_status_name(self, status: str) -> str:
        """获取状态中文名"""
        mapping = {
            'completed': '已完成',
            'pending': '待成交',
            'cancelled': '已取消'
        }
        return mapping.get(status, status)

    def _on_selection_changed(self):
        """选择变化事件"""
        current_row = self.currentRow()
        if current_row >= 0 and current_row < len(self.trades_data):
            # 找到对应的交易数据（考虑排序）
            trade_id_item = self.item(current_row, 11)
            if trade_id_item:
                trade_id = int(trade_id_item.text())
                for trade in self.trades_data:
                    if trade.get('id') == trade_id:
                        self.trade_selected.emit(trade)
                        break


class TradeHistoryPanel(QWidget):
    """交易历史主面板"""

    # 定义信号
    export_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.db = get_database()
        self.init_ui()
        self.load_data()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 标题和导出按钮
        title_layout = QHBoxLayout()
        title_label = QLabel("交易历史")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        self.export_btn = QPushButton("导出Excel")
        self.export_btn.clicked.connect(self._export_to_excel)
        title_layout.addWidget(self.export_btn)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_data)
        title_layout.addWidget(self.refresh_btn)

        layout.addLayout(title_layout)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # 左侧：筛选和统计
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        self.filter_widget = TradeFilterWidget()
        self.filter_widget.filter_changed.connect(self._on_filter_changed)
        left_layout.addWidget(self.filter_widget)

        self.statistics_widget = TradeStatisticsWidget()
        left_layout.addWidget(self.statistics_widget)

        left_layout.addStretch()
        splitter.addWidget(left_widget)

        # 右侧：交易表格
        self.trade_table = TradeTableWidget()
        splitter.addWidget(self.trade_table)

        # 设置分割比例
        splitter.setSizes([250, 750])

        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(self.status_label)

    def load_data(self, filters: Dict = None):
        """加载数据"""
        try:
            if filters is None:
                filters = self.filter_widget.get_filters()

            # 从数据库获取交易记录
            trades = self.db.get_trades(
                strategy_name=filters.get('strategy_name') or None,
                start_date=filters.get('start_date'),
                end_date=filters.get('end_date'),
                limit=filters.get('limit')
            )

            # 按信号类型和状态筛选
            if filters.get('signal_type'):
                trades = [t for t in trades if t.get('signal_type') == filters.get('signal_type')]
            if filters.get('status'):
                trades = [t for t in trades if t.get('status') == filters.get('status')]

            # 加载到表格
            self.trade_table.load_trades(trades)

            # 更新统计
            self.statistics_widget.update_statistics(trades)

            # 更新状态
            self.status_label.setText(f"共 {len(trades)} 条记录")

        except Exception as e:
            self.status_label.setText(f"加载失败: {e}")

    def _on_filter_changed(self, filters: Dict):
        """筛选条件变化"""
        self.load_data(filters)

    def _export_to_excel(self):
        """导出到Excel"""
        try:
            # 获取筛选条件
            filters = self.filter_widget.get_filters()

            # 选择保存路径
            default_name = f"交易记录_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出交易记录", default_name, "Excel文件 (*.xlsx)"
            )

            if not file_path:
                return

            # 导出
            success = self.db.export_to_excel(
                file_path,
                start_date=filters.get('start_date'),
                end_date=filters.get('end_date'),
                strategy_name=filters.get('strategy_name') or None
            )

            if success:
                QMessageBox.information(self, "成功", f"交易记录已导出到:\n{file_path}")
            else:
                QMessageBox.warning(self, "警告", "导出失败或没有数据可导出")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {e}")

    def add_trade(self, trade_info: Dict):
        """添加新交易记录"""
        try:
            # 添加到数据库
            self.db.add_trade(trade_info)

            # 刷新显示
            self.load_data()

        except Exception as e:
            print(f"添加交易记录失败: {e}")

    def refresh(self):
        """刷新数据"""
        self.load_data()

    def update_strategy_list(self, strategies: List[str]):
        """更新策略列表"""
        self.filter_widget.update_strategy_list(strategies)
