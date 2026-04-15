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
});