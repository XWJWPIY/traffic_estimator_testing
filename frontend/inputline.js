// ============================================
// 大台北公車票價計算機 - 路線輸入頁面 (inputline.html)
// ============================================

import { BACKEND_URL, ENDPOINTS } from './config.js';

/**
 * 初始化路線輸入頁面
 */
export async function initInputLinePage() {
    // 取得頁面元素
    const loadingStatus = document.getElementById('loading-status');
    const fareForm = document.getElementById('fare-form');
    const lineContainer = document.getElementById('line-container');
    const addLineBtn = document.getElementById('add-line-btn');
    const resetBtn = document.getElementById('reset-btn');
    const fareTypeSelect = document.getElementById('fare-type');
    const resultDiv = document.getElementById('result');
    const errorDiv = document.getElementById('error-message');

    if (!loadingStatus || !fareForm || !lineContainer || !addLineBtn || !resetBtn || !fareTypeSelect || !resultDiv || !errorDiv) {
        console.error("Error: Missing one or more required elements for inputline.html.");
        return;
    }

    let allRoutes = [];

    /**
     * 載入所有路線資料
     */
    async function loadRoutes() {
        try {
            const response = await fetch(BACKEND_URL + ENDPOINTS.ROUTES);
            if (!response.ok) {
                throw new Error('無法載入路線資料。');
            }
            const data = await response.json();
            allRoutes = data;

            loadingStatus.style.display = 'none';
            fareForm.style.display = 'block';

            // 創建第一個選單
            createLineSelect(lineContainer.querySelector('.route-select'));

        } catch (error) {
            console.error('載入路線資料失敗:', error);
            loadingStatus.textContent = '載入路線資料失敗，請稍後再試。';
        }
    }

    /**
     * 動態建立路線選單
     * @param {HTMLSelectElement} selectElement - 選單元素
     */
    function createLineSelect(selectElement) {
        selectElement.innerHTML = '<option value="">請選擇路線...</option>';

        allRoutes.forEach(route => {
            const option = document.createElement('option');
            option.value = route.RouteName;
            option.textContent = route.OutputName;
            selectElement.appendChild(option);
        });
    }

    /**
     * 新增路線輸入
     */
    function addLine() {
        const lineItem = document.createElement('div');
        lineItem.classList.add('line-item');
        lineItem.innerHTML = `
            <select name="line[]" class="route-select"></select>
            <label>段數：</label>
            <input type="number" class="trip_count" value="1" min="1" max="99">
            <button type="button" class="remove-btn">移除</button>
        `;
        createLineSelect(lineItem.querySelector('.route-select'));
        lineContainer.appendChild(lineItem);

        // 顯示第一個移除按鈕
        if (lineContainer.querySelectorAll('.line-item').length > 1) {
            lineContainer.querySelector('.line-item .remove-btn').style.display = 'inline-block';
        }
    }

    /**
     * 移除路線輸入（事件委派）
     */
    lineContainer.addEventListener('click', (event) => {
        if (event.target.classList.contains('remove-btn')) {
            event.target.closest('.line-item').remove();
            // 如果只剩一個選單，隱藏移除按鈕
            if (lineContainer.querySelectorAll('.line-item').length === 1) {
                lineContainer.querySelector('.line-item .remove-btn').style.display = 'none';
            }
        }
    });

    /**
     * 表單提交處理
     */
    fareForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const busTrips = [];
        const lineItems = lineContainer.querySelectorAll('.line-item');

        if (lineItems.length === 0) {
            errorDiv.textContent = '請至少選擇一條路線。';
            resultDiv.textContent = '';
            return;
        }

        let hasInvalidInput = false;

        lineItems.forEach(item => {
            const routeName = item.querySelector('.route-select').value;
            const tripCount = parseInt(item.querySelector('.trip_count').value);

            if (!routeName || isNaN(tripCount) || tripCount < 1) {
                hasInvalidInput = true;
                return;
            }

            busTrips.push({
                line_name: routeName,
                trip_count: tripCount
            });
        });

        if (hasInvalidInput) {
            errorDiv.textContent = '請確認您已選擇路線並輸入有效段數 (大於0)。';
            resultDiv.textContent = '';
            return;
        }

        const fareType = fareTypeSelect.value;
        const payload = {
            bus_trips: busTrips,
            fare_type: fareType
        };

        resultDiv.textContent = '計算中...';
        errorDiv.textContent = '';

        try {
            const response = await fetch(BACKEND_URL + ENDPOINTS.LINE_CALCULATE, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || '後端計算失敗，請檢查輸入。');
            }

            const result = await response.json();
            if (result.total_fare !== undefined) {
                resultDiv.innerHTML = `總票價為: <strong>${result.total_fare} 元</strong>`;
            } else {
                errorDiv.textContent = '計算結果無效。';
            }
            errorDiv.textContent = '';

        } catch (error) {
            console.error('計算票價時發生錯誤:', error);
            errorDiv.textContent = `錯誤：${error.message}`;
            resultDiv.textContent = '';
        }
    });

    /**
     * 重設表單
     */
    function resetForm() {
        lineContainer.innerHTML = `
            <div class="line-item">
                <select name="line[]" class="route-select"></select>
                <label>段數：</label>
                <input type="number" class="trip_count" value="1" min="1" max="99">
                <button type="button" class="remove-btn" style="display:none;">移除</button>
            </div>
        `;
        createLineSelect(lineContainer.querySelector('.route-select'));
        fareTypeSelect.value = 'full_fare';
        resultDiv.textContent = '';
        errorDiv.textContent = '';
    }

    // 綁定事件
    addLineBtn.addEventListener('click', addLine);
    resetBtn.addEventListener('click', resetForm);

    // 載入路線資料
    loadRoutes();
}
