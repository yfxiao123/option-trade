# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个期权交易自动化程序，使用 Selenium 进行 Web 自动化，实现基于价格波动的双向套利交易策略。程序监控期权合约的价格变化，当检测到超过阈值的暴涨或暴跌信号时，自动执行开仓和平仓操作。

## 依赖管理

项目依赖以下 Python 库（需要手动安装）：
```bash
pip install selenium pandas
```

还需要安装 Chrome 浏览器和对应的 ChromeDriver。

## 核心配置

在 `code.py` 文件顶部的配置区域需要设置：
- `TARGET_URL`: 交易网站URL（默认：https://ares.sse.com.cn/）
- `USERNAME`: 交易账户用户名
- `PASSWORD`: 交易账户密码
- `TARGET_CONTRACT`: 目标期权合约代码
- `EXCEL_FILE_PATH`: 交易记录导出路径

## 策略参数

重要的交易参数：
- `FIXED_DELAY_BEFORE_OPEN`: 信号触发后等待时间（默认2秒）
- `TARGET_INTERVAL_CLOSE`: 开仓到平仓的目标间隔（默认5秒）
- `TRADE_QTY`: 单次交易数量（默认10）
- `THRESHOLD`: 价格变动阈值（默认0.005，即0.5%）
- `CONTRACT_MULTIPLIER`: 合约乘数（默认10000）

## 运行方式

```bash
python code.py
```

## 代码架构

主要模块功能：
1. **浏览器控制** (`setup_driver`): 配置 Chrome 浏览器选项，反检测自动化
2. **登录模块** (`login`): 自动填写用户名密码并登录
3. **合约选择** (`select_contract_auto`): 在期权列表中查找并选择目标合约
4. **价格监控** (`get_market_depth_price`): 获取实时买一价和卖一价
5. **交易执行** (`trade_option`): 通用下单函数，支持开仓和平仓
6. **策略核心** (`run_dual_strategy`): 双向套利策略主循环
7. **记录追踪** (`fetch_latest_trade_record`): 获取最新成交记录

## 交易策略

程序采用双向动态套利策略：
- 监控连续3个时间点的价格变化
- 当卖价上涨超过阈值时，执行买入开仓 -> 卖出平仓
- 当买价下跌超过阈值时，执行卖出开仓 -> 买入平仓
- 每次交易完成后记录到Excel文件，包含平均平仓价和累计收益

## 注意事项

1. 交易具有高风险，在实盘环境前需充分测试
2. 需要确保网络连接稳定，避免因延迟导致交易失败
3. ChromeDriver 版本需要与 Chrome 浏览器版本匹配
4. 程序包含异常处理，但在出现异常时需要人工介入