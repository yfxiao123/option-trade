"""
市场行情面板（重写版）
整合市场行情、价格走势图和成交量，参考同花顺/东方财富风格
"""

import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QGridLayout, QFrame, QGroupBox, QSplitter)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor
from collections import deque
from datetime import datetime
import pyqtgraph as pg


class PriceBoardWidget(QGroupBox):
    """价格板组件 - 显示当前价格信息（大字显示）"""

    def __init__(self):
        super().__init__("实时行情")
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout(self)

        # 合约名称
        self.contract_label = QLabel("--")
        self.contract_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(self.contract_label, 0, 0, 1, 2)

        # 最新价（大字显示）
        self.price_label = QLabel("0.0000")
        self.price_label.setStyleSheet("""
            font-size: 36px;
            font-weight: bold;
            color: #2c3e50;
            background-color: #ecf0f1;
            padding: 10px;
            border-radius: 5px;
            min-width: 150px;
        """)
        self.price_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.price_label, 1, 0)

        # 涨跌幅
        self.change_label = QLabel("0.00%")
        self.change_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #95a5a6;
            background-color: #ecf0f1;
            padding: 10px;
            border-radius: 5px;
            min-width: 80px;
        """)
        self.change_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.change_label, 1, 1)

        # 买卖价
        bid_ask_layout = QGridLayout()
        bid_ask_layout.addWidget(QLabel("买一:"), 0, 0)
        self.bid_label = QLabel("0.0000")
        self.bid_label.setStyleSheet("font-size: 18px; color: #27ae60; font-weight: bold;")
        bid_ask_layout.addWidget(self.bid_label, 0, 1)

        bid_ask_layout.addWidget(QLabel("卖一:"), 1, 0)
        self.ask_label = QLabel("0.0000")
        self.ask_label.setStyleSheet("font-size: 18px; color: #e74c3c; font-weight: bold;")
        bid_ask_layout.addWidget(self.ask_label, 1, 1)

        layout.addLayout(bid_ask_layout, 2, 0, 1, 2)

        # 其他信息
        info_layout = QGridLayout()
        info_layout.addWidget(QLabel("成交量:"), 0, 0)
        self.volume_label = QLabel("0")
        info_layout.addWidget(self.volume_label, 0, 1)

        info_layout.addWidget(QLabel("持仓量:"), 0, 2)
        self.oi_label = QLabel("0")
        info_layout.addWidget(self.oi_label, 0, 3)

        info_layout.addWidget(QLabel("更新时间:"), 1, 0)
        self.time_label = QLabel("--:--:--")
        info_layout.addWidget(self.time_label, 1, 1, 1, 3)

        layout.addLayout(info_layout, 3, 0, 1, 2)

    def update_price(self, bid: float, ask: float, mid: float, change: float = 0):
        """更新价格显示"""
        self.bid_label.setText(f"{bid:.4f}")
        self.ask_label.setText(f"{ask:.4f}")
        self.price_label.setText(f"{mid:.4f}")

        # 更新颜色
        if change > 0:
            color = "#e74c3c"  # 红色上涨
        elif change < 0:
            color = "#27ae60"  # 绿色下跌
        else:
            color = "#2c3e50"  # 无变化

        self.price_label.setStyleSheet(f"""
            font-size: 36px;
            font-weight: bold;
            color: {color};
            background-color: #ecf0f1;
            padding: 10px;
            border-radius: 5px;
            min-width: 150px;
        """)

        # 更新涨跌幅
        self.change_label.setText(f"{change:.2%}")
        self.change_label.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {color};
            background-color: #ecf0f1;
            padding: 10px;
            border-radius: 5px;
            min-width: 80px;
        """)

    def update_info(self, volume: int = 0, oi: int = 0, timestamp: str = ""):
        """更新其他信息"""
        self.volume_label.setText(f"{volume:,}")
        self.oi_label.setText(f"{oi:,}")
        self.time_label.setText(timestamp)

    def set_contract(self, name: str):
        """设置合约名称"""
        self.contract_label.setText(name)


class OrderBookWidget(QGroupBox):
    """五档行情组件"""

    def __init__(self):
        super().__init__("五档行情")
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout(self)

        # 表头
        layout.addWidget(QLabel("方向"), 0, 0)
        layout.addWidget(QLabel("价格"), 0, 1)
        layout.addWidget(QLabel("数量"), 0, 2)

        # 卖盘（红色）
        self.sell_prices = []
        self.sell_volumes = []
        for i in range(5):
            label = QLabel(f"卖{5-i}")
            label.setStyleSheet("color: #e74c3c;")
            layout.addWidget(label, i + 1, 0)

            price = QLabel("--")
            price.setStyleSheet("color: #e74c3c; font-weight: bold;")
            price.setAlignment(Qt.AlignRight)
            layout.addWidget(price, i + 1, 1)
            self.sell_prices.append(price)

            volume = QLabel("--")
            volume.setStyleSheet("color: #e74c3c;")
            volume.setAlignment(Qt.AlignRight)
            layout.addWidget(volume, i + 1, 2)
            self.sell_volumes.append(volume)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line, 6, 0, 1, 3)

        # 买盘（绿色）
        self.buy_prices = []
        self.buy_volumes = []
        for i in range(5):
            label = QLabel(f"买{i+1}")
            label.setStyleSheet("color: #27ae60;")
            layout.addWidget(label, i + 7, 0)

            price = QLabel("--")
            price.setStyleSheet("color: #27ae60; font-weight: bold;")
            price.setAlignment(Qt.AlignRight)
            layout.addWidget(price, i + 7, 1)
            self.buy_prices.append(price)

            volume = QLabel("--")
            volume.setStyleSheet("color: #27ae60;")
            volume.setAlignment(Qt.AlignRight)
            layout.addWidget(volume, i + 7, 2)
            self.buy_volumes.append(volume)

    def update_sell(self, prices: list, volumes: list):
        """更新卖盘"""
        for i in range(min(5, len(prices))):
            self.sell_prices[i].setText(f"{prices[i]:.4f}")
            self.sell_volumes[i].setText(f"{volumes[i]}")

    def update_buy(self, prices: list, volumes: list):
        """更新买盘"""
        for i in range(min(5, len(prices))):
            self.buy_prices[i].setText(f"{prices[i]:.4f}")
            self.buy_volumes[i].setText(f"{volumes[i]}")


class PriceVolumeChartWidget(QGroupBox):
    """价格成交量图表组件 - 整合价格图和成交量"""

    def __init__(self):
        super().__init__("价格走势")
        self.init_ui()
        self.init_data()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 创建图表区域（上下分割）
        self.chart_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(self.chart_splitter)

        # 价格图表（主图）
        self.price_plot = pg.PlotWidget()
        self.setup_price_plot()
        self.chart_splitter.addWidget(self.price_plot)

        # 成交量图表（副图）
        self.volume_plot = pg.PlotWidget()
        self.setup_volume_plot()
        self.chart_splitter.addWidget(self.volume_plot)

        # 设置分割比例（价格图占75%，成交量占25%）
        self.chart_splitter.setSizes([300, 100])

    def init_data(self):
        """初始化数据存储"""
        self.max_points = 1000
        self.timestamps = deque(maxlen=self.max_points)
        self.bid_prices = deque(maxlen=self.max_points)
        self.ask_prices = deque(maxlen=self.max_points)
        self.mid_prices = deque(maxlen=self.max_points)
        self.volumes = deque(maxlen=self.max_points)

        self.data_count = 0

    def setup_price_plot(self):
        """设置价格图表"""
        # 设置背景色
        self.price_plot.setBackground('#2c3e50')

        # 隐藏自动范围
        self.price_plot.enableAutoRange(axis='y')

        # 设置标题
        self.price_plot.setTitle("价格", color='white', size='10pt')

        # 创建图例
        self.price_plot.addLegend(offset=(10, 10))

        # 创建三条价格线
        self.bid_line = self.price_plot.plot(
            pen=pg.mkPen(color='#27ae60', width=2),
            name='买一价'
        )
        self.ask_line = self.price_plot.plot(
            pen=pg.mkPen(color='#e74c3c', width=2),
            name='卖一价'
        )
        self.mid_line = self.price_plot.plot(
            pen=pg.mkPen(color='#f1c40f', width=1),
            name='中间价'
        )

        # 设置坐标轴
        self.price_plot.setLabel('left', '价格', units='')
        self.price_plot.setLabel('bottom', '时间')

        # 添加网格
        self.price_plot.showGrid(x=True, y=True, alpha=0.3)

        # 十字线
        self.vLine_price = pg.InfiniteLine(angle=90, movable=False,
                                             pen=pg.mkPen('w', width=1, style=Qt.DashLine))
        self.hLine_price = pg.InfiniteLine(angle=0, movable=False,
                                            pen=pg.mkPen('w', width=1, style=Qt.DashLine))
        self.price_plot.addItem(self.vLine_price, ignoreBounds=True)
        self.price_plot.addItem(self.hLine_price, ignoreBounds=True)

    def setup_volume_plot(self):
        """设置成交量图表"""
        # 设置背景色
        self.volume_plot.setBackground('#2c3e50')

        # 设置标题
        self.volume_plot.setTitle("成交量", color='white', size='10pt')

        # 创建成交量柱状图
        self.volume_bar = pg.BarGraphItem(x=[], height=[], width=0.8, brush='#3498db')
        self.volume_plot.addItem(self.volume_bar)

        # 设置坐标轴
        self.volume_plot.setLabel('left', '成交量', units='')
        self.volume_plot.setLabel('bottom', '时间')

        # 添加网格
        self.volume_plot.showGrid(x=True, y=True, alpha=0.3)

        # 隐藏Y轴刻度（与价格图共享X轴）
        # self.volume_plot.getAxis('bottom').setStyle(showValues=False)

    def add_data_point(self, market_data: dict):
        """添加数据点"""
        try:
            if not market_data.get('bid') or not market_data.get('ask'):
                return

            # 获取数据
            timestamp = market_data.get('timestamp', datetime.now().strftime("%H:%M:%S"))
            bid = market_data['bid']
            ask = market_data['ask']
            mid = market_data.get('mid_price', (bid + ask) / 2)
            volume = market_data.get('volume', 0)

            # 添加到数据
            self.timestamps.append(timestamp)
            self.bid_prices.append(bid)
            self.ask_prices.append(ask)
            self.mid_prices.append(mid)
            self.volumes.append(volume)

            self.data_count += 1

            # 更新图表
            self.update_charts()

        except Exception as e:
            print(f"添加数据点失败: {e}")

    def update_charts(self):
        """更新图表"""
        if len(self.timestamps) == 0:
            return

        # 创建X轴数据（索引）
        x_data = np.arange(len(self.timestamps))

        # 更新价格线
        self.bid_line.setData(x_data, list(self.bid_prices))
        self.ask_line.setData(x_data, list(self.ask_prices))
        self.mid_line.setData(x_data, list(self.mid_prices))

        # 更新成交量柱状图
        self.volume_bar.setOpts(x=x_data, height=list(self.volumes))

        # 自动调整Y轴范围
        all_prices = list(self.bid_prices) + list(self.ask_prices)
        if all_prices:
            min_price = min(all_prices)
            max_price = max(all_prices)
            padding = (max_price - min_price) * 0.1 if max_price > min_price else max_price * 0.01
            self.price_plot.setYRange(min_price - padding, max_price + padding)

        # 成交量Y轴范围
        if self.volumes:
            max_vol = max(self.volumes)
            self.volume_plot.setYRange(0, max_vol * 1.1 if max_vol > 0 else 1)

        # 设置X轴范围（显示最近的数据）
        visible_points = 100
        if len(x_data) > visible_points:
            self.price_plot.setXRange(len(x_data) - visible_points, len(x_data))
            self.volume_plot.setXRange(len(x_data) - visible_points, len(x_data))

    def clear_charts(self):
        """清空图表"""
        self.timestamps.clear()
        self.bid_prices.clear()
        self.ask_prices.clear()
        self.mid_prices.clear()
        self.volumes.clear()
        self.data_count = 0

        self.bid_line.setData([], [])
        self.ask_line.setData([], [])
        self.mid_line.setData([], [])
        self.volume_bar.setOpts(x=[], height=[])


class MarketPanel(QWidget):
    """市场行情主面板（重写版）"""

    # 定义信号
    market_data_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_timer()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 标题
        title_layout = QHBoxLayout()
        title_label = QLabel("市场行情")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 数据状态指示
        self.status_label = QLabel("等待数据...")
        self.status_label.setStyleSheet("color: #f39c12;")
        title_layout.addWidget(self.status_label)

        layout.addLayout(title_layout)

        # 创建水平分割器
        h_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(h_splitter)

        # 左侧：价格板和五档行情
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        self.price_board = PriceBoardWidget()
        left_layout.addWidget(self.price_board)

        self.order_book = OrderBookWidget()
        left_layout.addWidget(self.order_book)

        left_layout.addStretch()
        h_splitter.addWidget(left_widget)

        # 右侧：价格成交量图表
        self.chart_widget = PriceVolumeChartWidget()
        h_splitter.addWidget(self.chart_widget)

        # 设置分割比例
        h_splitter.setSizes([300, 700])

    def setup_timer(self):
        """设置定时器"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.request_market_data)
        self.update_timer.start(500)  # 每500ms请求一次数据

    def update_market_data(self, market_data: dict):
        """更新市场数据显示"""
        try:
            # 更新价格板
            bid = market_data.get('bid', 0)
            ask = market_data.get('ask', 0)
            mid = market_data.get('mid_price', (bid + ask) / 2)
            change = market_data.get('price_change', 0)

            self.price_board.update_price(bid, ask, mid, change)
            self.price_board.update_info(
                volume=market_data.get('volume', 0),
                oi=market_data.get('open_interest', 0),
                timestamp=market_data.get('timestamp', '--:--:--')
            )

            # 更新合约名称
            if 'contract_code' in market_data:
                self.price_board.set_contract(market_data['contract_code'])

            # 更新图表
            self.chart_widget.add_data_point(market_data)

            # 更新数据状态
            if market_data.get('history_ready'):
                self.status_label.setText("数据就绪")
                self.status_label.setStyleSheet("color: #27ae60;")
            else:
                self.status_label.setText("初始化...")
                self.status_label.setStyleSheet("color: #f39c12;")

        except Exception as e:
            print(f"更新市场数据显示失败: {e}")

    def update_contract_code(self, code: str):
        """更新合约代码"""
        self.price_board.set_contract(code)

    def request_market_data(self):
        """请求市场数据"""
        self.market_data_requested.emit()

    def set_enabled(self, enabled: bool):
        """设置面板启用状态"""
        super().setEnabled(enabled)
        if enabled:
            self.update_timer.start()
        else:
            self.update_timer.stop()

    def clear_data(self):
        """清空数据"""
        self.chart_widget.clear_charts()
