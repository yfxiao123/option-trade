"""
日志显示面板
显示系统运行日志、交易记录和错误信息
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                             QPushButton, QComboBox, QLabel, QCheckBox)
from PyQt5.QtCore import Qt, QDateTime, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor, QColor
from datetime import datetime


class LogPanel(QWidget):
    """日志面板"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 控制栏
        control_layout = QHBoxLayout()

        # 日志级别选择
        self.level_combo = QComboBox()
        self.level_combo.addItems(["全部", "信息", "警告", "错误", "交易", "信号"])
        self.level_combo.currentTextChanged.connect(self.filter_logs)
        control_layout.addWidget(QLabel("日志级别:"))
        control_layout.addWidget(self.level_combo)

        # 自动滚动
        self.autoscroll_checkbox = QCheckBox("自动滚动")
        self.autoscroll_checkbox.setChecked(True)
        control_layout.addWidget(self.autoscroll_checkbox)

        # 清空按钮
        self.clear_btn = QPushButton("清空日志")
        self.clear_btn.clicked.connect(self.clear_logs)
        control_layout.addWidget(self.clear_btn)

        # 导出按钮
        self.export_btn = QPushButton("导出日志")
        self.export_btn.clicked.connect(self.export_logs)
        control_layout.addWidget(self.export_btn)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        # 日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.log_text)

        # 状态栏
        status_layout = QHBoxLayout()
        self.status_label = QLabel("就绪")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        self.line_count_label = QLabel("行数: 0")
        status_layout.addWidget(self.line_count_label)
        layout.addLayout(status_layout)

        # 设置样式
        self.setup_styles()

    def setup_styles(self):
        """设置样式"""
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 5px;
            }
        """)

    def log(self, message, level="INFO"):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # 根据级别设置颜色
        color = {
            "INFO": "#ecf0f1",
            "WARNING": "#f39c12",
            "ERROR": "#e74c3c",
            "TRADE": "#3498db",
            "SIGNAL": "#27ae60"
        }.get(level, "#ecf0f1")

        # 格式化日志
        log_line = f'<span style="color: #95a5a6;">[{timestamp}]</span> ' \
                  f'<span style="color: {color}; font-weight: bold;">[{level}]</span> ' \
                  f'<span style="color: #ecf0f1;">{message}</span>'

        # 添加到文本框
        self.log_text.append(log_line)

        # 更新行数
        self.line_count_label.setText(f"行数: {self.log_text.document().blockCount()}")

        # 自动滚动到底部
        if self.autoscroll_checkbox.isChecked():
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log_text.setTextCursor(cursor)

    def log_info(self, message):
        """记录信息日志"""
        self.log(message, "INFO")

    def log_warning(self, message):
        """记录警告日志"""
        self.log(message, "WARNING")

    def log_error(self, message):
        """记录错误日志"""
        self.log(message, "ERROR")

    def log_trade(self, message):
        """记录交易日志"""
        self.log(message, "TRADE")

    def log_signal(self, message):
        """记录信号日志"""
        self.log(message, "SIGNAL")

    def log_success(self, message):
        """记录成功日志"""
        self.log(f"✓ {message}", "INFO")

    def log_failure(self, message):
        """记录失败日志"""
        self.log(f"✗ {message}", "ERROR")

    def clear_logs(self):
        """清空日志"""
        self.log_text.clear()
        self.line_count_label.setText("行数: 0")

    def filter_logs(self, level):
        """过滤日志"""
        # TODO: 实现日志过滤功能
        pass

    def export_logs(self):
        """导出日志"""
        try:
            filename = f"trading_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_text.toPlainText())
            self.log_info(f"日志已导出到: {filename}")
        except Exception as e:
            self.log_error(f"导出日志失败: {e}")

    def set_status(self, message):
        """设置状态栏消息"""
        self.status_label.setText(message)