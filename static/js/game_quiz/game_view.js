// static/js/game_quiz/game_view.js
document.addEventListener('DOMContentLoaded', () => {
    const els = {
        gameData: document.getElementById('game-data'),
        btnStart: document.getElementById('btn-start-game'),
        btnNext: document.getElementById('btn-next-question'),
        hostControls: document.getElementById('host-controls'),
        timerDisplay: document.getElementById('timer-display'),
        qNumber: document.getElementById('q-number'),
        qText: document.getElementById('q-text'),
        qArea: document.getElementById('question-area'),
        playersList: document.getElementById('players-list'),
        ratingList: document.getElementById('rating-list'),
        statusBadge: document.getElementById('game-status'),
        qResult: document.getElementById('question-result')
    };

    const config = {
        gameCode: els.gameData?.dataset.gameCode || '',
        isHost: els.gameData?.dataset.isHost === 'true'
    };

    let ws = null;
    let timerInterval = null;
    let timeLeft = 0;
    let currentOptions = [];
    let currentCorrectIndex = -1;
    let currentExplanation = '';

    if (!config.isHost && els.hostControls) {
        els.hostControls.style.display = 'none';
    }

    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/game/${config.gameCode}/`;

        console.log('🔌 Connecting to:', wsUrl);
        ws = new WebSocket(wsUrl);

        ws.onopen = () => console.log('✅ Game WS connected');
        ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            console.log('📩 Received:', data.type);
            handleGameMessage(data);
        };
        ws.onclose = () => console.log('❌ Game WS disconnected');
    }

    function handleGameMessage(data) {
        console.log('🔄 Handling:', data.type);
        switch (data.type) {
            case 'game_started':
                handleGameStarted();
                break;
            case 'question_update':
                renderQuestion(data);
                break;
            case 'timer_update':
                updateTimerDisplay(data.seconds_left);
                break;
            case 'player_answer':
                updatePlayerStatus(data.vk_id, 'answered');
                break;
            case 'leaderboard_update':
                updateRating(data.leaderboard);
                break;
            case 'question_ended':
                renderQuestionEnd(data);
                break;
            case 'game_ended':
                renderGameResults(data);
                break;
        }
    }

    function renderQuestion(data) {
        console.log('📝 Rendering question:', data.question_number);

        if (els.qNumber) els.qNumber.textContent = `Вопрос ${data.question_number} из ${data.total_questions}`;
        if (els.qText) els.qText.textContent = data.text;

        // Сохраняем данные
        currentOptions = data.options || [];
        currentCorrectIndex = data.correct_index !== undefined ? data.correct_index : -1;
        currentExplanation = data.explanation || '';

        renderAnswerOptions(data.options);
        hideQuestionResult();

        if (data.timer) startTimer(data.timer);

        document.querySelectorAll('.player-item').forEach(el => {
            el.dataset.status = 'waiting';
            const s = el.querySelector('.player-status');
            const t = el.querySelector('.player-status-text');
            if (s) s.textContent = '⏳';
            if (t) t.textContent = 'Ожидает ответа...';
        });
    }

    function renderAnswerOptions(options) {
        if (!options || options.length === 0) {
            console.warn('⚠️ No options to render');
            return;
        }

        const oldContainer = els.qArea?.querySelector('.answer-options');
        if (oldContainer) oldContainer.remove();

        if (!els.qArea) {
            console.error('❌ qArea not found');
            return;
        }

        const container = document.createElement('div');
        container.className = 'answer-options';
        container.style.cssText = `
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin-top: 20px;
            width: 100%;
            max-width: 600px;
        `;

        options.forEach((opt, idx) => {
            const btn = document.createElement('button');
            btn.className = 'answer-option';
            btn.textContent = opt;
            btn.dataset.index = idx;
            btn.style.cssText = `
                padding: 12px 16px;
                background: white;
                border: 3px solid #ddd;
                border-radius: 12px;
                font-weight: 600;
                font-size: 1rem;
                cursor: default;
                transition: all 0.2s;
                text-align: left;
            `;
            container.appendChild(btn);
        });

        if (els.qText) {
            els.qText.insertAdjacentElement('afterend', container);
            console.log('✅ Options rendered');
        }
    }

    function hideQuestionResult() {
        if (els.qResult) {
            els.qResult.style.display = 'none';
            els.qResult.innerHTML = '';
        }
        document.querySelectorAll('.answer-option').forEach(btn => {
            btn.style.borderColor = '#ddd';
            btn.style.background = 'white';
            btn.style.opacity = '1';
            btn.innerHTML = btn.textContent;
            btn.disabled = false;
        });
    }

    function renderQuestionEnd(data) {
        console.log('🏁 Question ended');

        const correctIdx = data.correct_index !== undefined ? data.correct_index : currentCorrectIndex;
        const explanation = data.explanation || currentExplanation;
        const correctText = currentOptions[correctIdx] || 'Неизвестно';

        document.querySelectorAll('.answer-option').forEach(btn => {
            const idx = parseInt(btn.dataset.index);
            if (idx === correctIdx) {
                btn.style.borderColor = '#2ecc71';
                btn.style.background = '#e8f8f0';
                btn.style.color = '#27ae60';
                btn.innerHTML = `✅ ${btn.textContent}`;
            } else {
                btn.style.opacity = '0.5';
            }
            btn.disabled = true;
        });

        if (els.qResult) {
            els.qResult.innerHTML = `
                <div style="margin-bottom: 12px;">
                    <strong style="color: #27ae60;">✅ Правильный ответ:</strong> 
                    <span style="font-weight: 600;">${correctText}</span>
                </div>
                ${explanation ?
                `<div style="
                        padding: 12px 16px;
                        background: #f9f9f9;
                        border-left: 4px solid var(--primary);
                        border-radius: 0 8px 8px 0;
                    ">
                        💡 <strong>Пояснение:</strong> ${explanation}
                    </div>`
                : ''}
            `;
            els.qResult.style.display = 'block';
        }

        if (els.btnNext && config.isHost) {
            els.btnNext.style.display = 'inline-flex';
            els.btnNext.disabled = false;
        }

        if (els.timerDisplay) {
            els.timerDisplay.textContent = '⏱ Завершено';
            els.timerDisplay.style.background = '#95a5a6';
        }
        clearInterval(timerInterval);
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
        if (!els.timerDisplay) return;
        const m = Math.floor(sec / 60).toString().padStart(2, '0');
        const s = (sec % 60).toString().padStart(2, '0');
        els.timerDisplay.textContent = `${m}:${s}`;
        if (sec <= 10 && sec > 0) {
            els.timerDisplay.style.background = '#e74c3c';
        } else if (sec === 0) {
            els.timerDisplay.style.background = '#95a5a6';
        }
    }

    function updatePlayerStatus(vk_id, status) {
        const el = document.querySelector(`.player-item[data-username="${vk_id}"]`);
        if (!el) return;
        el.dataset.status = status;
        const s = el.querySelector('.player-status');
        const t = el.querySelector('.player-status-text');
        if (status === 'answered') {
            if (s) {
                s.textContent = '✅';
                s.style.color = '#2ecc71';
            }
            if (t) {
                t.textContent = 'Ответил!';
                t.style.color = '#2ecc71';
            }
        }
    }

    function updateRating(leaderboard) {
        if (!els.ratingList) return;
        if (!leaderboard || leaderboard.length === 0) {
            els.ratingList.innerHTML = '<div class="rating-placeholder"><p>Рейтинг появится после начала игры</p></div>';
            return;
        }
        els.ratingList.innerHTML = '';
        leaderboard.forEach((p, i) => {
            const pos = i + 1;
            const medal = pos === 1 ? '🥇' : pos === 2 ? '🥈' : pos === 3 ? '🥉' : `#${pos}`;
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
            els.ratingList.appendChild(div);
        });
    }

    function handleGameStarted() {
        console.log('🟢 Game started');
        if (els.statusBadge) {
            els.statusBadge.textContent = '🟢 Игра идёт';
            els.statusBadge.style.background = '#e0ffe8';
            els.statusBadge.style.color = '#2ecc71';
        }
        if (els.btnStart) els.btnStart.style.display = 'none';
    }

    function renderGameResults(data) {
        const modal = document.getElementById('results-modal');
        const list = document.getElementById('results-list');
        if (!modal || !list) return;

        list.innerHTML = '';
        data.results.forEach(player => {
            const row = document.createElement('div');
            row.className = `results-row player ${player.rank <= 3 ? 'top-' + player.rank : ''}`;
            const medal = player.rank === 1 ? '🥇' : player.rank === 2 ? '🥈' : player.rank === 3 ? '🥉' : `#${player.rank}`;
            row.innerHTML = `
                <span class="col-rank">${medal}</span>
                <span class="col-player">${player.name}</span>
                <span class="col-stats">${player.correct}/${data.total_questions}</span>
                <span class="col-score">${player.score}</span>
            `;
            list.appendChild(row);
        });
        modal.style.display = 'flex';
    }

    if (els.btnStart && config.isHost) {
        els.btnStart.addEventListener('click', () => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({action: 'start_game'}));
                els.btnStart.disabled = true;
            }
        });
    }

    if (els.btnNext && config.isHost) {
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