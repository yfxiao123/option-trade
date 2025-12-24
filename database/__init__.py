"""
数据库模块
提供交易记录持久化存储功能
"""

from .trade_database import TradeDatabase, get_database

__all__ = ['TradeDatabase', 'get_database']
