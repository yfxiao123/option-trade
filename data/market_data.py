"""
市场数据获取模块
提供实时行情数据获取、价格变化监控和历史数据管理功能
"""

import time
import datetime
import collections
from typing import Optional, Tuple, List, Dict
from selenium.webdriver.common.by import By
from config import config


class MarketData:
    """市场数据管理器"""

    def __init__(self, driver):
        self.driver = driver
        self.price_history = collections.deque(maxlen=config.HISTORY_LEN)
        self.last_update_time = None

    def select_contract(self, contract_code: str) -> bool:
        """
        选中指定的合约
        实现与 code.py 一致
        """
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            wait = WebDriverWait(self.driver, 10)
            print(f"正在尝试选中合约: {contract_code} ...")
            
            # 1. 尝试点击“期权”标签
            try:
                option_tab = self.driver.find_element(By.XPATH, "//div[contains(@class,'el-tabs__item') and contains(text(),'期权')]")
                self.driver.execute_script("arguments[0].click();", option_tab)
                time.sleep(1)
            except Exception as e:
                print(f"点击期权标签失败(可能已选中): {e}")

            # 2. 查找并选中合约
            target_xpath = f"//div[contains(@class, 'twoTableWrapper')]//div[contains(@class, 'cell') and normalize-space(text())='{contract_code}']"
            target_element = wait.until(EC.presence_of_element_located((By.XPATH, target_xpath)))
            
            # 滚动到视图并点击
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target_element)
            time.sleep(1)
            self.driver.execute_script("arguments[0].click();", target_element)
            
            print(f"✅ 成功选中合约: {contract_code}")
            time.sleep(2)  # 等待界面刷新
            return True
            
        except Exception as e:
            print(f"❌ 选中合约失败: {e}")
            return False

    def get_market_depth_price(self) -> Tuple[Optional[float], Optional[float]]:
        """
        获取市场深度价格（买一价和卖一价）
        使用与code.py完全相同的实现方式

        Returns:
            Tuple[买一价, 卖一价] 或 (None, None) 如果获取失败
        """
        try:

            # 检查五档面板是否存在
            try:
                pane = self.driver.find_element(By.ID, 'pane-wudang')
                if not pane.is_displayed():
                    print("DEBUG: pane-wudang 存在但不显示，尝试点击对应标签")
                    tab = self.driver.find_element(By.ID, 'tab-wudang')
                    self.driver.execute_script("arguments[0].click();", tab)
                    time.sleep(0.5)
            except Exception as e:
                print(f"DEBUG: 找不到 pane-wudang: {e}")
                return None, None

            # 与 code.py 完全一致的实现方式
            sell_xpath = "//div[@id='pane-wudang']//tr[.//div[contains(text(),'卖1')]]//td[2]//span"
            buy_xpath = "//div[@id='pane-wudang']//tr[.//div[contains(text(),'买1')]]//td[2]//span"
            
            sell_element = self.driver.find_element(By.XPATH, sell_xpath)
            buy_element = self.driver.find_element(By.XPATH, buy_xpath)
            
            sell_1 = float(sell_element.text.strip())
            buy_1 = float(buy_element.text.strip())
            
            return buy_1, sell_1
        except Exception as e:
            # 记录具体错误
            print(f"获取市场深度数据失败: {e}")
            return None, None

    def update_price_history(self):
        """更新价格历史记录"""
        bid, ask = self.get_market_depth_price()
        if bid is not None and ask is not None:
            timestamp = datetime.datetime.now()
            self.price_history.append({
                'timestamp': timestamp,
                'bid': bid,
                'ask': ask
            })
            self.last_update_time = timestamp
            return True
        return False

    def get_latest_prices(self) -> Optional[Dict]:
        """获取最新价格数据"""
        if self.price_history:
            return self.price_history[-1]
        return None

    def get_price_change(self) -> Tuple[float, float]:
        """
        计算价格变化率

        Returns:
            Tuple[买价变化率, 卖价变化率]
        """
        if len(self.price_history) < config.HISTORY_LEN:
            return 0.0, 0.0

        current = self.price_history[-1]
        old = self.price_history[0]

        bid_change = (current['bid'] - old['bid']) / old['bid'] if old['bid'] > 0 else 0
        ask_change = (current['ask'] - old['ask']) / old['ask'] if old['ask'] > 0 else 0

        return bid_change, ask_change

    def is_price_history_ready(self) -> bool:
        """检查价格历史是否已准备就绪"""
        return len(self.price_history) >= config.HISTORY_LEN

    def clear_history(self):
        """清空价格历史"""
        self.price_history.clear()

    def get_market_status(self) -> Dict:
        """
        获取市场状态信息

        Returns:
            包含市场状态的字典
        """
        bid, ask = self.get_market_depth_price()
        bid_change, ask_change = self.get_price_change()
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        return {
            'timestamp': timestamp,
            'bid': bid,
            'ask': ask,
            'bid_change': bid_change,
            'ask_change': ask_change,
            'spread': ask - bid if bid and ask else None,
            'mid_price': (bid + ask) / 2 if bid and ask else None,
            'history_ready': self.is_price_history_ready(),
            'history_length': len(self.price_history)
        }

    def start_monitoring(self, callback=None, interval=None):
        """
        开始监控市场数据

        Args:
            callback: 数据更新时的回调函数
            interval: 监控间隔（秒），默认使用配置中的间隔
        """
        interval = interval or config.INTERVAL

        print(f"开始监控市场数据，间隔: {interval}秒")

        while True:
            try:
                if self.update_price_history():
                    market_status = self.get_market_status()

                    if callback:
                        callback(market_status)

                    # 打印市场状态
                    if market_status['bid'] and market_status['ask']:
                        print(f"\r[{market_status['timestamp']}] "
                              f"卖:{market_status['ask']:.4f}({market_status['ask_change']:.2%}) | "
                              f"买:{market_status['bid']:.4f}({market_status['bid_change']:.2%}) | "
                              f"价差:{market_status['spread']:.4f}", end="")

                time.sleep(interval)

            except KeyboardInterrupt:
                print("\n停止监控市场数据")
                break
            except Exception as e:
                print(f"\n监控异常: {e}")
                time.sleep(1)