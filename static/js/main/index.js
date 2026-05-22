/**
 * index.js - Скрипты для главной страницы
 * Анимации кнопок выбора роли
 */

document.addEventListener('DOMContentLoaded', () => {

    const roleButtons = document.querySelectorAll('.role-btn');

    // Эффект при наведении на кнопки ролей
    roleButtons.forEach(btn => {
        btn.addEventListener('mouseenter', function () {
            // Добавляем дополнительный эффект масштабирования
            this.style.transform = 'translateY(-10px) rotate(-2deg) scale(1.02)';
        });

        btn.addEventListener('mouseleave', function () {
            this.style.transform = 'translateY(0) rotate(0) scale(1)';
        });

        // Эффект при клике
        btn.addEventListener('click', function (e) {
            // Визуальная обратная связь
            const ripple = document.createElement('div');
            ripple.style.cssText = `
                position: absolute;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.6);
                transform: scale(0);
                animation: ripple 0.6s ease-out;
                pointer-events: none;
            `;

            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
            ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';

            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);

            setTimeout(() => ripple.remove(), 600);
        });
    });

    // Добавляем анимацию ripple в стили
    const style = document.createElement('style');
    style.textContent = `
        @keyframes ripple {
            to {
                transform: scale(2);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
});