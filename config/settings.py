"""
期权交易系统配置文件
集中管理所有系统参数，便于维护和调整
"""

class TradingConfig:
    """交易系统配置类"""

    # 基础配置
    TARGET_URL = "https://ares.sse.com.cn/"
    USERNAME = "X000009875"
    PASSWORD = "00979386Abc!"
    TARGET_CONTRACT = "10009497"
    EXCEL_FILE_PATH = "arbitrage_advanced_stats.xlsx"

    # 时间参数
    FIXED_DELAY_BEFORE_OPEN = 2.0  # 信号触发后等待时间
    TARGET_INTERVAL_CLOSE = 5.0    # 开仓到平仓的目标间隔
    SYSTEM_DELAY = 1.0             # UI刷新硬等待

    # 交易参数
    TRADE_QTY = 10                 # 单次交易数量
    THRESHOLD = 0.005              # 价格变动阈值（0.5%）
    CONTRACT_MULTIPLIER = 10000    # 合约乘数

    # 策略参数
    HISTORY_LEN = 3                # 价格历史长度
    INTERVAL = 0.5                 # 价格监控间隔（秒）
    THRESHOLD = 0.005              # 价格变动阈值（0.5%）
    TRADE_QTY = 10                 # 单次交易数量

    # 期权波动率策略参数
    IV_UPPER_THRESHOLD = 0.4       # 隐含波动率上限
    IV_LOWER_THRESHOLD = 0.2       # 隐含波动率下限
    TIME_VALUE_RATIO = 0.8         # 时间价值占比阈值
    MAX_HOLDING_TIME = 600         # 最大持仓时间（秒）

    # 浏览器配置
    BROWSER_WINDOW_SIZE = "1400,900"
    PAGE_LOAD_TIMEOUT = 10         # 页面加载超时时间
    ELEMENT_WAIT_TIMEOUT = 5       # 元素等待超时时间

    # 重试参数
    MAX_RETRY_COUNT = 3            # 最大重试次数
    RETRY_INTERVAL = 1.0           # 重试间隔（秒）

    @classmethod
    def update_config(cls, **kwargs):
        """动态更新配置参数"""
        for key, value in kwargs.items():
            if hasattr(cls, key):
                setattr(cls, key, value)
            else:
                print(f"警告：未知配置参数 {key}")

    @classmethod
    def get_config_dict(cls):
        """获取所有配置参数的字典"""
        config = {}
        for attr in dir(cls):
            if not attr.startswith('_'):
                value = getattr(cls, attr)
                if not callable(value):
                    config[attr] = value
        return config

# 创建全局配置实例
config = TradingConfig()