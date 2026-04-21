// =========================================
// ЛОГИКА ВКЛАДОК (TABS)
// =========================================

function setupTabs() {
    const hash = window.location.hash;
    if (hash) {
        const triggerEl = document.querySelector(`button[data-bs-target="${hash}"]`);
        if (triggerEl) {
            const tab = new bootstrap.Tab(triggerEl);
            tab.show();
            window.scrollTo(0, 0);
            window.history.replaceState(null, null, window.location.pathname);
        }
    }
}

// =========================================
// ВАЛИДАЦИЯ ФОРМ
// =========================================

function setupFormValidation() {
    const editForm = document.getElementById('editProfileForm');
    const passwordForm = document.getElementById('passwordChangeForm');

    // Валидация логина
    if (editForm) {
        editForm.addEventListener('submit', (e) => {
            let isValid = true;
            const username = document.getElementById('username');
            const errorBox = document.getElementById('usernameError');

            if (username.value.trim().length < 3) {
                errorBox.textContent = "❌ Логин слишком короткий";
                errorBox.classList.add('show');
                username.classList.add('is-invalid');
                isValid = false;
            } else {
                errorBox.textContent = "";
                errorBox.classList.remove('show');
                username.classList.remove('is-invalid');
            }
            if (!isValid) e.preventDefault();
        });
    }

    // Валидация смены пароля
    if (passwordForm) {
        passwordForm.addEventListener('submit', (e) => {
            let isValid = true;
            const newPass1 = document.getElementById('new_password1');
            const newPass2 = document.getElementById('new_password2');
            const err1 = document.getElementById('newPassword1Error');
            const err2 = document.getElementById('newPassword2Error');

            // Очистка ошибок
            [err1, err2].forEach(el => el.textContent = '');
            [newPass1, newPass2].forEach(el => el.classList.remove('is-invalid'));

            if (newPass1.value.length < 8) {
                err1.textContent = "❌ Минимум 8 символов";
                err1.classList.add('show');
                newPass1.classList.add('is-invalid');
                isValid = false;
            }

            if (newPass1.value !== newPass2.value) {
                err2.textContent = "❌ Пароли не совпадают";
                err2.classList.add('show');
                newPass2.classList.add('is-invalid');
                isValid = false;
            }

            if (!isValid) e.preventDefault();
        });
    }
}

// =========================================
// EMAIL ВЕРИФИКАЦИЯ
// =========================================

function setupEmailVerification() {
    const emailGroup = document.getElementById('email-group');
    if (!emailGroup) return; // Если нет блока email, выходим

    const emailInput = document.getElementById('email');
    const verifyBtn = document.getElementById('btn-verify-email');
    const codeSection = document.getElementById('code-section');
    const codeInput = document.getElementById('verification-code');
    const confirmBtn = document.getElementById('btn-confirm-code');
    const statusMsg = document.getElementById('email-status-msg');

    // Получаем URL и CSRF токен
    const SEND_URL = emailGroup.dataset.sendUrl;
    const VERIFY_URL = emailGroup.dataset.verifyUrl;
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // 1. Проверка валидности Email при вводе
    emailInput.addEventListener('input', (e) => {
        emailInput.classList.remove('is-verified');
        statusMsg.textContent = '';
        statusMsg.className = 'form-text text-muted';

        const email = e.target.value;
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (emailRegex.test(email)) {
            verifyBtn.style.display = 'block';
        } else {
            verifyBtn.style.display = 'none';
            // Если изменили email, сбрасываем статус подтверждения
            if (codeSection.style.display !== 'none') {
                codeSection.style.display = 'none';
                emailInput.classList.remove('is-verified');
                statusMsg.textContent = '';
            }
        }
    });

    // 2. Отправка кода на почту
    verifyBtn.addEventListener('click', () => {
        verifyBtn.disabled = true;
        verifyBtn.textContent = 'Отправка...';

        fetch(SEND_URL, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({email: emailInput.value})
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    verifyBtn.style.display = 'none';
                    codeSection.style.display = 'block';
                    codeInput.focus();
                    statusMsg.textContent = '📨 Код отправлен на ваш Email!';
                    statusMsg.className = 'form-text text-muted';
                } else {
                    showToast(data.error, 'error');
                }
            })
            .finally(() => {
                verifyBtn.disabled = false;
                verifyBtn.textContent = 'Проверить';
            });
    });

    // 3. Подтверждение кода
    confirmBtn.addEventListener('click', () => {
        const code = codeInput.value;
        confirmBtn.disabled = true;

        fetch(VERIFY_URL, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({code: code})
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    emailInput.classList.add('is-verified');
                    codeSection.style.display = 'none';
                    statusMsg.textContent = '✅ Email успешно подтвержден!';
                    statusMsg.className = 'form-text text-success';
                } else {
                    statusMsg.textContent = '❌ ' + data.error;
                    statusMsg.className = 'form-text text-danger';
                    confirmBtn.disabled = false;
                }
            });
    });
}

// =========================================
// СОХРАНЕНИЕ ПРОФИЛЯ (AJAX)
// =========================================

function setupProfileSave() {
    const profileForm = document.getElementById('editProfileForm');
    if (!profileForm) return;

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const saveBtn = profileForm.querySelector('button[type="submit"]');
    let isSubmitting = false; // Флаг защиты от двойного клика

    profileForm.addEventListener('submit', function (e) {
        e.preventDefault();

        if (isSubmitting) return;
        isSubmitting = true;

        // Блокируем кнопку
        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<span class="btn-icon">⏳</span> Сохранение...';
            saveBtn.style.opacity = '0.7';
            saveBtn.style.cursor = 'not-allowed';
        }

        const formData = new FormData(e.target);

        fetch(e.target.action, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Ajax-Request': 'true'
            },
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast(data.message || 'Профиль обновлен!', 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    showToast(data.error, 'error');
                    // Разблокируем только при ошибке
                    isSubmitting = false;
                    if (saveBtn) {
                        saveBtn.disabled = false;
                        saveBtn.innerHTML = '<span class="btn-icon">💾</span> Сохранить изменения';
                        saveBtn.style.opacity = '1';
                        saveBtn.style.cursor = 'pointer';
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Произошла ошибка сети', 'error');
                isSubmitting = false;
                if (saveBtn) {
                    saveBtn.disabled = false;
                    saveBtn.innerHTML = '<span class="btn-icon">💾</span> Сохранить изменения';
                    saveBtn.style.opacity = '1';
                    saveBtn.style.cursor = 'pointer';
                }
            });
    });
}

// =========================================
// ИНИЦИАЛИЗАЦИЯ
// =========================================

document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    setupFormValidation();
    setupEmailVerification();
    setupProfileSave();
});