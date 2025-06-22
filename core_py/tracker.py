import threading
import time
from datetime import datetime
from pynput import keyboard
from PIL import Image, ImageGrab
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

# 【修改】移除顶层的 SCREENSHOT_DIR 导入，因为它在加载时会是 None
from config import (IDLE_THRESHOLD_SECONDS, SCREENSHOT_INTERVAL_SECONDS, 
                    WINDOW_CHECK_INTERVAL_SECONDS, IDLE_CHECK_INTERVAL_SECONDS, 
                    WATCHED_DIRECTORIES, HEARTBEAT_INTERVAL_SECONDS)
from database import save_event
from window_monitor import get_active_window_info

log = logging.getLogger(__name__)

class FileChangeEventHandler(FileSystemEventHandler):
    def __init__(self, tracker_instance): self.tracker = tracker_instance
    def on_created(self, event):
        if not event.is_directory: self.tracker._update_activity("file_created", {"path": event.src_path})
    def on_modified(self, event):
        if not event.is_directory: self.tracker._update_activity("file_modified", {"path": event.src_path})
    def on_deleted(self, event):
        if not event.is_directory: self.tracker._update_activity("file_deleted", {"path": event.src_path})
    def on_moved(self, event):
        if not event.is_directory: self.tracker._update_activity("file_moved", {"from_path": event.src_path, "to_path": event.dest_path})

class ActivityTracker:
    def __init__(self):
        self.stop_event = threading.Event(); self.threads = []; self.listeners = []
        self.last_activity_time = time.time(); self.is_idle = False; self.is_running = False
        self.file_observer = None; self.current_app_session = None
        self.session_start_time = None

    def _update_activity(self, event_type: str, details: dict):
        self.last_activity_time = time.time()
        if self.is_idle:
            self.is_idle = False; save_event("status_change", {"status": "active"})
        save_event(event_type, details)
    
    def _on_press(self, key): self._update_activity("keyboard_press", details={});

    def _monitor_idle_status(self):
        last_heartbeat_time = time.time()
        while not self.stop_event.is_set():
            idle_duration = time.time() - self.last_activity_time
            if not self.is_idle and idle_duration > IDLE_THRESHOLD_SECONDS:
                self.is_idle = True; self._update_activity("status_change", {"status": "idle", "duration_seconds": int(idle_duration)})
            if not self.is_idle and (time.time() - last_heartbeat_time > HEARTBEAT_INTERVAL_SECONDS):
                self._update_activity("heartbeat", {"message": "User is active."}); last_heartbeat_time = time.time()
            self.stop_event.wait(IDLE_CHECK_INTERVAL_SECONDS)
            
    def _end_app_session(self):
        if self.current_app_session:
            end_time = datetime.now()
            duration = (end_time - self.current_app_session['start_time_obj']).total_seconds()
            if duration > 1:
                session_details = {
                    "process_name": self.current_app_session['process_name'],
                    "app_title": self.current_app_session['app_title'],
                    "start_time": self.current_app_session['start_time_obj'].isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": round(duration)
                }
                save_event("app_session", session_details)
            self.current_app_session = None
            
    def _monitor_active_window(self):
        while not self.stop_event.is_set():
            if not self.is_running or self.is_idle:
                self._end_app_session()
                self.stop_event.wait(WINDOW_CHECK_INTERVAL_SECONDS)
                continue
            
            active_info = get_active_window_info()
            if active_info:
                current_process = active_info.get("process_name", "unknown")
                current_title = active_info.get("title", "")

                if not self.current_app_session:
                    self.current_app_session = {
                        "process_name": current_process, "app_title": current_title, 
                        "start_time_obj": datetime.now()
                    }
                elif (self.current_app_session['process_name'] != current_process or 
                      self.current_app_session['app_title'] != current_title):
                    self._end_app_session()
                    self.current_app_session = {
                        "process_name": current_process, "app_title": current_title,
                        "start_time_obj": datetime.now()
                    }
            else:
                self._end_app_session()
            self.stop_event.wait(WINDOW_CHECK_INTERVAL_SECONDS)
            
    def _auto_screenshot_taker(self):
        while not self.stop_event.is_set():
            self.stop_event.wait(SCREENSHOT_INTERVAL_SECONDS)
            if self.stop_event.is_set(): break
            if not self.is_idle: self.take_manual_screenshot(is_auto=True)
            
    def take_manual_screenshot(self, bbox=None, is_auto=False):
        # 【核心修复】在函数执行时动态导入 SCREENSHOT_DIR，确保获取到最新的、已初始化的路径
        from config import SCREENSHOT_DIR
        
        log.info("--- Attempting to take a screenshot ---")
        log.info(f"Received BBOX: {bbox}")
        log.info(f"Is auto-screenshot: {is_auto}")
        
        if SCREENSHOT_DIR is None:
            log.error("CRITICAL: SCREENSHOT_DIR is not initialized! Cannot save screenshot.")
            return None

        log.info(f"Using screenshot directory: {SCREENSHOT_DIR}")

        try:
            log.info("Calling ImageGrab.grab()...")
            screenshot = ImageGrab.grab(bbox=bbox, all_screens=True)
            log.info(f"ImageGrab.grab() successful. Screenshot object: {screenshot}")

            if screenshot is None:
                log.error("ImageGrab.grab() returned None.")
                return None

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            shot_type = "auto" if is_auto else "manual"
            filename = f"screenshot_{shot_type}_{timestamp}.png"
            filepath = SCREENSHOT_DIR / filename
            log.info(f"Generated filepath: {filepath}")

            log.info("Calling screenshot.save()...")
            screenshot.save(filepath, "PNG")
            log.info("screenshot.save() successful.")

            event_type = "screenshot_auto" if is_auto else "screenshot_manual"
            details = {"filename": filename}
            if bbox: 
                details["bbox"] = bbox
            
            log.info("Updating activity log for screenshot event...")
            self._update_activity(event_type, details)
            log.info("--- Screenshot process completed successfully. ---")
            
            return str(filepath)
            
        except Exception as e:
            log.critical(f"--- Screenshot process FAILED. Error: {e} ---", exc_info=True)
            return None
        
    def take_fullscreen_screenshot(self):
        if not self.is_running: 
            return None
        return self.take_manual_screenshot(bbox=None, is_auto=False)

    def start(self):
        if self.is_running: return
        self.stop_event.clear(); self.last_activity_time = time.time(); self.is_running = True
        self.session_start_time = datetime.now()
        
        kb_listener = keyboard.Listener(on_press=self._on_press)
        self.listeners = [kb_listener]
        
        for l in self.listeners: l.start()
        
        self.threads = [threading.Thread(target=self._monitor_idle_status, daemon=True), threading.Thread(target=self._monitor_active_window, daemon=True), threading.Thread(target=self._auto_screenshot_taker, daemon=True)]
        for t in self.threads: t.start()
        
        if WATCHED_DIRECTORIES:
            self.file_observer = Observer(); event_handler = FileChangeEventHandler(self)
            for path in WATCHED_DIRECTORIES: self.file_observer.schedule(event_handler, path, recursive=True)
            self.file_observer.start()
        log.info("TRACKER: All monitors started.")

    def stop(self):
        if not self.is_running: return None
        self._end_app_session()
        self.stop_event.set()
        for l in self.listeners:
            if l.is_alive(): l.stop()
        if self.file_observer and self.file_observer.is_alive():
            self.file_observer.stop(); self.file_observer.join(timeout=2)
        for t in self.threads: t.join(timeout=2)
        self.threads.clear(); self.listeners.clear(); self.is_running = False
        log.info("TRACKER: All monitors stopped.")
        return {"start_time": self.session_start_time, "end_time": datetime.now()}

activity_tracker = ActivityTracker()