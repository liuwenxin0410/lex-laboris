import os
import sys
import logging
from datetime import datetime
import glob
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import shutil
from pathlib import Path

# --- 日志记录设置 ---
log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt): sys.__excepthook__(exc_type, exc_value, exc_traceback); return
    log.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = handle_exception
log.info("Logger backend partially initialized. Waiting for paths...")
# ---

from config import set_data_paths

app = Flask(__name__)
CORS(app)

DB_FILE_PATH = None

@app.route('/api/init', methods=['POST'])
def initialize_app():
    global DB_FILE_PATH
    
    data = request.json
    user_data_path = data.get('userDataPath')
    logs_path = data.get('logsPath')
    is_dev = data.get('isDev', False)

    if not user_data_path or not logs_path:
        return jsonify({"status": "error", "message": "Missing userDataPath or logsPath"}), 400

    try:
        set_data_paths(user_data_path)
        DB_FILE_PATH = Path(user_data_path) / 'work_log.db'

        if is_dev:
            log_dir = Path(logs_path)
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file_path = log_dir / "backend_dev.log"
            
            file_handler = logging.FileHandler(log_file_path, 'w', 'utf-8')
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'))
            log.addHandler(file_handler)
            log.info(f"DEV MODE: File logging enabled at {log_file_path}")
        else:
            log.info("PRODUCTION MODE: File logging is disabled.")
        
        from database import init_db
        init_db()
        log.info("Database initialized successfully.")
        
        log.info("Logger and paths fully initialized. Application ready.")
        return jsonify({"status": "success", "message": "Backend initialized successfully."})

    except Exception as e:
        log.critical(f"FAILED TO INITIALIZE APP with paths: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Initialization failed: {e}"}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    from tracker import activity_tracker
    return jsonify({"status": "success", "is_tracking": activity_tracker.is_running, "is_idle": activity_tracker.is_idle})

@app.route('/api/start_tracking', methods=['POST'])
def start():
    from tracker import activity_tracker
    from system_info import save_snapshot_event
    from database import clear_db
    from config import SCREENSHOT_DIR

    if activity_tracker.is_running: return jsonify({"status": "error", "message": "追踪已在运行中。"}), 400
    try:
        if SCREENSHOT_DIR and os.path.exists(SCREENSHOT_DIR):
            for f in glob.glob(str(SCREENSHOT_DIR / "*.png")): os.remove(f)
            log.info("Cleared old screenshots before starting new session.")
        clear_db()
        log.info("Cleared database before starting new session.")
    except Exception as e:
        log.error(f"Error while clearing old data: {e}")
        
    activity_tracker.start()
    save_snapshot_event()
    return jsonify({"status": "success", "message": "新会话已开始，旧数据已清除。"})

@app.route('/api/stop_tracking', methods=['POST'])
def stop():
    from tracker import activity_tracker
    if not activity_tracker.is_running: return jsonify({"status": "error", "message": "追踪未在运行。"}), 400
    session_data = activity_tracker.stop()
    if session_data:
        return jsonify({
            "status": "success", "message": "会话已结束。",
            "session": {
                "start_time": session_data["start_time"].isoformat(),
                "end_time": session_data["end_time"].isoformat()
            }
        })
    return jsonify({"status": "error", "message": "追踪器未运行。"}), 400

# 【移除】删除数据库的整个路由函数
# @app.route('/api/delete_database', methods=['POST'])
# def delete_database():
#     # ...

@app.route('/api/events', methods=['GET'])
def get_events():
    from database import get_recent_events
    try: return jsonify({"status": "success", "events": get_recent_events()})
    except Exception as e: return jsonify({"status": "error", "message": f"获取历史事件时出错: {e}"}), 500

@app.route('/api/screenshots/<path:filename>')
def get_screenshot(filename):
    file_dir = os.path.dirname(filename)
    file_name = os.path.basename(filename)
    return send_from_directory(file_dir, file_name)

@app.route('/api/take_screenshot', methods=['POST'])
def take_screenshot_endpoint():
    from tracker import activity_tracker
    data = request.json; bbox = tuple(data.get('bbox')) if data.get('bbox') else None
    filepath = activity_tracker.take_manual_screenshot(bbox=bbox)
    if filepath: return jsonify({"status": "success", "message": "截图成功。"})
    else: return jsonify({"status": "error", "message": "截图失败。"}), 500

@app.route('/api/shortcut_screenshot', methods=['POST'])
def shortcut_screenshot():
    from tracker import activity_tracker
    filepath = activity_tracker.take_fullscreen_screenshot()
    if filepath: return jsonify({"status": "success"})
    else: return jsonify({"status": "ignored"})

@app.route('/api/generate_report', methods=['POST'])
def generate_report_endpoint():
    from report_generator import ReportGenerator
    from config import SCREENSHOT_DIR as sdir, BASE_DATA_DIR as bdd
    
    data = request.json
    report_screenshots_dir = None
    try:
        pdf_save_path = data['savePath']
        pdf_dir = os.path.dirname(pdf_save_path)
        pdf_basename = os.path.basename(pdf_save_path)
        pdf_name_without_ext = os.path.splitext(pdf_basename)[0]

        report_screenshots_dir = os.path.join(pdf_dir, f"{pdf_name_without_ext}_截图")
        os.makedirs(report_screenshots_dir, exist_ok=True)
        log.info(f"Created screenshot directory for report: {report_screenshots_dir}")

        source_screenshots = glob.glob(str(sdir / "*.png"))
        for src_path in source_screenshots:
            filename = os.path.basename(src_path)
            dest_path = os.path.join(report_screenshots_dir, filename)
            shutil.copy(src_path, dest_path)
        log.info(f"Copied {len(source_screenshots)} screenshots to {report_screenshots_dir}")

        start_date = datetime.fromisoformat(data['startDate'])
        end_date = datetime.fromisoformat(data['endDate'])
        generator = ReportGenerator(
            start_date=start_date,
            end_date=end_date,
            user_info=data['userInfo'],
            save_path=pdf_save_path,
            final_screenshot_dir_for_report=os.path.abspath(report_screenshots_dir)
        )
        filepath = generator.generate()
        
        if filepath:
            db_archive_path = os.path.join(pdf_dir, f"db_{pdf_name_without_ext}.sqlite")
            shutil.copy(Path(bdd) / 'work_log.db', db_archive_path)
            log.info(f"Database archived to {db_archive_path}")
            
            return jsonify({"status": "success", "filepath": os.path.abspath(filepath)})
        else:
            shutil.rmtree(report_screenshots_dir, ignore_errors=True)
            log.warning("Report generation failed, temporary report screenshot directory removed.")
            return jsonify({"status": "error", "message": "该时段内无数据可供生成报告。"}), 404
            
    except Exception as e:
        log.critical(f"生成报告时发生严重错误: {e}", exc_info=True)
        if report_screenshots_dir and os.path.exists(report_screenshots_dir):
            shutil.rmtree(report_screenshots_dir, ignore_errors=True)
        return jsonify({"status": "error", "message": f"生成报告时发生错误: {e}"}), 500

if __name__ == '__main__':
    try:
        log.info(f"PYTHON CORE: Starting Flask server on http://127.0.0.1:5001")
        app.run(host='127.0.0.1', port=5001, debug=False)
    except Exception as e:
        log.critical(f"Failed to start the server: {e}", exc_info=True)
        sys.exit(1)