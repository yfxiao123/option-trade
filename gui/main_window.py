"""
主窗口模块（重构版）
交易系统的主界面，整合所有子面板和组件
"""

import sys
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QSplitter, QMenuBar, QStatusBar, QAction,
                             QToolBar, QDockWidget, QMessageBox, QTabWidget,
                             QLabel, QFileDialog)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon, QFont, QKeySequence

# 导入面板
from gui.widgets.market_panel import MarketPanel
from gui.widgets.trade_panel import TradePanel
from gui.widgets.position_panel import PositionPanel
from gui.widgets.strategy_panel import StrategyPanel
from gui.widgets.trade_history_panel import TradeHistoryPanel
from gui.widgets.log_panel import LogPanel

# 导入对话框
from gui.dialogs.settings_dialog import SettingsDialog
from gui.dialogs.about_dialog import AboutDialog

# 导入交易系统
from trading_system_gui import TradingSystemGUI
from database import get_database


class MainWindow(QMainWindow):
    """主窗口类（重构版）"""

    # 定义信号
    market_data_updated = pyqtSignal(dict)
    trade_signal_generated = pyqtSignal(object)
    position_updated = pyqtSignal(dict)
    trade_executed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.trading_system = TradingSystemGUI()
        self.db = get_database()
        self.setup_status_bar()
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        """初始化用户界面"""
        # 设置窗口属性
        self.setWindowTitle("期权交易自动化系统 v2.0")
        self.setGeometry(100, 100, 1600, 900)
        self.setMinimumSize(1400, 800)

        # 创建中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # 创建主布局
        self.main_layout = QHBoxLayout(self.central_widget)

        # 创建水平分割器（左右布局）
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.main_splitter)

        # 创建左侧面板（市场行情）
        self.create_left_panel()

        # 创建右侧面板（交易、策略、持仓、历史）
        self.create_right_panel()

        # 创建菜单栏
        self.create_menu_bar()

        # 创建工具栏
        self.create_tool_bar()

        # 创建停靠窗口（日志）
        self.create_dock_widgets()

        # 设置初始分割比例
        self.main_splitter.setSizes([900, 700])

    def create_left_panel(self):
        """创建左侧面板（市场行情）"""
        # 市场面板已经整合了价格图和成交量
        self.market_panel = MarketPanel()
        self.main_splitter.addWidget(self.market_panel)

    def create_right_panel(self):
        """创建右侧面板（交易、策略、持仓、历史）"""
        # 创建选项卡控件
        self.right_tabs = QTabWidget()
        self.right_tabs.setTabPosition(QTabWidget.North)
        self.right_tabs.setDocumentMode(True)

        # 1. 交易面板
        self.trade_panel = TradePanel()
        self.right_tabs.addTab(self.trade_panel, "📈 交易")

        # 2. 策略管理面板
        self.strategy_panel = StrategyPanel()
        self.right_tabs.addTab(self.strategy_panel, "⚙️ 策略")

        # 3. 持仓监控面板
        self.position_panel = PositionPanel()
        self.right_tabs.addTab(self.position_panel, "📊 持仓")

        # 4. 交易历史面板
        self.trade_history_panel = TradeHistoryPanel()
        self.right_tabs.addTab(self.trade_history_panel, "🕒 历史")

        # 将选项卡添加到主分割器
        self.main_splitter.addWidget(self.right_tabs)
        # 设置默认显示的选项卡（例如策略管理）
        self.right_tabs.setCurrentIndex(1)

    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu('文件(&F)')

        # 连接交易系统
        connect_action = QAction('连接交易系统(&C)', self)
        connect_action.setShortcut('F2')
        connect_action.triggered.connect(self.connect_trading_system)
        file_menu.addAction(connect_action)

        # 断开连接
        disconnect_action = QAction('断开连接(&D)', self)
        disconnect_action.setShortcut('F3')
        disconnect_action.triggered.connect(self.disconnect_trading_system)
        file_menu.addAction(disconnect_action)

        file_menu.addSeparator()

        # 导出交易记录
        export_action = QAction('导出交易记录(&E)', self)
        export_action.triggered.connect(self.export_trade_data)
        file_menu.addAction(export_action)

        # 导出策略汇总
        export_summary_action = QAction('导出策略汇总(&S)', self)
        export_summary_action.triggered.connect(self.export_strategy_summary)
        file_menu.addAction(export_summary_action)

        file_menu.addSeparator()

        # 退出
        exit_action = QAction('退出(&Q)', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 工具菜单
        tools_menu = menubar.addMenu('工具(&T)')

        # 设置
        settings_action = QAction('设置(&S)', self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)

        # 帮助菜单
        help_menu = menubar.addMenu('帮助(&H)')

        # 关于
        about_action = QAction('关于(&A)', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_tool_bar(self):
        """创建工具栏"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 连接按钮
        self.connect_btn = toolbar.addAction("🔌 连接")
        self.connect_btn.triggered.connect(self.connect_trading_system)

        # 断开按钮
        self.disconnect_btn = toolbar.addAction("🔌 断开")
        self.disconnect_btn.triggered.connect(self.disconnect_trading_system)

        toolbar.addSeparator()

        # 启动策略按钮
        self.start_strategy_btn = toolbar.addAction("▶ 启动策略")
        self.start_strategy_btn.triggered.connect(self.start_strategy)

        # 停止策略按钮
        self.stop_strategy_btn = toolbar.addAction("⏹ 停止策略")
        self.stop_strategy_btn.triggered.connect(self.stop_strategy)

        toolbar.addSeparator()

        # 紧急停止按钮
        self.emergency_stop_btn = toolbar.addAction("🛑 紧急停止")
        self.emergency_stop_btn.triggered.connect(self.emergency_stop_all)

        # 初始状态
        self.update_connection_status(False)

    def create_dock_widgets(self):
        """创建停靠窗口"""
        # 日志窗口
        self.log_dock = QDockWidget("系统日志", self)
        self.log_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.log_panel = LogPanel()
        self.log_dock.setWidget(self.log_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)

    def setup_connections(self):
        """设置信号连接"""
        # 连接交易系统信号
        self.trading_system.market_data_updated.connect(self.on_market_data_updated)
        self.trading_system.trade_signal_generated.connect(self.on_trade_signal_generated)
        self.trading_system.position_updated.connect(self.on_position_updated)
        self.trading_system.trade_executed.connect(self.on_trade_executed)

        # 连接面板信号
        self.trade_panel.manual_trade_requested.connect(self.on_manual_trade_requested)
        self.trade_panel.auto_trade_toggled.connect(self.on_auto_trade_toggled)
        self.trade_panel.strategy_changed.connect(self.on_strategy_changed)
        self.strategy_panel.strategy_parameters_changed.connect(self.on_strategy_parameters_changed)

    def setup_status_bar(self):
        """设置状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 状态标签
        self.connection_label = QLabel("连接状态: 未连接")
        self.status_bar.addPermanentWidget(self.connection_label)

        # 活跃策略标签
        self.strategy_label = QLabel("活跃策略: 无")
        self.status_bar.addPermanentWidget(self.strategy_label)

        self.position_label = QLabel("持仓: 0")
        self.status_bar.addPermanentWidget(self.position_label)

        self.pnl_label = QLabel("盈亏: 0.00")
        self.status_bar.addPermanentWidget(self.pnl_label)

    @pyqtSlot()
    def connect_trading_system(self):
        """连接交易系统"""
        try:
            self.log_panel.log_info("正在连接交易系统...")
            success = self.trading_system.initialize()

            if success:
                self.log_panel.log_success("交易系统连接成功")
                self.update_connection_status(True)
            else:
                self.log_panel.log_error("交易系统连接失败")

        except Exception as e:
            self.log_panel.log_error(f"连接异常: {e}")
            QMessageBox.critical(self, "连接错误", f"无法连接到交易系统: {e}")

    @pyqtSlot()
    def disconnect_trading_system(self):
        """断开交易系统"""
        try:
            self.log_panel.log_info("正在断开交易系统...")
            self.trading_system.cleanup()
            self.update_connection_status(False)
            self.log_panel.log_info("交易系统已断开")

        except Exception as e:
            self.log_panel.log_error(f"断开异常: {e}")

    @pyqtSlot()
    def start_strategy(self):
        """启动交易策略"""
        if not self.trading_system.is_connected():
            QMessageBox.warning(self, "警告", "请先连接交易系统")
            return

        try:
            self.log_panel.log_info("正在启动交易策略...")
            self.trading_system.start_strategy()
            self.strategy_panel.start_runtime_timer()
            self.log_panel.log_success("交易策略已启动")

        except Exception as e:
            self.log_panel.log_error(f"启动策略失败: {e}")

    @pyqtSlot()
    def stop_strategy(self):
        """停止交易策略"""
        try:
            self.log_panel.log_info("正在停止交易策略...")
            self.trading_system.stop_strategy()
            self.strategy_panel.stop_runtime_timer()
            self.log_panel.log_success("交易策略已停止")

        except Exception as e:
            self.log_panel.log_error(f"停止策略失败: {e}")

    @pyqtSlot()
    def emergency_stop_all(self):
        """紧急停止所有策略"""
        reply = QMessageBox.warning(
            self, '紧急停止',
            "确定要紧急停止所有策略吗？\n这将立即停止所有自动交易并禁用所有策略。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # 停止交易系统
                self.trading_system.stop_strategy()

                # 禁用所有策略
                from strategy import get_strategy_manager
                manager = get_strategy_manager()
                manager.disable_all_strategies()

                # 停止运行时间计时
                self.strategy_panel.stop_runtime_timer()

                self.log_panel.log_warning("已紧急停止所有策略")
                QMessageBox.information(self, "提示", "所有策略已紧急停止")

            except Exception as e:
                self.log_panel.log_error(f"紧急停止失败: {e}")

    @pyqtSlot(dict)
    def on_market_data_updated(self, market_data):
        """处理市场数据更新"""
        # 更新行情面板
        self.market_panel.update_market_data(market_data)

        # 发出信号
        self.market_data_updated.emit(market_data)

    @pyqtSlot(object)
    def on_trade_signal_generated(self, signal):
        """处理交易信号"""
        self.log_panel.log_signal(f"交易信号: {signal}")
        self.trade_signal_generated.emit(signal)

    @pyqtSlot(dict)
    def on_position_updated(self, position_info):
        """处理持仓更新"""
        # 更新持仓面板
        self.position_panel.update_position(position_info)

        # 更新状态栏
        self.position_label.setText(f"持仓: {position_info.get('quantity', 0)}")
        self.pnl_label.setText(f"盈亏: {position_info.get('unrealized_pnl', 0):.2f}")

        # 更新活跃策略显示
        strategy_name = position_info.get('strategy_name', '')
        if strategy_name:
            self.strategy_label.setText(f"活跃策略: {strategy_name}")

        # 发出信号
        self.position_updated.emit(position_info)

    @pyqtSlot(dict)
    def on_trade_executed(self, trade_info):
        """处理交易执行"""
        self.log_panel.log_trade(f"交易执行: {trade_info}")

        # 添加到交易历史
        self.trade_history_panel.add_trade(trade_info)

        # 发出信号
        self.trade_executed.emit(trade_info)

    @pyqtSlot(dict)
    def on_manual_trade_requested(self, trade_params):
        """处理手动交易请求"""
        try:
            self.log_panel.log_info(f"执行手动交易: {trade_params}")
            
            # 检查连接状态
            if not self.trading_system.is_connected():
                QMessageBox.warning(self, "警告", "交易系统未连接，请先连接交易系统")
                return
            
            # 执行手动交易
            success = self.trading_system.execute_manual_trade(trade_params)
            
            if success:
                self.log_panel.log_info("手动交易请求已发送")
                QMessageBox.information(self, "成功", "手动交易已执行")
            else:
                self.log_panel.log_error("手动交易执行失败")
                QMessageBox.warning(self, "失败", "手动交易执行失败")
                
        except Exception as e:
            self.log_panel.log_error(f"手动交易失败: {e}")
            QMessageBox.critical(self, "错误", f"手动交易失败: {e}")

    @pyqtSlot(str, dict)
    def on_strategy_parameters_changed(self, strategy_name: str, params: dict):
        """处理策略参数变更"""
        try:
            self.trading_system.update_strategy_parameters(params)
            self.log_panel.log_info(f"策略参数已更新 [{strategy_name}]: {params}")
        except Exception as e:
            self.log_panel.log_error(f"更新策略参数失败: {e}")

    @pyqtSlot()
    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        if dialog.exec_():
            # 应用设置
            settings = dialog.get_settings()
            self.apply_settings(settings)

    @pyqtSlot()
    def show_about(self):
        """显示关于对话框"""
        dialog = AboutDialog(self)
        dialog.exec_()

    @pyqtSlot()
    def export_trade_data(self):
        """导出交易数据"""
        try:
            # 选择保存路径
            default_name = f"交易记录_{self._get_timestamp()}.xlsx"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出交易记录", default_name, "Excel文件 (*.xlsx)"
            )

            if not file_path:
                return

            # 导出
            success = self.db.export_to_excel(file_path)

            if success:
                QMessageBox.information(self, "成功", f"交易记录已导出到:\n{file_path}")
            else:
                QMessageBox.warning(self, "警告", "导出失败或没有数据可导出")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {e}")

    @pyqtSlot()
    def export_strategy_summary(self):
        """导出策略汇总"""
        try:
            # 选择保存路径
            default_name = f"策略汇总_{self._get_timestamp()}.xlsx"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出策略汇总", default_name, "Excel文件 (*.xlsx)"
            )

            if not file_path:
                return

            # 导出
            success = self.db.export_summary_to_excel(file_path)

            if success:
                QMessageBox.information(self, "成功", f"策略汇总已导出到:\n{file_path}")
            else:
                QMessageBox.warning(self, "警告", "导出失败或没有数据可导出")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {e}")

    def _get_timestamp(self) -> str:
        """获取时间戳字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def update_connection_status(self, connected):
        """更新连接状态"""
        if connected:
            self.connection_label.setText("连接状态: 已连接")
            self.connection_label.setStyleSheet("color: #27ae60;")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.start_strategy_btn.setEnabled(True)
            self.stop_strategy_btn.setEnabled(True)
            self.emergency_stop_btn.setEnabled(True)
        else:
            self.connection_label.setText("连接状态: 未连接")
            self.connection_label.setStyleSheet("color: #e74c3c;")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self.start_strategy_btn.setEnabled(False)
            self.stop_strategy_btn.setEnabled(False)
            self.emergency_stop_btn.setEnabled(False)

    def apply_settings(self, settings):
        """应用设置"""
        # TODO: 实现设置应用逻辑
        pass

    @pyqtSlot(bool)
    def on_auto_trade_toggled(self, enabled: bool):
        """处理自动交易开关"""
        try:
            if enabled:
                # 启动自动交易
                current_strategy = self.trade_panel.get_current_strategy()
                if current_strategy:
                    # 设置活跃策略
                    self.trading_system.strategy_manager.set_active_strategy(current_strategy)
                    # 启动策略执行
                    self.trading_system.start_strategy()
                    self.log_panel.log_info(f"自动交易已启动，使用策略: {current_strategy}")
                    self.strategy_label.setText(f"活跃策略: {current_strategy}")
                else:
                    self.log_panel.log_warning("没有可用的策略，无法启动自动交易")
                    self.trade_panel.auto_trade_checkbox.setChecked(False)
            else:
                # 停止自动交易
                self.trading_system.stop_strategy()
                self.log_panel.log_info("自动交易已停止")
                self.strategy_label.setText("活跃策略: 无")
        except Exception as e:
            self.log_panel.log_error(f"自动交易切换失败: {e}")

    @pyqtSlot(str)
    def on_strategy_changed(self, strategy_name: str):
        """处理策略变更"""
        try:
            self.log_panel.log_info(f"策略已切换到: {strategy_name}")
            self.strategy_label.setText(f"活跃策略: {strategy_name}")
            
            # 如果自动交易正在运行，重启策略
            if self.trade_panel.auto_trade_checkbox.isChecked():
                self.trading_system.stop_strategy()
                # 设置新的活跃策略
                self.trading_system.strategy_manager.set_active_strategy(strategy_name)
                # 重新启动策略执行
                self.trading_system.start_strategy()
                self.log_panel.log_info(f"已重启策略: {strategy_name}")
        except Exception as e:
            self.log_panel.log_error(f"策略切换失败: {e}")

    def closeEvent(self, event):
        """关闭事件处理"""
        reply = QMessageBox.question(
            self, '确认退出',
            '确定要退出期权交易系统吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 清理资源
            if hasattr(self, 'trading_system'):
                self.trading_system.cleanup()
            event.accept()
        else:
            event.ignore()
