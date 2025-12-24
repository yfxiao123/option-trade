"""
设置对话框
提供系统参数配置功能
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
                             QPushButton, QTabWidget, QGroupBox, QCheckBox,
                             QComboBox, QTextEdit, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt
from config import TradingConfig


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = {}
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("系统设置")
        self.setModal(True)
        self.resize(600, 500)

        layout = QVBoxLayout(self)

        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 基础设置页
        self.create_basic_settings_tab()

        # 交易参数页
        self.create_trading_settings_tab()

        # 高级设置页
        self.create_advanced_settings_tab()

        # 按钮栏
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.reset_btn = QPushButton("重置默认")
        self.reset_btn.clicked.connect(self.reset_to_default)
        button_layout.addWidget(self.reset_btn)

        self.import_btn = QPushButton("导入配置")
        self.import_btn.clicked.connect(self.import_settings)
        button_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("导出配置")
        self.export_btn.clicked.connect(self.export_settings)
        button_layout.addWidget(self.export_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept_settings)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        layout.addLayout(button_layout)

    def create_basic_settings_tab(self):
        """创建基础设置页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 登录信息
        login_group = QGroupBox("登录信息")
        login_layout = QFormLayout(login_group)

        self.url_edit = QLineEdit()
        login_layout.addRow("交易地址:", self.url_edit)

        self.username_edit = QLineEdit()
        self.username_edit.setEchoMode(QLineEdit.Password)
        login_layout.addRow("用户名:", self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        login_layout.addRow("密码:", self.password_edit)

        self.contract_edit = QLineEdit()
        login_layout.addRow("合约代码:", self.contract_edit)

        layout.addWidget(login_group)

        # 基础参数
        basic_group = QGroupBox("基础参数")
        basic_layout = QFormLayout(basic_group)

        self.contract_multiplier_spin = QSpinBox()
        self.contract_multiplier_spin.setRange(1, 100000)
        self.contract_multiplier_spin.setValue(10000)
        basic_layout.addRow("合约乘数:", self.contract_multiplier_spin)

        self.system_delay_spin = QDoubleSpinBox()
        self.system_delay_spin.setRange(0.1, 10)
        self.system_delay_spin.setValue(1.0)
        self.system_delay_spin.setSuffix(" 秒")
        basic_layout.addRow("系统延迟:", self.system_delay_spin)

        layout.addWidget(basic_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "基础设置")

    def create_trading_settings_tab(self):
        """创建交易参数页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 策略参数
        strategy_group = QGroupBox("策略参数")
        strategy_layout = QFormLayout(strategy_group)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.001, 0.1)
        self.threshold_spin.setDecimals(4)
        self.threshold_spin.setValue(0.005)
        self.threshold_spin.setSingleStep(0.001)
        strategy_layout.addRow("价格阈值:", self.threshold_spin)

        self.trade_qty_spin = QSpinBox()
        self.trade_qty_spin.setRange(1, 1000)
        self.trade_qty_spin.setValue(10)
        strategy_layout.addRow("单次数量:", self.trade_qty_spin)

        layout.addWidget(strategy_group)

        # 时间参数
        time_group = QGroupBox("时间参数")
        time_layout = QFormLayout(time_group)

        self.fixed_delay_spin = QDoubleSpinBox()
        self.fixed_delay_spin.setRange(0.1, 60)
        self.fixed_delay_spin.setValue(2.0)
        self.fixed_delay_spin.setSuffix(" 秒")
        time_layout.addRow("开仓延迟:", self.fixed_delay_spin)

        self.close_interval_spin = QDoubleSpinBox()
        self.close_interval_spin.setRange(0.5, 300)
        self.close_interval_spin.setValue(5.0)
        self.close_interval_spin.setSuffix(" 秒")
        time_layout.addRow("平仓间隔:", self.close_interval_spin)

        layout.addWidget(time_group)

        # 监控参数
        monitor_group = QGroupBox("监控参数")
        monitor_layout = QFormLayout(monitor_group)

        self.history_len_spin = QSpinBox()
        self.history_len_spin.setRange(2, 10)
        self.history_len_spin.setValue(3)
        monitor_layout.addRow("历史长度:", self.history_len_spin)

        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.1, 5)
        self.interval_spin.setValue(0.5)
        self.interval_spin.setSuffix(" 秒")
        monitor_layout.addRow("监控间隔:", self.interval_spin)

        layout.addWidget(monitor_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "交易参数")

    def create_advanced_settings_tab(self):
        """创建高级设置页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 浏览器设置
        browser_group = QGroupBox("浏览器设置")
        browser_layout = QFormLayout(browser_group)

        self.window_size_edit = QLineEdit("1400,900")
        browser_layout.addRow("窗口大小:", self.window_size_edit)

        self.page_timeout_spin = QSpinBox()
        self.page_timeout_spin.setRange(5, 60)
        self.page_timeout_spin.setValue(10)
        self.page_timeout_spin.setSuffix(" 秒")
        browser_layout.addRow("页面超时:", self.page_timeout_spin)

        self.element_timeout_spin = QSpinBox()
        self.element_timeout_spin.setRange(3, 30)
        self.element_timeout_spin.setValue(5)
        self.element_timeout_spin.setSuffix(" 秒")
        browser_layout.addRow("元素超时:", self.element_timeout_spin)

        layout.addWidget(browser_group)

        # 重试设置
        retry_group = QGroupBox("重试设置")
        retry_layout = QFormLayout(retry_group)

        self.max_retry_spin = QSpinBox()
        self.max_retry_spin.setRange(1, 10)
        self.max_retry_spin.setValue(3)
        retry_layout.addRow("最大重试:", self.max_retry_spin)

        self.retry_interval_spin = QDoubleSpinBox()
        self.retry_interval_spin.setRange(0.1, 10)
        self.retry_interval_spin.setValue(1.0)
        self.retry_interval_spin.setSuffix(" 秒")
        retry_layout.addRow("重试间隔:", self.retry_interval_spin)

        layout.addWidget(retry_group)

        # 日志设置
        log_group = QGroupBox("日志设置")
        log_layout = QVBoxLayout(log_group)

        self.enable_log_checkbox = QCheckBox("启用日志记录")
        self.enable_log_checkbox.setChecked(True)
        log_layout.addWidget(self.enable_log_checkbox)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentText("INFO")
        log_layout.addWidget(QLabel("日志级别:"))
        log_layout.addWidget(self.log_level_combo)

        self.log_path_edit = QLineEdit("logs/trading.log")
        self.log_browse_btn = QPushButton("浏览...")
        self.log_browse_btn.clicked.connect(self.browse_log_path)
        log_path_layout = QHBoxLayout()
        log_path_layout.addWidget(QLabel("日志路径:"))
        log_path_layout.addWidget(self.log_path_edit)
        log_path_layout.addWidget(self.log_browse_btn)
        log_layout.addLayout(log_path_layout)

        layout.addWidget(log_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "高级设置")

    def load_settings(self):
        """加载设置"""
        config_obj = TradingConfig()

        # 基础设置
        self.url_edit.setText(getattr(config_obj, 'TARGET_URL', ''))
        self.username_edit.setText(getattr(config_obj, 'USERNAME', ''))
        self.password_edit.setText(getattr(config_obj, 'PASSWORD', ''))
        self.contract_edit.setText(getattr(config_obj, 'TARGET_CONTRACT', ''))
        self.contract_multiplier_spin.setValue(getattr(config_obj, 'CONTRACT_MULTIPLIER', 10000))
        self.system_delay_spin.setValue(getattr(config_obj, 'SYSTEM_DELAY', 1.0))

        # 交易参数
        self.threshold_spin.setValue(getattr(config_obj, 'THRESHOLD', 0.005))
        self.trade_qty_spin.setValue(getattr(config_obj, 'TRADE_QTY', 10))
        self.fixed_delay_spin.setValue(getattr(config_obj, 'FIXED_DELAY_BEFORE_OPEN', 2.0))
        self.close_interval_spin.setValue(getattr(config_obj, 'TARGET_INTERVAL_CLOSE', 5.0))
        self.history_len_spin.setValue(getattr(config_obj, 'HISTORY_LEN', 3))
        self.interval_spin.setValue(getattr(config_obj, 'INTERVAL', 0.5))

        # 高级设置
        self.page_timeout_spin.setValue(getattr(config_obj, 'PAGE_LOAD_TIMEOUT', 10))
        self.element_timeout_spin.setValue(getattr(config_obj, 'ELEMENT_WAIT_TIMEOUT', 5))
        self.max_retry_spin.setValue(getattr(config_obj, 'MAX_RETRY_COUNT', 3))
        self.retry_interval_spin.setValue(getattr(config_obj, 'RETRY_INTERVAL', 1.0))

    def accept_settings(self):
        """应用设置"""
        try:
            # 收集所有设置
            self.settings = {
                'TARGET_URL': self.url_edit.text(),
                'USERNAME': self.username_edit.text(),
                'PASSWORD': self.password_edit.text(),
                'TARGET_CONTRACT': self.contract_edit.text(),
                'CONTRACT_MULTIPLIER': self.contract_multiplier_spin.value(),
                'SYSTEM_DELAY': self.system_delay_spin.value(),
                'THRESHOLD': self.threshold_spin.value(),
                'TRADE_QTY': self.trade_qty_spin.value(),
                'FIXED_DELAY_BEFORE_OPEN': self.fixed_delay_spin.value(),
                'TARGET_INTERVAL_CLOSE': self.close_interval_spin.value(),
                'HISTORY_LEN': self.history_len_spin.value(),
                'INTERVAL': self.interval_spin.value(),
                'PAGE_LOAD_TIMEOUT': self.page_timeout_spin.value(),
                'ELEMENT_WAIT_TIMEOUT': self.element_timeout_spin.value(),
                'MAX_RETRY_COUNT': self.max_retry_spin.value(),
                'RETRY_INTERVAL': self.retry_interval_spin.value()
            }

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败: {e}")

    def reset_to_default(self):
        """重置为默认值"""
        reply = QMessageBox.question(
            self, '确认重置',
            '确定要重置所有设置为默认值吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.load_settings()

    def import_settings(self):
        """导入配置"""
        filename, _ = QFileDialog.getOpenFileName(
            self, '导入配置', '', 'JSON文件 (*.json)'
        )
        if filename:
            try:
                import json
                with open(filename, 'r', encoding='utf-8') as f:
                    settings = json.load(f)

                # 应用导入的设置
                # TODO: 应用设置到界面
                QMessageBox.information(self, '成功', '配置导入成功')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导入配置失败: {e}')

    def export_settings(self):
        """导出配置"""
        if not self.settings:
            QMessageBox.warning(self, '警告', '请先点击确定保存设置')
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, '导出配置', 'settings.json', 'JSON文件 (*.json)'
        )
        if filename:
            try:
                import json
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.settings, f, indent=4, ensure_ascii=False)
                QMessageBox.information(self, '成功', '配置导出成功')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导出配置失败: {e}')

    def browse_log_path(self):
        """浏览日志路径"""
        path = QFileDialog.getExistingDirectory(self, '选择日志目录')
        if path:
            self.log_path_edit.setText(path)

    def get_settings(self):
        """获取设置"""
        return self.settings