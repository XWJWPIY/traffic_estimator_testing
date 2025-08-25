// 引入常數檔案
// import { BACKEND_URL, ENDPOINTS, BUS_OPTIONS, version } from './config.js';

// 版本號
const VERSION = '0.0.1';

// 後端 API 的基礎網址
const BACKEND_URL = 'https://xwjwpiy-traffic-estimator-api.onrender.com';

// 後端 API 的各個端點
const ENDPOINTS = {
    CALCULATE: '/calculate_fare',
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


async function getVersion() {
    const statusDiv = document.getElementById('get-version');
    // 如果 HTML 中沒有這個元素，則不執行
    if (!statusDiv) {
        return;
    }
    statusDiv.textContent = '版本 ' + VERSION;
}


// 直接在 HTML 中預留一個 id="server-status" 的 div
async function checkServerStatus() {
    const statusDiv = document.getElementById('server-status');
    // 如果 HTML 中沒有這個元素，則不執行
    if (!statusDiv) {
        return;
    }
    
    statusDiv.textContent = '伺服器連線狀態：檢查中...';
    statusDiv.style.color = 'black'; // 確保初始顏色
    
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

// 函式：生成一個新的路線輸入框 (修訂版)
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

// 函式：刪除最後一個路線輸入框 (修訂版)
function removeLastTrip(tripsContainer) {
    const tripRows = tripsContainer.querySelectorAll('.trip-row');
    if (tripRows.length > 1) {
        tripsContainer.removeChild(tripRows[tripRows.length - 1]);
    }
}

// 函式：清空所有路線輸入框 (修訂版)
function clearAllTrips() {
    const tripsContainer = document.getElementById('trips_container');
    tripsContainer.innerHTML = '';
    const resultDiv = document.getElementById('result');
    if (resultDiv) {
      resultDiv.textContent = '';
    }
    // 注意：這裡我們不需要 tripCount，因為我們只負責清空和新增第一筆
    addTripRow(tripsContainer, 1);
}

// 計算邏輯函式
async function handleCalculate() {
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
        const response = await fetch(BACKEND_URL + ENDPOINTS.CALCULATE, {
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


document.addEventListener('DOMContentLoaded', () => {
    // 總是執行伺服器連線檢查
    checkServerStatus();
    getVersion();

    const currentPage = window.location.pathname;

    if (currentPage.includes('inputtype.html')) { 
        // 只在 inputtype.html 頁面選取這些元素
        const tripsContainer = document.getElementById('trips_container');
        const addTripBtn = document.getElementById('addTripBtn');
        const removeLastBtn = document.getElementById('removeLastBtn');
        const clearAllBtn = document.getElementById('clearAllBtn');
        const calculateBtn = document.getElementById('calculateBtn');
        let tripCount = 0; // 在這裡初始化，確保只在 inputtype.html 頁面使用

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

        calculateBtn.addEventListener('click', handleCalculate);
    }
});

