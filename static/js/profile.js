// =========================================
// JS ВАЛИДАЦИЯ ФОРМ ПРОФИЛЯ
// =========================================

document.addEventListener('DOMContentLoaded', () => {
    const editForm = document.getElementById('editProfileForm');
    const passwordForm = document.getElementById('passwordChangeForm');

    // Валидация редактирования
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
});