import platform
import socket
import getpass
import json
from datetime import datetime
import time 

def get_environment_snapshot():
    """获取当前取证环境的快照"""
    return {
        "snapshot_timestamp": datetime.now().isoformat(),
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version()
        },
        "node": platform.node(),
        "user": getpass.getuser(),
        "python_version": platform.python_version(),
        "system_timezone": time.tzname
    }

def save_snapshot_event():
    """将环境快照作为一个事件保存到数据库"""
    from database import save_event
    snapshot = get_environment_snapshot()
    save_event(event_type="environment_snapshot", details=snapshot)