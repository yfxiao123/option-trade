"""
策略控制面板（重写版）
提供策略管理、启用/禁用、切换和参数调整功能
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QSpinBox, QDoubleSpinBox,
                             QGroupBox, QFormLayout, QCheckBox,
                             QProgressBar, QTextEdit, QSlider, QListWidget,
                             QListWidgetItem, QSplitter, QFrame, QMessageBox,
                             QRadioButton, QButtonGroup, QDialog, QTableWidget,
                             QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QColor, QBrush

from strategy import get_strategy_manager, StrategyState


class StrategyListItem(QWidget):
    """策略列表项组件"""

    def __init__(self, strategy_name: str, is_enabled: bool, is_active: bool):
        super().__init__()
        self.strategy_name = strategy_name
        self.is_enabled = is_enabled
        self.is_active = is_active
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 启用复选框
        self.enabled_checkbox = QCheckBox()
        self.enabled_checkbox.setChecked(self.is_enabled)
        self.enabled_checkbox.stateChanged.connect(self._on_enabled_changed)
        layout.addWidget(self.enabled_checkbox)

        # 策略名称
        self.name_label = QLabel(self.strategy_name)
        self.name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.name_label)

        layout.addStretch()

        # 活跃指示器
        if self.is_active:
            active_label = QLabel("● 活跃")
            active_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            layout.addWidget(active_label)

    def _on_enabled_changed(self, state):
        """启用状态变化"""
        is_enabled = state == Qt.Checked
        self.is_enabled = is_enabled

    def set_active(self, is_active: bool):
        """设置活跃状态"""
        self.is_active = is_active
        # 重新构建UI以更新活跃指示器
        # 简化处理：实际应该只更新指示器
        layout = self.layout()
        if layout.count() > 2:
            item = layout.itemAt(layout.count() - 1)
            if item:
                widget = item.widget()
                if widget and isinstance(widget, QLabel):
                    widget.setParent(None)


class StrategyListWidget(QGroupBox):
    """策略列表组件"""

    # 定义信号
    strategy_enabled_changed = pyqtSignal(str, bool)
    strategy_activated = pyqtSignal(str)
    strategy_selected = pyqtSignal(str)

    def __init__(self):
        super().__init__("策略列表")
        self.strategies = {}
        self.active_strategy = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 策略列表
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget)

        # 控制按钮
        button_layout = QHBoxLayout()

        self.enable_all_btn = QPushButton("全部启用")
        self.enable_all_btn.clicked.connect(self._enable_all)
        button_layout.addWidget(self.enable_all_btn)

        self.disable_all_btn = QPushButton("全部禁用")
        self.disable_all_btn.clicked.connect(self._disable_all_confirm)
        button_layout.addWidget(self.disable_all_btn)

        layout.addLayout(button_layout)

    def load_strategies(self, strategies_info: list):
        """加载策略列表"""
        self.list_widget.clear()
        self.strategies = {}

        for info in strategies_info:
            name = info['name']
            enabled = info['enabled']
            state = info['state']

            # 创建列表项
            item = QListWidgetItem()

            # 创建自定义widget
            widget = StrategyListItem(name, enabled, state == StrategyState.RUNNING.value)
            widget.setMaximumHeight(40)

            # 设置widget属性以便后续访问
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.UserRole, name)

            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

            # 存储策略信息
            self.strategies[name] = {
                'item': item,
                'widget': widget,
                'enabled': enabled,
                'state': state
            }

    def update_strategy_state(self, name: str, enabled: bool, state: StrategyState):
        """更新策略状态"""
        if name in self.strategies:
            info = self.strategies[name]
            info['enabled'] = enabled
            info['state'] = state

            # 更新widget
            widget = info['widget']
            widget.is_enabled = enabled
            widget.enabled_checkbox.blockSignals(True)
            widget.enabled_checkbox.setChecked(enabled)
            widget.enabled_checkbox.blockSignals(False)

    def set_active_strategy(self, name: str):
        """设置活跃策略"""
        self.active_strategy = name

        # 更新显示
        for strategy_name, info in self.strategies.items():
            widget = info['widget']
            is_active = (strategy_name == name)

            # 移除旧的活跃指示器
            layout = widget.layout()
            if layout.count() > 2:
                item = layout.itemAt(layout.count() - 1)
                if item:
                    old_widget = item.widget()
                    if old_widget:
                        old_widget.setParent(None)

            # 添加新的活跃指示器
            if is_active:
                active_label = QLabel("● 活跃")
                active_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                layout.addWidget(active_label)

    def _on_selection_changed(self):
        """选择变化"""
        current_item = self.list_widget.currentItem()
        if current_item:
            name = current_item.data(Qt.UserRole)
            self.strategy_selected.emit(name)

    def _on_item_double_clicked(self, item):
        """双击设置为活跃策略"""
        name = item.data(Qt.UserRole)
        self.strategy_activated.emit(name)

    def _enable_all(self):
        """启用所有策略"""
        for name, info in self.strategies.items():
            if not info['enabled']:
                self.strategy_enabled_changed.emit(name, True)

    def _disable_all_confirm(self):
        """禁用所有策略（带确认）"""
        reply = QMessageBox.warning(
            self, '确认操作',
            "确定要禁用所有策略吗？\n这将停止所有自动交易。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            for name, info in self.strategies.items():
                if info['enabled']:
                    self.strategy_enabled_changed.emit(name, False)


class StrategyParametersWidget(QGroupBox):
    """策略参数设置组件（动态生成）"""

    # 定义信号
    parameters_changed = pyqtSignal(str, dict)

    def __init__(self):
        super().__init__("策略参数")
        self.current_strategy = None
        self.parameter_widgets = {}  # 存储动态生成的控件 {param_key: widget}
        self.manager = get_strategy_manager()
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        
        # 参数容器
        self.params_container = QWidget()
        self.params_layout = QFormLayout(self.params_container)
        self.main_layout.addWidget(self.params_container)

        # 应用按钮
        self.apply_btn = QPushButton("应用参数")
        self.apply_btn.clicked.connect(self._apply_parameters)
        self.main_layout.addWidget(self.apply_btn)

    def set_strategy(self, strategy_name: str, parameters: dict = None):
        """设置当前策略并动态生成参数界面"""
        if self.current_strategy == strategy_name:
            if parameters:
                self._set_parameter_values(parameters)
            return

        self.current_strategy = strategy_name
        
        # 1. 清除旧的参数控件
        self._clear_params_layout()
        self.parameter_widgets = {}

        # 2. 获取策略参数配置
        config = self.manager.get_strategy_parameter_config(strategy_name)
        if not config:
            self.params_layout.addRow(QLabel("该策略无可配置参数"))
            return

        # 3. 动态生成控件
        for key, info in config.items():
            label_text = info.get('name', key) + ":"
            widget = self._create_parameter_widget(key, info)
            
            if widget:
                self.params_layout.addRow(label_text, widget)
                self.parameter_widgets[key] = widget
                
                # 设置提示信息
                if 'description' in info:
                    widget.setToolTip(info['description'])

        # 4. 设置初始值
        if parameters:
            self._set_parameter_values(parameters)
        else:
            # 如果没有传入参数，使用配置中的默认值
            default_params = {k: v.get('default') for k, v in config.items() if 'default' in v}
            self._set_parameter_values(default_params)

    def _create_parameter_widget(self, key, info):
        """根据配置创建对应的输入控件"""
        param_type = info.get('type', 'float')
        
        if param_type == 'int':
            widget = QSpinBox()
            widget.setRange(info.get('min', 0), info.get('max', 999999))
            widget.setSingleStep(info.get('step', 1))
            if 'suffix' in info:
                widget.setSuffix(info['suffix'])
            return widget
            
        elif param_type == 'float':
            widget = QDoubleSpinBox()
            widget.setRange(info.get('min', 0.0), info.get('max', 999999.0))
            widget.setDecimals(info.get('decimals', 4))
            widget.setSingleStep(info.get('step', 0.01))
            if 'suffix' in info:
                widget.setSuffix(info['suffix'])
            return widget
            
        elif param_type == 'bool':
            widget = QCheckBox()
            return widget
            
        return None

    def _clear_params_layout(self):
        """清空参数布局中的所有控件"""
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _set_parameter_values(self, params: dict):
        """根据传入的字典设置控件值"""
        for key, value in params.items():
            if key in self.parameter_widgets:
                widget = self.parameter_widgets[key]
                if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                    widget.setValue(value)
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(bool(value))

    def _apply_parameters(self):
        """收集当前控件值并应用参数"""
        if not self.current_strategy:
            return

        params = {}
        for key, widget in self.parameter_widgets.items():
            if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                params[key] = widget.value()
            elif isinstance(widget, QCheckBox):
                params[key] = widget.isChecked()

        # 发送信号
        self.parameters_changed.emit(self.current_strategy, params)
        
        # 提示用户
        QMessageBox.information(self, "成功", f"策略 '{self.current_strategy}' 参数已更新")


class StrategyStatusWidget(QGroupBox):
    """策略状态显示组件"""

    def __init__(self):
        super().__init__("策略状态")
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        # 当前活跃策略
        self.active_strategy_label = QLabel("无")
        self.active_strategy_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        layout.addRow("活跃策略:", self.active_strategy_label)

        # 策略状态
        self.state_label = QLabel("空闲")
        self.state_label.setStyleSheet("font-size: 14px; color: #95a5a6;")
        layout.addRow("状态:", self.state_label)

        # 运行时间
        self.runtime_label = QLabel("00:00:00")
        layout.addRow("运行时间:", self.runtime_label)

        # 信号计数
        self.signal_count_label = QLabel("0")
        layout.addRow("信号次数:", self.signal_count_label)

        # 交易计数
        self.trade_count_label = QLabel("0")
        layout.addRow("交易次数:", self.trade_count_label)

        # 累计盈亏
        self.pnl_label = QLabel("0.00")
        self.pnl_label.setStyleSheet("font-size: 14px; color: #2c3e50;")
        layout.addRow("累计盈亏:", self.pnl_label)

    def update_status(self, info: dict):
        """更新状态显示"""
        # 更新活跃策略
        self.active_strategy_label.setText(info.get('name', '无'))

        # 更新状态
        state = info.get('state', 'IDLE')
        state_map = {
            '空闲': '空闲',
            '运行中': '运行中',
            '暂停': '暂停',
            '错误': '错误'
        }
        state_text = state_map.get(state, '未知')
        self.state_label.setText(state_text)

        if state == '运行中':
            self.state_label.setStyleSheet("font-size: 14px; color: #27ae60; font-weight: bold;")
        elif state == '错误':
            self.state_label.setStyleSheet("font-size: 14px; color: #e74c3c; font-weight: bold;")
        else:
            self.state_label.setStyleSheet("font-size: 14px; color: #95a5a6;")

        # 更新计数
        self.signal_count_label.setText(str(info.get('signal_count', 0)))
        self.trade_count_label.setText(str(info.get('trade_count', 0)))

        # 更新盈亏
        pnl = info.get('total_pnl', 0)
        self.pnl_label.setText(f"{pnl:.2f}")
        if pnl > 0:
            self.pnl_label.setStyleSheet("font-size: 14px; color: #27ae60; font-weight: bold;")
        elif pnl < 0:
            self.pnl_label.setStyleSheet("font-size: 14px; color: #e74c3c; font-weight: bold;")
        else:
            self.pnl_label.setStyleSheet("font-size: 14px; color: #2c3e50;")

    def update_runtime(self, seconds: int):
        """更新运行时间"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        self.runtime_label.setText(f"{hours:02d}:{minutes:02d}:{secs:02d}")


class StrategyPerformanceWidget(QGroupBox):
    """策略性能统计组件"""

    def __init__(self):
        super().__init__("性能统计")
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        # 总交易次数
        self.total_trades_label = QLabel("0")
        layout.addRow("总交易:", self.total_trades_label)

        # 胜率
        self.win_rate_progress = QProgressBar()
        self.win_rate_progress.setRange(0, 100)
        self.win_rate_progress.setValue(0)
        self.win_rate_progress.setFormat("%p%")
        layout.addRow("胜率:", self.win_rate_progress)

        # 最大盈利
        self.max_profit_label = QLabel("0.00")
        self.max_profit_label.setStyleSheet("color: #27ae60;")
        layout.addRow("最大盈利:", self.max_profit_label)

        # 最大亏损
        self.max_loss_label = QLabel("0.00")
        self.max_loss_label.setStyleSheet("color: #e74c3c;")
        layout.addRow("最大亏损:", self.max_loss_label)

    def update_performance(self, stats: dict):
        """更新性能统计"""
        # 处理 None 或空字典的情况
        if not stats or not isinstance(stats, dict):
            stats = {}

        self.total_trades_label.setText(str(stats.get('total_trades', 0)))

        # 胜率
        close_trades = stats.get('close_trades', 0) or 0
        win_count = stats.get('win_count', 0) or 0
        if close_trades > 0:
            win_rate = (win_count / close_trades) * 100
        else:
            win_rate = 0
        self.win_rate_progress.setValue(int(win_rate))

        # 最大盈亏（处理 None 值）
        max_profit = stats.get('max_profit')
        max_loss = stats.get('max_loss')
        self.max_profit_label.setText(f"{max_profit if max_profit is not None else 0:.2f}")
        self.max_loss_label.setText(f"{max_loss if max_loss is not None else 0:.2f}")


class StrategyPanel(QWidget):
    """策略控制主面板（重写版）"""

    # 外部信号
    strategy_parameters_changed = pyqtSignal(str, dict)
    start_strategy_requested = pyqtSignal()
    stop_strategy_requested = pyqtSignal()

    # 内部信号（用于线程安全地处理后台回调）
    _internal_signal_received = pyqtSignal(str, object)
    _internal_error_received = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.strategy_manager = get_strategy_manager()
        self.init_ui()
        self.setup_connections()
        self.refresh_display()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 标题
        title_label = QLabel("策略管理")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # 左侧：策略列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        self.strategy_list = StrategyListWidget()
        self.strategy_list.strategy_enabled_changed.connect(self._on_strategy_enabled_changed)
        self.strategy_list.strategy_activated.connect(self._on_strategy_activated)
        self.strategy_list.strategy_selected.connect(self._on_strategy_selected)
        left_layout.addWidget(self.strategy_list)

        # 策略状态
        self.status_widget = StrategyStatusWidget()
        left_layout.addWidget(self.status_widget)

        left_layout.addStretch()
        splitter.addWidget(left_widget)

        # 右侧：策略参数和性能
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        self.parameters_widget = StrategyParametersWidget()
        self.parameters_widget.parameters_changed.connect(self._on_parameters_changed)
        right_layout.addWidget(self.parameters_widget)

        self.performance_widget = StrategyPerformanceWidget()
        right_layout.addWidget(self.performance_widget)

        right_layout.addStretch()
        splitter.addWidget(right_widget)

        # 设置分割比例
        splitter.setSizes([400, 400])

        # 运行时间计时器
        self.runtime_timer = QTimer()
        self.runtime_timer.timeout.connect(self._update_runtime)
        self.runtime_seconds = 0

        # 刷新定时器
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_display)
        self.refresh_timer.start(1000)  # 每秒刷新一次

    def setup_connections(self):
        """设置信号连接"""
        # 连接策略管理器回调（这些回调会在后台线程触发）
        self.strategy_manager.set_signal_callback(lambda name, sig: self._internal_signal_received.emit(name, sig))
        self.strategy_manager.set_error_callback(lambda name, err: self._internal_error_received.emit(name, err))

        # 将内部信号连接到主线程处理函数
        self._internal_signal_received.connect(self._on_signal_generated_safe)
        self._internal_error_received.connect(self._on_strategy_error_safe)

    def refresh_display(self):
        """刷新显示"""
        # 静默错误标志，避免重复打印相同错误
        if not hasattr(self, '_last_error'):
            self._last_error = None
        if not hasattr(self, '_error_count'):
            self._error_count = 0

        try:
            # 获取所有策略信息
            strategies = self.strategy_manager.get_all_strategies()
            self.strategy_list.load_strategies(strategies)

            # 更新活跃策略显示
            active_strategy = self.strategy_manager.get_active_strategy()
            if active_strategy:
                self.strategy_list.set_active_strategy(active_strategy)

                # 更新状态显示
                info = self.strategy_manager.get_strategy_info(active_strategy)
                if info:
                    self.status_widget.update_status(info)
                    
                    # 第一次运行时或者没有当前策略时，设置参数界面
                    if not self.parameters_widget.current_strategy:
                        strategy_status = info.get('strategy_status') or {}
                        self.parameters_widget.set_strategy(active_strategy, strategy_status)

                    # 从数据库获取统计
                    try:
                        from database import get_database
                        db = get_database()
                        stats = db.get_strategy_statistics(active_strategy)
                        self.performance_widget.update_performance(stats)
                    except Exception as db_error:
                        # 数据库错误不应影响界面刷新
                        self.performance_widget.update_performance({})

            # 重置错误计数
            self._last_error = None
            self._error_count = 0

        except Exception as e:
            error_msg = str(e)
            # 只在错误消息变化或每100次打印一次
            if error_msg != self._last_error or self._error_count % 100 == 0:
                print(f"刷新策略显示失败: {e}")
                self._last_error = error_msg
            self._error_count += 1

    def _on_strategy_enabled_changed(self, name: str, enabled: bool):
        """策略启用状态变化"""
        if enabled:
            self.strategy_manager.enable_strategy(name)
        else:
            self.strategy_manager.disable_strategy(name)

        self.refresh_display()

    def _on_strategy_activated(self, name: str):
        """激活策略"""
        if self.strategy_manager.set_active_strategy(name):
            self.strategy_list.set_active_strategy(name)
            self.refresh_display()

    def _on_strategy_selected(self, name: str):
        """策略被选中，更新参数界面"""
        info = self.strategy_manager.get_strategy_info(name)
        if info:
            strategy_status = info.get('strategy_status') or {}
            self.parameters_widget.set_strategy(name, strategy_status)

    def _on_parameters_changed(self, name: str, params: dict):
        """处理参数变化信号"""
        # 更新到管理器
        success = self.strategy_manager.update_strategy_parameters(name, **params)
        if success:
            self.strategy_parameters_changed.emit(name, params)
        else:
            QMessageBox.critical(self, "错误", f"策略 '{name}' 参数更新失败")

    def _on_signal_generated_safe(self, strategy_name: str, signal):
        """主线程中安全处理信号生成"""
        self.refresh_display()

    def _on_strategy_error_safe(self, strategy_name: str, error_message: str):
        """主线程中安全处理策略错误"""
        print(f"策略错误 [{strategy_name}]: {error_message}")
        self.refresh_display()

    def _update_runtime(self):
        """更新运行时间"""
        self.runtime_seconds += 1
        self.status_widget.update_runtime(self.runtime_seconds)

    def start_runtime_timer(self):
        """启动运行时间计时"""
        self.runtime_seconds = 0
        self.runtime_timer.start(1000)

    def stop_runtime_timer(self):
        """停止运行时间计时"""
        self.runtime_timer.stop()

    def get_current_strategy(self) -> str:
        """获取当前活跃策略名称"""
        return self.strategy_manager.get_active_strategy()
