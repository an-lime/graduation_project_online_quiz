// =========================================
// ЛОББИ ИГРЫ - ЛОГИКА С WEBSOCKET
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
        players: new Set(['{{ game.owner.username }}']), // Ведущий уже в списке
        isHost: true,
        gameStarted: false,
        ws: null,
        reconnectAttempts: 0,
        maxReconnectAttempts: 5
    };

    // =========================================
    // 1. WEBSOCKET ПОДКЛЮЧЕНИЕ
    // =========================================
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/lobby/${config.gameCode}/`;

        console.log('🔌 Connecting to WebSocket:', wsUrl);
        state.ws = new WebSocket(wsUrl);

        state.ws.onopen = () => {
            console.log('✅ WebSocket connected');
            state.reconnectAttempts = 0;
        };

        state.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };

        state.ws.onclose = () => {
            console.log('❌ WebSocket disconnected');
            // Попытка переподключения
            if (state.reconnectAttempts < state.maxReconnectAttempts) {
                state.reconnectAttempts++;
                const delay = Math.min(2000 * state.reconnectAttempts, 10000);
                console.log(`🔄 Reconnecting... (${state.reconnectAttempts}/${state.maxReconnectAttempts}) in ${delay}ms`);
                setTimeout(() => connectWebSocket(), delay);
            } else {
                showToast('⚠️ Потеряно соединение с сервером', 'warning');
            }
        };

        state.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    function handleWebSocketMessage(data) {
        switch (data.type) {
            case 'participants_list':
                // Инициализация списка участников (полный список при подключении)
                initializeParticipants(data.participants);
                break;

            case 'participant_joined':
                handleParticipantJoined(data.username, data.is_host);
                break;

            case 'participant_left':
                handleParticipantLeft(data.username);
                break;

            case 'game_started':
                handleGameStarted();
                break;
        }
    }

    function initializeParticipants(participants) {
        state.players.clear();
        els.playerList.innerHTML = '';

        participants.forEach(p => {
            state.players.add(p.username);
            addPlayerToList(p.username, p.is_host, false); // false = без анимации
        });

        updatePlayerCount();
        checkStartButton();
    }

    function handleParticipantJoined(username, isHost) {
        if (!state.players.has(username)) {
            state.players.add(username);
            addPlayerToList(username, isHost, true); // true = с анимацией
            updatePlayerCount();
            showToast(`🎉 ${username} присоединился!`, 'success');
            checkStartButton();
        }
    }

    function handleParticipantLeft(username) {
        if (state.players.has(username)) {
            state.players.delete(username);
            removePlayerFromList(username);
            updatePlayerCount();
            showToast(`${username} покинул лобби`, 'info');
        }
    }

    function handleGameStarted() {
        showToast('🚀 Игра начинается!', 'success');
        state.gameStarted = true;
        setTimeout(() => {
            window.location.href = `/quiz/play/${config.gameCode}/`;
        }, 2000);
    }

    // =========================================
    // 2. УПРАВЛЕНИЕ СПИСКОМ ИГРОКОВ
    // =========================================
    function addPlayerToList(username, isHost, animate = true) {
        const li = document.createElement('li');
        li.className = `player-item ${animate ? 'new' : ''}`;
        li.dataset.username = username;

        const avatar = isHost ? '👑' : '🎮';
        const role = isHost ? '<span class="player-role">Ведущий</span>' : '';

        li.innerHTML = `
            <span class="player-avatar">${avatar}</span>
            <span class="player-name">${username}</span>
            ${role}
        `;

        els.playerList.appendChild(li);

        // Убираем анимацию через 300мс
        if (animate) {
            setTimeout(() => li.classList.remove('new'), 300);
        }
    }

    function removePlayerFromList(username) {
        const item = els.playerList.querySelector(`[data-username="${username}"]`);
        if (item) {
            item.remove();
        }
    }

    function updatePlayerCount() {
        if (els.playerCount) {
            els.playerCount.textContent = state.players.size;
        }
    }

    function checkStartButton() {
        if (els.btnStart) {
            els.btnStart.disabled = state.players.size < config.minPlayers || state.gameStarted;
        }
    }

    // =========================================
    // 3. КОПИРОВАНИЕ КОДА КОМНАТЫ
    // =========================================
    function copyGameCode() {
        if (!config.gameCode) return;

        navigator.clipboard.writeText(config.gameCode).then(() => {
            showToast('📋 Код скопирован!', 'success');

            // Визуальная обратная связь
            const hintEl = els.codeSection.querySelector('.code-hint');
            const originalText = hintEl.textContent;
            hintEl.textContent = '✅ Скопировано!';
            setTimeout(() => {
                hintEl.textContent = originalText;
            }, 2000);
        }).catch(() => {
            showToast('❌ Не удалось скопировать', 'error');
        });
    }

    // =========================================
    // 4. ОБРАБОТКА КНОПОК
    // =========================================
    if (els.btnStart) {
        els.btnStart.addEventListener('click', async () => {
            if (state.players.size < config.minPlayers) {
                showToast(`Нужно минимум ${config.minPlayers} игрока`, 'warning');
                return;
            }

            state.gameStarted = true;
            els.btnStart.disabled = true;
            els.btnStart.innerHTML = '<span class="btn-icon">⏳</span> Запуск...';

            try {
                const response = await fetch(`/quiz/lobby/${config.gameCode}/start/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
                        'Content-Type': 'application/json'
                    }
                });

                const data = await response.json();
                if (data.success) {
                    showToast('🚀 Игра начинается!', 'success');
                } else {
                    showToast(data.error || 'Ошибка запуска игры', 'error');
                    els.btnStart.disabled = false;
                    els.btnStart.innerHTML = '<span class="btn-icon">🚀</span> Начать игру';
                }
            } catch (error) {
                console.error('Error starting game:', error);
                showToast('Произошла ошибка сети', 'error');
                els.btnStart.disabled = false;
                els.btnStart.innerHTML = '<span class="btn-icon">🚀</span> Начать игру';
            }
        });
    }

    if (els.btnSettings) {
        els.btnSettings.addEventListener('click', () => {
            showToast('⚙️ Настройки комнаты (заглушка)', 'info');
            // Здесь можно открыть модальное окно с настройками
        });
    }

    // =========================================
    // 5. ИНИЦИАЛИЗАЦИЯ
    // =========================================
    if (els.codeSection) {
        els.codeSection.addEventListener('click', copyGameCode);
    }

    // Подключаемся к WebSocket
    connectWebSocket();

    // Отправляем ping каждые 30 секунд для поддержания соединения
    setInterval(() => {
        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({type: 'ping'}));
        }
    }, 30000);

    // Обновляем состояние кнопок при загрузке
    checkStartButton();
});