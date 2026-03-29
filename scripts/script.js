/**
 * script.js
 * Общая логика для всех страниц Онлайн-Квиза
 * 
 * Функции:
 * 1. Генерация кода комнаты
 * 2. Копирование кода в буфер обмена
 * 3. Валидация форм
 * 4. Имитация WebSocket для лобби
 * 5. Уведомления (toast)
 */

// =========================================
// 1. ГЕНЕРАЦИЯ КОДА КОМНАТЫ
// =========================================

/**
 * Генерирует случайный 4-символьный код
 * Вызывается на странице create_game.html
 */
function generateCode() {
    const codeInput = document.getElementById('host-game-code');
    const createBtn = document.getElementById('btn-create-game');

    if (!codeInput) return;

    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let result = '';

    for (let i = 0; i < 4; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }

    codeInput.value = result;

    // Активируем кнопку создания если выбран квиз
    checkCreateGameForm();

    // Визуальный эффект
    codeInput.style.borderColor = '#2ed573';
    setTimeout(() => {
        codeInput.style.borderColor = '#ddd';
    }, 500);
}

// =========================================
// 2. ПРОВЕРКА ФОРМЫ СОЗДАНИЯ ИГРЫ
// =========================================

/**
 * Проверяет заполненность формы создания игры
 * Активирует кнопку только при выборе квиза и генерации кода
 */
function checkCreateGameForm() {
    const quizSelect = document.getElementById('quiz-select');
    const codeInput = document.getElementById('host-game-code');
    const createBtn = document.getElementById('btn-create-game');

    if (quizSelect && codeInput && createBtn) {
        const quizSelected = quizSelect.value !== '';
        const codeGenerated = codeInput.value !== '';

        if (quizSelected && codeGenerated) {
            createBtn.disabled = false;
        } else {
            createBtn.disabled = true;
        }
    }
}

// =========================================
// 3. КОПИРОВАНИЕ КОДА КОМНАТЫ
// =========================================

/**
 * Копирует код комнаты в буфер обмена
 * Вызывается при клике на код в лобби
 */
function copyGameCode() {
    const codeElement = document.getElementById('lobby-code');

    if (!codeElement) return;

    const code = codeElement.textContent.trim();

    navigator.clipboard.writeText(code).then(() => {
        // Визуальное подтверждение
        const originalText = codeElement.textContent;
        codeElement.textContent = '✓ СКОПИРОВАНО!';
        codeElement.style.color = '#2ed573';

        showToast('Код скопирован в буфер обмена!', 'success');

        setTimeout(() => {
            codeElement.textContent = originalText;
            codeElement.style.color = '';
        }, 2000);
    }).catch(err => {
        console.error('Не удалось скопировать код:', err);
        showToast('Не удалось скопировать код', 'error');
    });
}

// =========================================
// 4. ИМИТАЦИЯ WEBSOCKET ДЛЯ ЛОББИ
// =========================================

/**
 * Имитирует подключение игроков в лобби
 * Для демонстрации работы интерфейса
 */
function initLobbySimulation() {
    const playerCountElement = document.getElementById('player-count');
    const playerListElement = document.getElementById('player-list');
    const startBtn = document.getElementById('start-btn');
    const quizNameElement = document.getElementById('selected-quiz');

    if (!playerCountElement) return;

    // Получаем название квиза из URL параметров (имитация)
    const urlParams = new URLSearchParams(window.location.search);
    const quizParam = urlParams.get('quiz');

    if (quizParam && quizNameElement) {
        const quizNames = {
            'quiz1': 'Общие знания',
            'quiz2': 'Киноманы',
            'quiz3': 'Наука и Факты',
            'quiz4': 'Музыкальный квиз',
            'quiz5': 'География мира'
        };
        quizNameElement.textContent = quizNames[quizParam] || 'Общие знания';
    }

    // Генерируем случайный код для лобби если нет в URL
    const codeElement = document.getElementById('lobby-code');
    if (codeElement && codeElement.textContent === 'ABCD') {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
        let code = '';
        for (let i = 0; i < 4; i++) {
            code += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        codeElement.textContent = code;
    }

    // Имена игроков для имитации
    const playerNames = ['AlexGamer', 'QuizMaster', 'SmartGirl', 'JohnDoe', 'AnnaK', 'MaxPower', 'NataLi', 'Dimon2000'];
    let count = 0;

    const interval = setInterval(() => {
        if (count < 5 && Math.random() > 0.3) {
            count++;
            playerCountElement.textContent = count;

            // Добавляем игрока в список
            if (playerListElement) {
                // Удаляем заглушку если это первый игрок
                const emptyItem = playerListElement.querySelector('.empty');
                if (emptyItem) {
                    emptyItem.remove();
                }

                const playerName = playerNames[count - 1] || `Игрок ${count}`;
                const li = document.createElement('li');
                li.className = 'player-item';
                li.innerHTML = `
                    <span>👤 ${playerName}</span>
                    <span class="status-badge live">Подключён</span>
                `;
                li.style.animation = 'popIn 0.3s ease-out';
                playerListElement.appendChild(li);
            }

            // Анимация счётчика
            playerCountElement.style.transform = 'scale(1.3)';
            playerCountElement.style.color = '#2ed573';
            setTimeout(() => {
                playerCountElement.style.transform = 'scale(1)';
                playerCountElement.style.color = '';
            }, 200);
        }

        // Активируем кнопку старта если есть игроки
        if (count > 0 && startBtn) {
            startBtn.disabled = false;
            startBtn.textContent = `🚀 Начать игру (${count})`;
        }
    }, 2500);

    // Останавливаем симуляцию через 15 секунд
    setTimeout(() => clearInterval(interval), 15000);
}

// =========================================
// 5. УВЕДОМЛЕНИЯ (TOAST)
// =========================================

/**
 * Показывает всплывающее уведомление
 * @param {string} message - Текст уведомления
 * @param {string} type - Тип: 'success', 'error', 'info', 'warning'
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    const colors = {
        success: '#2ed573',
        error: '#ff4757',
        warning: '#ffa502',
        info: '#00d2be'
    };

    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 15px 25px;
        border-radius: 10px;
        color: white;
        font-weight: bold;
        font-family: 'Montserrat', sans-serif;
        z-index: 1000;
        animation: slideIn 0.3s ease-out;
        background: ${colors[type] || colors.info};
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Добавляем анимации для toast в документ
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// =========================================
// 6. ИНИЦИАЛИЗАЦИЯ ПРИ ЗАГРУЗКЕ
// =========================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🎲 Онлайн-Квиз загружен');

    // Инициализация формы создания игры
    const quizSelect = document.getElementById('quiz-select');
    if (quizSelect) {
        quizSelect.addEventListener('change', checkCreateGameForm);
    }

    // Инициализация лобби
    const lobbyCodeElement = document.getElementById('lobby-code');
    if (lobbyCodeElement) {
        console.log('📍 Страница лобби обнаружена');
        initLobbySimulation();
    }

    // Валидация форм перед отправкой
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const requiredInputs = form.querySelectorAll('input[required], select[required]');
            let isValid = true;

            requiredInputs.forEach(input => {
                if (!input.value.trim()) {
                    input.style.borderColor = '#ff4757';
                    isValid = false;
                } else {
                    input.style.borderColor = '#ddd';
                }
            });

            if (!isValid) {
                e.preventDefault();
                showToast('Заполните все обязательные поля', 'error');
            } else {
                showToast('Форма отправлена!', 'success');
            }
        });
    });

    // Анимация кнопок при наведении
    const roleButtons = document.querySelectorAll('.role-btn');
    roleButtons.forEach(btn => {
        btn.addEventListener('mouseenter', () => {
            btn.style.transform = 'translateY(-5px) rotate(-2deg)';
        });
        btn.addEventListener('mouseleave', () => {
            btn.style.transform = 'translateY(0) rotate(0)';
        });
    });

    // Закрытие модальных окон по Esc
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            const modals = document.querySelectorAll('.modal');
            modals.forEach(modal => modal.classList.add('hidden'));
        }
    });
});

// =========================================
// 7. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
// =========================================

/**
 * Получает параметры из URL
 * @param {string} param - Имя параметра
 * @returns {string|null} Значение параметра
 */
function getUrlParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

/**
 * Форматирует число с разделителями
 * @param {number} num - Число для форматирования
 * @returns {string} Отформатированное число
 */
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}

/**
 * Запускает таймер обратного отсчёта
 * @param {number} seconds - Количество секунд
 * @param {function} callback - Функция вызова по окончании
 */
function startTimer(seconds, callback) {
    let remaining = seconds;

    const interval = setInterval(() => {
        remaining--;

        const timerElement = document.querySelector('.question-timer');
        if (timerElement) {
            timerElement.textContent = `⏱ ${remaining} сек`;

            if (remaining <= 10) {
                timerElement.style.color = '#ff4757';
            }
        }

        if (remaining <= 0) {
            clearInterval(interval);
            if (callback) callback();
        }
    }, 1000);

    return interval;
}