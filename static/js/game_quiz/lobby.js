// =========================================
// ЛОББИ ИГРЫ - ЛОГИКА
// =========================================
document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const els = {
        codeSection: document.getElementById('code-section'),
        codeValue: document.getElementById('lobby-code'),
        playerCount: document.getElementById('player-count'),
        playerList: document.getElementById('player-list'),
        btnStart: document.getElementById('btn-start-game'),
        btnSettings: document.getElementById('btn-settings'),
        lobbyData: document.getElementById('lobby-data')
    };

    // Конфигурация из data-атрибутов
    const config = {
        gameCode: els.lobbyData?.dataset.gameCode || '',
        minPlayers: parseInt(els.lobbyData?.dataset.minPlayers) || 2
    };

    // Состояние лобби
    const state = {
        players: [],
        isHost: true, // В реальном проекте проверять через бэкенд
        gameStarted: false
    };

    // =========================================
    // 1. КОПИРОВАНИЕ КОДА КОМНАТЫ
    // =========================================
    function copyGameCode() {
        if (!config.gameCode) return;

        navigator.clipboard.writeText(config.gameCode).then(() => {
            showToast('📋 Код скопирован!', 'success');

            // Визуальная обратная связь
            const originalText = els.codeSection.querySelector('.code-hint').textContent;
            els.codeSection.querySelector('.code-hint').textContent = '✅ Скопировано!';
            setTimeout(() => {
                els.codeSection.querySelector('.code-hint').textContent = originalText;
            }, 2000);
        }).catch(() => {
            showToast('❌ Не удалось скопировать', 'error');
        });
    }

    if (els.codeSection) {
        els.codeSection.addEventListener('click', copyGameCode);
    }

    // =========================================
    // 2. УПРАВЛЕНИЕ СПИСКОМ ИГРОКОВ
    // =========================================
    function addPlayer(username, isHost = false) {
        if (state.players.some(p => p.username === username)) return;

        state.players.push({username, isHost});
        renderPlayerList();
        updatePlayerCount();
        checkStartButton();
    }

    function removePlayer(username) {
        state.players = state.players.filter(p => p.username !== username);
        renderPlayerList();
        updatePlayerCount();
        checkStartButton();
    }

    function renderPlayerList() {
        if (!els.playerList) return;

        els.playerList.innerHTML = '';

        if (state.players.length === 0) {
            els.playerList.innerHTML = `
                <li class="player-item empty">
                    <span class="player-avatar placeholder">⏳</span>
                    <span class="player-name">Ожидание подключения...</span>
                </li>
            `;
            return;
        }

        state.players.forEach((player, idx) => {
            const li = document.createElement('li');
            li.className = 'player-item new';
            li.innerHTML = `
                <span class="player-avatar">${player.isHost ? '👑' : '🎮'}</span>
                <span class="player-name">${player.username}</span>
                ${player.isHost ? '<span class="player-role">Ведущий</span>' : ''}
            `;
            els.playerList.appendChild(li);

            // Убираем анимацию после завершения
            setTimeout(() => li.classList.remove('new'), 300);
        });
    }

    function updatePlayerCount() {
        if (els.playerCount) {
            els.playerCount.textContent = state.players.length;
        }
    }

    function checkStartButton() {
        if (els.btnStart) {
            els.btnStart.disabled = state.players.length < config.minPlayers || state.gameStarted;
        }
    }

    // =========================================
    // 3. ОБРАБОТКА КНОПОК
    // =========================================
    if (els.btnStart) {
        els.btnStart.addEventListener('click', () => {
            if (state.players.length < config.minPlayers) {
                showToast(`Нужно минимум ${config.minPlayers} игрока`, 'warning');
                return;
            }

            state.gameStarted = true;
            els.btnStart.disabled = true;
            els.btnStart.innerHTML = '<span class="btn-icon">⏳</span> Запуск...';

            // Заглушка под переход в игру
            setTimeout(() => {
                showToast('🚀 Игра начинается!', 'success');
                // window.location.href = `/quiz/play/${config.gameCode}/`;
            }, 1000);
        });
    }

    if (els.btnSettings) {
        els.btnSettings.addEventListener('click', () => {
            showToast('⚙️ Настройки комнаты (заглушка)', 'info');
            // Здесь можно открыть модальное окно с настройками
        });
    }

    // =========================================
    // 4. ИМИТАЦИЯ ПОДКЛЮЧЕНИЯ ИГРОКОВ (для демо)
    // =========================================
    function simulatePlayerJoin() {
        const demoPlayers = ['Алексей', 'Мария', 'Дмитрий', 'Анна'];
        const randomPlayer = demoPlayers[Math.floor(Math.random() * demoPlayers.length)];

        if (!state.players.some(p => p.username === randomPlayer)) {
            addPlayer(randomPlayer);
            showToast(`🎉 ${randomPlayer} присоединился!`, 'info');
        }
    }

    // В реальном проекте здесь будет WebSocket или long-polling
    // Для демо: симулируем подключение каждого 5 секунд
    const demoInterval = setInterval(simulatePlayerJoin, 5000);

    // =========================================
    // 5. ИНИЦИАЛИЗАЦИЯ
    // =========================================
    // Добавляем ведущего в список

    // Обновляем состояние кнопок
    checkStartButton();
});