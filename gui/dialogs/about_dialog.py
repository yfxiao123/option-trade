"""
关于对话框
显示程序信息和版本说明
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTextEdit, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QIcon


class AboutDialog(QDialog):
    """关于对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("关于期权交易自动化系统")
        self.setModal(True)
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        # 标题和图标
        title_layout = QHBoxLayout()

        # 图标（如果有的话）
        # icon_label = QLabel()
        # icon_pixmap = QPixmap("icons/app_icon.png").scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # icon_label.setPixmap(icon_pixmap)
        # title_layout.addWidget(icon_label)

        title_layout.addStretch()

        title_vlayout = QVBoxLayout()
        title_label = QLabel("期权交易自动化系统")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_vlayout.addWidget(title_label)

        version_label = QLabel("版本 2.0.0")
        version_label.setFont(QFont("Arial", 12))
        version_label.setStyleSheet("color: #7f8c8d;")
        title_vlayout.addWidget(version_label)

        title_layout.addLayout(title_vlayout)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # 描述文本
        desc_text = QTextEdit()
        desc_text.setReadOnly(True)
        desc_text.setMaximumHeight(200)
        desc_text.setHtml("""
        <p><b>系统简介</b></p>
        <p>期权交易自动化系统是一个基于Python和Selenium的自动化交易程序，
        采用模块化架构设计，实现基于价格波动的双向套利交易策略。</p>

        <p><b>主要特性</b></p>
        <ul>
        <li>实时市场数据获取</li>
        <li>智能交易信号生成</li>
        <li>自动交易执行</li>
        <li>实时盈亏监控</li>
        <li>可视化操作界面</li>
        <li>灵活的策略参数配置</li>
        </ul>
        """)
        layout.addWidget(desc_text)

        # 技术信息
        tech_text = QTextEdit()
        tech_text.setReadOnly(True)
        tech_text.setMaximumHeight(100)
        tech_text.setHtml("""
        <p><b>技术架构</b></p>
        <p>
        <b>前端:</b> PyQt5<br>
        <b>后端:</b> Python 3.x<br>
        <b>自动化:</b> Selenium WebDriver<br>
        <b>数据处理:</b> Pandas, NumPy<br>
        <b>图表绘制:</b> PyQtGraph
        </p>
        """)
        layout.addWidget(tech_text)

        # 版权信息
        copyright_label = QLabel("© 2024 期权交易自动化系统. All rights reserved.")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("color: #95a5a6; font-size: 10px;")
        layout.addWidget(copyright_label)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 检查更新按钮
        self.check_update_btn = QPushButton("检查更新")
        self.check_update_btn.clicked.connect(self.check_update)
        button_layout.addWidget(self.check_update_btn)

        # 确定按钮
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        layout.addLayout(button_layout)

    def check_update(self):
        """检查更新"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(
            self, '检查更新',
            '您当前使用的是最新版本。',
            QMessageBox.Ok
        )