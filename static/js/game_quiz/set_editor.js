// =========================================
// КОНСТРУКТОР ВОПРОСОВ - ЛОГИКА
// =========================================
document.addEventListener('DOMContentLoaded', () => {
    let questions = [];
    let currentEditIndex = -1;

    const setIdElement = document.getElementById('set-id');
    const isEditing = setIdElement && setIdElement.value !== '';

    // DOM Elements
    const els = {
        setId: setIdElement,
        nameInput: document.getElementById('set-name'),
        qText: document.getElementById('q-text'),
        explanation: document.getElementById('q-explanation'),
        optionsContainer: document.getElementById('options-container'),
        btnAddOption: document.getElementById('btn-add-option'),
        btnSaveQuestion: document.getElementById('btn-save-question'),
        btnClear: document.getElementById('btn-clear-form'),
        btnSaveSet: document.getElementById('btn-save-set'),
        list: document.getElementById('question-list'),
        count: document.getElementById('q-count')
    };

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

    // =========================================
    // ПЕРЕКЛЮЧАТЕЛЬ ВИДИМОСТИ
    // =========================================

    const visPrivateBtn = document.getElementById('vis-private-btn');
    const visPublicBtn = document.getElementById('vis-public-btn');
    const isPublicInput = document.getElementById('is-public');
    const visHintText = document.getElementById('vis-hint-text');

    function updateVisibilityUI() {
        const isPublic = isPublicInput.value.toLowerCase() === 'true';

        if (isPublic) {
            visPublicBtn.classList.add('active');
            visPrivateBtn.classList.remove('active');
            visHintText.textContent = '🌐 Публичный набор будет виден всем пользователям';
        } else {
            visPrivateBtn.classList.add('active');
            visPublicBtn.classList.remove('active');
            visHintText.textContent = '🔒 Приватный набор виден только вам';
            visHintText.style.color = 'var(--text-gray)';
        }
    }

    if (visPrivateBtn) {
        visPrivateBtn.addEventListener('click', () => {
            isPublicInput.value = 'false';
            updateVisibilityUI();
        });
    }

    if (visPublicBtn) {
        visPublicBtn.addEventListener('click', () => {
            isPublicInput.value = 'true';
            updateVisibilityUI();
        });
    }

    // Инициализация
    updateVisibilityUI();

    // =========================================
    // 1. УПРАВЛЕНИЕ ВАРИАНТАМИ ОТВЕТА
    // =========================================
    function addOptionRow(value = '', isCorrect = false) {
        if (!els.optionsContainer) return;

        const row = document.createElement('div');
        row.className = `option-row ${isCorrect ? 'correct' : ''}`;
        row.innerHTML = `
            <input type="radio" name="correct-option" class="option-radio" ${isCorrect ? 'checked' : ''}>
            <input type="text" class="form-control option-input" placeholder="Вариант..." value="${value}">
            <button type="button" class="btn-remove-option">×</button>
        `;

        const radioBtn = row.querySelector('.option-radio');
        if (radioBtn) {
            radioBtn.addEventListener('change', () => {
                document.querySelectorAll('.option-row').forEach(r => r.classList.remove('correct'));
                row.classList.add('correct');
            });
        }

        const removeBtn = row.querySelector('.btn-remove-option');
        if (removeBtn) {
            removeBtn.addEventListener('click', () => {
                if (document.querySelectorAll('.option-row').length > 2) {
                    row.remove();
                } else {
                    if (typeof showToast === 'function') {
                        showToast('Минимум 2 варианта ответа', 'warning');
                    }
                }
            });
        }

        els.optionsContainer.appendChild(row);
    }

    if (els.btnAddOption) {
        els.btnAddOption.addEventListener('click', () => addOptionRow());
    }

    // Инициализация 2 пустых вариантов
    for (let i = 0; i < 2; i++) {
        addOptionRow();
    }

    // =========================================
    // 2. СБОР ДАННЫХ ИЗ ФОРМЫ
    // =========================================
    function getFormData() {
        const options = [];
        let correctIndex = -1;

        document.querySelectorAll('.option-row').forEach((row, idx) => {
            const input = row.querySelector('.option-input');
            const radio = row.querySelector('.option-radio');
            const text = input ? input.value.trim() : '';
            const isCorrect = radio ? radio.checked : false;

            if (text) options.push(text);
            if (isCorrect) correctIndex = options.length - 1;
        });

        return {
            question: els.qText ? els.qText.value.trim() : '',
            options: options,
            correctIndex: correctIndex,
            explanation: els.explanation ? els.explanation.value.trim() : ''
        };
    }

    // =========================================
    // 3. РЕНДЕР СПИСК
    // =========================================
    function renderList() {
        els.list.innerHTML = '';
        els.count.textContent = questions.length;

        if (questions.length === 0) {
            els.list.innerHTML = '<div class="empty-state">Пока нет вопросов.<br>Добавьте первый слева 👈</div>';
            return;
        }

        questions.forEach((q, idx) => {
            const item = document.createElement('div');
            item.className = `q-item ${idx === currentEditIndex ? 'active' : ''}`;

            // Добавляем кнопку удаления
            item.innerHTML = `
            <span class="q-item-text">
                <span class="q-item-num">#${idx + 1}</span> ${q.question}
            </span>
            <button type="button" class="btn-delete-q" title="Удалить вопрос">🗑️</button>
        `;

            // Клик по тексту вопроса → загрузка в редактор
            item.querySelector('.q-item-text').addEventListener('click', () => loadQuestion(idx));

            // Клик по корзине → удаление
            item.querySelector('.btn-delete-q').addEventListener('click', (e) => {
                e.stopPropagation(); // Чтобы не срабатывал loadQuestion
                deleteQuestion(idx);
            });

            els.list.appendChild(item);
        });
    }

    // =========================================
    // 4. ЗАГРУЗКА ВОПРОСА В РЕДАКТОР
    // =========================================
    function loadQuestion(idx) {
        if (idx < 0 || idx >= questions.length) return;

        currentEditIndex = idx;
        const q = questions[idx];

        if (els.qText) els.qText.value = q.question || '';
        if (els.explanation) els.explanation.value = q.explanation || '';

        if (els.optionsContainer) {
            els.optionsContainer.innerHTML = '';
            if (q.options && Array.isArray(q.options)) {
                q.options.forEach((opt, i) => {
                    addOptionRow(opt, i === q.correctIndex);
                });
            }
        }

        renderList();
    }

    // =========================================
    // 5. СОХРАНЕНИЕ ВОПРОСА
    // =========================================
    if (els.btnSaveQuestion) {
        els.btnSaveQuestion.addEventListener('click', () => {
            const data = getFormData();

            if (!data.question) {
                if (typeof showToast === 'function') showToast('Введите текст вопроса', 'error');
                if (els.qText) els.qText.focus();
                return;
            }
            if (data.options.length < 2) {
                if (typeof showToast === 'function') showToast('Нужно минимум 2 варианта ответа', 'error');
                return;
            }
            if (data.correctIndex === -1) {
                if (typeof showToast === 'function') showToast('Отметьте правильный ответ галочкой', 'error');
                return;
            }

            if (currentEditIndex !== -1) {
                questions[currentEditIndex] = data;
            } else {
                questions.push(data);
                currentEditIndex = questions.length - 1;
            }

            clearForm();
            renderList();
            if (typeof showToast === 'function') showToast('Вопрос сохранён в набор!', 'success');
        });
    }

    // =========================================
    // 5.1. УДАЛЕНИЕ ВОПРОСА
    // =========================================
    function deleteQuestion(idx) {
        if (!confirm('Удалить этот вопрос из набора?')) return;

        questions.splice(idx, 1); // Удаляем из массива

        // Корректируем индекс редактируемого вопроса
        if (idx === currentEditIndex) {
            currentEditIndex = -1;
            clearForm(); // Очищаем редактор, т.к. текущий вопрос удалён
        } else if (idx < currentEditIndex) {
            currentEditIndex--; // Сдвигаем индекс назад, если удалили вопрос выше
        }

        renderList();
        if (typeof showToast === 'function') showToast('Вопрос удалён из набора', 'info');
    }

    // =========================================
    // 6. ОЧИСТКА ФОРМЫ
    // =========================================
    function clearForm() {
        currentEditIndex = -1;
        if (els.qText) els.qText.value = '';
        if (els.explanation) els.explanation.value = '';
        if (els.optionsContainer) {
            els.optionsContainer.innerHTML = '';
            for (let i = 0; i < 2; i++) {
                addOptionRow();
            }
        }
        renderList();
    }

    if (els.btnClear) {
        els.btnClear.addEventListener('click', clearForm);
    }

    // =========================================
    // 7. СОХРАНЕНИЕ НАБОРА НА СЕРВЕР (AJAX)
    // =========================================
    if (els.btnSaveSet) {
        els.btnSaveSet.addEventListener('click', () => {
            const setName = els.nameInput ? els.nameInput.value.trim() : '';

            if (!setName) {
                if (typeof showToast === 'function') {
                    showToast('Введите название набора вопросов', 'error');
                }
                if (els.nameInput) els.nameInput.focus();
                return;
            }

            if (questions.length === 0) {
                if (typeof showToast === 'function') {
                    showToast('Добавьте хотя бы один вопрос', 'error');
                }
                return;
            }

            els.btnSaveSet.disabled = true;
            els.btnSaveSet.innerHTML = '<span class="btn-icon">⏳</span> Сохранение...';

            const payload = {
                name: setName,
                questions: questions,
                is_public: isPublicInput.value === 'true'
            };

            const setIdValue = els.setId ? els.setId.value : '';
            const url = setIdValue && isEditing
                ? `/quiz/sets/edit/${setIdValue}/save/`
                : '/quiz/sets/new/save/';

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(payload)
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        if (typeof showToast === 'function') {
                            showToast(data.message || 'Набор успешно сохранён!', 'success');

                            setTimeout(() => {
                                window.location.reload();
                            }, 1000)
                        }
                        if (data.set_id && els.setId) {
                            els.setId.value = data.set_id;
                        }
                    } else {
                        if (typeof showToast === 'function') {
                            showToast(data.error || 'Ошибка сохранения', 'error');

                            els.btnSaveSet.disabled = false;
                            els.btnSaveSet.innerHTML = '<span class="btn-icon">💾</span> Сохранить набор';
                        }
                    }
                })
                .catch(error => {
                    if (typeof showToast === 'function') {
                        showToast('Произошла ошибка сети', 'error');
                    }
                })
        });
    }

    // =========================================
    // 8. ИНИЦИАЛИЗАЦИЯ (загрузка существующих вопросов)
    // =========================================
    const initialJsonInput = document.getElementById('initial-questions-json');

    if (initialJsonInput && initialJsonInput.value) {
        try {
            // Парсим валидный JSON из скрытого поля
            const loadedQuestions = JSON.parse(initialJsonInput.value);

            if (Array.isArray(loadedQuestions) && loadedQuestions.length > 0) {
                questions = loadedQuestions;
                currentEditIndex = -1;
            }
        } catch (e) {
        }
    }

    renderList();

    // ==========================================
    // ЛОГИКА УДАЛЕНИЯ НАБОРА ВОПРОСОВ
    // ==========================================
    const btnDeleteSet = document.getElementById('btn-delete-set');

    if (btnDeleteSet) {
        btnDeleteSet.addEventListener('click', function () {
            // Извлекаем ID набора из data-атрибута кнопки
            const setId = this.dataset.setId;

            // Запрашиваем подтверждение у пользователя (защита от случайного клика)
            if (confirm('Вы уверены, что хотите навсегда удалить этот набор вопросов? Это действие необратимо.')) {

                // Ищем CSRF-токен на странице
                const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
                if (!csrfInput) {
                    alert('Ошибка: CSRF токен не найден на странице.');
                    return;
                }
                const csrfToken = csrfInput.value;

                // Блокируем кнопку на время запроса, чтобы не было двойных кликов
                const originalText = this.innerHTML;
                this.innerHTML = '⏳ Удаление...';
                this.disabled = true;

                // Отправляем AJAX-запрос на сервер
                fetch(`/quiz/set/${setId}/delete/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'Content-Type': 'application/json'
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // Показываем сообщение об успехе
                            alert('✅ ' + data.message);
                            // Перенаправляем пользователя на страницу со списком наборов/игр
                            window.location.href = '/quiz/';
                        } else {
                            // Если сработала серверная защита (например, идет активная игра)
                            alert('🛑 Отказ сервера: ' + data.error);
                            // Разблокируем кнопку
                            btnDeleteSet.innerHTML = originalText;
                            btnDeleteSet.disabled = false;
                        }
                    })
                    .catch(error => {
                        alert('Произошла сетевая ошибка при попытке удалить набор.');
                        btnDeleteSet.innerHTML = originalText;
                        btnDeleteSet.disabled = false;
                    });
            }
        });
    }
});