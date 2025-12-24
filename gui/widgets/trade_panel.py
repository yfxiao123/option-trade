"""
交易控制面板
提供手动交易功能和交易参数设置
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QSpinBox, QDoubleSpinBox,
                             QGroupBox, QComboBox, QFormLayout, QCheckBox,
                             QButtonGroup, QRadioButton, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from strategy import get_strategy_manager


class TradePanel(QWidget):
    """交易控制面板"""

    # 定义信号
    manual_trade_requested = pyqtSignal(dict)
    auto_trade_toggled = pyqtSignal(bool)
    strategy_changed = pyqtSignal(str)  # 新增：策略变更信号

    def __init__(self):
        super().__init__()
        self.strategy_manager = get_strategy_manager()
        self.init_ui()
        self.setup_strategy_refresh()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 标题
        title_label = QLabel("交易控制")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 自动交易控制
        self.create_auto_trade_control(layout)

        # 手动交易区域
        self.create_manual_trade_section(layout)

        # 交易参数设置
        self.create_trade_parameters_section(layout)

        layout.addStretch()

    def create_auto_trade_control(self, parent_layout):
        """创建自动交易控制区域"""
        group = QGroupBox("自动交易")
        group_layout = QVBoxLayout(group)

        # 自动交易开关
        self.auto_trade_checkbox = QCheckBox("启用自动交易")
        self.auto_trade_checkbox.stateChanged.connect(self.on_auto_trade_toggled)
        group_layout.addWidget(self.auto_trade_checkbox)

        # 策略选择
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(QLabel("交易策略:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.currentTextChanged.connect(self.on_strategy_changed)
        strategy_layout.addWidget(self.strategy_combo)
        group_layout.addLayout(strategy_layout)

        # 紧急停止按钮
        self.emergency_stop_btn = QPushButton("紧急停止")
        self.emergency_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.emergency_stop_btn.clicked.connect(self.on_emergency_stop)
        group_layout.addWidget(self.emergency_stop_btn)

        parent_layout.addWidget(group)

    def create_manual_trade_section(self, parent_layout):
        """创建手动交易区域"""
        group = QGroupBox("手动交易")
        group_layout = QFormLayout(group)

        # 交易方向
        direction_layout = QHBoxLayout()
        self.direction_group = QButtonGroup()
        self.buy_radio = QRadioButton("买入")
        self.sell_radio = QRadioButton("卖出")
        self.buy_radio.setChecked(True)
        self.direction_group.addButton(self.buy_radio, 0)
        self.direction_group.addButton(self.sell_radio, 1)
        direction_layout.addWidget(self.buy_radio)
        direction_layout.addWidget(self.sell_radio)
        group_layout.addRow("交易方向:", direction_layout)

        # 开平仓
        position_layout = QHBoxLayout()
        self.position_group = QButtonGroup()
        self.open_radio = QRadioButton("开仓")
        self.close_radio = QRadioButton("平仓")
        self.open_radio.setChecked(True)
        self.position_group.addButton(self.open_radio, 0)
        self.position_group.addButton(self.close_radio, 1)
        position_layout.addWidget(self.open_radio)
        position_layout.addWidget(self.close_radio)
        group_layout.addRow("开平仓:", position_layout)

        # 价格类型
        price_layout = QHBoxLayout()
        self.price_group = QButtonGroup()
        self.market_radio = QRadioButton("市价")
        self.limit_radio = QRadioButton("限价")
        self.market_radio.setChecked(True)
        self.price_group.addButton(self.market_radio, 0)
        self.price_group.addButton(self.limit_radio, 1)
        price_layout.addWidget(self.market_radio)
        price_layout.addWidget(self.limit_radio)
        group_layout.addRow("价格类型:", price_layout)

        # 限价输入（默认禁用）
        self.limit_price = QDoubleSpinBox()
        self.limit_price.setRange(0, 9999)
        self.limit_price.setDecimals(4)
        self.limit_price.setEnabled(False)
        group_layout.addRow("限价:", self.limit_price)

        # 数量
        self.trade_quantity = QSpinBox()
        self.trade_quantity.setRange(1, 1000)
        self.trade_quantity.setValue(10)
        group_layout.addRow("数量:", self.trade_quantity)

        # 执行按钮
        button_layout = QHBoxLayout()
        self.execute_btn = QPushButton("执行交易")
        self.execute_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.execute_btn.clicked.connect(self.on_execute_trade)
        button_layout.addWidget(self.execute_btn)

        self.reset_btn = QPushButton("重置")
        self.reset_btn.clicked.connect(self.on_reset_params)
        button_layout.addWidget(self.reset_btn)

        group_layout.addRow(button_layout)

        parent_layout.addWidget(group)

        # 连接价格类型变化事件
        self.market_radio.toggled.connect(self.on_price_type_changed)

    def create_trade_parameters_section(self, parent_layout):
        """创建交易参数设置区域"""
        group = QGroupBox("交易参数")
        group_layout = QFormLayout(group)

        # 阈值设置
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.001, 0.1)
        self.threshold_spin.setDecimals(4)
        self.threshold_spin.setValue(0.005)
        self.threshold_spin.setSingleStep(0.001)
        self.threshold_spin.setSuffix("")
        group_layout.addRow("价格阈值(%):", self.threshold_spin)

        # 固定延迟
        self.fixed_delay = QDoubleSpinBox()
        self.fixed_delay.setRange(0.1, 60)
        self.fixed_delay.setValue(2.0)
        self.fixed_delay.setSuffix(" s")
        group_layout.addRow("开仓延迟:", self.fixed_delay)

        # 平仓间隔
        self.close_interval = QDoubleSpinBox()
        self.close_interval.setRange(0.5, 300)
        self.close_interval.setValue(5.0)
        self.close_interval.setSuffix(" s")
        group_layout.addRow("平仓间隔:", self.close_interval)

        # 单次交易数量
        self.single_quantity = QSpinBox()
        self.single_quantity.setRange(1, 100)
        self.single_quantity.setValue(10)
        group_layout.addRow("默认数量:", self.single_quantity)

        # 应用参数按钮
        self.apply_params_btn = QPushButton("应用参数")
        self.apply_params_btn.clicked.connect(self.on_apply_parameters)
        group_layout.addRow(self.apply_params_btn)

        parent_layout.addWidget(group)

    def on_auto_trade_toggled(self, state):
        """自动交易开关切换"""
        enabled = state == Qt.Checked
        self.auto_trade_toggled.emit(enabled)

        # 禁用/启用手动交易控件
        self.execute_btn.setEnabled(not enabled)
        self.trade_quantity.setEnabled(not enabled)

    def on_price_type_changed(self, checked):
        """价格类型改变"""
        is_market = self.market_radio.isChecked()
        self.limit_price.setEnabled(not is_market)

    def on_execute_trade(self):
        """执行手动交易"""
        try:
            # 获取交易参数
            direction = "买入" if self.buy_radio.isChecked() else "卖出"
            position = "开仓" if self.open_radio.isChecked() else "平仓"
            price_type = "市价" if self.market_radio.isChecked() else "限价"
            quantity = self.trade_quantity.value()
            limit_price = self.limit_price.value() if not self.market_radio.isChecked() else None

            # 构建交易参数
            trade_params = {
                'direction': direction,
                'position': position,
                'price_type': price_type,
                'quantity': quantity,
                'limit_price': limit_price
            }

            # 确认对话框
            reply = QMessageBox.question(
                self, '确认交易',
                f"确定要执行以下交易吗？\n\n"
                f"方向: {direction}{position}\n"
                f"类型: {price_type}\n"
                f"数量: {quantity}张\n"
                f"{'价格: ' + str(limit_price) if limit_price else ''}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.manual_trade_requested.emit(trade_params)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"交易参数错误: {e}")

    def on_reset_params(self):
        """重置参数"""
        self.buy_radio.setChecked(True)
        self.open_radio.setChecked(True)
        self.market_radio.setChecked(True)
        self.trade_quantity.setValue(10)
        self.limit_price.setValue(0)

    def on_emergency_stop(self):
        """紧急停止"""
        reply = QMessageBox.warning(
            self, '紧急停止',
            "确定要紧急停止所有交易吗？\n这将立即停止自动交易并取消所有挂单。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.auto_trade_checkbox.setChecked(False)
            # 发出停止信号
            self.auto_trade_toggled.emit(False)



    def get_trade_parameters(self):
        """获取当前交易参数"""
        return {
            'threshold': self.threshold_spin.value(),
            'fixed_delay_before_open': self.fixed_delay.value(),
            'target_interval_close': self.close_interval.value(),
            'trade_qty': self.single_quantity.value()
        }

    def set_trade_parameters(self, params):
        """设置交易参数"""
        if 'threshold' in params:
            self.threshold_spin.setValue(params['threshold'])
        if 'fixed_delay_before_open' in params:
            self.fixed_delay.setValue(params['fixed_delay_before_open'])
        if 'target_interval_close' in params:
            self.close_interval.setValue(params['target_interval_close'])
        if 'trade_qty' in params:
            self.single_quantity.setValue(params['trade_qty'])

    def setup_strategy_refresh(self):
        """设置策略刷新定时器"""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_strategies)
        self.refresh_timer.start(2000)  # 每2秒刷新一次策略列表
        self.refresh_strategies()  # 立即加载一次

    def refresh_strategies(self):
        """刷新策略列表"""
        try:
            strategies = self.strategy_manager.get_all_strategies()
            current_text = self.strategy_combo.currentText()
            
            # 清空并重新加载策略
            self.strategy_combo.blockSignals(True)
            self.strategy_combo.clear()
            
            if strategies:
                for strategy_info in strategies:
                    # 安全检查策略信息
                    if (isinstance(strategy_info, dict) and 
                        strategy_info.get('enabled', False) and 
                        strategy_info.get('name')):
                        self.strategy_combo.addItem(strategy_info['name'])
            else:
                # 如果没有策略，添加一个提示项
                self.strategy_combo.addItem("无可用策略")
            
            # 恢复之前选择的策略
            index = self.strategy_combo.findText(current_text)
            if index >= 0:
                self.strategy_combo.setCurrentIndex(index)
            elif self.strategy_combo.count() > 0:
                self.strategy_combo.setCurrentIndex(0)
            
            self.strategy_combo.blockSignals(False)
            
        except Exception as e:
            # 更详细的错误信息
            import traceback
            error_detail = traceback.format_exc()
            print(f"刷新策略列表失败: {e}")
            print(f"详细错误: {error_detail}")
            
            # 在出错时尝试恢复
            try:
                self.strategy_combo.blockSignals(True)
                self.strategy_combo.clear()
                self.strategy_combo.addItem("策略加载失败")
                self.strategy_combo.blockSignals(False)
            except:
                pass

    def on_strategy_changed(self, strategy_name):
        """策略变更处理"""
        if strategy_name:
            # 设置为活跃策略
            self.strategy_manager.set_active_strategy(strategy_name)
            # 发出策略变更信号
            self.strategy_changed.emit(strategy_name)
            print(f"切换到策略: {strategy_name}")

    def get_current_strategy(self):
        """获取当前选择的策略"""
        return self.strategy_combo.currentText()

    def on_apply_parameters(self):
        """应用交易参数（重写以实际更新到策略）"""
        try:
            current_strategy = self.get_current_strategy()
            if not current_strategy:
                QMessageBox.warning(self, "警告", "请先选择一个策略")
                return

            params = {
                'trade_qty': self.single_quantity.value(),
                'threshold': self.threshold_spin.value(),
                'fixed_delay_before_open': self.fixed_delay.value(),
                'target_interval_close': self.close_interval.value()
            }

            # 更新策略参数
            self.strategy_manager.update_strategy_parameters(current_strategy, **params)
            
            # 发出参数更新信号
            self.strategy_changed.emit(current_strategy)

            QMessageBox.information(self, "成功", f"策略参数已应用到 {current_strategy}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用参数失败: {e}")