"""
浏览器工具模块
提供浏览器初始化和基本操作功能
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from config import config


def setup_driver():
    """配置并初始化Chrome浏览器驱动"""
    options = Options()
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument(f'--window-size={config.BROWSER_WINDOW_SIZE}')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)

    return driver


def wait_and_click(driver, locator, timeout=None):
    """等待元素可点击并点击"""
    if timeout is None:
        timeout = config.ELEMENT_WAIT_TIMEOUT

    wait = WebDriverWait(driver, timeout)
    element = wait.until(EC.element_to_be_clickable(locator))
    driver.execute_script("arguments[0].click();", element)
    return element


def wait_for_element(driver, locator, timeout=None):
    """等待元素出现"""
    if timeout is None:
        timeout = config.ELEMENT_WAIT_TIMEOUT

    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.presence_of_element_located(locator))


def scroll_to_element(driver, element):
    """滚动到元素位置"""
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)


def safe_find_element(driver, locator, default=None):
    """安全查找元素，失败时返回默认值"""
    try:
        return driver.find_element(*locator)
    except:
        return default


def safe_find_elements(driver, locator, default=None):
    """安全查找多个元素，失败时返回默认值"""
    try:
        return driver.find_elements(*locator)
    except:
        return default or []