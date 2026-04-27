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
    const btnEditSet = document.getElementById('btn-edit-set');

    // =========================================
    // 1. ГЕНЕРАЦИЯ КОДА ПРИГЛАШЕНИЯ
    // =========================================
    function generateCode() {
        const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
        let code = '';
        for (let i = 0; i < 4; i++) {
            code += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        codeInput.value = code;
        codeInput.classList.remove('is-invalid');
        validateForm();
    }

    if (generateBtn) {
        generateBtn.addEventListener('click', generateCode);
    }

    // =========================================
    // 2. ВАЛИДАЦИЯ ФОРМЫ
    // =========================================
    function validateForm() {
        const isQuizSelected = quizSelect && quizSelect.value !== '';
        const isNameValid = gameNameInput && gameNameInput.value.trim().length >= 3;
        const isCodeGenerated = codeInput && codeInput.value.length === 4;

        if (gameNameInput) {
            if (gameNameInput.value.trim().length > 0 && gameNameInput.value.trim().length < 3) {
                gameNameInput.classList.add('is-invalid');
            } else {
                gameNameInput.classList.remove('is-invalid');
            }
        }

        if (submitBtn) {
            submitBtn.disabled = !(isQuizSelected && isNameValid && isCodeGenerated);
        }
    }

    if (quizSelect) {
        quizSelect.addEventListener('change', () => {
            validateForm();
            updateEditButton();
        });
    }

    if (gameNameInput) {
        gameNameInput.addEventListener('input', validateForm);
    }

    // =========================================
    // 3. УПРАВЛЕНИЕ КНОПКОЙ "РЕДАКТИРОВАТЬ"
    // =========================================
    function updateEditButton() {
        if (!quizSelect || !btnEditSet) return;

        const selectedOption = quizSelect.options[quizSelect.selectedIndex];

        if (!selectedOption || !selectedOption.value || selectedOption.dataset.isMine !== 'true') {
            btnEditSet.style.display = 'none';
            return;
        }

        btnEditSet.style.display = 'inline-flex';
        btnEditSet.href = `/quiz/sets/edit/${quizSelect.value}/`;
    }

    // =========================================
    // 4. ОТПРАВКА ФОРМЫ
    // =========================================
    if (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            validateForm();

            if (submitBtn && submitBtn.disabled) {
                if (typeof showToast === 'function') {
                    showToast('Заполните все поля корректно', 'error');
                }
                return;
            }

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="btn-icon">⏳</span> Создание...';
            }

            setTimeout(() => {
                if (typeof showToast === 'function') {
                    showToast('Игра создана! Переход в лобби...', 'success');
                }
            }, 800);
        });
    }

    // Инициализация при загрузке
    validateForm();
});