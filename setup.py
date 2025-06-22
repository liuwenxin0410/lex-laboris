import subprocess
import sys
import time
import socket
from pathlib import Path
import psutil
import os

def kill_lingering_python_processes():
    script_name = "main.py"
    killed_count = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            is_python = 'python' in proc.info['name'].lower()
            if is_python:
                cmdline = proc.info.get('cmdline')
                if cmdline and any(script_name in arg for arg in cmdline):
                    print(f"--- Found lingering backend process (PID: {proc.pid}). Terminating... ---")
                    p = psutil.Process(proc.pid)
                    p.terminate()
                    try:
                        p.wait(timeout=3)
                        print(f"--- Process {proc.pid} terminated gracefully. ---")
                    except psutil.TimeoutExpired:
                        print(f"--- Process {proc.pid} did not terminate, killing... ---")
                        p.kill()
                        p.wait()
                        print(f"--- Process {proc.pid} killed. ---")
                    killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    if killed_count == 0:
        print("--- No lingering backend processes found. Good to go! ---")
    else:
        print(f"--- Terminated {killed_count} lingering backend process(es). ---")

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('127.0.0.1', port)) == 0

def run_dev_concurrently():
    print(">>> Starting development environment...")
    
    kill_lingering_python_processes()
    
    python_command = [sys.executable, str(Path('core_py') / 'main.py')]
    python_process = subprocess.Popen(python_command)
    print(f"--- Attempting to start Python backend with: {' '.join(python_command)} ---")
    print(f"--- Python backend process started (PID: {python_process.pid}). Waiting for server to initialize... ---")

    max_wait_time = 20
    wait_interval = 1
    port = 5001
    start_time = time.time()
    backend_ready = False
    while time.time() - start_time < max_wait_time:
        if is_port_in_use(port):
            print(f"--- Python backend is up and running on port {port}! ---")
            backend_ready = True
            break
        print(f"--- Waiting for Python backend... ({int(time.time() - start_time)}s)")
        time.sleep(wait_interval)
    
    if not backend_ready:
        print(f"!!! Python backend failed to start on port {port} within {max_wait_time} seconds. Aborting.")
        python_process.terminate()
        sys.exit(1)

    # 【最终修复】使用你确认的正确目录名 `desktop_ui`
    ui_path = str(Path('desktop_ui').resolve())

    print(f"\n--- Handing over to yarn in directory: {ui_path} ---")
    print("--- Yarn will now install dependencies (if needed), build the UI, and launch Electron. ---")
    
    # 使用 `yarn dev`，它会处理好一切
    electron_process = subprocess.Popen('yarn dev', cwd=ui_path, shell=True)

    try:
        electron_process.wait()
        print("\n--- Electron application has been closed. ---")
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Shutting down...")
    finally:
        print("\n--- Shutting down all processes... ---")
        if python_process.poll() is None:
            print("--- Terminating Python backend... ---")
            python_process.terminate()
            try: python_process.wait(timeout=5)
            except subprocess.TimeoutExpired: python_process.kill()
            print("--- Python backend process terminated. ---")

        if electron_process.poll() is None:
            print("--- Terminating Electron frontend... ---")
            if sys.platform == 'win32':
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(electron_process.pid)], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            else:
                electron_process.terminate()
            print("--- Electron frontend process terminated. ---")
        print("\n--- Development environment shut down. ---")

def install_dependencies():
    """安装所有Python和Node.js依赖"""
    print(">>> Step 1: Installing Python dependencies...")
    python_executable = sys.executable
    requirements_path = Path('core_py') / 'requirements.txt'
    subprocess.check_call([python_executable, '-m', 'pip', 'install', '-r', str(requirements_path)])
    
    print("\n>>> Step 2: Installing Node.js dependencies using Yarn...")
    # 【最终修复】使用你确认的正确目录名 `desktop_ui`
    ui_path = Path('desktop_ui').resolve()
    # 使用 shell=True 确保 yarn.cmd 能被找到并执行
    subprocess.check_call('yarn install', cwd=str(ui_path), shell=True)

if __name__ == "__main__":
    # 简化了主函数逻辑，因为 install 功能现在被 yarn dev 包含了
    if len(sys.argv) < 2 or sys.argv[1] not in ['install', 'dev']:
        print("Usage: python setup.py [install|dev]")
        print("  install - Installs all dependencies.")
        print("  dev     - Installs dependencies (if needed) and starts the app.")
        sys.exit(1)

    action = sys.argv[1]

    if action == 'install':
        install_dependencies()
        print("\n*** ✅ Installation complete! ***")
        print("You can now start the application by running: python setup.py dev")
    elif action == 'dev':
        print("Starting dev server. Press Ctrl+C in this terminal to stop all processes.")
        run_dev_concurrently()