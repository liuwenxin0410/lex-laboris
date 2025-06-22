import { contextBridge, ipcRenderer } from 'electron';

interface CaptureArea { x: number; y: number; width: number; height: number; }

const API_BASE_URL = 'http://127.0.0.1:5001';
const apiRequest = async (endpoint: string, options: RequestInit = {}) => {
    try {
        const response = await fetch(`${API_BASE_URL}/api${endpoint}`, options);
        if (!response.ok) {
            const errorBody = await response.json().catch(() => ({ message: 'Failed to parse error response.' }));
            throw new Error(`API Error ${response.status}: ${errorBody.message || 'Unknown error'}`);
        }
        // 对于没有返回体的请求，比如 204 No Content，直接返回成功
        if (response.status === 204) return { status: 'success' };
        return await response.json();
    } catch (error: any) {
        return { status: 'error', message: error.message };
    }
};

const api = {
    startTracking: () => apiRequest('/start_tracking', { method: 'POST' }),
    stopTracking: () => apiRequest('/stop_tracking', { method: 'POST' }),
    getStatus: () => apiRequest('/status'),
    getEvents: () => apiRequest('/events'),
    getScreenshotUrl: (filepath: string) => `${API_BASE_URL}/api/screenshots/${encodeURIComponent(filepath)}`,
    takeScreenshot: (data: any) => apiRequest('/take_screenshot', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data), }),
    generateReport: (data: any) => apiRequest('/generate_report', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data), }),
    // 【移除】删除数据库的接口
    // deleteDatabase: () => apiRequest('/delete_database', { method: 'POST' }),
    showFileInFolder: (filepath: string) => ipcRenderer.send('show-file-in-folder', filepath),
    showSaveReportDialog: (defaultFilename: string) => ipcRenderer.invoke('show-save-report-dialog', defaultFilename),
    openExternalLink: (url: string) => ipcRenderer.send('open-external-link', url),
    onScreenshotCaptured: (callback: (area: CaptureArea) => void) => {
        const sub = (event: Electron.IpcRendererEvent, area: CaptureArea) => callback(area);
        ipcRenderer.on('screenshot-area-captured', sub);
        return () => ipcRenderer.removeListener('screenshot-area-captured', sub);
    },
    endCapture: (area: CaptureArea) => ipcRenderer.send('capture-end', area),
    closeCapture: () => ipcRenderer.send('capture-close'),
    triggerShortcut: (shortcut: string) => ipcRenderer.send('trigger-shortcut', shortcut),
};

contextBridge.exposeInMainWorld('api', api);