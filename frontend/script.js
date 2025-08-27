// 引入常數檔案
// import { BACKEND_URL, ENDPOINTS, BUS_OPTIONS, version } from './config.js';

// 版本號
const VERSION = '0.0.3';

// 後端 API 的基礎網址
const BACKEND_URL = 'https://xwjwpiy-traffic-estimator-testing-api.onrender.com';

// 後端 API 的各個端點
// 新增了用於獲取所有路線資料的端點
const ENDPOINTS = {
    TYPE_CALCULATE: '/type_calculate_fare',
    LINE_CALCULATE: '/line_calculate_fare',
    ROUTES: '/api/routes',
    HEALTH: '/health'
};

// 公車種類選項
const BUS_OPTIONS = [
    "台北市一般公車", 
    "新北市一般公車", 
    "幹線公車", 
    "快速公車",
    "市民小巴", 
    "內科專車", 
    "跳蛙公車"
];

// 通用函式：獲取版本號
async function getVersion() {
    const statusDiv = document.getElementById('get-version');
    if (!statusDiv) {
        return;
    }
    statusDiv.textContent = 'version: ' + VERSION;
}

// 通用函式：檢查伺服器狀態
async function checkServerStatus() {
    const statusDiv = document.getElementById('server-status');
    if (!statusDiv) {
        return;
    }
    
    statusDiv.textContent = '伺服器連線狀態：檢查中...';
    statusDiv.style.color = 'black';
    
    try {
        const response = await fetch(BACKEND_URL + ENDPOINTS.HEALTH);
        if (response.ok) {
            statusDiv.textContent = '後端伺服器連線狀態：已連線';
            statusDiv.style.color = 'green';
        } else {
            statusDiv.textContent = '後端伺服器連線狀態：連線失敗';
            statusDiv.style.color = 'orange';
        }
    } catch (error) {
        statusDiv.textContent = '後端伺服器連線狀態：連線失敗 (伺服器可能正在啟動)';
        statusDiv.style.color = 'red';
    }
}


// ============== inputtype.html 頁面的專屬函式 ==============

// 函式：生成一個新的路線輸入框
function addTripRow(tripsContainer, tripCount) {
    const row = document.createElement('div');
    row.classList.add('trip-row');
    row.innerHTML = `
        <label>路線 ${tripCount}:</label>
        <select class="bus_type">
            <option value="">請選擇公車種類</option>
            ${BUS_OPTIONS.map(option => `<option value="${option}">${option}</option>`).join('')}
        </select>
        <label>段數：</label>
        <input type="number" class="trip_count" value="1" min="1" max="99">
    `;
    tripsContainer.appendChild(row);
}

// 函式：刪除最後一個路線輸入框
function removeLastTrip(tripsContainer) {
    const tripRows = tripsContainer.querySelectorAll('.trip-row');
    if (tripRows.length > 1) {
        tripsContainer.removeChild(tripRows[tripRows.length - 1]);
    }
}

// 函式：清空所有路線輸入框
function clearAllTrips() {
    const tripsContainer = document.getElementById('trips_container');
    tripsContainer.innerHTML = '';
    const resultDiv = document.getElementById('result');
    if (resultDiv) {
      resultDiv.textContent = '';
    }
    addTripRow(tripsContainer, 1);
}

// 計算邏輯函式
async function handleCalculateType() {
    const fareType = document.getElementById('fare_type').value;
    const busTrips = [];
    
    const tripRows = document.querySelectorAll('.trip-row');
    if (tripRows.length === 0) {
        document.getElementById('result').textContent = '請至少新增一筆搭乘紀錄。';
        return;
    }

    let hasInvalidInput = false;
    
    tripRows.forEach(row => {
        const busType = row.querySelector('.bus_type').value;
        const tripCount = parseInt(row.querySelector('.trip_count').value);
        
        if (busType === "" && tripCount > 0) {
            hasInvalidInput = true;
            return;
        }
        if (busType !== "" && tripCount > 0) {
            busTrips.push({
                "bus_type": busType,
                "trip_count": tripCount
            });
        }
    });

    if (hasInvalidInput) {
        document.getElementById('result').textContent = '請填寫有效的公車種類。';
        return;
    }

    if (busTrips.length === 0) {
        document.getElementById('result').textContent = '請填寫有效的搭乘紀錄。';
        return;
    }

    const dataToSend = {
        "fare_type": fareType,
        "bus_trips": busTrips
    };
    
    const resultDiv = document.getElementById('result');
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
            resultDiv.textContent = `總票價：${result.total_fare} 元`;
        } else {
            resultDiv.textContent = `錯誤：${result.error}`;
        }
    } catch (error) {
        resultDiv.textContent = `發生錯誤：${error.message}`;
        console.error('Fetch Error:', error);
    }
}


// ============== inputline.html 頁面的專屬函式 ==============

async function handleInputlinePage() {
    // 檢查必要的元素是否存在
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

    let allRoutes = {}; // 將其改為物件以適應後端回傳格式

    // 函式：載入所有路線資料
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

    // 函式：動態建立路線選單
    function createLineSelect(selectElement) {
        selectElement.innerHTML = '<option value="">請選擇路線...</option>';
        
        // 將字典的值（即路線資訊物件）轉換成陣列
        const routesArray = Object.values(allRoutes);
        allRoutes.forEach(route => {
            const option = document.createElement('option');
            option.value = route.RouteName;
            option.textContent = route.OutputName;
            selectElement.appendChild(option);
        });
    }

    // 函式：增加路線輸入
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

    // 函式：移除路線輸入
    lineContainer.addEventListener('click', (event) => {
        if (event.target.classList.contains('remove-btn')) {
            event.target.closest('.line-item').remove();
            // 如果只剩一個選單，隱藏移除按鈕
            if (lineContainer.querySelectorAll('.line-item').length === 1) {
                lineContainer.querySelector('.line-item .remove-btn').style.display = 'none';
            }
        }
    });

    // 表單提交處理
    fareForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        // 從所有 .line-item 元素中收集路線和段數資料
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

            // 檢查是否所有選單都已選擇且段數有效
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
            bus_trips: busTrips, // 將資料改為 bus_trips 以便後端處理
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

    // 啟動函式
    addLineBtn.addEventListener('click', addLine);
    resetBtn.addEventListener('click', () => {
        // 重設表單
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
    });

    // 載入頁面時，呼叫載入路線資料函式
    loadRoutes();
}


// ============== 頁面載入時的總執行函式 ==============

document.addEventListener('DOMContentLoaded', () => {
    // 總是執行伺服器連線檢查和版本號顯示
    checkServerStatus();
    getVersion();

    const currentPage = window.location.pathname;

    // 根據頁面路徑執行不同的邏輯
    if (currentPage.includes('inputtype.html')) { 
        // 這是您原有的 inputtype.html 頁面邏輯
        const tripsContainer = document.getElementById('trips_container');
        const addTripBtn = document.getElementById('addTripBtn');
        const removeLastBtn = document.getElementById('removeLastBtn');
        const clearAllBtn = document.getElementById('clearAllBtn');
        const calculateBtn = document.getElementById('calculateBtn');
        let tripCount = 0;

        if (!tripsContainer || !addTripBtn || !removeLastBtn || !clearAllBtn || !calculateBtn) {
            console.error("Error: Missing one or more required elements for inputtype.html.");
            return;
        }

        // 頁面載入時新增第一筆
        addTripRow(tripsContainer, ++tripCount);

        // 監聽按鈕事件
        addTripBtn.addEventListener('click', () => {
            addTripRow(tripsContainer, ++tripCount);
        });

        removeLastBtn.addEventListener('click', () => {
            if (tripCount > 1) {
                removeLastTrip(tripsContainer);
                tripCount--;
            }
        });

        clearAllBtn.addEventListener('click', () => {
            clearAllTrips();
            tripCount = 1; // 重設 tripCount
        });

        calculateBtn.addEventListener('click', handleCalculateType); // 呼叫處理車種的函式
    } else if (currentPage.includes('inputline.html')) {
        // 這是新增的 inputline.html 頁面邏輯
        handleInputlinePage();
    }
});
