/**
 * base.js - Общие скрипты для всех страниц
 * Инициализация компонентов Bootstrap, общие обработчики
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('🎲 Онлайн-Квиз: base.js загружен');

    // Инициализация всех tooltip'ов Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Инициализация всех popover'ов Bootstrap
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Плавное закрытие мобильного меню при клике на ссылку
    document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
        link.addEventListener('click', () => {
            const navbarCollapse = document.querySelector('.navbar-collapse');
            if (navbarCollapse && navbarCollapse.classList.contains('show')) {
                bootstrap.Collapse.getInstance(navbarCollapse)?.hide();
            }
        });
    });

    headerLogo = document.getElementById('header-logo-div');

    headerLogo.addEventListener('click', () => {
        window.location.href = '/'
    })
});

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.textContent = message;

    const colors = {
        success: '#2ed573',
        error: '#ff4757',
        warning: '#ffa502',
        info: '#00d2be'
    };

    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 15px 25px;
        border-radius: 10px;
        color: white;
        font-weight: bold;
        font-family: 'Montserrat', sans-serif;
        z-index: 1000;
        background: ${colors[type] || colors.info};
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        animation: slideIn 0.3s ease-out;
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Добавляем анимации
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
`;
document.head.appendChild(style);