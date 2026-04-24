/**
 * login.js - Скрипты для страницы авторизации
 * Валидация формы, анимации, UX-улучшения
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('🔑 Страница авторизации загружена');

    const form = document.querySelector('.auth-form');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');

    // =========================================
    // 1. АНИМАЦИЯ ПОЛЕЙ ПРИ ФОКУСЕ
    // =========================================

    [usernameInput, passwordInput].forEach(input => {
        if (!input) return;

        // Эффект при фокусе
        input.addEventListener('focus', function () {
            this.parentElement.style.transform = 'scale(1.02)';
            this.parentElement.style.transition = 'transform 0.2s ease';
        });

        // Возврат при потере фокуса
        input.addEventListener('blur', function () {
            this.parentElement.style.transform = 'scale(1)';
        });
    });

    // =========================================
    // 2. ВАЛИДАЦИЯ В РЕАЛЬНОМ ВРЕМЕНИ
    // =========================================

    function validateField(input) {
        const value = input.value.trim();

        if (value.length === 0) {
            input.classList.remove('is-valid');
            input.classList.add('is-invalid');
            return false;
        }

        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        return true;
    }

    [usernameInput, passwordInput].forEach(input => {
        if (!input) return;

        input.addEventListener('input', () => validateField(input));
    });

    // =========================================
    // 3. ЭФФЕКТ НАЖАТИЯ НА КНОПКУ ВХОДА
    // =========================================

    const submitBtn = form?.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.addEventListener('click', function (e) {
            // Проверяем валидность полей перед отправкой
            const isUsernameValid = validateField(usernameInput);
            const isPasswordValid = validateField(passwordInput);

            if (!isUsernameValid || !isPasswordValid) {
                e.preventDefault();

                // Анимация тряски кнопки
                this.style.animation = 'shake 0.5s ease-in-out';
                setTimeout(() => {
                    this.style.animation = '';
                }, 500);
            } else {
                // Визуальная обратная связь при успешной валидации
                this.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    this.style.transform = '';
                }, 100);
            }
        });
    }

    // =========================================
    // 4. АНИМАЦИЯ ОШИБОК
    // =========================================

    const errorAlert = document.querySelector('.alert-jackbox');
    if (errorAlert) {
        // Добавляем эффект пульсации для иконки ошибки
        const icon = errorAlert.querySelector('.alert-icon');
        if (icon) {
            icon.style.animation = 'wiggle 1s infinite';
        }

        // Автозакрытие через 10 секунд (опционально)
        setTimeout(() => {
            errorAlert.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            errorAlert.style.opacity = '0';
            errorAlert.style.transform = 'translateY(-10px)';
            setTimeout(() => errorAlert.remove(), 500);
        }, 10000);
    }

    console.log('✅ Все скрипты авторизации инициализированы');
});