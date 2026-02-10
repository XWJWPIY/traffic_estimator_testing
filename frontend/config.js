// ============================================
// 大台北公車票價計算機 - 設定常數
// ============================================

// 版本號
export const VERSION = 'v0.1.0';

// 作者資訊
export const AUTHOR = 'XWJWPIY (Xiang 詳)';

// 後端 API 的基礎網址
// 本機開發: 'http://127.0.0.1:5000'
export const BACKEND_URL = 'https://xwjwpiy-traffic-estimator-testing-api.onrender.com';

// 後端 API 的各個端點
export const ENDPOINTS = {
    TYPE_CALCULATE: '/type_calculate_fare',
    LINE_CALCULATE: '/line_calculate_fare',
    TYPE_CALCULATE: '/type_calculate_fare',
    LINE_CALCULATE: '/line_calculate_fare',
    ROUTES: '/api/routes',
    BUS_OPTIONS: '/api/bus_options',
    ROUTE_STOPS: '/api/route_stops',
    HEALTH: '/health'
};

// 公車種類選項 (已改為動態讀取，保留作為 fallback 或參考)
export const BUS_OPTIONS = [
    "台北市一般公車",
    "新北市一般公車",
    "幹線公車",
    "快速公車",
    "市民小巴",
    "內科專車",
    "跳蛙公車",
    "新北市新巴士"
];
