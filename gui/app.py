"""
期权交易GUI应用核心
应用程序主入口，负责初始化和启动GUI
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QIcon
from gui.main_window import MainWindow
from config import config


class TradingApp(QApplication):
    """交易应用程序主类"""

    def __init__(self, argv):
        super().__init__(argv)

        # 设置应用属性
        self.setApplicationName("期权交易自动化系统")
        self.setApplicationVersion("2.0")
        self.setOrganizationName("QuantTrading")

        # 创建主窗口
        self.main_window = MainWindow()
        self.main_window.show()

        # 设置定时器处理事件
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_events)
        self.timer.start(100)  # 每100ms处理一次事件

        # 设置样式
        self.setup_style()

    def setup_style(self):
        """设置应用样式"""
        try:
            # 尝试加载样式文件
            style_file = os.path.join(os.path.dirname(__file__), 'styles', 'dark.qss')
            if os.path.exists(style_file):
                with open(style_file, 'r', encoding='utf-8') as f:
                    self.setStyleSheet(f.read())
        except Exception as e:
            print(f"加载样式失败: {e}")

    def process_events(self):
        """处理应用事件"""
        # 可以在这里添加定期处理的事件
        pass

    def close_all(self):
        """关闭所有窗口和资源"""
        self.main_window.close()
        self.quit()


def main():
    """GUI应用入口函数"""
    app = TradingApp(sys.argv)

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        app.close_all()
    except Exception as e:
        print(f"应用异常退出: {e}")
        app.close_all()


if __name__ == "__main__":
    main()