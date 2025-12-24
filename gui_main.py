"""
期权交易GUI程序入口
启动图形化界面的交易系统
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置Qt插件路径（如果需要）
# os.environ['QT_PLUGIN_PATH'] = os.path.join(os.path.dirname(__file__), 'plugins')

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from gui.app import TradingApp


def main():
    """主函数"""
    # 设置高DPI支持 (必须在创建QApplication之前设置)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    print("="*50)
    print("期权交易自动化系统 v2.0 (GUI版本)")
    print("="*50)
    print("正在启动图形界面...")

    try:
        app = TradingApp(sys.argv)
        ret = app.exec_()
        print("程序已退出")
        sys.exit(ret)

    except ImportError as e:
        print(f"导入模块失败: {e}")
        print("\n请确保已安装所有依赖:")
        print("pip install -r requirements.txt")
        sys.exit(1)

    except Exception as e:
        print(f"程序启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()