"""
登录模块
处理用户登录和合约选择功能
"""

import time
from selenium.webdriver.common.by import By
from utils import wait_and_click, wait_for_element, scroll_to_element
from config import config


class LoginManager:
    """登录管理器"""

    def __init__(self, driver):
        self.driver = driver

    def login(self, username=None, password=None):
        """执行登录操作"""
        username = username or config.USERNAME
        password = password or config.PASSWORD

        try:
            print(f"正在访问: {config.TARGET_URL}")
            self.driver.get(config.TARGET_URL)

            # 输入用户名
            user_input = wait_for_element(
                self.driver,
                (By.NAME, "username")
            )
            user_input.clear()
            user_input.send_keys(username)

            # 输入密码
            self.driver.find_element(By.NAME, "password").send_keys(password)
            time.sleep(1)

            # 点击登录按钮
            login_btn = self.driver.find_element(
                By.XPATH,
                "//button[contains(@class, 'el-button--primary')]//span[contains(text(), '登录')]/.."
            )
            self.driver.execute_script("arguments[0].click();", login_btn)

            print("登录操作已执行，等待页面加载...")
            time.sleep(5)

            return True

        except Exception as e:
            print(f"登录失败: {e}")
            raise e

    def select_contract(self, contract_code=None):
        """自动选择目标合约"""
        contract_code = contract_code or config.TARGET_CONTRACT

        print(f"\n正在列表中搜索合约: {contract_code} ...")
        try:
            # 尝试点击期权标签
            try:
                option_tab = self.driver.find_element(
                    By.XPATH,
                    "//div[contains(@class,'el-tabs__item') and contains(text(),'期权')]"
                )
                self.driver.execute_script("arguments[0].click();", option_tab)
                time.sleep(0.5)
            except:
                pass

            # 查找并点击目标合约
            target_xpath = f"//div[contains(@class, 'twoTableWrapper')]//div[contains(@class, 'cell') and normalize-space(text())='{contract_code}']"
            target_element = wait_for_element(
                self.driver,
                (By.XPATH, target_xpath)
            )

            scroll_to_element(self.driver, target_element)
            time.sleep(1)
            target_element.click()

            print(f"成功选中合约: {contract_code}")
            time.sleep(2)

            return True

        except Exception as e:
            print(f"无法选中合约: {e}")
            raise e