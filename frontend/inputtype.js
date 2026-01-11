// ============================================
// 大台北公車票價計算機 - 車種輸入頁面 (inputtype.html)
// ============================================

import { BACKEND_URL, ENDPOINTS, BUS_OPTIONS } from './config.js';

/**
 * 初始化車種輸入頁面
 */
export function initInputTypePage() {
    // 取得頁面元素
    const tripsContainer = document.getElementById('trips_container');
    const addTripBtn = document.getElementById('addTripBtn');
    const clearAllBtn = document.getElementById('clearAllBtn');
    const calculateBtn = document.getElementById('calculateBtn');
    const resultDiv = document.getElementById('result');

    if (!tripsContainer || !addTripBtn || !clearAllBtn || !calculateBtn || !resultDiv) {
        console.error("Error: Missing one or more required elements for inputtype.html.");
        return;
    }

    /**
     * 動態建立公車種類選單
     * @param {HTMLSelectElement} selectElement - 選單元素
     */
    function createBusTypeSelect(selectElement) {
        selectElement.innerHTML = '<option value="">請選擇公車種類...</option>';

        BUS_OPTIONS.forEach(option => {
            const optionEl = document.createElement('option');
            optionEl.value = option;
            optionEl.textContent = option;
            selectElement.appendChild(optionEl);
        });
    }

    /**
     * 新增路線輸入
     */
    function addTrip() {
        const tripItem = document.createElement('div');
        tripItem.classList.add('line-item');
        tripItem.innerHTML = `
            <select class="bus_type"></select>
            <label>段數：</label>
            <input type="number" class="trip_count" value="1" min="1" max="99">
            <button type="button" class="remove-btn">移除</button>
        `;
        createBusTypeSelect(tripItem.querySelector('.bus_type'));
        tripsContainer.appendChild(tripItem);

        // 顯示第一個移除按鈕
        if (tripsContainer.querySelectorAll('.line-item').length > 1) {
            tripsContainer.querySelector('.line-item .remove-btn').style.display = 'inline-block';
        }
    }

    /**
     * 移除路線輸入（事件委派）
     */
    tripsContainer.addEventListener('click', (event) => {
        if (event.target.classList.contains('remove-btn')) {
            event.target.closest('.line-item').remove();
            // 如果只剩一個選單，隱藏移除按鈕
            if (tripsContainer.querySelectorAll('.line-item').length === 1) {
                tripsContainer.querySelector('.line-item .remove-btn').style.display = 'none';
            }
        }
    });

    /**
     * 重設表單
     */
    function resetForm() {
        tripsContainer.innerHTML = `
            <div class="line-item">
                <select class="bus_type"></select>
                <label>段數：</label>
                <input type="number" class="trip_count" value="1" min="1" max="99">
                <button type="button" class="remove-btn" style="display:none;">移除</button>
            </div>
        `;
        createBusTypeSelect(tripsContainer.querySelector('.bus_type'));
        resultDiv.textContent = '';
    }

    /**
     * 計算票價（車種模式）
     */
    async function handleCalculate() {
        const fareType = document.getElementById('fare_type').value;
        const busTrips = [];

        const tripItems = tripsContainer.querySelectorAll('.line-item');

        if (tripItems.length === 0) {
            resultDiv.textContent = '請至少新增一筆搭乘紀錄。';
            return;
        }

        let hasInvalidInput = false;

        tripItems.forEach(item => {
            const busType = item.querySelector('.bus_type').value;
            const tripCount = parseInt(item.querySelector('.trip_count').value);

            if (!busType || isNaN(tripCount) || tripCount < 1) {
                hasInvalidInput = true;
                return;
            }

            busTrips.push({
                "bus_type": busType,
                "trip_count": tripCount
            });
        });

        if (hasInvalidInput) {
            resultDiv.textContent = '請確認您已選擇公車種類並輸入有效段數 (大於0)。';
            return;
        }

        if (busTrips.length === 0) {
            resultDiv.textContent = '請填寫有效的搭乘紀錄。';
            return;
        }

        const dataToSend = {
            "fare_type": fareType,
            "bus_trips": busTrips
        };

        resultDiv.textContent = '計算中...';

        try {
            const response = await fetch(BACKEND_URL + ENDPOINTS.TYPE_CALCULATE, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dataToSend)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            if (result.total_fare !== undefined) {
                resultDiv.innerHTML = `總票價為: <strong>${result.total_fare} 元</strong>`;
            } else {
                resultDiv.textContent = `錯誤：${result.error}`;
            }
        } catch (error) {
            resultDiv.textContent = `發生錯誤：${error.message}`;
            console.error('Fetch Error:', error);
        }
    }

    // 綁定事件
    addTripBtn.addEventListener('click', addTrip);
    clearAllBtn.addEventListener('click', resetForm);
    calculateBtn.addEventListener('click', handleCalculate);

    // 頁面載入時初始化第一筆
    resetForm();
}
