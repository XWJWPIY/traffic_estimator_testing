// ============================================
// 大台北公車票價計算機 - 查詢站牌頁面 (getlinestations.html)
// ============================================

import { BACKEND_URL, ENDPOINTS } from './config.js';

/**
 * 初始化查詢站牌頁面
 */
export async function initGetLineStationsPage() {
    const routeSelect = document.getElementById('route-select');
    const loadingRoutesStatus = document.getElementById('loading-routes-status');
    const loadingStopsStatus = document.getElementById('loading-stops-status');
    const errorMessage = document.getElementById('error-message');
    const stationsContainer = document.getElementById('stations-container');

    const singleColumn = document.getElementById('single-column');
    const outboundColumn = document.getElementById('outbound-column');
    const inboundColumn = document.getElementById('inbound-column');

    const startStopContainer = document.getElementById('start-stop-container');
    const startStopSelect = document.getElementById('start-stop-select');
    const endStopContainer = document.getElementById('end-stop-container');
    const endStopSelect = document.getElementById('end-stop-select');
    const fareCalcResult = document.getElementById('fare-calc-result');
    const fareSegmentsSpan = document.getElementById('fare-segments');

    const routeSearch = document.getElementById('route-search');
    const routeList = document.getElementById('route-list');
    const routeSelectHidden = document.getElementById('route-select');

    if (!routeSelect || !stationsContainer) {
        console.error("Missing elements for getlinestations page");
        return;
    }

    let allRoutes = [];
    let currentFlatStops = []; // Store flattened list of stops for fare calc
    let currentRoutes = []; // Fix: Declare here to avoid ReferenceError

    // 1. 載入所有路線
    try {
        const response = await fetch(BACKEND_URL + ENDPOINTS.ROUTES);
        if (!response.ok) throw new Error('無法載入路線資料');

        allRoutes = await response.json();
        populateRouteSelect(allRoutes);
        loadingRoutesStatus.style.display = 'none';

    } catch (error) {
        console.error(error);
        loadingRoutesStatus.textContent = `載入路線失敗: ${error.message}`;
        loadingRoutesStatus.style.color = 'red';
    }

    const clearRouteSearchBtn = document.getElementById('clear-route-search');

    // 2. 填充與搜尋邏輯
    function populateRouteSelect(routes) {
        currentRoutes = routes;
        // renderDropdown(routes); 
    }

    function toggleClearBtn() {
        if (routeSearch.value.trim().length > 0) {
            clearRouteSearchBtn.style.display = 'flex';
        } else {
            clearRouteSearchBtn.style.display = 'none';
        }
    }

    // Input Event (Filtering)
    routeSearch.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        toggleClearBtn();

        const filtered = currentRoutes.filter(r =>
            r.OutputName.toLowerCase().includes(query) ||
            r.RouteName.toLowerCase().includes(query)
        );

        // Smart Sort: Exact Match > Starts With > Numeric Start > Length > Alphabetical
        filtered.sort((a, b) => {
            const nameA = a.OutputName.toLowerCase();
            const nameB = b.OutputName.toLowerCase();
            const routeA = a.RouteName.toLowerCase();
            const routeB = b.RouteName.toLowerCase();

            // 1. Exact Match on RouteName (e.g. "5" vs "5")
            if (routeA === query && routeB !== query) return -1;
            if (routeB === query && routeA !== query) return 1;

            // 2. Starts With on RouteName (e.g. "5" vs "508")
            const startA = routeA.startsWith(query);
            const startB = routeB.startsWith(query);
            if (startA && !startB) return -1;
            if (!startA && startB) return 1;

            // 3. Numeric Start Priority & Value Sort
            // Routes starting with a digit come before routes starting with non-digit
            // AND within numeric routes, sort by integer value (e.g. 225 < 225區 < 226)
            const isNumA = /^\d/.test(routeA);
            const isNumB = /^\d/.test(routeB);

            if (isNumA && !isNumB) return -1;
            if (!isNumA && isNumB) return 1;

            if (isNumA && isNumB) {
                // Parse integer part
                const numA = parseInt(routeA, 10);
                const numB = parseInt(routeB, 10);

                if (numA !== numB) {
                    return numA - numB;
                }
                // If numbers match (e.g. 225 vs 225區), shorter usually base route
                // localeCompare handles this nicely too (225 < 225Sec)
                return nameA.localeCompare(nameB);
            }

            // 4. Length (Shorter is usually more relevant for text routes)
            if (nameA.length !== nameB.length) return nameA.length - nameB.length;

            return nameA.localeCompare(nameB);
        });

        renderDropdown(filtered, query);
        routeList.style.display = 'block';
    });

    // Clear Button Click
    clearRouteSearchBtn.addEventListener('click', (e) => {
        // Prevent event bubbling if needed, though button is outside ul
        routeSearch.value = '';
        routeSelectHidden.value = '';
        renderDropdown(currentRoutes, ""); // Show all logic? Or reset?
        // Let's reset display logic too
        resetDisplay();
        toggleClearBtn();
        routeList.style.display = 'block'; // Keep list open or close? User might want to browse. Open is better.
        routeSearch.focus();
    });

    // Focus Event (Show List)
    routeSearch.addEventListener('focus', () => {
        toggleClearBtn();
        if (routeSearch.value.trim() === "") {
            renderDropdown(currentRoutes, "");
        } else {
            renderDropdown(currentRoutes.filter(r => r.OutputName.includes(routeSearch.value) || r.RouteName.includes(routeSearch.value)), routeSearch.value);
        }
        routeList.style.display = 'block';
    });

    // Click Outside to Close
    document.addEventListener('click', (e) => {
        if (!e.target.closest('#route-select-container')) {
            routeList.style.display = 'none';
            toggleClearBtn(); // Hide clear button when dropdown closes
        }
    });

    function renderDropdown(routes, query) {
        routeList.innerHTML = '';
        if (routes.length === 0) {
            const li = document.createElement('li');
            li.className = 'dropdown-item';
            li.textContent = '無符合路線';
            li.style.color = '#999';
            li.style.cursor = 'default';
            routeList.appendChild(li);
            return;
        }

        // Limit results to improve performance
        // User requested ALL results. Removing limit. 
        // const MAX_RESULTS = 100;
        // const displayRoutes = routes.slice(0, MAX_RESULTS);
        const displayRoutes = routes;

        displayRoutes.forEach(route => {
            const li = document.createElement('li');
            li.className = 'dropdown-item';

            // Highlight Logic
            const text = route.OutputName;
            /* Simple highlighting if needed, maybe overkill for now. */
            li.textContent = text;

            li.addEventListener('click', () => {
                routeSearch.value = route.OutputName;
                routeSelectHidden.value = route.RouteName; // Set hidden value
                routeList.style.display = 'none';
                toggleClearBtn(); // Show clear btn after selection

                // Trigger change logic manually since hidden input doesn't fire events the same way
                handleRouteChange(route.RouteName);
            });
            routeList.appendChild(li);
        });
    }

    // 3. 處理路線變更 (Refactored to separate function)
    async function handleRouteChange(routeName) {
        // Clear previous Stops/Fare inputs
        if (!routeName) {
            resetDisplay();
            return;
        }
        await loadStops(routeName);
    }

    /* 
    // OLD SELECT EVENT - Removed
    routeSelect.addEventListener('change', async (e) => { ... }) 
    */

    // 3.5 票價計算器監聽器
    if (startStopSelect && endStopSelect) {
        // Start Stop Change -> Populate End Stop
        startStopSelect.addEventListener('change', (e) => {
            const startVal = e.target.value;
            fareCalcResult.style.display = 'none';

            if (!startVal) {
                endStopContainer.style.display = 'none';
                return;
            }

            const startIdx = parseInt(startVal);
            populateEndSelect(startIdx);
            endStopContainer.style.display = 'block';
        });

        // End Stop Change -> Calculate Fare
        endStopSelect.addEventListener('change', (e) => {
            const endVal = e.target.value;
            const startVal = startStopSelect.value;

            if (!endVal || !startVal) {
                fareCalcResult.style.display = 'none';
                return;
            }

            const startIdx = parseInt(startVal);
            const endIdx = parseInt(endVal);

            calculateFare(startIdx, endIdx);
        });
    }

    function populateStartSelect() {
        if (!startStopSelect) return;
        startStopSelect.innerHTML = '<option value="">請選擇起點站</option>';
        currentFlatStops.forEach((stop, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = `(${stop.dir}) ${stop.name}`;
            startStopSelect.appendChild(option);
        });
        if (startStopContainer) startStopContainer.style.display = 'block';
    }

    function populateEndSelect(startIdx) {
        endStopSelect.innerHTML = '<option value="">請選擇終點站</option>';
        // Only allow stops strictly AFTER Start Stop
        for (let i = startIdx + 1; i < currentFlatStops.length; i++) {
            const stop = currentFlatStops[i];
            const option = document.createElement('option');
            option.value = i;
            option.textContent = `(${stop.dir}) ${stop.name}`;
            endStopSelect.appendChild(option);
        }
    }

    function calculateFare(startIdx, endIdx) {
        const startStop = currentFlatStops[startIdx];
        const endStop = currentFlatStops[endIdx];

        // Formula: max(Alighting_Seg - Boarding_Seg + 1, 1)
        let segments = (endStop.alighting - startStop.boarding) + 1;
        if (segments < 1) segments = 1;

        fareSegmentsSpan.textContent = segments;
        fareCalcResult.style.display = 'block';
    }


    // 4. 載入特定路線站牌
    async function loadStops(routeName) {
        resetDisplay();
        loadingStopsStatus.style.display = 'block';
        errorMessage.textContent = '';

        try {
            const url = new URL(BACKEND_URL + ENDPOINTS.ROUTE_STOPS);
            url.searchParams.append('route_name', routeName);

            const response = await fetch(url);
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || '載入站牌失敗');
            }

            const data = await response.json();
            renderStops(data);
        } catch (error) {
            console.error(error);
            errorMessage.textContent = `錯誤: ${error.message}`;
        } finally {
            loadingStopsStatus.style.display = 'none';
        }
    }

    // 5. 渲染站牌
    function renderStops(data) {
        const outbound = data.outbound || [];
        const inbound = data.inbound || [];

        // 準備票價計算資料 (Flatten)
        currentFlatStops = [];
        outbound.forEach(s => currentFlatStops.push({ ...s, dir: '去' }));
        inbound.forEach(s => currentFlatStops.push({ ...s, dir: '返' }));

        // 更新 UI
        populateStartSelect();
        if (endStopContainer) endStopContainer.style.display = 'none';
        if (fareCalcResult) fareCalcResult.style.display = 'none';

        // 顯示警告 (如果有)
        const warningBox = document.getElementById('route-warning');
        if (warningBox) {
            if (data.warning) {
                warningBox.textContent = data.warning;
                warningBox.style.display = 'block';
                warningBox.className = 'warning-banner'; // Ensure CSS exists or add inline style
            } else {
                warningBox.style.display = 'none';
            }
        }

        // 判斷顯示模式
        if (outbound.length > 0 && inbound.length > 0) {
            // 雙欄模式
            renderColumn(outboundColumn, outbound, '(去程)');
            renderColumn(inboundColumn, inbound, '(返程)');

            // 更新目的地名稱
            const outboundDestSpan = outboundColumn.querySelector('.dest-name');
            const inboundDestSpan = inboundColumn.querySelector('.dest-name');
            if (outboundDestSpan) outboundDestSpan.textContent = data.outbound_dest || '';
            if (inboundDestSpan) inboundDestSpan.textContent = data.inbound_dest || '';

            outboundColumn.style.display = 'block';
            inboundColumn.style.display = 'block';
        } else {
            // 單欄模式 (合併或只有單邊)
            const list = outbound.length > 0 ? outbound : inbound;
            renderColumn(singleColumn, list, '');
            singleColumn.style.display = 'block';
        }
    }

    function renderColumn(columnElement, stops, directionLabel) {
        const listElement = columnElement.querySelector('.station-list');
        listElement.innerHTML = ''; // 清空

        // 更新標題 (若有需要顯示起訖點資訊，可從 data 擴充回傳)
        // 目前僅顯示基本列表

        stops.forEach(stop => {
            const li = document.createElement('li');
            li.className = 'station-item';

            // Check for Phantom Stop (support both half/full width parentheses)
            if (stop.name.includes('(虛擬站不停靠)') || stop.name.includes('（虛擬站不停靠）')) {
                li.classList.add('phantom-stop');
            }

            const seqSpan = document.createElement('span');
            seqSpan.className = 'station-seq';
            seqSpan.textContent = stop.seq;

            const nameSpan = document.createElement('span');
            nameSpan.className = 'station-name';
            nameSpan.textContent = stop.name;

            const segmentSpan = document.createElement('span');
            segmentSpan.className = 'station-segment';
            segmentSpan.textContent = ` [上${stop.boarding}|下${stop.alighting}]`;
            segmentSpan.style.marginLeft = '10px';
            segmentSpan.style.fontSize = '0.9em';
            segmentSpan.style.color = '#666';

            li.appendChild(seqSpan);
            li.appendChild(nameSpan);
            li.appendChild(segmentSpan);
            listElement.appendChild(li);
        });
    }

    function resetDisplay() {
        singleColumn.style.display = 'none';
        outboundColumn.style.display = 'none';
        inboundColumn.style.display = 'none';
        errorMessage.textContent = '';

        // Reset Fare UI
        if (startStopContainer) startStopContainer.style.display = 'none';
        if (endStopContainer) endStopContainer.style.display = 'none';
        if (fareCalcResult) fareCalcResult.style.display = 'none';
    }
}
