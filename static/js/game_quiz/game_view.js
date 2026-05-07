document.addEventListener('DOMContentLoaded', () => {
    const els = {
        gameData: document.getElementById('game-data'),
        btnStart: document.getElementById('btn-start-game'),
        btnNext: document.getElementById('btn-next-question'),
        hostControls: document.getElementById('host-controls'),
        timerDisplay: document.getElementById('timer-display'),
        qNumber: document.getElementById('q-number'),
        qText: document.getElementById('q-text'),
        playersList: document.getElementById('players-list'),
        statusBadge: document.getElementById('game-status')
    };

    const config = {
        gameCode: els.gameData?.dataset.gameCode || '',
        isHost: els.gameData?.dataset.isHost === 'true'
    };

    let ws = null;
    let timerInterval = null;
    let timeLeft = 0;

    if (!config.isHost && els.hostControls) els.hostControls.style.display = 'none';

    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/game/${config.gameCode}/`;

        ws = new WebSocket(wsUrl);
        ws.onopen = () => console.log('✅ Game WS connected');
        ws.onmessage = (e) => handleGameMessage(JSON.parse(e.data));
        ws.onclose = () => console.log('❌ Game WS disconnected');
    }

    function handleGameMessage(data) {
        switch (data.type) {
            case 'game_started':
                els.statusBadge.textContent = '🟢 Игра идёт';
                els.statusBadge.style.background = '#e0ffe8';
                els.statusBadge.style.color = '#2ecc71';
                if (els.btnStart) els.btnStart.style.display = 'none';
                // Очищаем заглушку "Пока нет участников"
                const placeholder = els.playersList.querySelector('.rating-placeholder');
                if (placeholder) placeholder.remove();
                break;
            case 'question_update':
                els.qNumber.textContent = `Вопрос ${data.question_number} из ${data.total_questions}`;
                els.qText.textContent = data.text;
                startTimer(data.timer);
                // Сброс статусов
                document.querySelectorAll('.player-item').forEach(el => {
                    el.dataset.status = 'waiting';
                    const s = el.querySelector('.player-status');
                    const t = el.querySelector('.player-status-text');
                    if (s) {
                        s.textContent = '';
                    }
                    if (t) {
                        t.textContent = 'Ожидает ответа...';
                    }
                });
                break;
            case 'player_answer':
                updatePlayerStatus(data.username, 'answered');
                break;
            case 'leaderboard_update':
                updateRating(data.leaderboard);
                break;
            case 'question_ended':
                if (els.btnNext) {
                    els.btnNext.style.display = 'inline-flex';
                    els.btnNext.disabled = false;
                }
                break;
            case 'game_ended':
                els.statusBadge.textContent = '✅ Игра завершена';
                els.statusBadge.style.background = '#ffe0e0';
                els.statusBadge.style.color = '#e74c3c';
                break;
        }
    }

    function updatePlayerStatus(username, status) {
        const el = document.querySelector(`.player-item[data-username="${username}"]`);
        if (!el) return;
        el.dataset.status = status;
        const s = el.querySelector('.player-status');
        const t = el.querySelector('.player-status-text');
        if (status === 'answered') {
            if (s) s.textContent = '✅';
            if (t) {
                t.textContent = 'Ответил!';
                t.style.color = '#2ecc71';
            }
        } else {
            if (s) s.textContent = '⏳';
            if (t) {
                t.textContent = 'Ожидает ответа...';
                t.style.color = 'var(--text-gray)';
            }
        }
    }

    function updateRating(leaderboard) {
        const list = document.getElementById('rating-list');
        if (!list || !leaderboard) return;
        list.innerHTML = '';
        leaderboard.forEach((p, i) => {
            const pos = i + 1;
            const medal = pos === 1 ? '' : pos === 2 ? '' : pos === 3 ? '🥉' : `#${pos}`;
            const div = document.createElement('div');
            div.className = `rating-item ${pos <= 3 ? 'top-' + pos : ''}`;
            div.innerHTML = `
                <span class="rating-position">${medal}</span>
                <span class="rating-avatar">🎮</span>
                <div class="rating-info">
                    <span class="rating-name">${p.name}</span>
                    <span class="rating-score">${p.correct || 0} из ${p.total || 0}</span>
                </div>
                <span class="rating-points">${p.score || 0}</span>
            `;
            list.appendChild(div);
        });
    }

    function startTimer(seconds) {
        clearInterval(timerInterval);
        timeLeft = seconds;
        updateTimerDisplay(timeLeft);
        timerInterval = setInterval(() => {
            if (timeLeft > 0) {
                timeLeft--;
                updateTimerDisplay(timeLeft);
            } else {
                clearInterval(timerInterval);
            }
        }, 1000);
    }

    function updateTimerDisplay(sec) {
        const m = Math.floor(sec / 60).toString().padStart(2, '0');
        const s = (sec % 60).toString().padStart(2, '0');
        els.timerDisplay.textContent = `${m}:${s}`;
    }

    // Кнопки ведущего
    if (els.btnStart) {
        els.btnStart.addEventListener('click', () => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({action: 'start_game'}));
                els.btnStart.disabled = true;
            }
        });
    }
    if (els.btnNext) {
        els.btnNext.addEventListener('click', () => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({action: 'next_question'}));
                els.btnNext.style.display = 'none';
                els.btnNext.disabled = true;
            }
        });
    }

    connectWebSocket();
});