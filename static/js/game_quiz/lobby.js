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

    const btnDeleteGame = document.getElementById('btn-delete-game');

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

        state.ws = new WebSocket(wsUrl);

        state.ws.onopen = () => {
            state.reconnectAttempts = 0;
        };

        state.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'game_aborted') {
                alert('🛑 Ведущий удалил эту игровую комнату или все участники вышли.');
                window.location.href = '/';
                return;
            }
            handleWebSocketMessage(data);
        };

        state.ws.onclose = () => {
            // Попытка переподключения
            if (state.reconnectAttempts < state.maxReconnectAttempts) {
                state.reconnectAttempts++;
                const delay = Math.min(2000 * state.reconnectAttempts, 10000);
                setTimeout(() => connectWebSocket(), delay);
            } else {
                showToast('⚠️ Потеряно соединение с сервером', 'warning');
            }
        };
    }

    function handleWebSocketMessage(data) {

        switch (data.type) {
            case 'participants_list':
                // Инициализация списка участников (полный список при подключении)
                initializeParticipants(data.participants);
                break;

            case 'participant_joined':
                handleParticipantJoined(data);
                break;

            case 'participant_left':
                handleParticipantLeft(data);
                break;

            case 'go_game_page':
                handleGoGamePage();
                break;
        }
    }

    function initializeParticipants(participants) {
        state.players.clear();
        els.playerList.innerHTML = '';

        participants.forEach(p => {
            state.players.add(p.username);
            addPlayerToList(p, false); // false = без анимации
        });

        updatePlayerCount();
        checkStartButton();
    }

    function handleParticipantJoined(data) {
        if (!state.players.has(data.username)) {
            state.players.add(data.username);
            addPlayerToList(data, true);
            updatePlayerCount();
            showToast(`🎉 ${data.username} присоединился!`, 'success');
            checkStartButton();
        }
    }

    function handleParticipantLeft(data) {
        if (state.players.has(data.username)) {
            state.players.delete(data.username);
            removePlayerFromList(data.username);
            updatePlayerCount();
            showToast(`${data.username} покинул лобби`, 'info');
            checkStartButton()
        }
    }

    function handleGoGamePage() {
        showToast('🚀 Игра начинается! Переход в комнату...', 'success');
        state.gameStarted = true;
        setTimeout(() => {
            window.location.href = `/quiz/play/${config.gameCode}/`;
        }, 2000);
    }

    // =========================================
    // 2. УПРАВЛЕНИЕ СПИСКОМ ИГРОКОВ
    // =========================================
    function addPlayerToList(data, animate = true) {
        const li = document.createElement('li');
        li.className = `player-item ${animate ? 'new' : ''}`;
        li.dataset.username = data.username;

        const avatar = data.isHost ? '👑' : '🎮';
        const role = data.isHost ? '<span class="player-role">Ведущий</span>' : '';

        li.innerHTML = `
            <span class="player-avatar">${avatar}</span>
            <span class="player-name">${data.username}</span>
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
            // Проверка минимального количества игроков
            const currentPlayers = state.players.size || state.players.length;
            if (currentPlayers < config.minPlayers) {
                showToast(`Нужно минимум ${config.minPlayers} игрока`, 'warning');
                return;
            }

            // Блокируем кнопку
            els.btnStart.disabled = true;
            els.btnStart.innerHTML = '<span class="btn-icon">⏳</span> Запуск...';

            try {
                const csrfToken = document.querySelector('#csrf-form input[name="csrfmiddlewaretoken"]')?.value ||
                    document.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';

                const response = await fetch(`/quiz/lobby/${config.gameCode}/start/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'Content-Type': 'application/json'
                    }
                });

                const data = await response.json();

                if (data.success && data.redirect_url) {

                    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
                        state.ws.send(JSON.stringify({action: 'go_game_page'}));
                        els.btnStart.disabled = true;
                    }

                } else {
                    showToast(data.error || 'Ошибка запуска игры', 'error');
                    els.btnStart.disabled = false;
                    els.btnStart.innerHTML = '<span class="btn-icon">🚀</span> Начать игру';
                }
            } catch (error) {
                showToast('Произошла ошибка сети', 'error');
                els.btnStart.disabled = false;
                els.btnStart.innerHTML = '<span class="btn-icon">🚀</span> Начать игру';
            }
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

    // Обработка клика по кнопке "Отменить и удалить игру"
    if (btnDeleteGame) {
        btnDeleteGame.addEventListener('click', function () {
            if (confirm('Вы уверены, что хотите полностью удалить эту игру? Все подключенные игроки будут возвращены на главную страницу.')) {
                const csrfToken = document.querySelector('#csrf-form [name=csrfmiddlewaretoken]').value;
                const gameCode = document.getElementById('lobby-data').dataset.gameCode;

                fetch(`/quiz/lobby/${gameCode}/delete/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'Content-Type': 'application/json'
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // Ведущего после удаления перенаправляем на главную
                            window.location.href = '/';
                        } else {
                            alert('Ошибка при удалении игры: ' + data.error);
                        }
                    })
                    .catch(_ => {
                        alert('Произошла сетевая ошибка при попытке удалить игру.');
                    });
            }
        });
    }
});