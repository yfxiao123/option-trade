"""
交易数据库模块
使用SQLite持久化存储交易记录和策略配置
"""

import sqlite3
import os
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from threading import Lock
import pandas as pd


class TradeDatabase:
    """交易数据库管理类"""

    def __init__(self, db_path: str = None):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径，默认为 data/trades.db
        """
        if db_path is None:
            # 获取项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(project_root, "data", "trades.db")

        # 确保data目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.db_path = db_path
        self.lock = Lock()  # 用于线程安全
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # 返回字典格式
        return conn

    def _init_database(self):
        """初始化数据库表结构"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 1. 交易记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE NOT NULL,              -- 交易ID（开平仓配对用）
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, -- 交易时间
                    strategy_name TEXT NOT NULL,                -- 策略名称
                    signal_type TEXT NOT NULL,                 -- 信号类型
                    direction TEXT NOT NULL,                    -- 方向（买入/卖出）
                    position_type TEXT NOT NULL,                -- 开平仓类型
                    price REAL NOT NULL,                        -- 成交价格
                    quantity INTEGER NOT NULL,                  -- 数量
                    pnl REAL DEFAULT 0,                         -- 盈亏（平仓时填写）
                    status TEXT DEFAULT 'completed',            -- 状态
                    reason TEXT,                                -- 交易原因
                    contract_code TEXT,                         -- 合约代码
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. 策略配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT UNIQUE NOT NULL,         -- 策略名称
                    strategy_class TEXT NOT NULL,               -- 策略类名
                    enabled INTEGER DEFAULT 0,                  -- 是否启用（0/1）
                    priority INTEGER DEFAULT 0,                 -- 优先级
                    description TEXT,                           -- 策略描述
                    parameters TEXT,                            -- 策略参数（JSON格式）
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. 每日汇总表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date DATE UNIQUE NOT NULL,            -- 交易日期
                    strategy_name TEXT NOT NULL,                -- 策略名称
                    total_trades INTEGER DEFAULT 0,             -- 总交易次数
                    open_trades INTEGER DEFAULT 0,              -- 开仓次数
                    close_trades INTEGER DEFAULT 0,             -- 平仓次数
                    total_pnl REAL DEFAULT 0,                   -- 总盈亏
                    win_rate REAL DEFAULT 0,                    -- 胜率
                    max_profit REAL DEFAULT 0,                  -- 最大盈利
                    max_loss REAL DEFAULT 0,                    -- 最大亏损
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. 持仓记录表（用于追踪开平仓配对）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    position_id TEXT UNIQUE NOT NULL,           -- 持仓ID
                    strategy_name TEXT NOT NULL,                -- 策略名称
                    open_time DATETIME NOT NULL,                -- 开仓时间
                    close_time DATETIME,                        -- 平仓时间
                    open_price REAL NOT NULL,                   -- 开仓价格
                    close_price REAL,                           -- 平仓价格
                    quantity INTEGER NOT NULL,                  -- 数量
                    direction TEXT NOT NULL,                    -- 方向
                    status TEXT DEFAULT 'open',                 -- 状态（open/closed）
                    pnl REAL DEFAULT 0,                         -- 盈亏
                    max_profit REAL DEFAULT 0,                  -- 最大浮盈
                    max_loss REAL DEFAULT 0,                    -- 最大浮亏
                    hold_seconds INTEGER DEFAULT 0,             -- 持仓时长（秒）
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_summary_date ON daily_summary(trade_date)")

            conn.commit()
            conn.close()

    # ==================== 交易记录相关方法 ====================

    def add_trade(self, trade_info: Dict) -> int:
        """
        添加交易记录

        Args:
            trade_info: 交易信息字典
                {
                    'trade_id': str,
                    'strategy_name': str,
                    'signal_type': str,
                    'direction': str,
                    'position_type': str,
                    'price': float,
                    'quantity': int,
                    'pnl': float (可选),
                    'status': str,
                    'reason': str (可选),
                    'contract_code': str (可选)
                }

        Returns:
            插入记录的ID
        """
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT INTO trades (
                        trade_id, timestamp, strategy_name, signal_type,
                        direction, position_type, price, quantity,
                        pnl, status, reason, contract_code
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_info.get('trade_id'),
                    trade_info.get('timestamp', datetime.now().isoformat()),
                    trade_info['strategy_name'],
                    trade_info['signal_type'],
                    trade_info['direction'],
                    trade_info['position_type'],
                    trade_info['price'],
                    trade_info['quantity'],
                    trade_info.get('pnl', 0),
                    trade_info.get('status', 'completed'),
                    trade_info.get('reason', ''),
                    trade_info.get('contract_code', '')
                ))

                trade_id = cursor.lastrowid
                conn.commit()

                # 更新每日汇总
                self._update_daily_summary(cursor, trade_info)

                return trade_id

            except sqlite3.IntegrityError:
                conn.rollback()
                return -1
            finally:
                conn.close()

    def get_trades(self, strategy_name: str = None, start_date: str = None,
                   end_date: str = None, limit: int = None) -> List[Dict]:
        """
        获取交易记录

        Args:
            strategy_name: 策略名称过滤
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            limit: 限制返回数量

        Returns:
            交易记录列表
        """
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM trades WHERE 1=1"
            params = []

            if strategy_name:
                query += " AND strategy_name = ?"
                params.append(strategy_name)

            if start_date:
                query += " AND DATE(timestamp) >= ?"
                params.append(start_date)

            if end_date:
                query += " AND DATE(timestamp) <= ?"
                params.append(end_date)

            query += " ORDER BY timestamp DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

    def get_trade_by_id(self, trade_id: int) -> Optional[Dict]:
        """根据ID获取交易记录"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None

    def update_trade_pnl(self, trade_id: int, pnl: float) -> bool:
        """更新交易盈亏"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE trades SET pnl = ? WHERE id = ?", (pnl, trade_id))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0

    def get_latest_trades(self, limit: int = 50) -> List[Dict]:
        """获取最新的交易记录"""
        return self.get_trades(limit=limit)

    # ==================== 策略配置相关方法 ====================

    def register_strategy(self, strategy_name: str, strategy_class: str,
                          description: str = "", priority: int = 0) -> bool:
        """
        注册策略

        Args:
            strategy_name: 策略名称
            strategy_class: 策略类名
            description: 策略描述
            priority: 优先级

        Returns:
            是否成功
        """
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO strategies
                    (strategy_name, strategy_class, description, priority, enabled)
                    VALUES (?, ?, ?, ?, 0)
                """, (strategy_name, strategy_class, description, priority))

                conn.commit()
                return cursor.rowcount > 0

            except Exception:
                conn.rollback()
                return False
            finally:
                conn.close()

    def set_strategy_enabled(self, strategy_name: str, enabled: bool) -> bool:
        """设置策略启用状态"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE strategies SET enabled = ?, updated_at = CURRENT_TIMESTAMP
                WHERE strategy_name = ?
            """, (1 if enabled else 0, strategy_name))

            conn.commit()
            conn.close()
            return cursor.rowcount > 0

    def get_enabled_strategies(self) -> List[str]:
        """获取所有启用的策略名称列表"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT strategy_name FROM strategies WHERE enabled = 1 ORDER BY priority")
            rows = cursor.fetchall()
            conn.close()
            return [row['strategy_name'] for row in rows]

    def get_all_strategies(self) -> List[Dict]:
        """获取所有策略配置"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM strategies ORDER BY priority")
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]

    def get_strategy_info(self, strategy_name: str) -> Optional[Dict]:
        """获取指定策略信息"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM strategies WHERE strategy_name = ?", (strategy_name,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None

    def is_strategy_enabled(self, strategy_name: str) -> bool:
        """检查策略是否启用"""
        info = self.get_strategy_info(strategy_name)
        return info and info['enabled'] == 1

    def disable_all_strategies(self) -> bool:
        """禁用所有策略"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE strategies SET enabled = 0, updated_at = CURRENT_TIMESTAMP")
            conn.commit()
            conn.close()
            return True

    def update_strategy_parameters(self, strategy_name: str, parameters: Dict) -> bool:
        """更新策略参数（存储为JSON）"""
        import json
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE strategies SET parameters = ?, updated_at = CURRENT_TIMESTAMP
                WHERE strategy_name = ?
            """, (json.dumps(parameters), strategy_name))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0

    # ==================== 持仓记录相关方法 ====================

    def open_position(self, position_info: Dict) -> bool:
        """开仓记录"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT INTO positions (
                        position_id, strategy_name, open_time, open_price,
                        quantity, direction, status
                    ) VALUES (?, ?, ?, ?, ?, ?, 'open')
                """, (
                    position_info['position_id'],
                    position_info['strategy_name'],
                    position_info.get('open_time', datetime.now().isoformat()),
                    position_info['open_price'],
                    position_info['quantity'],
                    position_info['direction']
                ))

                conn.commit()
                return True

            except Exception:
                conn.rollback()
                return False
            finally:
                conn.close()

    def close_position(self, position_id: str, close_info: Dict) -> bool:
        """平仓记录"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    UPDATE positions SET
                        close_time = ?,
                        close_price = ?,
                        status = 'closed',
                        pnl = ?,
                        hold_seconds = ?
                    WHERE position_id = ?
                """, (
                    close_info.get('close_time', datetime.now().isoformat()),
                    close_info['close_price'],
                    close_info.get('pnl', 0),
                    close_info.get('hold_seconds', 0),
                    position_id
                ))

                conn.commit()
                return cursor.rowcount > 0

            except Exception:
                conn.rollback()
                return False
            finally:
                conn.close()

    def get_open_positions(self) -> List[Dict]:
        """获取所有未平仓记录"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM positions WHERE status = 'open'")
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]

    def get_position_by_id(self, position_id: str) -> Optional[Dict]:
        """根据ID获取持仓记录"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM positions WHERE position_id = ?", (position_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None

    # ==================== 统计相关方法 ====================

    def get_strategy_statistics(self, strategy_name: str = None) -> Dict:
        """获取策略统计信息"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            if strategy_name:
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN position_type = 'open' THEN 1 ELSE 0 END) as open_trades,
                        SUM(CASE WHEN position_type = 'close' THEN 1 ELSE 0 END) as close_trades,
                        SUM(pnl) as total_pnl,
                        AVG(pnl) as avg_pnl,
                        COALESCE(MAX(pnl), 0.0) as max_profit,  -- 使用COALESCE处理NULL值
                        COALESCE(MIN(pnl), 0.0) as max_loss,   -- 使用COALESCE处理NULL值
                        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as win_count,
                        SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as loss_count
                    FROM trades WHERE strategy_name = ?
                """, (strategy_name,))
            else:
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN position_type = 'open' THEN 1 ELSE 0 END) as open_trades,
                        SUM(CASE WHEN position_type = 'close' THEN 1 ELSE 0 END) as close_trades,
                        SUM(pnl) as total_pnl,
                        AVG(pnl) as avg_pnl,
                        MAX(pnl) as max_profit,
                        MIN(pnl) as max_loss,
                        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as win_count,
                        SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as loss_count
                    FROM trades
                """)

            row = cursor.fetchone()
            conn.close()

            result = dict(row) if row else {}

            # 计算胜率
            if result.get('close_trades', 0) > 0:
                result['win_rate'] = result.get('win_count', 0) / result['close_trades']
            else:
                result['win_rate'] = 0

            return result

    def get_daily_pnl(self, days: int = 30) -> List[Dict]:
        """获取每日盈亏统计"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    DATE(timestamp) as trade_date,
                    strategy_name,
                    COUNT(*) as total_trades,
                    SUM(pnl) as total_pnl
                FROM trades
                WHERE DATE(timestamp) >= DATE('now', '-' || ? || ' days')
                GROUP BY DATE(timestamp), strategy_name
                ORDER BY trade_date DESC
            """, (days,))

            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]

    def _update_daily_summary(self, cursor, trade_info: Dict):
        """更新每日汇总"""
        trade_date = datetime.now().date()
        strategy_name = trade_info['strategy_name']

        # 检查是否已有记录
        cursor.execute("""
            SELECT * FROM daily_summary
            WHERE trade_date = ? AND strategy_name = ?
        """, (trade_date, strategy_name))

        existing = cursor.fetchone()

        if existing:
            # 更新现有记录
            cursor.execute("""
                UPDATE daily_summary SET
                    total_trades = total_trades + 1,
                    open_trades = open_trades + CASE WHEN position_type = 'open' THEN 1 ELSE 0 END,
                    close_trades = close_trades + CASE WHEN position_type = 'close' THEN 1 ELSE 0 END,
                    total_pnl = total_pnl + ?
                WHERE id = ?
            """, (trade_info.get('pnl', 0), existing['id']))
        else:
            # 插入新记录
            cursor.execute("""
                INSERT INTO daily_summary (
                    trade_date, strategy_name, total_trades, open_trades, close_trades, total_pnl
                ) VALUES (?, ?, 1, ?, ?, ?)
            """, (
                trade_date,
                strategy_name,
                1 if trade_info['position_type'] == 'open' else 0,
                1 if trade_info['position_type'] == 'close' else 0,
                trade_info.get('pnl', 0)
            ))

    # ==================== 导出功能 ====================

    def export_to_excel(self, output_path: str, start_date: str = None,
                        end_date: str = None, strategy_name: str = None) -> bool:
        """
        导出交易记录到Excel

        Args:
            output_path: 输出文件路径
            start_date: 开始日期
            end_date: 结束日期
            strategy_name: 策略名称过滤

        Returns:
            是否成功
        """
        try:
            trades = self.get_trades(strategy_name=strategy_name,
                                     start_date=start_date,
                                     end_date=end_date)

            if not trades:
                return False

            df = pd.DataFrame(trades)

            # 移除不需要的列
            columns_to_drop = ['id', 'created_at']
            for col in columns_to_drop:
                if col in df.columns:
                    df = df.drop(columns=[col])

            # 重命名列
            column_rename = {
                'trade_id': '交易ID',
                'timestamp': '交易时间',
                'strategy_name': '策略名称',
                'signal_type': '信号类型',
                'direction': '方向',
                'position_type': '开平仓',
                'price': '价格',
                'quantity': '数量',
                'pnl': '盈亏',
                'status': '状态',
                'reason': '原因',
                'contract_code': '合约代码'
            }
            df = df.rename(columns=column_rename)

            # 导出到Excel
            df.to_excel(output_path, index=False, sheet_name='交易记录')

            # 如果有多个策略，创建汇总页
            if strategy_name is None:
                strategies = df['策略名称'].unique()
                if len(strategies) > 1:
                    with pd.ExcelWriter(output_path, mode='a', engine='openpyxl') as writer:
                        summary = df.groupby('策略名称').agg({
                            '盈亏': 'sum',
                            '交易时间': 'count'
                        }).rename(columns={'交易时间': '交易次数'})
                        summary.to_excel(writer, sheet_name='策略汇总')

            return True

        except Exception as e:
            print(f"导出Excel失败: {e}")
            return False

    def export_summary_to_excel(self, output_path: str) -> bool:
        """导出统计汇总到Excel"""
        try:
            # 获取各策略统计
            strategies = self.get_all_strategies()
            summary_data = []

            for strategy in strategies:
                stats = self.get_strategy_statistics(strategy['strategy_name'])
                stats['策略名称'] = strategy['strategy_name']
                stats['启用状态'] = '是' if strategy['enabled'] else '否'
                summary_data.append(stats)

            df = pd.DataFrame(summary_data)

            # 重命名列
            column_rename = {
                '策略名称': '策略名称',
                'total_trades': '总交易次数',
                'open_trades': '开仓次数',
                'close_trades': '平仓次数',
                'total_pnl': '总盈亏',
                'avg_pnl': '平均盈亏',
                'max_profit': '最大盈利',
                'max_loss': '最大亏损',
                'win_count': '盈利次数',
                'loss_count': '亏损次数',
                'win_rate': '胜率',
                '启用状态': '启用状态'
            }

            df = df.rename(columns=column_rename)

            # 导出到Excel
            df.to_excel(output_path, index=False, sheet_name='策略汇总')

            return True

        except Exception as e:
            print(f"导出汇总失败: {e}")
            return False


# 创建全局数据库实例
_db_instance = None
_db_lock = Lock()


def get_database() -> TradeDatabase:
    """获取全局数据库实例（单例模式）"""
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = TradeDatabase()
    return _db_instance
