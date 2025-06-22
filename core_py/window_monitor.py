import sys
import time
import psutil

try:
    if sys.platform == "win32":
        import win32gui
        import win32process
    elif sys.platform == "darwin":
        from AppKit import NSWorkspace
        import Quartz
    elif sys.platform.startswith("linux"):
        from Xlib import display as XlibDisplay, X
except ImportError as e:
    print(f"[WINDOW_MONITOR_WARN] Failed to import platform-specific library: {e}. Functionality may be limited.")


def get_active_window_info():
    """
    获取当前活动窗口的详细信息，包括标题、进程名和可执行文件路径。
    返回一个字典: {'title': str, 'process_name': str, 'exe_path': str} 或 None
    """
    active_window_info = {
        "title": "Unknown",
        "process_name": "Unknown",
        "exe_path": "Unknown"
    }
    
    try:
        if sys.platform == "win32":
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None
                
            active_window_info['title'] = win32gui.GetWindowText(hwnd) or "Unknown"
            
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid > 0 and psutil.pid_exists(pid):
                p = psutil.Process(pid)
                active_window_info['process_name'] = p.name()
                active_window_info['exe_path'] = p.exe()
                
        elif sys.platform == "darwin": # macOS
            ws = NSWorkspace.sharedWorkspace()
            active_app = ws.frontmostApplication()
            pid = active_app.processIdentifier()

            if psutil.pid_exists(pid):
                p = psutil.Process(pid)
                active_window_info['process_name'] = p.name()
                active_window_info['exe_path'] = p.exe()

            options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
            window_list = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)
            
            for window in window_list:
                owner_pid = window.get('kCGWindowOwnerPID')
                if owner_pid == pid:
                    window_title = window.get('kCGWindowName')
                    if window_title:
                        active_window_info['title'] = window_title
                        break

        elif sys.platform.startswith("linux"):
            d = XlibDisplay.Display()
            root = d.screen().root
            
            window_id_prop = d.intern_atom('_NET_ACTIVE_WINDOW')
            window_id_result = root.get_full_property(window_id_prop, X.AnyPropertyType)
            if not window_id_result:
                return None
            window_id = window_id_result.value[0]
            
            active_window = d.create_resource_object('window', window_id)
            
            pid_prop = d.intern_atom('_NET_WM_PID')
            pid_result = active_window.get_full_property(pid_prop, X.AnyPropertyType)
            if pid_result and pid_result.value:
                pid = pid_result.value[0]
                if pid > 0 and psutil.pid_exists(pid):
                    p = psutil.Process(pid)
                    active_window_info['process_name'] = p.name()
                    active_window_info['exe_path'] = p.exe()

            window_name_prop = d.intern_atom('_NET_WM_NAME')
            title_bytes_result = active_window.get_full_property(window_name_prop, 0, 200)
            if title_bytes_result and title_bytes_result.value:
                title_bytes = title_bytes_result.value
                if isinstance(title_bytes, bytes):
                    active_window_info['title'] = title_bytes.decode('utf-8', 'ignore')
                elif isinstance(title_bytes, str):
                    active_window_info['title'] = title_bytes

        else:
            return None

    except Exception as e:
        return None

    if not active_window_info.get('title') or active_window_info.get('title') == "Unknown":
        active_window_info['title'] = active_window_info.get('process_name', 'Desktop')
        
    return active_window_info


if __name__ == '__main__':
    print("Testing active window monitor. Press Ctrl+C to stop.")
    last_info = None
    try:
        while True:
            current_info = get_active_window_info()
            if current_info and current_info != last_info:
                print(f"Title: {current_info.get('title', 'N/A')}")
                print(f"Process: {current_info.get('process_name', 'N/A')}")
                print(f"Path: {current_info.get('exe_path', 'N/A')}")
                print("-" * 20)
                last_info = current_info
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTest finished.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")