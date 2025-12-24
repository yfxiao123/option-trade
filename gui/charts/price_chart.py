"""
价格走势图表组件
使用pyqtgraph绘制实时价格走势图
"""

import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg
from collections import deque
from datetime import datetime


class PriceChart(QWidget):
    """价格走势图表"""

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.init_data()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 标题
        title_layout = QHBoxLayout()
        title_label = QLabel("价格走势图")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 时间范围选择
        self.time_range = "1分钟"  # 默认1分钟
        self.time_label = QLabel(f"时间范围: {self.time_range}")
        title_layout.addWidget(self.time_label)

        layout.addLayout(title_layout)

        # 创建图表
        self.plot_widget = pg.PlotWidget()
        self.setup_plot()
        layout.addWidget(self.plot_widget)

    def init_data(self):
        """初始化数据"""
        # 数据存储（使用deque限制长度）
        self.max_points = 1000
        self.timestamps = deque(maxlen=self.max_points)
        self.bid_prices = deque(maxlen=self.max_points)
        self.ask_prices = deque(maxlen=self.max_points)
        self.mid_prices = deque(maxlen=self.max_points)

        # 数据计数
        self.data_count = 0

    def setup_plot(self):
        """设置图表"""
        # 设置背景色
        self.plot_widget.setBackground('#2c3e50')

        # 隐藏鼠标坐标
        self.plot_widget.hideAxis('left')

        # 设置标题
        self.plot_widget.setTitle("实时价格", color='white', size='12pt')

        # 创建图例
        self.plot_widget.addLegend()

        # 创建三条线
        self.bid_line = self.plot_widget.plot(
            pen=pg.mkPen(color='#27ae60', width=2),
            name='买一价'
        )
        self.ask_line = self.plot_widget.plot(
            pen=pg.mkPen(color='#e74c3c', width=2),
            name='卖一价'
        )
        self.mid_line = self.plot_widget.plot(
            pen=pg.mkPen(color='#3498db', width=1, style=Qt.DashLine),
            name='中间价'
        )

        # 设置X轴
        self.plot_widget.setLabel('bottom', '时间', units='')

        # 添加网格
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # 添加十字线
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('w', width=1, style=Qt.DashLine))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('w', width=1, style=Qt.DashLine))
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        self.plot_widget.addItem(self.hLine, ignoreBounds=True)

        # 鼠标移动事件
        self.proxy = pg.SignalProxy(self.plot_widget.scene().sigMouseMoved, rateLimit=60, slot=self.mouse_moved)

        # 设置Y轴范围
        self.y_range = None
        self.auto_range = True

    def mouse_moved(self, evt):
        """鼠标移动事件"""
        pos = evt[0]
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            index = int(mouse_point.x())

            if 0 <= index < len(self.timestamps):
                self.vLine.setPos(mouse_point.x())
                self.hLine.setPos(mouse_point.y())

                # 显示价格信息
                timestamp = self.timestamps[index]
                bid = self.bid_prices[index]
                ask = self.ask_prices[index]

                # 更新标题显示当前价格
                self.plot_widget.setTitle(
                    f"实时价格 - 时间: {timestamp} | 买一: {bid:.4f} | 卖一: {ask:.4f}",
                    color='white', size='10pt'
                )

    def add_data_point(self, market_data):
        """添加数据点"""
        try:
            if not market_data.get('bid') or not market_data.get('ask'):
                return

            # 获取数据
            timestamp = market_data.get('timestamp', datetime.now().strftime("%H:%M:%S"))
            bid = market_data['bid']
            ask = market_data['ask']
            mid = market_data.get('mid_price', (bid + ask) / 2)

            # 添加到数据
            self.timestamps.append(timestamp)
            self.bid_prices.append(bid)
            self.ask_prices.append(ask)
            self.mid_prices.append(mid)

            self.data_count += 1

            # 更新图表
            self.update_chart()

        except Exception as e:
            print(f"添加数据点失败: {e}")

    def update_chart(self):
        """更新图表"""
        if len(self.timestamps) == 0:
            return

        # 创建X轴数据（索引）
        x_data = list(range(len(self.timestamps)))

        # 更新线条数据
        self.bid_line.setData(x_data, list(self.bid_prices))
        self.ask_line.setData(x_data, list(self.ask_prices))
        self.mid_line.setData(x_data, list(self.mid_prices))

        # 自动调整Y轴范围
        if self.auto_range or self.data_count < 10:
            all_prices = list(self.bid_prices) + list(self.ask_prices)
            if all_prices:
                min_price = min(all_prices)
                max_price = max(all_prices)
                padding = (max_price - min_price) * 0.1
                self.plot_widget.setYRange(min_price - padding, max_price + padding)
                self.y_range = (min_price - padding, max_price + padding)

        # 设置X轴范围（显示最近的数据）
        if len(x_data) > 100:
            self.plot_widget.setXRange(len(x_data) - 100, len(x_data))

    def clear_chart(self):
        """清空图表"""
        self.timestamps.clear()
        self.bid_prices.clear()
        self.ask_prices.clear()
        self.mid_prices.clear()
        self.data_count = 0

        # 清空图表
        self.bid_line.clear()
        self.ask_line.clear()
        self.mid_line.clear()

    def set_time_range(self, time_range):
        """设置时间范围"""
        self.time_range = time_range
        self.time_label.setText(f"时间范围: {time_range}")

        # 根据时间范围调整显示的点数
        ranges = {
            "30秒": 30,
            "1分钟": 60,
            "5分钟": 300,
            "10分钟": 600,
            "30分钟": 1800,
            "1小时": 3600
        }

        if time_range in ranges:
            # TODO: 根据时间范围过滤数据
            pass

    def toggle_auto_range(self, enabled):
        """切换自动范围"""
        self.auto_range = enabled

    def export_data(self):
        """导出数据"""
        try:
            import pandas as pd

            if len(self.timestamps) == 0:
                return

            # 创建DataFrame
            df = pd.DataFrame({
                '时间': list(self.timestamps),
                '买一价': list(self.bid_prices),
                '卖一价': list(self.ask_prices),
                '中间价': list(self.mid_prices)
            })

            # 保存到CSV
            filename = f"price_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')

            return filename

        except Exception as e:
            print(f"导出数据失败: {e}")
            return None