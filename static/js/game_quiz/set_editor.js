// =========================================
// КОНСТРУКТОР ВОПРОСОВ - ЛОГИКА
// =========================================
document.addEventListener('DOMContentLoaded', () => {
    let questions = [];
    let currentEditIndex = -1;
    const isEditing = document.getElementById('set-id').value !== '';

    // DOM Elements
    const els = {
        setId: document.getElementById('set-id'),
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

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // =========================================
    // 1. УПРАВЛЕНИЕ ВАРИАНТАМИ ОТВЕТА
    // =========================================
    function addOptionRow(value = '', isCorrect = false) {
        const row = document.createElement('div');
        row.className = `option-row ${isCorrect ? 'correct' : ''}`;
        row.innerHTML = `
            <input type="radio" name="correct-option" class="option-radio" ${isCorrect ? 'checked' : ''}>
            <input type="text" class="form-control option-input" placeholder="Вариант..." value="${value}">
            <button type="button" class="btn-remove-option">×</button>
        `;

        row.querySelector('.option-radio').addEventListener('change', () => {
            document.querySelectorAll('.option-row').forEach(r => r.classList.remove('correct'));
            row.classList.add('correct');
        });

        row.querySelector('.btn-remove-option').addEventListener('click', () => {
            if (document.querySelectorAll('.option-row').length > 2) {
                row.remove();
            } else {
                if (typeof showToast === 'function') showToast('Минимум 2 варианта ответа', 'warning');
            }
        });

        els.optionsContainer.appendChild(row);
    }

    els.btnAddOption.addEventListener('click', () => addOptionRow());
    for (let i = 0; i < 4; i++) addOptionRow();

    // =========================================
    // 2. СБОР ДАННЫХ ИЗ ФОРМЫ
    // =========================================
    function getFormData() {
        const options = [];
        let correctIndex = -1;

        document.querySelectorAll('.option-row').forEach((row, idx) => {
            const text = row.querySelector('.option-input').value.trim();
            const isCorrect = row.querySelector('.option-radio').checked;
            if (text) options.push(text);
            if (isCorrect) correctIndex = options.length - 1;
        });

        return {
            question: els.qText.value.trim(),
            options: options,
            correctIndex: correctIndex,
            explanation: els.explanation.value.trim()
        };
    }

    // =========================================
    // 3. РЕНДЕР СПИСКА ВОПРОСОВ
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
            item.innerHTML = `
                <span class="q-item-text"><span class="q-item-num">#${idx + 1}</span> ${q.question}</span>
                <span style="color: var(--success); font-weight:bold;">✓</span>
            `;
            item.addEventListener('click', () => loadQuestion(idx));
            els.list.appendChild(item);
        });
    }

    // =========================================
    // 4. ЗАГРУЗКА ВОПРОСА В РЕДАКТОР
    // =========================================
    function loadQuestion(idx) {
        currentEditIndex = idx;
        const q = questions[idx];

        els.qText.value = q.question;
        els.explanation.value = q.explanation || '';

        els.optionsContainer.innerHTML = '';
        q.options.forEach((opt, i) => {
            addOptionRow(opt, i === q.correctIndex);
        });

        renderList();
    }

    // =========================================
    // 5. СОХРАНЕНИЕ ВОПРОСА
    // =========================================
    els.btnSaveQuestion.addEventListener('click', () => {
        const data = getFormData();

        if (!data.question) {
            if (typeof showToast === 'function') showToast('Введите текст вопроса', 'error');
            els.qText.focus();
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

    // =========================================
    // 6. ОЧИСТКА ФОРМЫ
    // =========================================
    function clearForm() {
        currentEditIndex = -1;
        els.qText.value = '';
        els.explanation.value = '';
        els.optionsContainer.innerHTML = '';
        for (let i = 0; i < 4; i++) addOptionRow();
        renderList();
    }

    els.btnClear.addEventListener('click', clearForm);

    // =========================================
    // 7. СОХРАНЕНИЕ НАБОРА НА СЕРВЕР (AJAX)
    // =========================================
    els.btnSaveSet.addEventListener('click', () => {
        const setName = els.nameInput.value.trim();

        // Валидация названия
        if (!setName) {
            if (typeof showToast === 'function') showToast('Введите название набора вопросов', 'error');
            els.nameInput.focus();
            return;
        }

        // Валидация наличия вопросов
        if (questions.length === 0) {
            if (typeof showToast === 'function') showToast('Добавьте хотя бы один вопрос', 'error');
            return;
        }

        // Блокировка кнопки при отправке
        els.btnSaveSet.disabled = true;
        els.btnSaveSet.innerHTML = '<span class="btn-icon">⏳</span> Сохранение...';

        const payload = {
            name: setName,
            questions: questions
        };

        const url = isEditing
            ? `/quiz/sets/edit/${els.setId.value}/save/`
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
                    if (typeof showToast === 'function') showToast(data.message || 'Набор успешно сохранён!', 'success');
                    // Обновляем ID для последующих сохранений
                    if (data.set_id) {
                        els.setId.value = data.set_id;
                    }
                } else {
                    if (typeof showToast === 'function') showToast(data.error || 'Ошибка сохранения', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                if (typeof showToast === 'function') showToast('Произошла ошибка сети', 'error');
            })
            .finally(() => {
                els.btnSaveSet.disabled = false;
                els.btnSaveSet.innerHTML = '<span class="btn-icon">💾</span> Сохранить набор';
            });
    });

    // =========================================
    // 8. ИНИЦИАЛИЗАЦИЯ (загрузка существующих вопросов)
    // =========================================
    const initialDataEl = document.getElementById('initial-data');
    if (initialDataEl) {
        const initialQuestions = JSON.parse(initialDataEl.dataset.questions || '[]');
        if (initialQuestions.length > 0) {
            questions = initialQuestions;
            currentEditIndex = -1;
            renderList();
        }
    }

    renderList();
});