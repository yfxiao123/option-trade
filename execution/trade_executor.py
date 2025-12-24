"""
交易执行模块
负责执行具体的买卖操作，处理交易确认和异常情况
"""

import time
from typing import Optional, Tuple, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from utils import wait_for_element, safe_find_element
from config import config


class TradeRecord:
    """交易记录数据类"""

    def __init__(self, price: float, quantity: int, time_str: str, signature: str):
        self.price = price
        self.quantity = quantity
        self.time_str = time_str
        self.signature = signature

    def __str__(self):
        return f"{self.quantity}张 @ {self.price:.4f} [{self.time_str}]"


class TradeExecutor:
    """交易执行器"""

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, config.ELEMENT_WAIT_TIMEOUT)
        self.last_known_signature = None

    def set_market_order(self):
        """设置为市价订单"""
        try:
            dropdown_input = self.driver.find_element(
                By.XPATH,
                "//div[contains(@class, 'market')]//input"
            )

            if "市价订单" not in dropdown_input.get_attribute("value"):
                self.driver.execute_script("arguments[0].click();", dropdown_input)
                target_option = self.wait.until(
                    EC.visibility_of_element_located(
                        (By.XPATH, "//li[contains(., '市价订单')]")
                    )
                )
                self.driver.execute_script("arguments[0].click();", target_option)

            return True

        except Exception as e:
            print(f"设置市价订单失败: {e}")
            return False

    def set_quantity(self, quantity: int):
        """设置交易数量"""
        try:
            qty_input = self.driver.find_element(
                By.XPATH,
                "//span[contains(text(), '数量')]/following-sibling::div//input"
            )
            qty_input.click()
            qty_input.send_keys(Keys.CONTROL + "a")
            qty_input.send_keys(Keys.BACK_SPACE)
            qty_input.send_keys(str(quantity))

            return True

        except Exception as e:
            print(f"设置交易数量失败: {e}")
            return False

    def click_trade_button(self, action_type: str):
        """
        点击交易按钮

        Args:
            action_type: 交易类型 (buy_open, sell_open, buy_close, sell_close)
        """
        try:
            button_selectors = {
                "buy_open": "button.buyOpen",
                "sell_open": "button.sellOpen",
                "buy_close": "//button[.//span[contains(text(), '买入平仓')]]",
                "sell_close": "//button[.//span[contains(text(), '卖出平仓')]]"
            }

            selector = button_selectors.get(action_type)
            if not selector:
                raise ValueError(f"未知的交易类型: {action_type}")

            if "close" in action_type:
                trade_btn = self.driver.find_element(By.XPATH, selector)
            else:
                trade_btn = self.driver.find_element(By.CSS_SELECTOR, selector)

            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", trade_btn
            )
            self.driver.execute_script("arguments[0].click();", trade_btn)

            return True

        except Exception as e:
            print(f"点击交易按钮失败 ({action_type}): {e}")
            return False

    def confirm_trade(self):
        """确认交易弹窗"""
        try:
            confirm = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH,
                     "//div[contains(@class,'el-dialog__wrapper') and not(contains(@style,'display: none'))]//button[contains(., '提交') or contains(., '确 定')]")
                )
            )
            confirm.click()
            return True

        except:
            # 如果没有确认弹窗，直接返回成功
            return True

    def execute_trade(self, quantity: int, action_type: str) -> bool:
        """
        执行交易操作

        Args:
            quantity: 交易数量
            action_type: 交易类型

        Returns:
            交易是否成功执行
        """
        print(f"执行交易: {action_type} {quantity}张")

        # 设置市价订单
        if not self.set_market_order():
            return False

        # 设置数量
        if not self.set_quantity(quantity):
            return False

        # 点击交易按钮
        if not self.click_trade_button(action_type):
            return False

        # 确认交易
        if not self.confirm_trade():
            return False

        # 等待交易处理
        time.sleep(config.SYSTEM_DELAY)

        return True

    def get_latest_trade_record(self) -> Optional[TradeRecord]:
        """
        获取最新成交记录

        Returns:
            TradeRecord或None如果没有新记录
        """
        try:
            # 点击当日成交标签
            deal_tab = self.driver.find_element(
                By.XPATH,
                "//div[@id='tab-third' and contains(., '当日成交')]"
            )
            self.driver.execute_script("arguments[0].click();", deal_tab)
            time.sleep(0.5)

            # 获取最新成交记录
            base_xpath = "//div[@id='pane-third']//div[contains(@class, 'el-table__body-wrapper')]//tbody/tr[1]"

            time_element = safe_find_element(
                self.driver,
                (By.XPATH, f"{base_xpath}/td[1]//div")
            )
            qty_element = safe_find_element(
                self.driver,
                (By.XPATH, f"{base_xpath}/td[5]//div")
            )
            price_element = safe_find_element(
                self.driver,
                (By.XPATH, f"{base_xpath}/td[6]//div")
            )

            if not all([time_element, qty_element, price_element]):
                return None

            time_str = time_element.text.strip()
            qty = int(qty_element.text.strip())
            price = float(price_element.text.strip())

            signature = f"{time_str}_{price}_{qty}"

            # 检查是否是新的成交记录
            if self.last_known_signature and signature == self.last_known_signature:
                return None

            self.last_known_signature = signature
            return TradeRecord(price, qty, time_str, signature)

        except Exception as e:
            print(f"获取成交记录失败: {e}")
            return None

    def wait_for_trade_completion(self, timeout: float = 10.0) -> Optional[TradeRecord]:
        """
        等待交易完成并返回成交记录

        Args:
            timeout: 超时时间（秒）

        Returns:
            成交记录或None如果超时
        """
        start_time = time.time()
        last_signature = self.last_known_signature

        while time.time() - start_time < timeout:
            record = self.get_latest_trade_record()

            if record and record.signature != last_signature:
                return record

            time.sleep(0.5)

        print("等待交易成交超时")
        return None

    def execute_with_signal(self, signal) -> Optional[TradeRecord]:
        """
        根据交易信号执行交易

        Args:
            signal: 交易信号

        Returns:
            成交记录或None如果失败
        """
        # 将信号类型转换为action_type
        action_mapping = {
            "买入开仓": "buy_open",
            "卖出开仓": "sell_open",
            "买入平仓": "buy_close",
            "卖出平仓": "sell_close"
        }

        action_type = action_mapping.get(signal.signal_type.value)
        if not action_type:
            print(f"未知的信号类型: {signal.signal_type.value}")
            return None

        # 执行交易
        if self.execute_trade(signal.quantity, action_type):
            # 等待成交
            return self.wait_for_trade_completion()

        return None