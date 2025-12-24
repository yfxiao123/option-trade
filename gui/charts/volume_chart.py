"""
成交量图表组件
显示交易量和成交量统计信息
"""

import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg
from collections import deque
from datetime import datetime


class VolumeChart(QWidget):
    """成交量图表"""

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.init_data()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 标题和统计信息
        header_layout = QHBoxLayout()
        title_label = QLabel("成交量统计")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # 统计信息
        self.total_volume_label = QLabel("总量: 0")
        self.total_volume_label.setStyleSheet("color: #3498db; font-weight: bold;")
        header_layout.addWidget(self.total_volume_label)

        self.avg_volume_label = QLabel("均量: 0")
        self.avg_volume_label.setStyleSheet("color: #95a5a6;")
        header_layout.addWidget(self.avg_volume_label)

        layout.addLayout(header_layout)

        # 创建图表
        self.plot_widget = pg.PlotWidget()
        self.setup_plot()
        layout.addWidget(self.plot_widget)

    def init_data(self):
        """初始化数据"""
        # 数据存储
        self.max_points = 200  # 最近200个时间点
        self.timestamps = deque(maxlen=self.max_points)
        self.volumes = deque(maxlen=self.max_points)
        self.buy_volumes = deque(maxlen=self.max_points)
        self.sell_volumes = deque(maxlen=self.max_points)

        # 统计数据
        self.total_volume = 0
        self.tick_count = 0

        # 模拟成交量数据（实际应该从交易记录获取）
        self.simulated_volume = 0

    def setup_plot(self):
        """设置图表"""
        # 设置背景色
        self.plot_widget.setBackground('#2c3e50')

        # 设置标题
        self.plot_widget.setTitle("实时成交量", color='white', size='12pt')

        # 设置Y轴标签
        self.plot_widget.setLabel('left', '成交量', units='张')
        self.plot_widget.setLabel('bottom', '时间', units='')

        # 创建柱状图
        self.buy_bar = pg.BarGraphItem(x=[], height=[], width=0.8, brush='#27ae60', name='买入量')
        self.sell_bar = pg.BarGraphItem(x=[], height=[], width=0.8, brush='#e74c3c', name='卖出量')
        self.plot_widget.addItem(self.buy_bar)
        self.plot_widget.addItem(self.sell_bar)

        # 添加图例
        self.plot_widget.addLegend()

        # 添加网格
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # 添加平均线
        self.avg_line = self.plot_widget.plot(
            pen=pg.mkPen(color='#f39c12', width=2, style=Qt.DashLine),
            name='平均量'
        )

    def add_data_point(self, market_data):
        """添加数据点"""
        try:
            # 获取时间戳
            timestamp = market_data.get('timestamp', datetime.now().strftime("%H:%M:%S"))

            # 真实成交量应该从交易记录获取
            # 在没有真实成交时，成交量应为0
            tick_volume = 0 
            buy_volume = 0
            sell_volume = 0

            # 添加到数据
            self.timestamps.append(timestamp)
            self.volumes.append(tick_volume)
            self.buy_volumes.append(buy_volume)
            self.sell_volumes.append(sell_volume)

            # 更新统计
            self.total_volume += tick_volume
            self.tick_count += 1
            # self.simulated_volume += tick_volume  # 移除模拟变量

            # 更新图表
            self.update_chart()

            # 更新统计信息
            self.update_statistics()

        except Exception as e:
            print(f"添加成交量数据失败: {e}")

    def update_chart(self):
        """更新图表"""
        if len(self.timestamps) == 0:
            return

        # 创建X轴数据
        x_data = list(range(len(self.timestamps)))

        # 更新柱状图
        # 买入量
        self.buy_bar.setOpts(x=x_data, height=list(self.buy_volumes))

        # 卖出量（需要偏移以显示在买入量上方）
        sell_height = list(self.sell_volumes)
        self.sell_bar.setOpts(x=x_data, height=sell_height)

        # 计算并更新平均线
        if len(self.volumes) > 0:
            avg_volume = sum(self.volumes) / len(self.volumes)
            avg_data = [avg_volume] * len(x_data)
            self.avg_line.setData(x_data, avg_data)

        # 自动调整Y轴范围
        all_volumes = list(self.volumes)
        if all_volumes:
            max_volume = max(all_volumes)
            self.plot_widget.setYRange(0, max_volume * 1.2)

        # 设置X轴范围（显示最近的数据）
        if len(x_data) > 50:
            self.plot_widget.setXRange(len(x_data) - 50, len(x_data))

    def update_statistics(self):
        """更新统计信息"""
        # 更新总量
        self.total_volume_label.setText(f"总量: {self.total_volume}张")

        # 更新均量
        if self.tick_count > 0:
            avg_volume = self.total_volume / self.tick_count
            self.avg_volume_label.setText(f"均量: {avg_volume:.1f}张")

    def add_trade_volume(self, trade_info):
        """添加真实交易量（当有交易执行时调用）"""
        try:
            quantity = trade_info.get('quantity', 0)
            direction = trade_info.get('direction', '买入')
            timestamp = trade_info.get('time', datetime.now().strftime("%H:%M:%S"))

            # 更新最近时间点的成交量
            if len(self.timestamps) > 0 and self.timestamps[-1] == timestamp:
                # 同一时间点，累加成交量
                last_index = len(self.volumes) - 1
                self.volumes[last_index] += quantity
                self.total_volume += quantity

                if direction == '买入':
                    self.buy_volumes[last_index] += quantity
                else:
                    self.sell_volumes[last_index] += quantity

                # 更新显示
                self.update_chart()
                self.update_statistics()

        except Exception as e:
            print(f"添加交易量失败: {e}")

    def clear_chart(self):
        """清空图表"""
        self.timestamps.clear()
        self.volumes.clear()
        self.buy_volumes.clear()
        self.sell_volumes.clear()
        self.total_volume = 0
        self.tick_count = 0
        self.simulated_volume = 0

        # 清空图表
        self.buy_bar.setOpts(x=[], height=[])
        self.sell_bar.setOpts(x=[], height=[])
        self.avg_line.clear()

        # 重置统计信息
        self.total_volume_label.setText("总量: 0")
        self.avg_volume_label.setText("均量: 0")

    def get_volume_statistics(self):
        """获取成交量统计"""
        if len(self.volumes) == 0:
            return None

        return {
            'total_volume': self.total_volume,
            'avg_volume': self.total_volume / self.tick_count if self.tick_count > 0 else 0,
            'max_volume': max(self.volumes),
            'min_volume': min(self.volumes),
            'buy_ratio': sum(self.buy_volumes) / self.total_volume if self.total_volume > 0 else 0,
            'sell_ratio': sum(self.sell_volumes) / self.total_volume if self.total_volume > 0 else 0,
            'data_points': len(self.volumes)
        }