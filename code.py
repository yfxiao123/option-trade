import time
import collections
import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys

# --- 配置信息 ---
TARGET_URL = "https://ares.sse.com.cn/"
USERNAME = "X000009875"
PASSWORD = "00979386Abc!"
TARGET_CONTRACT = "10009497"
EXCEL_FILE_PATH = "arbitrage_advanced_stats.xlsx"

# --- 核心时间参数 ---
FIXED_DELAY_BEFORE_OPEN = 2.0  # 阶段一：固定等待2秒
TARGET_INTERVAL_CLOSE = 5.0    # 阶段二：开仓到平仓的目标间隔（动态计算）

# --- 其他参数 ---
TRADE_QTY = 10            # 单次数量
SYSTEM_DELAY = 1.0        # UI刷新硬等待
THRESHOLD = 0.005         # 阈值
CONTRACT_MULTIPLIER = 10000 # 合约乘数 (假设1张对应10000份)

def setup_driver():
    options = Options()
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1400,900')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

def login(driver):
    try:
        print(f"正在访问: {TARGET_URL}")
        driver.get(TARGET_URL)
        wait = WebDriverWait(driver, 10)
        
        user_input = wait.until(EC.visibility_of_element_located((By.NAME, "username")))
        user_input.clear()
        user_input.send_keys(USERNAME)
        driver.find_element(By.NAME, "password").send_keys(PASSWORD)
        time.sleep(1)
        
        login_btn = driver.find_element(By.XPATH, "//button[contains(@class, 'el-button--primary')]//span[contains(text(), '登录')]/..")
        driver.execute_script("arguments[0].click();", login_btn)
        
        print("登录操作已执行，等待页面加载...")
        time.sleep(5) 
    except Exception as e:
        print(f"登录失败: {e}")
        raise e

def select_contract_auto(driver, contract_code):
    wait = WebDriverWait(driver, 10)
    print(f"\n正在列表中搜索合约: {contract_code} ...")
    try:
        try:
            driver.find_element(By.XPATH, "//div[contains(@class,'el-tabs__item') and contains(text(),'期权')]").click()
        except:
            pass 
        target_xpath = f"//div[contains(@class, 'twoTableWrapper')]//div[contains(@class, 'cell') and normalize-space(text())='{contract_code}']"
        target_element = wait.until(EC.presence_of_element_located((By.XPATH, target_xpath)))
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target_element)
        time.sleep(1)
        target_element.click()
        print(f"成功选中合约: {contract_code}")
        time.sleep(2)
    except Exception as e:
        print(f"无法选中合约: {e}")
        raise e

def get_market_depth_price(driver):
    try:
        sell_1 = float(driver.find_element(By.XPATH, "//div[@id='pane-wudang']//tr[.//div[contains(text(),'卖1')]]//td[2]//span").text.strip())
        buy_1 = float(driver.find_element(By.XPATH, "//div[@id='pane-wudang']//tr[.//div[contains(text(),'买1')]]//td[2]//span").text.strip())
        return buy_1, sell_1
    except:
        return None, None

def fetch_latest_trade_record(driver):
    """获取最新成交记录"""
    try:
        deal_tab = driver.find_element(By.XPATH, "//div[@id='tab-third' and contains(., '当日成交')]")
        driver.execute_script("arguments[0].click();", deal_tab)
        time.sleep(0.5) 

        base_xpath = "//div[@id='pane-third']//div[contains(@class, 'el-table__body-wrapper')]//tbody/tr[1]"
        time_str = driver.find_element(By.XPATH, f"{base_xpath}/td[1]//div").text.strip()
        qty = int(driver.find_element(By.XPATH, f"{base_xpath}/td[5]//div").text.strip())
        price = float(driver.find_element(By.XPATH, f"{base_xpath}/td[6]//div").text.strip())
        
        record_signature = f"{time_str}_{price}_{qty}"
        return price, qty, time_str, record_signature
    except Exception:
        return None, 0, None, None

def trade_option(driver, quantity, action_type):
    """通用下单函数"""
    wait = WebDriverWait(driver, 5)
    try:
        dropdown_input = driver.find_element(By.XPATH, "//div[contains(@class, 'market')]//input")
        if "市价订单" not in dropdown_input.get_attribute("value"):
            driver.execute_script("arguments[0].click();", dropdown_input)
            target_option = wait.until(EC.visibility_of_element_located((By.XPATH, "//li[contains(., '市价订单')]")))
            driver.execute_script("arguments[0].click();", target_option)

        qty_input = driver.find_element(By.XPATH, "//span[contains(text(), '数量')]/following-sibling::div//input")
        qty_input.click()
        qty_input.send_keys(Keys.CONTROL + "a")
        qty_input.send_keys(Keys.BACK_SPACE)
        qty_input.send_keys(str(quantity))

        btn_selector = {
            "buy_open": "button.buyOpen",
            "sell_open": "button.sellOpen",
            "buy_close": "//button[.//span[contains(text(), '买入平仓')]]",
            "sell_close": "//button[.//span[contains(text(), '卖出平仓')]]"
        }
        
        selector = btn_selector.get(action_type)
        if "close" in action_type:
            trade_btn = driver.find_element(By.XPATH, selector)
        else:
            trade_btn = driver.find_element(By.CSS_SELECTOR, selector)
            
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", trade_btn)
        driver.execute_script("arguments[0].click();", trade_btn)
        
        try:
            confirm = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'el-dialog__wrapper') and not(contains(@style,'display: none'))]//button[contains(., '提交') or contains(., '确 定')]")))
            confirm.click()
        except:
            pass
            
    except Exception as e:
        print(f"下单异常 ({action_type}): {e}")

def run_dual_strategy(driver):
    """双向动态套利：包含平均价统计与累计收益"""
    HISTORY_LEN = 3
    INTERVAL = 0.5
    
    price_queue = collections.deque(maxlen=HISTORY_LEN)
    trade_logs = []
    
    current_position = 0 
    
    # [新增] 全局累计收益
    cumulative_profit = 0.0
    
    print(f"\n>>> 启动策略 | 信号等待: {FIXED_DELAY_BEFORE_OPEN}s | 平仓间隔: {TARGET_INTERVAL_CLOSE}s")
    
    def execute_cycle(direction_name, open_action, close_action):
        nonlocal current_position, cumulative_profit
        
        # === 阶段 1: 信号触发后的固定等待 ===
        print(f"1. [{direction_name}] 信号触发，固定等待 {FIXED_DELAY_BEFORE_OPEN} 秒...")
        time.sleep(FIXED_DELAY_BEFORE_OPEN)
        
        # === 阶段 2: 执行开仓 ===
        print(f"2. 发送开仓指令 ({open_action} {TRADE_QTY})...")
        t0_order_sent = time.time() # 记录时间锚点
        
        trade_option(driver, TRADE_QTY, open_action)
        time.sleep(SYSTEM_DELAY) 
        
        # === 阶段 3: 确认成交 ===
        open_price, open_qty, open_time_str, open_sig = fetch_latest_trade_record(driver)
        
        if open_qty == 0:
            print(" [警告] 开仓未成交，退出循环")
            return
        
        current_position = open_qty
        print(f"3. 开仓成交: {open_qty}张 @ {open_price}")
        
        # === 阶段 4: 动态延时 ===
        elapsed_time = time.time() - t0_order_sent
        wait_remaining = TARGET_INTERVAL_CLOSE - elapsed_time
        if wait_remaining < 0: wait_remaining = 0
        
        print(f"4. 动态等待平仓 (需sleep {wait_remaining:.2f}s)...")
        time.sleep(wait_remaining)
        
        # === 阶段 5: 循环强制平仓 & 计算平均价 ===
        print(f"5. 开始平仓循环 (持仓: {current_position})...")
        
        cycle_total_profit = 0      # 本次套利总利润
        total_close_revenue = 0     # 本次平仓总金额（用于算均价）
        total_close_qty_accum = 0   # 本次实际平仓总数量
        
        last_known_sig = open_sig 
        attempt_count = 0
        
        while current_position > 0:
            attempt_count += 1
            trade_option(driver, current_position, close_action)
            time.sleep(SYSTEM_DELAY) 
            
            curr_price, curr_qty, curr_time, curr_sig = fetch_latest_trade_record(driver)
            
            if curr_sig != last_known_sig:
                filled_qty = curr_qty
                filled_price = curr_price
                
                print(f"      >> 成交: {filled_qty}张 @ {filled_price}")
                
                # 数据更新
                current_position -= filled_qty
                if current_position < 0: current_position = 0
                
                # [核心逻辑] 累加计算
                total_close_qty_accum += filled_qty
                total_close_revenue += (filled_price * filled_qty)
                
                # 利润计算 (单笔)
                if direction_name == 'Bull (Buy->Sell)':
                    cycle_total_profit += (filled_price - open_price) * filled_qty * CONTRACT_MULTIPLIER
                else:
                    cycle_total_profit += (open_price - filled_price) * filled_qty * CONTRACT_MULTIPLIER
                
                last_known_sig = curr_sig
            else:
                print("      >> 未检测到新成交，重试...")
                time.sleep(1) 
        
        # === 阶段 6: 统计与记录 ===
        # 计算加权平均平仓价
        avg_close_price = total_close_revenue / total_close_qty_accum if total_close_qty_accum > 0 else 0
        
        # 更新累计收益
        cumulative_profit += cycle_total_profit
        
        print("-" * 40)
        print(f"交易结束 | 平均平仓价: {avg_close_price:.4f}")
        print(f"本次盈亏: {cycle_total_profit:.2f}")
        print(f"★ 累计总盈亏: {cumulative_profit:.2f}") # 实时给出累计大小
        print("-" * 40)
        
        log = {
            "Strategy": direction_name,
            "Open_Time": open_time_str,
            "Open_Price": open_price,
            "Avg_Close_Price": round(avg_close_price, 4), # 记录平均价
            "Total_Qty": open_qty,
            "Profit": cycle_total_profit,
            "Cumulative_Profit": cumulative_profit,       # 记录进Excel
            "Actual_Wait": f"{time.time() - t0_order_sent:.2f}s"
        }
        trade_logs.append(log)
        pd.DataFrame(trade_logs).to_excel(EXCEL_FILE_PATH, index=False)
        print("=== 记录已保存 ===\n")
        price_queue.clear()


    while True:
        try:
            bid, ask = get_market_depth_price(driver)
            if bid is None: continue
            
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            
            if len(price_queue) < HISTORY_LEN:
                price_queue.append((bid, ask))
                print(f"\r[{ts}] 初始化... {len(price_queue)}", end="")
                time.sleep(INTERVAL)
                continue
            
            old_bid, old_ask = price_queue.popleft()
            price_queue.append((bid, ask))
            
            ask_change = (ask - old_ask) / old_ask if old_ask > 0 else 0
            bid_change = (bid - old_bid) / old_bid if old_bid > 0 else 0
            
            # 实时状态栏，增加累计盈利显示
            status_msg = f"\r[{ts}] 卖:{ask}({ask_change:.2%}) | 买:{bid}({bid_change:.2%}) | 持仓:{current_position} | 总盈亏:{cumulative_profit:.2f}  "
            print(status_msg, end="")

            if current_position == 0:
                if ask_change > THRESHOLD:
                    print(f"\n\n[!!!] 暴涨信号触发")
                    execute_cycle("Bull (Buy->Sell)", "buy_open", "sell_close")
                
                elif bid_change < -THRESHOLD:
                    print(f"\n\n[!!!] 暴跌信号触发")
                    execute_cycle("Bear (Sell->Buy)", "sell_open", "buy_close")
            
            time.sleep(INTERVAL)

        except KeyboardInterrupt:
            print("\n停止")
            break
        except Exception as e:
            print(f"\n[Error] {e}")
            time.sleep(1)

def main():
    driver = setup_driver()
    try:
        login(driver)
        select_contract_auto(driver, TARGET_CONTRACT)
        run_dual_strategy(driver)
    except Exception as e:
        print(f"主程序错误: {e}")

if __name__ == "__main__":
    main()