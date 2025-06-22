interface CaptureArea { x: number; y: number; width: number; height: number; }
type ApiResponse<T> = ({ status: 'success' } & T) | { status: 'error'; message: string };

interface LexLaborisApi {
    startTracking: () => Promise<ApiResponse<{}>>;
    stopTracking: () => Promise<ApiResponse<{ session: { start_time: string; end_time: string } }>>;
    getStatus: () => Promise<ApiResponse<{ is_tracking: boolean; is_idle: boolean }>>;
    getEvents: () => Promise<ApiResponse<{ events: any[] }>>;
    getScreenshotUrl: (filepath: string) => string;
    takeScreenshot: (data: { bbox: number[] | null }) => Promise<ApiResponse<{ filepath: string }>>;
    generateReport: (data: any) => Promise<ApiResponse<{ filepath: string }>>;
    // 【移除】删除数据库的类型定义
    // deleteDatabase: () => Promise<ApiResponse<{}>>;
    showFileInFolder: (filepath: string) => void;
    showSaveReportDialog: (defaultFilename: string) => Promise<string | undefined>;
    openExternalLink: (url: string) => void;
    onScreenshotCaptured: (callback: (area: CaptureArea) => void) => () => void;
    endCapture: (area: CaptureArea) => void;
    closeCapture: () => void;
    triggerShortcut: (shortcut: string) => void;
}

declare global {
    interface Window {
        api: LexLaborisApi;
    }
}

export {};