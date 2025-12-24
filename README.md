# 期权交易自动化程序 v2.0 (模块化版本)

## 项目概述

这是一个基于Selenium的期权交易自动化程序，采用模块化架构设计，实现基于价格波动的双向套利交易策略。

## 新版本特性

### 模块化架构
- **配置模块** (`config/`): 集中管理所有系统参数
- **认证模块** (`auth/`): 处理用户登录和合约选择
- **数据模块** (`data/`): 市场数据获取和管理
- **策略模块** (`strategy/`): 交易策略实现
- **执行模块** (`execution/`): 交易执行和确认
- **监控模块** (`monitor/`): 交易监控和报告
- **工具模块** (`utils/`): 浏览器工具和辅助函数
- **集成模块** (`trading_system_gui.py`): GUI 系统的核心后端逻辑封装

### 优势
- **易于维护**: 各功能模块独立，便于调试和修改
- **易于扩展**: 可轻松添加新的交易策略或数据源
- **便于测试**: 每个模块可独立进行单元测试
- **支持界面化**: 清晰的接口设计，便于后续添加Web界面

## 安装依赖

```bash
pip install selenium pandas
```

需要安装Chrome浏览器和对应的ChromeDriver。

## 配置参数

在 `config/settings.py` 中修改配置：

```python
# 基础配置
TARGET_URL = "https://ares.sse.com.cn/"
USERNAME = "您的用户名"
PASSWORD = "您的密码"
TARGET_CONTRACT = "您的合约代码"

# 交易参数
TRADE_QTY = 10            # 单次交易数量
THRESHOLD = 0.005         # 价格变动阈值 (0.5%)
CONTRACT_MULTIPLIER = 10000  # 合约乘数

# 时间参数
FIXED_DELAY_BEFORE_OPEN = 2.0  # 信号触发后等待时间
TARGET_INTERVAL_CLOSE = 5.0    # 目标平仓间隔
```

## 运行程序

```bash
python main.py
```

## 程序架构

### TradingSystemGUI (核心集成类 - `trading_system_gui.py`)
- **定位**：作为 GUI 界面与底层交易逻辑之间的桥梁（中继层）。
- **多线程架构**：内置 `TradingThread` (基于 `QThread`)，确保复杂的交易逻辑、网络请求（Selenium）和策略分析在后台运行，不阻塞主界面的响应。
- **信号机制**：通过 PyQt5 的信号槽机制，实时向界面推送：
  - `market_data_updated`: 行情数据更新（价格、IV等）。
  - `trade_signal_generated`: 策略生成的交易信号。
  - `position_updated`: 当前持仓状态（盈亏、持仓量）。
  - `trade_executed`: 交易执行结果。
- **组件集成**：统一管理 `MarketData`、`StrategyManager`、`TradeExecutor` 等核心组件的生命周期。
- **手动交易支持**：提供手动开平仓接口，允许用户通过界面直接干预交易。

### TradingSystem (主控制器)
- 协调各个模块的工作
- 管理交易生命周期
- 处理异常和清理资源

### 数据流
1. **MarketData** 获取实时行情数据
2. **TradingStrategy** 分析数据并生成交易信号
3. **TradeExecutor** 执行交易操作
4. **TradingMonitor** 记录和监控交易结果

### 关键接口

#### MarketData
- `get_market_depth_price()`: 获取买卖价
- `update_price_history()`: 更新价格历史
- `get_market_status()`: 获取市场状态

#### TradingStrategy
- `analyze_market_data()`: 分析市场并生成信号
- `should_close_position()`: 判断是否平仓
- `update_position()`: 更新持仓信息

#### TradeExecutor
- `execute_with_signal()`: 根据信号执行交易
- `wait_for_trade_completion()`: 等待交易成交
- `get_latest_trade_record()`: 获取最新成交记录

#### TradingMonitor
- `record_trading_session()`: 记录交易会话
- `get_monitoring_stats()`: 获取统计信息
- `generate_daily_report()`: 生成日报

## 扩展开发

### 添加新的交易策略

1. 在 `strategy/` 目录创建新的策略类
2. 继承或参考 `TradingStrategy` 的接口设计
3. 实现 `analyze_market_data()` 方法生成信号

### 添加新的数据源

1. 在 `data/` 目录创建新的数据类
2. 实现 `get_market_depth_price()` 等接口
3. 适配数据格式和更新频率

### 添加Web界面

各个模块已经提供了清晰的接口，可以轻松集成Web框架：

```python
# Flask示例
from flask import Flask
from trading_system import TradingSystem

app = Flask(__name__)
trading_system = TradingSystem()

@app.route('/api/status')
def get_status():
    return trading_system.monitor.get_monitoring_stats()

@app.route('/api/start')
def start_trading():
    threading.Thread(target=trading_system.run).start()
    return {"status": "started"}
```

## 风险提示

1. 交易具有高风险，请在充分测试后使用
2. 确保网络连接稳定，避免延迟导致的交易失败
3. 建议先在模拟环境测试策略有效性
4. 程序包含异常处理，但异常情况可能需要人工介入

## 版本历史

- v1.0: 单体架构，基础功能实现
- v2.0: 模块化重构，提高可维护性和扩展性

## 技术支持

如有问题或建议，请通过以下方式联系：
- 提交Issue到代码仓库
- 发送邮件至技术支持邮箱