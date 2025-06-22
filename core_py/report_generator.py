import os
import sys
import json
from datetime import datetime
import logging
import html
import shutil
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from database import SessionLocal, Event
from config import SCREENSHOT_DIR

log = logging.getLogger(__name__)

def resource_path(relative_path):
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# 【最终修复】使用 TTF 格式的字体
FONT_ASSET_PATH = os.path.join('assets', 'SourceHanSansSC-Regular.ttf')
FONT_NAME = 'Helvetica'

try:
    FONT_PATH = resource_path(FONT_ASSET_PATH)
    if os.path.exists(FONT_PATH):
        pdfmetrics.registerFont(TTFont('SimSun', FONT_PATH))
        FONT_NAME = 'SimSun'
        log.info(f"Successfully registered Chinese font from: {FONT_PATH}")
    else:
        log.error(f"Font file does not exist at resolved path: {FONT_PATH}")
        raise FileNotFoundError
except Exception as e:
    log.critical(f"Failed to load primary font. Falling back to system fonts. Error details: {e}")
    try:
        pdfmetrics.registerFont(TTFont('SimSun', 'simsun.ttc'))
        FONT_NAME = 'SimSun'
        log.warning("Fallback successful: Using system 'simsun.ttc'")
    except Exception as fallback_e:
        log.error(f"FATAL: All font loading attempts failed. Fallback error: {fallback_e}")

class ReportGenerator:
    # (此类的其余部分与之前修复后的版本完全相同，为简洁此处省略)
    # ...
    def __init__(self, start_date: datetime, end_date: datetime, user_info: dict, save_path: str, final_screenshot_dir_for_report: str):
        self.start_date = start_date
        self.end_date = end_date
        self.user_info = user_info
        self.styles = getSampleStyleSheet()
        self.story = []
        self.filepath = save_path
        self.final_screenshot_dir = Path(final_screenshot_dir_for_report)
        
        self.doc = SimpleDocTemplate(self.filepath, pagesize=letter, rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=1*inch, bottomMargin=1*inch)
        
        self.styles.add(ParagraphStyle(name='ChineseNormal', fontName=FONT_NAME, fontSize=10.5, leading=14, alignment=TA_JUSTIFY))
        self.styles.add(ParagraphStyle(name='ChineseBold', parent=self.styles['ChineseNormal'], fontName=FONT_NAME, bold=True))
        self.styles.add(ParagraphStyle(name='ChineseH1', parent=self.styles['ChineseNormal'], fontSize=18, leading=22, spaceAfter=12, textColor=colors.darkblue))
        self.styles.add(ParagraphStyle(name='ChineseH2', parent=self.styles['ChineseNormal'], fontSize=14, leading=18, spaceAfter=10, textColor=colors.darkslategray))
        self.styles.add(ParagraphStyle(name='CoverTitle', parent=self.styles['ChineseNormal'], fontSize=28, alignment=TA_CENTER, spaceAfter=24, textColor=colors.darkblue))
        self.styles.add(ParagraphStyle(name='Footer', fontName=FONT_NAME, alignment=TA_CENTER, fontSize=8, textColor=colors.grey))
        self.styles.add(ParagraphStyle(name='JsonCode', parent=self.styles['Code'], fontSize=8, leading=10, backColor=colors.whitesmoke, borderWidth=0.5, borderColor=colors.lightgrey, padding=5, wordWrap='CJK'))
        self.styles.add(ParagraphStyle(name='PathStyle', parent=self.styles['Code'], fontSize=8, textColor=colors.darkslategray, leading=12))

    def _get_events(self):
        with SessionLocal() as db:
            query = db.query(Event).filter(Event.timestamp >= self.start_date, Event.timestamp <= self.end_date)
            return query.order_by(Event.id.asc()).all()

    def _add_header_footer(self, canvas: canvas.Canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT_NAME, 9)
        canvas.drawString(inch, letter[1] - 0.5 * inch, f"工作事实记录报告 - {self.user_info.get('name', '未填写')}")
        canvas.drawCentredString(letter[0] / 2.0, 0.5 * inch, f"第 {doc.page} 页")
        canvas.restoreState()

    def _add_cover_page(self):
        self.story.append(Spacer(1, 2 * inch))
        self.story.append(Paragraph("工作事实与时长记录报告", self.styles['CoverTitle']))
        
        display_start_time = self.start_date.strftime('%Y年%m月%d日 %H:%M:%S')
        display_end_time = self.end_date.strftime('%Y年%m月%d日 %H:%M:%S')
        
        info_data = [
            [Paragraph("<b>报告主题:</b>", self.styles['ChineseBold']), Paragraph("工作事实与时长证据记录", self.styles['ChineseNormal'])],
            [Paragraph("<b>报告生成时间:</b>", self.styles['ChineseBold']), Paragraph(datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"), self.styles['ChineseNormal'])],
            [Paragraph("<b>证据覆盖时段:</b>", self.styles['ChineseBold']), Paragraph(f"{display_start_time} 至 {display_end_time} (系统本地时间)", self.styles['ChineseNormal'])],
            [Paragraph("<b>员工姓名:</b>", self.styles['ChineseBold']), Paragraph(self.user_info.get("name", "未提供"), self.styles['ChineseNormal'])],
            [Paragraph("<b>关联公司:</b>", self.styles['ChineseBold']), Paragraph(self.user_info.get("company", "未提供"), self.styles['ChineseNormal'])]
        ]
        
        table = Table(info_data, colWidths=[1.8 * inch, 5.2 * inch])
        table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 6)]))
        self.story.append(table)
        self.story.append(Spacer(1, 2 * inch))
        self.story.append(Paragraph("<i>此报告由 “工时壁垒 (Lex Laboris)” 工具自动生成，旨在客观记录工作期间的计算机活动。</i>", self.styles['ChineseNormal']))
        self.story.append(PageBreak())

    def _add_summary_and_snapshot(self, events):
        self.story.append(Paragraph("第一部分：摘要与环境信息", self.styles['ChineseH1']))
        self.story.append(Paragraph("报告摘要", self.styles['ChineseH2']))
        
        display_start_time = self.start_date.strftime('%Y年%m月%d日 %H:%M')
        display_end_time = self.end_date.strftime('%Y年%m月%d日 %H:%M')
        summary_text = f"本报告旨在证明，在 <b>{display_start_time}</b> 至 <b>{display_end_time}</b> 期间，本人持续使用特定计算机进行了工作。报告共包含 <b>{len(events)}</b> 条由程序自动捕获的活动记录，所有记录均通过哈希链技术保证其原始性和不可篡改性。"
        self.story.append(Paragraph(summary_text, self.styles['ChineseNormal']))
        self.story.append(Spacer(1, 0.2 * inch))
        self.story.append(Paragraph("取证环境快照", self.styles['ChineseH2']))
        self.story.append(Paragraph("以下信息为本次记录开始时，程序自动获取的计算机系统环境，用以佐证证据来源的同一性。", self.styles['ChineseNormal']))
        snapshot_event = next((e for e in events if e.event_type == 'environment_snapshot'), None)
        snapshot_details = {}
        if snapshot_event and snapshot_event.details:
             try: snapshot_details = json.loads(snapshot_event.details)
             except Exception: snapshot_details = {"error": "无法解析快照数据"}
        self.story.append(Paragraph(f"<pre>{json.dumps(snapshot_details, indent=4, ensure_ascii=False)}</pre>", self.styles['JsonCode']))
        self.story.append(PageBreak())

    def _add_detailed_log(self, events):
        self.story.append(Paragraph("第二部分：详细活动日志", self.styles['ChineseH1']))
        
        for event in events:
            event_time_local = event.timestamp
            
            event_type_zh = {
                "environment_snapshot": "环境快照", "status_change": "状态变更", "keyboard_press": "键盘输入",
                "heartbeat": "活跃心跳", "app_session": "应用聚焦", "screenshot_manual": "手动截屏", 
                "screenshot_auto": "自动截屏", "file_created": "文件创建", "file_modified": "文件修改", 
                "file_deleted": "文件删除", "file_moved": "文件移动"
            }.get(event.event_type, event.event_type)

            details_content_list = []
            try:
                details_obj = json.loads(event.details) if event.details else {}
                if event.event_type == 'app_session':
                    app_title_safe = html.escape(details_obj.get('app_title', ''))
                    title_text = f" - {app_title_safe}" if app_title_safe else ""
                    details_content_list.append(Paragraph(f"应用 <b>[{details_obj.get('process_name', '未知')}{title_text}]</b> 持续聚焦 {details_obj.get('duration_seconds')} 秒。", self.styles['ChineseNormal']))
                elif event.event_type == 'heartbeat':
                     details_content_list.append(Paragraph("<i>程序确认用户活跃。</i>", self.styles['ChineseNormal']))
                elif event.event_type == 'keyboard_press':
                     details_content_list.append(Paragraph("<i>检测到键盘输入。</i>", self.styles['ChineseNormal']))
                elif event.event_type.startswith("screenshot_"):
                    filename = details_obj.get("filename")
                    if filename:
                        final_image_path = self.final_screenshot_dir / filename
                        safe_path = html.escape(str(final_image_path))
                        path_text = f"截图文件名: {filename}<br/>本机绝对路径: {safe_path}"
                        details_content_list.append(Paragraph(path_text, self.styles['PathStyle']))
                    else:
                        details_content_list.append(Paragraph("截图事件，但未记录文件名。", self.styles['ChineseNormal']))
                else:
                    details_content_list.append(Paragraph(json.dumps(details_obj, ensure_ascii=False, sort_keys=True, indent=2), self.styles['JsonCode']))
            except Exception:
                details_content_list.append(Paragraph(f"无效数据: {event.details}", self.styles['JsonCode']))

            log_data = [
                [Paragraph("<b>时间:</b>", self.styles['ChineseBold']), Paragraph(event_time_local.strftime("%Y-%m-%d %H:%M:%S"), self.styles['ChineseNormal'])],
                [Paragraph("<b>类型:</b>", self.styles['ChineseBold']), Paragraph(event_type_zh, self.styles['ChineseNormal'])],
                [Paragraph("<b>详情:</b>", self.styles['ChineseBold']), details_content_list],
                [Paragraph("<b>哈希值:</b>", self.styles['ChineseBold']), Paragraph(f"数据: {event.data_hash[:16]}...<br/>前序: {event.previous_hash[:16]}...", self.styles['Code'])]
            ]
            
            log_table = Table(log_data, colWidths=[1.2 * inch, 5.8 * inch])
            log_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
                ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
            ]))
            self.story.append(log_table)
            self.story.append(Spacer(1, 0.2 * inch))

    def generate(self) -> str | None:
        events = self._get_events()
        if not events:
            log.warning("No events found to generate report.")
            return None
            
        self._add_cover_page()
        self._add_summary_and_snapshot(events)
        self._add_detailed_log(events)
        
        try:
            self.doc.build(self.story, onFirstPage=self._add_header_footer, onLaterPages=self._add_header_footer)
            log.info(f"Report generated successfully at {self.filepath}")
            return self.filepath
        except Exception as e:
            log.critical(f"Failed to build PDF document: {e}", exc_info=True)
            return None