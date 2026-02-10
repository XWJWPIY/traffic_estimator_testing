// ============================================
// 大台北公車票價計算機 - 主入口點
// ============================================

import { getVersion, checkServerStatus, renderFooter } from './utils.js';
import { initInputTypePage } from './fare-by-type.js';
import { initInputLinePage } from './fare-by-line.js';
import { initGetLineStationsPage } from './route-stops.js';
import { initResponsiveNav } from './nav.js';

/**
 * 頁面載入時的初始化
 */
document.addEventListener('DOMContentLoaded', () => {
    // 總是執行伺服器連線檢查和版本號顯示
    checkServerStatus();
    getVersion();
    renderFooter();
    initResponsiveNav();

    const currentPage = window.location.pathname;

    // 根據頁面路徑執行不同的初始化邏輯
    if (currentPage.includes('fare-by-type.html')) {
        initInputTypePage();
    } else if (currentPage.includes('fare-by-line.html')) {
        initInputLinePage();
    } else if (currentPage.includes('route-stops.html')) {
        initGetLineStationsPage();
    }
    // index.html 不需要額外的初始化邏輯
});
