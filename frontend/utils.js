// ============================================
// 大台北公車票價計算機 - 共用工具函式
// ============================================

import { VERSION, AUTHOR, BACKEND_URL, ENDPOINTS } from './config.js';

/**
 * 顯示版本號
 */
export function getVersion() {
    const statusDiv = document.getElementById('get-version');
    if (!statusDiv) {
        return;
    }
    statusDiv.textContent = 'version: ' + VERSION;
}

/**
 * 渲染頁尾（作者與版本資訊）
 */
export function renderFooter() {
    const footerDiv = document.getElementById('footer');
    if (footerDiv) {
        footerDiv.innerHTML = `
            <p class="author">Made by ${AUTHOR}</p>
            <div class="version">version: ${VERSION}</div>
        `;
    }

    // 渲染更新日誌旁的版本號
    const currentVersionSpan = document.getElementById('current-version');
    if (currentVersionSpan) {
        currentVersionSpan.textContent = `(目前版本: ${VERSION})`;
    }
}

/**
 * 檢查伺服器連線狀態
 */
export async function checkServerStatus() {
    const statusDiv = document.getElementById('server-status');
    if (!statusDiv) {
        return;
    }

    statusDiv.textContent = '伺服器連線狀態：檢查中...';
    statusDiv.className = 'checking';

    try {
        const response = await fetch(BACKEND_URL + ENDPOINTS.HEALTH);
        if (response.ok) {
            statusDiv.textContent = '後端伺服器連線狀態：已連線';
            statusDiv.className = 'connected';
        } else {
            statusDiv.textContent = '後端伺服器連線狀態：連線失敗';
            statusDiv.className = 'disconnected';
        }
    } catch (error) {
        statusDiv.textContent = '後端伺服器連線狀態：連線失敗 (伺服器可能正在啟動)';
        statusDiv.className = 'disconnected';
    }
}
