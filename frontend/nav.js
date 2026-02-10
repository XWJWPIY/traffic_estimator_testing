// ============================================
// 大台北公車票價計算機 - 響應式導覽列
// ============================================

/**
 * 導覽列項目定義（統一模板）
 */
const NAV_ITEMS = [
    { href: 'index.html', text: '首頁' },
    { href: 'fare-by-type.html', text: '車種組合計費' },
    { href: 'fare-by-line.html', text: '路線組合計費' },
    { href: 'route-stops.html', text: '路線站牌查詢' },
];

/**
 * 渲染導覽列 HTML 到 <nav id="main-nav"> 元素
 * 自動根據目前頁面 URL 標記 active 狀態
 */
export function renderNav() {
    const nav = document.getElementById('main-nav');
    if (!nav) return;

    const currentPage = window.location.pathname.split('/').pop() || 'index.html';

    const linksHtml = NAV_ITEMS.map(item => {
        const isActive = currentPage === item.href ? ' class="active"' : '';
        return `<a href="${item.href}"${isActive}>${item.text}</a>`;
    }).join('\n                ');

    nav.innerHTML = `
        <div class="nav-inner">
            <div class="nav-links">
                ${linksHtml}
            </div>
            <div class="nav-more" style="display:none;">
                <button class="nav-more-btn">更多 ▾</button>
                <div class="nav-more-menu"></div>
            </div>
        </div>
    `;
}

/**
 * 初始化響應式導覽列：
 * 當螢幕寬度不足以一行顯示所有連結時，
 * 將溢出的連結收進「更多 ▾」下拉選單。
 */
export function initResponsiveNav() {
    // 先渲染導覽列
    renderNav();

    const nav = document.getElementById('main-nav');
    if (!nav) return;

    const navInner = nav.querySelector('.nav-inner');
    const navLinks = nav.querySelector('.nav-links');
    const navMore = nav.querySelector('.nav-more');
    const moreBtn = nav.querySelector('.nav-more-btn');
    const moreMenu = nav.querySelector('.nav-more-menu');

    if (!navInner || !navLinks || !navMore || !moreBtn || !moreMenu) return;

    // 保存所有原始連結的資訊
    const allLinks = Array.from(navLinks.querySelectorAll('a'));
    const linkData = allLinks.map(a => ({
        href: a.getAttribute('href'),
        text: a.textContent,
        isActive: a.classList.contains('active')
    }));

    /**
     * 重新計算哪些連結需要被收進「更多」選單
     */
    function updateNav() {
        // 先把所有連結放回 navLinks，清空 moreMenu
        moreMenu.innerHTML = '';
        navLinks.innerHTML = '';
        linkData.forEach(data => {
            const a = document.createElement('a');
            a.href = data.href;
            a.textContent = data.text;
            if (data.isActive) a.classList.add('active');
            navLinks.appendChild(a);
        });

        // 暫時讓 navMore 隱藏以取得正確的可用寬度
        navMore.style.display = 'none';

        // 取得 navInner 的可用寬度
        const availableWidth = navInner.clientWidth;

        // 檢查是否有溢出
        if (navLinks.scrollWidth <= availableWidth) {
            // 全部放得下，不需要「更多」
            navMore.style.display = 'none';
            return;
        }

        // 需要「更多」按鈕 — 先顯示它來計算佔用的寬度
        navMore.style.display = '';
        const moreBtnWidth = navMore.offsetWidth + 8; // 加一點 margin

        // 逐一檢查能放幾個連結
        const links = Array.from(navLinks.querySelectorAll('a'));
        const overflowLinks = [];
        let usedWidth = 0;
        const maxWidth = availableWidth - moreBtnWidth;

        links.forEach((link, index) => {
            // 計算此連結佔的寬度 (包括 margin)
            const style = window.getComputedStyle(link);
            const linkWidth = link.offsetWidth
                + parseFloat(style.marginLeft)
                + parseFloat(style.marginRight);

            if (usedWidth + linkWidth <= maxWidth && overflowLinks.length === 0) {
                usedWidth += linkWidth;
            } else {
                overflowLinks.push({ link, index });
            }
        });

        // 將溢出的連結移到「更多」選單
        overflowLinks.forEach(({ link, index }) => {
            const menuItem = document.createElement('a');
            menuItem.href = linkData[index].href;
            menuItem.textContent = linkData[index].text;
            if (linkData[index].isActive) menuItem.classList.add('active');
            moreMenu.appendChild(menuItem);
            link.remove();
        });

        // 如果沒有溢出（不太可能到這裡，但以防萬一）
        if (overflowLinks.length === 0) {
            navMore.style.display = 'none';
        }
    }

    // 切換「更多」選單的顯示
    moreBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        moreMenu.classList.toggle('show');
    });

    // 點擊頁面其他地方關閉選單
    document.addEventListener('click', (e) => {
        if (!navMore.contains(e.target)) {
            moreMenu.classList.remove('show');
        }
    });

    // 初始化檢查
    updateNav();

    // 監聽視窗大小變化
    if (typeof ResizeObserver !== 'undefined') {
        const ro = new ResizeObserver(() => {
            moreMenu.classList.remove('show');
            updateNav();
        });
        ro.observe(navInner);
    } else {
        // Fallback for older browsers
        window.addEventListener('resize', () => {
            moreMenu.classList.remove('show');
            updateNav();
        });
    }
}
