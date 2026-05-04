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

            // Сбор данных формы
            const formData = {
                quiz_set_id: quizSelect.value,
                game_name: gameNameInput.value.trim(),
                game_code: codeInput.value,
                is_public: visToggle ? visToggle.checked : false
            };

            // Блокировка кнопки при отправке
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="btn-icon">⏳</span> Создание...';
            }

            // Отправка AJAX-запроса
            fetch('/quiz/create-game-ajax/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(formData)
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        if (typeof showToast === 'function') {
                            showToast('🎮 Игра создана! Переход в лобби...', 'success');
                        }
                        // Редирект в лобби с кодом комнаты
                        setTimeout(() => {
                            window.location.href = `/quiz/lobby/${data.game_code}/`;
                        }, 1000);
                    } else {
                        if (typeof showToast === 'function') {
                            console.log(data.error)
                            showToast(data.error || 'Ошибка создания игры', 'error');
                        }
                        // Разблокировка кнопки при ошибке
                        if (submitBtn) {
                            submitBtn.disabled = false;
                            submitBtn.innerHTML = '<span class="btn-icon">🚀</span> Создать игру';
                        }
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    if (typeof showToast === 'function') {
                        showToast('Произошла ошибка сети', 'error');
                    }
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = '<span class="btn-icon">🚀</span> Создать игру';
                    }
                });
        });
    }

    // =========================================
    // 5. ПЕРЕКЛЮЧАТЕЛЬ ВИДИМОСТИ
    // =========================================
    const visToggle = document.getElementById('game-visibility');
    const labelPrivate = document.getElementById('vis-private');
    const labelPublic = document.getElementById('vis-public');

    function updateVisLabels() {
        if (!visToggle) return;
        if (visToggle.checked) {
            labelPublic.classList.add('active');
            labelPrivate.classList.remove('active');
        } else {
            labelPrivate.classList.add('active');
            labelPublic.classList.remove('active');
        }
    }

    if (visToggle) {
        visToggle.addEventListener('change', updateVisLabels);
        updateVisLabels(); // Инициализация при загрузке
    }
});