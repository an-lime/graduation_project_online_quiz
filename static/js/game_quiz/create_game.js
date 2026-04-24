// =========================================
// СОЗДАНИЕ ИГРЫ - ЛОГИКА
// =========================================

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('createGameForm');
    const quizSelect = document.getElementById('quiz-select');
    const gameNameInput = document.getElementById('game-name');
    const codeInput = document.getElementById('host-game-code');
    const generateBtn = document.getElementById('btn-generate-code');
    const submitBtn = document.getElementById('btn-create-game');

    // =========================================
    // 1. ГЕНЕРАЦИЯ КОДА ПРИГЛАШЕНИЯ
    // =========================================
    function generateCode() {
        // Исключаем похожие символы (0/O, 1/I/L)
        const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
        let code = '';
        for (let i = 0; i < 4; i++) {
            code += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        codeInput.value = code;
        codeInput.classList.remove('is-invalid');
        validateForm();
    }

    generateBtn.addEventListener('click', generateCode);

    // =========================================
    // 2. ВАЛИДАЦИЯ ФОРМЫ
    // =========================================
    function validateForm() {
        const isQuizSelected = quizSelect.value !== '';
        const isNameValid = gameNameInput.value.trim().length >= 3;
        const isCodeGenerated = codeInput.value.length === 4;

        // Визуальная подсветка ошибок
        if (gameNameInput.value.trim().length > 0 && gameNameInput.value.trim().length < 3) {
            gameNameInput.classList.add('is-invalid');
        } else {
            gameNameInput.classList.remove('is-invalid');
        }

        // Активация кнопки создания
        submitBtn.disabled = !(isQuizSelected && isNameValid && isCodeGenerated);
    }

    quizSelect.addEventListener('change', validateForm);
    gameNameInput.addEventListener('input', validateForm);

    // =========================================
    // 3. ОТПРАВКА ФОРМЫ
    // =========================================
    form.addEventListener('submit', function (e) {
        e.preventDefault();
        validateForm();

        if (submitBtn.disabled) {
            if (typeof showToast === 'function') showToast('Заполните все поля корректно', 'error');
            return;
        }

        // Блокировка кнопки при отправке
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="btn-icon">⏳</span> Создание...';

        // Заглушка под AJAX/Redirect
        setTimeout(() => {
            if (typeof showToast === 'function') showToast('Игра создана! Переход в лобби...', 'success');
            // window.location.href = '/quiz/lobby/'; // Раскомментировать при интеграции
        }, 800);
    });

    const btnCreate = document.getElementById('btn-create-set');
    const btnEdit = document.getElementById('btn-edit-set');

    if (quizSelect) {
        quizSelect.addEventListener('change', function () {
            const hasValue = this.value !== '';
            btnCreate.style.display = hasValue ? 'none' : 'inline-flex';
            btnEdit.style.display = hasValue ? 'inline-flex' : 'none';

            btnEdit.href = `/quiz/sets/edit/${this.value}/`;
        });
    }
});