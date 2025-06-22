# core_py/config.py

from pathlib import Path
import os

# --- 核心配置 ---
# 【修改】将 BASE_DATA_DIR 初始化为 None，它将在运行时被设置
BASE_DATA_DIR = None
DATABASE_URL = None
SCREENSHOT_DIR = None

def set_data_paths(base_path_str: str):
    """由主程序调用，用于设置所有数据路径"""
    global BASE_DATA_DIR, DATABASE_URL, SCREENSHOT_DIR
    
    BASE_DATA_DIR = Path(base_path_str)
    BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    DATABASE_URL = f"sqlite:///{BASE_DATA_DIR / 'work_log.db'}"
    
    SCREENSHOT_DIR = BASE_DATA_DIR / "screenshots"
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    
    print(f"[CONFIG] Data paths set. Base directory: {BASE_DATA_DIR}")

# --- 跟踪器配置 (不变) ---
IDLE_THRESHOLD_SECONDS = 5 * 60 
SCREENSHOT_INTERVAL_SECONDS = 30 * 60
WINDOW_CHECK_INTERVAL_SECONDS = 2
IDLE_CHECK_INTERVAL_SECONDS = 10
HEARTBEAT_INTERVAL_SECONDS = 5 * 60

# --- 文件监控配置 (不变) ---
WATCHED_DIRECTORIES = []