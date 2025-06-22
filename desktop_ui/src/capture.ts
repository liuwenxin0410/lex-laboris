// 这里也不需要任何 import 或 declare global

document.addEventListener('DOMContentLoaded', () => {
    // 直接使用 window.api
    const api = window.api;

    const overlay = document.getElementById('overlay');
    const selectionBox = document.getElementById('selection-box');
    let isDrawing = false;
    let startX: number, startY: number;

    if (!overlay || !selectionBox) {
        console.error("Capture overlay or selection box not found!");
        return;
    }

    overlay.addEventListener('mousedown', (e: MouseEvent) => {
        isDrawing = true;
        startX = e.clientX;
        startY = e.clientY;
        selectionBox.style.left = `${startX}px`;
        selectionBox.style.top = `${startY}px`;
        selectionBox.style.width = '0px';
        selectionBox.style.height = '0px';
        selectionBox.style.display = 'block';
    });

    overlay.addEventListener('mousemove', (e: MouseEvent) => {
        if (!isDrawing) return;
        const currentX = e.clientX;
        const currentY = e.clientY;
        const width = Math.abs(currentX - startX);
        const height = Math.abs(currentY - startY);
        const newX = Math.min(startX, currentX);
        const newY = Math.min(startY, currentY);

        selectionBox.style.left = `${newX}px`;
        selectionBox.style.top = `${newY}px`;
        selectionBox.style.width = `${width}px`;
        selectionBox.style.height = `${height}px`;
    });

    overlay.addEventListener('mouseup', (e: MouseEvent) => {
        if (!isDrawing) return;
        isDrawing = false;
        
        const rect = selectionBox.getBoundingClientRect();
        
        // 确保用户画了一个有意义的区域，而不是误点
        if (rect.width > 5 && rect.height > 5) {
            api.endCapture({
                x: Math.round(rect.x),
                y: Math.round(rect.y),
                width: Math.round(rect.width),
                height: Math.round(rect.height)
            });
        } else {
            // 如果区域太小，则视为取消
            api.closeCapture();
        }
    });

    document.addEventListener('keydown', (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
            api.closeCapture();
        }
    });
});