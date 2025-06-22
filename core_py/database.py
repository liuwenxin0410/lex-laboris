import hashlib
import json
from datetime import datetime
import threading
import traceback
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

# 【修改】只导入 set_data_paths 函数，不导入变量
from config import set_data_paths

Base = declarative_base()

# 【修改】将 engine 和 SessionLocal 初始化为 None 或一个未绑定的状态
engine = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False)
db_lock = threading.Lock()

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    event_type = Column(String, index=True)
    details = Column(Text)
    data_hash = Column(String(64), index=True) 
    previous_hash = Column(String(64))

def init_db():
    """
    初始化数据库连接和表结构。
    这个函数现在是幂等的，可以被多次安全调用。
    """
    global engine
    # 只有在 engine 未初始化时才进行配置
    if engine is None:
        # 【修改】动态地从 config 获取 DATABASE_URL
        from config import DATABASE_URL
        if DATABASE_URL is None:
            raise ValueError("DATABASE_URL is not set. Please call config.set_data_paths() first.")
        
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
        SessionLocal.configure(bind=engine)
        print(f"[DB] Engine created and SessionLocal configured for: {DATABASE_URL}")

    Base.metadata.create_all(bind=engine)
    print("[DB] Database tables checked/created.")

def clear_db():
    """删除所有事件并重新创建表"""
    with db_lock:
        if engine:
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            print("[DB] Database cleared.")

def get_last_hash():
    # 确保在调用此函数前，数据库已初始化
    if not engine: return "0" * 64
    with SessionLocal() as db:
        last_event = db.query(Event).order_by(Event.id.desc()).first()
        return last_event.data_hash if last_event else "0" * 64

def _format_event_for_frontend(event_obj):
    details = {}
    try:
        if event_obj.details:
            details = json.loads(event_obj.details)
    except json.JSONDecodeError:
        details = {"error": "invalid_json_data", "original_text": event_obj.details}
    
    if event_obj.event_type.startswith("screenshot_") and "filename" in details:
        # 【修改】动态导入，因为 config 在运行时才被完全设置
        from config import SCREENSHOT_DIR
        if SCREENSHOT_DIR:
             details['filepath'] = str(SCREENSHOT_DIR / details['filename'])

    return {
        "id": event_obj.id,
        "timestamp": event_obj.timestamp.isoformat(),
        "event_type": event_obj.event_type,
        "details": details,
        "hash": event_obj.data_hash,
        "prev_hash": event_obj.previous_hash
    }

def save_event(event_type: str, details: dict):
    if not engine:
        print("[DB WARNING] save_event called before DB initialization. Ignoring.")
        return
    with db_lock:
        with SessionLocal() as db:
            try:
                details_json = json.dumps(details, sort_keys=True, ensure_ascii=False)
                timestamp = datetime.now()
                # 【修改】调用 get_last_hash 前，db 必须已经配置好
                previous_hash = get_last_hash()
                
                data_to_hash_str = f"{previous_hash}{timestamp.isoformat()}{event_type}{details_json}"
                data_hash = hashlib.sha256(data_to_hash_str.encode('utf-8')).hexdigest()
                
                new_event = Event(
                    timestamp=timestamp, event_type=event_type, details=details_json,
                    data_hash=data_hash, previous_hash=previous_hash
                )
                db.add(new_event)
                db.commit()
            except Exception as e:
                print(f"[DATABASE CRITICAL ERROR] in save_event: {e}")
                traceback.print_exc()
                db.rollback()

def get_recent_events(limit=50):
    if not engine: return []
    with SessionLocal() as db:
        try:
            events = db.query(Event).order_by(Event.id.desc()).limit(limit).all()
            return [_format_event_for_frontend(e) for e in events]
        except Exception as e:
            print(f"[DATABASE CRITICAL ERROR] in get_recent_events: {e}")
            traceback.print_exc()
            return []