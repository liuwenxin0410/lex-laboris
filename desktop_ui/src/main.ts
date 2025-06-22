import { app, BrowserWindow, shell, globalShortcut, ipcMain, dialog, screen, net } from 'electron';
import * as path from 'path';
import spawn from 'cross-spawn';
import { ChildProcess } from 'child_process';
import * as fs from 'fs';

let pythonProcess: ChildProcess | null = null;
let mainWindow: BrowserWindow | null = null;
let captureWindows: BrowserWindow[] = [];

const REGION_CAPTURE_SHORTCUT = 'CommandOrControl+Shift+A';
const QUICK_SCREENSHOT_SHORTCUT = 'CommandOrControl+Shift+S';

function startPythonBackend() {
    console.log("[DEBUG: main.ts] Preparing to start Python backend...");
    const isDev = !app.isPackaged;
    let command: string;
    let args: string[] = [];
    let cwd: string | undefined = undefined;

    if (isDev) {
        command = 'python';
        const pythonRoot = path.resolve(app.getAppPath(), '..', 'core_py');
        args = ['-u', 'main.py'];
        cwd = pythonRoot;
        console.log(`[DEV MODE] Starting Python with command: ${command} ${args.join(' ')} in ${cwd}`);
    } else {
        const exeName = process.platform === 'win32' ? 'main_app.exe' : 'main_app';
        command = path.join(process.resourcesPath, 'extraResources', exeName);
        cwd = path.dirname(command);

        if (process.platform !== 'win32') {
            try {
                fs.chmodSync(command, '755');
                console.log(`[PROD MODE] Set execute permission on ${command}`);
            } catch (err) {
                console.error(`[CRITICAL ERROR] Failed to set execute permission on ${command}:`, err);
            }
        }
        console.log(`[PROD MODE] Starting Python with command: ${command} in ${cwd}`);
    }
    
    pythonProcess = spawn(command, args, { cwd });

    if (pythonProcess) {
        pythonProcess.on('error', (err) => console.error('[CRITICAL ERROR: main.ts] Failed to start Python process.', err));
        pythonProcess.stdout?.on('data', (data) => console.log(`PYTHON_STDOUT: ${data.toString().trim()}`));
        pythonProcess.stderr?.on('data', (data) => console.error(`PYTHON_STDERR: ${data.toString().trim()}`));
        pythonProcess.on('close', (code) => { console.log(`PYTHON_PROCESS: Process exited with code ${code}`); pythonProcess = null; });
    } else {
        console.error("[CRITICAL ERROR: main.ts] spawn() returned null. Python process could not be created.");
    }
}

function createMainWindow() {
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 800,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
        title: "工时壁垒"
    });

    mainWindow.loadFile(path.join(__dirname, '..', 'index.html'));
    mainWindow.on('closed', () => { mainWindow = null; });
    
    if (!app.isPackaged) {
        mainWindow.webContents.openDevTools();
    }
}

function createCaptureWindows() {
    if (captureWindows.length > 0) { captureWindows.forEach(win => win.focus()); return; }
    
    captureWindows = screen.getAllDisplays().map(display => {
        const captureWindow = new BrowserWindow({
            x: display.bounds.x, y: display.bounds.y, width: display.bounds.width, height: display.bounds.height,
            frame: false, transparent: true, alwaysOnTop: true, skipTaskbar: true,
            webPreferences: { preload: path.join(__dirname, 'preload.js') }
        });
        captureWindow.loadFile(path.join(__dirname, '..', 'capture.html'));
        return captureWindow;
    });
}

function closeCaptureWindows() {
    captureWindows.forEach(win => win.close());
    captureWindows = [];
}

function triggerQuickScreenshot() {
    console.log(`Shortcut ${QUICK_SCREENSHOT_SHORTCUT} pressed. Triggering API.`);
    const request = net.request({
        method: 'POST',
        protocol: 'http:',
        hostname: '127.0.0.1',
        port: 5001,
        path: '/api/shortcut_screenshot'
    });
    request.on('response', (response) => {
        console.log(`Shortcut screenshot response STATUS: ${response.statusCode}`);
    });
    request.on('error', (error) => {
        console.error(`Failed to trigger shortcut screenshot: ${error.message}`);
    });
    request.end();
}

// 【新增】一个简单的辅助函数，等待 Python Flask 服务器启动
function waitForBackend(): Promise<void> {
    return new Promise((resolve) => {
        const interval = setInterval(() => {
            const req = net.request({
                method: 'GET',
                protocol: 'http:',
                hostname: '127.0.0.1',
                port: 5001,
                path: '/api/status' // 找一个简单的端点探测
            });
            req.on('response', (res) => {
                // Flask 没完全起来前可能会返回 404，所以任何响应都算成功
                console.log('[DEBUG] Backend is responding!');
                clearInterval(interval);
                resolve();
            });
            req.on('error', () => { /* 忽略错误，继续轮询 */ });
            req.end();
        }, 500); // 每半秒检查一次
    });
}

app.whenReady().then(async () => {
    startPythonBackend();
    await waitForBackend();
    
    const userDataPath = app.getPath('userData');
    const logsPath = app.getPath('logs');
    // 【修改】检测开发模式
    const isDev = !app.isPackaged;

    const initRequest = net.request({
        method: 'POST',
        protocol: 'http:',
        hostname: '127.0.0.1',
        port: 5001,
        path: '/api/init'
    });
    initRequest.setHeader('Content-Type', 'application/json');
    // 【修改】将 isDev 标志发送给后端
    initRequest.write(JSON.stringify({ userDataPath, logsPath, isDev }));

    initRequest.on('response', (response) => {
        console.log(`[INIT] Backend initialization response STATUS: ${response.statusCode}`);
        if (response.statusCode === 200) {
            createMainWindow();
        } else {
            console.error('[CRITICAL] Backend failed to initialize. Closing app.');
            app.quit();
        }
    });
    initRequest.on('error', (error) => {
        console.error(`[CRITICAL] Failed to send init request to backend: ${error.message}. Closing app.`);
        app.quit();
    });
    initRequest.end();
    
    if (!globalShortcut.register(REGION_CAPTURE_SHORTCUT, createCaptureWindows)) {
        console.error(`Failed to register shortcut: ${REGION_CAPTURE_SHORTCUT}`);
    }
    if (!globalShortcut.register(QUICK_SCREENSHOT_SHORTCUT, triggerQuickScreenshot)) {
        console.error(`Failed to register shortcut: ${QUICK_SCREENSHOT_SHORTCUT}`);
    }

    app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createMainWindow(); });
});

app.on('will-quit', () => {
    globalShortcut.unregisterAll();
    if (pythonProcess) { pythonProcess.kill(); }
});

// --- IPC Handlers ---

ipcMain.on('capture-end', (event, area: { x: number; y: number; width: number; height: number; }) => {
    closeCaptureWindows();
    const point = screen.getCursorScreenPoint();
    const display = screen.getDisplayNearestPoint(point);
    const scaleFactor = display.scaleFactor;
    
    console.log(`[DEBUG] Capture ended. Original area (logical):`, area);
    console.log(`[DEBUG] Display scale factor: ${scaleFactor}`);

    const physicalArea = {
        x: Math.round(area.x * scaleFactor),
        y: Math.round(area.y * scaleFactor),
        width: Math.round(area.width * scaleFactor),
        height: Math.round(area.height * scaleFactor),
    };

    console.log(`[DEBUG] Calculated physical area:`, physicalArea);
    mainWindow?.webContents.send('screenshot-area-captured', physicalArea);
});

ipcMain.on('capture-close', () => closeCaptureWindows());

ipcMain.on('trigger-shortcut', (event, shortcut) => {
    if (shortcut === REGION_CAPTURE_SHORTCUT) createCaptureWindows();
    else if (shortcut === QUICK_SCREENSHOT_SHORTCUT) triggerQuickScreenshot();
});

ipcMain.handle('show-save-report-dialog', async (event, defaultFilename) => {
    if (!mainWindow) return;
    const { filePath } = await dialog.showSaveDialog(mainWindow, {
        title: '保存工作记录报告',
        defaultPath: defaultFilename,
        filters: [{ name: 'PDF 文档', extensions: ['pdf'] }]
    });
    return filePath;
});

ipcMain.on('show-file-in-folder', (event, filepath) => shell.showItemInFolder(filepath));

ipcMain.on('open-external-link', (event, url) => {
    shell.openExternal(url);
});