document.addEventListener('DOMContentLoaded', () => {
    const api = window.api;
    let lastSession: { startTime: string, endTime: string } | null = null;
    let isTracking = false;

    // --- DOM 元素获取 (修改) ---
    const startBtn = document.getElementById('start-btn') as HTMLButtonElement;
    const stopBtn = document.getElementById('stop-btn') as HTMLButtonElement;
    const screenshotBtn = document.getElementById('manual-screenshot-btn') as HTMLButtonElement;
    const statusText = document.getElementById('status-text');
    const idleStatusText = document.getElementById('idle-status-text');
    const eventsLog = document.getElementById('events-log');
    const generateReportBtn = document.getElementById('generate-report-btn') as HTMLButtonElement;
    const userNameInput = document.getElementById('userName') as HTMLInputElement;
    const reportStatusDiv = document.getElementById('report-status');
    // 【移除】不再需要获取删除按钮和其状态 div
    // const deleteDbBtn = document.getElementById('delete-db-btn') as HTMLButtonElement;
    // const dbStatusDiv = document.getElementById('db-status');
    
    const eventTypeZh: { [key: string]: string } = {
        "environment_snapshot": "环境快照", "status_change": "状态变更", "keyboard_press": "键盘输入",
        "heartbeat": "活跃心跳", "app_session": "应用聚焦", 
        "screenshot_manual": "手动截屏", "screenshot_auto": "自动截屏", "file_created": "文件创建", 
        "file_modified": "文件修改", "file_deleted": "文件删除", "file_moved": "文件移动"
    };

    function updateUI(status: { is_tracking: boolean; is_idle: boolean }) {
        if (!statusText || !idleStatusText) return;
        isTracking = status.is_tracking;
        statusText.textContent = isTracking ? '运行中' : '未运行';
        statusText.className = `status-indicator ${isTracking ? 'active' : 'inactive'}`;
        idleStatusText.textContent = isTracking ? (status.is_idle ? '空闲' : '活跃') : '未知';
        idleStatusText.className = `status-indicator ${isTracking ? (status.is_idle ? 'idle' : 'active') : 'inactive'}`;
        
        startBtn.disabled = isTracking;
        stopBtn.disabled = !isTracking;
        screenshotBtn.disabled = !isTracking;
        generateReportBtn.disabled = isTracking || !lastSession;
        // 【移除】不再需要更新删除按钮的状态
        // deleteDbBtn.disabled = isTracking;
    }

    function createLogItemHTML(e: any): string {
        let detailsHTML = '';
        if (e.event_type.startsWith('screenshot_') && e.details.filepath) {
            const screenshotUrl = api.getScreenshotUrl(e.details.filepath);
            detailsHTML = `<a href="${screenshotUrl}" class="external-link">点击查看截图: ${e.details.filename}</a>`; 
        } else if (e.event_type === 'app_session') {
            const title = e.details.app_title ? ` - ${e.details.app_title}` : '';
            detailsHTML = `<strong>[${e.details.process_name}]${title}</strong><br>持续聚焦 ${e.details.duration_seconds} 秒。`;
        } 
        else if (e.event_type === 'keyboard_press') {
            detailsHTML = `<i>检测到键盘输入...</i>`;
        }
        else if (e.event_type === 'heartbeat') {
            detailsHTML = `<i>用户保持活跃...</i>`;
        } else {
            detailsHTML = `<pre>${JSON.stringify(e.details, null, 2).replace(/</g, '<').replace(/>/g, '>')}</pre>`;
        }
        return `<div class="log-item"><span class="timestamp">${new Date(e.timestamp).toLocaleTimeString()}</span><span class="event-type event-${e.event_type.replace(/_/g, '-')}">${eventTypeZh[e.event_type] || e.event_type}</span><span class="details" title='${JSON.stringify(e.details, null, 2)}'>${detailsHTML}</span><span class="hash" title="哈希: ${e.hash}\n前序: ${e.prev_hash}">🔗 ${e.hash.substring(0, 8)}</span></div>`;
    }

    async function fetchEventsAndStatus() {
        try {
            const statusResult = await api.getStatus();
            if (statusResult.status === 'success') {
                updateUI(statusResult);
                if (statusResult.is_tracking) {
                    const eventsResult = await api.getEvents();
                    if (eventsLog && eventsResult.status === 'success' && eventsResult.events) {
                        if(eventsLog.children.length !== eventsResult.events.length) {
                           eventsLog.innerHTML = eventsResult.events.map(createLogItemHTML).join('');
                        }
                    }
                }
            } else {
                 if (reportStatusDiv && !reportStatusDiv.textContent?.includes('错误')) {
                    reportStatusDiv.textContent = `错误：无法连接到后端服务。`;
                    reportStatusDiv.style.color = 'var(--inactive-color)';
                 }
            }
        } catch (err: any) {
             if (reportStatusDiv && !reportStatusDiv.textContent?.includes('错误')) {
                reportStatusDiv.textContent = `错误：无法连接到后端服务。(${err.message})`;
                reportStatusDiv.style.color = 'var(--inactive-color)';
             }
        }
    }

    startBtn.addEventListener('click', async () => { 
        const res = await api.startTracking();
        if(res.status === 'success') {
            if (eventsLog) eventsLog.innerHTML = "";
            lastSession = null;
            if (reportStatusDiv) reportStatusDiv.textContent = "请先完成一次“开始-结束”会话。";
            await fetchEventsAndStatus();
        } else {
            alert(`启动失败: ${res.message}`);
        }
    });

    stopBtn.addEventListener('click', async () => { 
        const result: any = await api.stopTracking(); 
        if (result.status === 'success' && result.session) {
            lastSession = { startTime: result.session.start_time, endTime: result.session.end_time };
            if (reportStatusDiv) reportStatusDiv.textContent = `上次会话已记录，可以生成报告了。`;
        }
        await fetchEventsAndStatus();
    });

    screenshotBtn.addEventListener('click', () => { if (!screenshotBtn.disabled) api.triggerShortcut('CommandOrControl+Shift+A'); });

    generateReportBtn.addEventListener('click', async () => {
        if (!reportStatusDiv || !lastSession) return;
        
        const now = new Date();
        const dateStr = now.getFullYear().toString() + (now.getMonth() + 1).toString().padStart(2, '0') + now.getDate().toString().padStart(2, '0');
        const timeStr = now.toTimeString().substring(0, 8).replace(/:/g, '');
        const timestamp = `${dateStr}_${timeStr}`;

        const userName = userNameInput.value.trim().replace(/\s/g, '_') || '用户';
        const defaultFilename = `工作记录报告_${userName}_${timestamp}.pdf`;
        
        const savePath = await api.showSaveReportDialog(defaultFilename);
        if (!savePath) return;
        
        reportStatusDiv.textContent = '正在生成报告...';
        generateReportBtn.disabled = true;
        
        const result = await api.generateReport({
            userInfo: { name: userNameInput.value || "匿名用户" },
            savePath: savePath, startDate: lastSession.startTime, endDate: lastSession.endTime,
        });
        
        if (result.status === 'success') {
            reportStatusDiv.innerHTML = `报告已保存！ <a href="#" id="show-file-link">(在文件夹中显示)</a>`;
            document.getElementById('show-file-link')?.addEventListener('click', (ev) => {
                ev.preventDefault(); api.showFileInFolder(result.filepath);
            });
        } else {
            reportStatusDiv.textContent = `错误: ${result.message}`;
        }
        generateReportBtn.disabled = false;
    });

    // 【移除】删除数据库按钮的整个事件监听器
    /*
    deleteDbBtn.addEventListener('click', async () => {
        // ...
    });
    */

    api.onScreenshotCaptured((area) => api.takeScreenshot({ bbox: [area.x, area.y, area.x + area.width, area.y + area.height] }));
    
    eventsLog?.addEventListener('click', (event) => {
        const target = event.target as HTMLElement;
        if (target.tagName === 'A' && target.classList.contains('external-link')) {
            event.preventDefault();
            const url = target.getAttribute('href');
            if (url) {
                api.openExternalLink(url);
            }
        }
    });

    // --- 初始化 ---
    fetchEventsAndStatus();
    setInterval(fetchEventsAndStatus, 1500);
});