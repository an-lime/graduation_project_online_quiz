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

    function getMedal(rank) {
        return rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : `#${rank}`;
    }

    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/game/${config.gameCode}/`;

        ws = new WebSocket(wsUrl);

        ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            handleGameMessage(data);
        };
    }

    function handleGameMessage(data) {
        switch (data.type) {
            case 'current_state':
                restoreGameState(data.state);
                break;
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
            case 'participant_left':
                removePlayerFromGame(data.vk_id);
                break;
            case 'game_aborted':
                renderGameAborted();
                break;
        }
    }

    function renderQuestion(data) {

        if (els.qNumber) els.qNumber.textContent = `Вопрос ${data.question_number} из ${data.total_questions}`;
        if (els.qText) els.qText.textContent = data.text;
        if (els.btnNext) els.btnNext.style.display = 'none';

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
            return;
        }

        const oldContainer = els.qArea?.querySelector('.answer-options');
        if (oldContainer) oldContainer.remove();

        if (!els.qArea) {
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

            if (data.is_last) {
                els.btnNext.innerHTML = '<span class="btn-icon">🏁</span> Подвести итоги';
            } else {
                els.btnNext.innerHTML = '<span class="btn-icon">➡️</span> Следующий вопрос';
            }
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
            const medal = getMedal(pos)
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
        if (els.statusBadge) {
            els.statusBadge.textContent = '🟢 Игра идёт';
            els.statusBadge.style.background = '#e0ffe8';
            els.statusBadge.style.color = '#2ecc71';
        }
        if (els.btnStart) els.btnStart.style.display = 'none';
    }

    function restoreGameState(state) {
        if (!state.is_running) return;

        handleGameStarted();

        if (state.current_idx >= 0 && state.current_idx < state.questions.length) {
            const q = state.questions[state.current_idx];
            const correctIdx = q.correctIndex !== undefined ? q.correctIndex : (q.correct_answer !== undefined ? q.correct_answer : -1);
            const isLast = state.current_idx === state.questions.length - 1;

            // 1. Восстанавливаем вопрос
            renderQuestion({
                question_number: state.current_idx + 1,
                total_questions: state.questions.length,
                text: q.question,
                options: q.options || q.answers || [],
                correct_index: correctIdx,
                explanation: q.explanation || q.hint || '',
                timer: 0 // таймер подхватится следующим тиком от сервера
            });

            // 2. Статусы игроков
            Object.values(state.participants).forEach(p => {
                if (p.answered_current) updatePlayerStatus(p.vk_id, 'answered');
            });

            // 3. Рейтинг
            const leaderboard = Object.values(state.participants)
                .filter(p => !p.is_host)
                .sort((a, b) => b.score - a.score)
                .map(p => ({
                    name: p.first_name ? `${p.first_name} ${p.last_name}` : p.username,
                    score: p.score,
                    correct: p.correct_count || 0,
                    total: p.total
                }));
            updateRating(leaderboard);

            // 4. ГЛАВНОЕ: Если вопрос уже завершен, принудительно рисуем итоги вопроса и кнопку
            if (!state.question_active) {
                renderQuestionEnd({
                    correct_index: correctIdx,
                    explanation: q.explanation || q.hint || '',
                    is_last: isLast
                });
            }
        }
    }

    function renderGameResults(data) {
        const modal = document.getElementById('results-modal');
        const list = document.getElementById('results-list');

        if (!modal || !list) return;

        // Скрываем панель управления ведущего, так как игра окончена
        if (els.hostControls) {
            els.hostControls.style.display = 'none';
        }

        // Если с бэкенда пришло название игры, обновляем его
        const gameNameEl = document.getElementById('results-game-name');
        if (gameNameEl && data.game_name) {
            gameNameEl.textContent = data.game_name;
        }

        // Очищаем старый список
        list.innerHTML = '';

        // Защита от пустых результатов (если никто не играл)
        if (!data.results || data.results.length === 0) {
            list.innerHTML = '<div class="results-row" style="justify-content: center;">Нет данных о результатах участников</div>';
            modal.style.display = 'flex';
            return;
        }

        // Рендерим таблицу
        data.results.forEach(player => {
            const row = document.createElement('div');
            row.className = `results-row player ${player.rank <= 3 ? 'top-' + player.rank : ''}`;

            const medal = getMedal(player.rank);

            row.innerHTML = `
                <span class="col-rank">${medal}</span>
                <span class="col-player">${player.name}</span>
                <span class="col-stats">${player.correct} / ${data.total_questions}</span>
                <span class="col-score">${player.score}</span>
            `;
            list.appendChild(row);
        });

        // Показываем модальное окно
        modal.style.display = 'flex';
    }

    // Функция для отображения модалки при преждевременном завершении
    function renderGameAborted() {
        const modal = document.getElementById('results-modal');
        const list = document.getElementById('results-list');
        const headerObj = document.querySelector('.results-header h2');
        const subtitleObj = document.getElementById('results-game-name');

        if (!modal || !list) return;

        if (els.hostControls) els.hostControls.style.display = 'none';

        if (headerObj) {
            headerObj.textContent = "🛑 Игра прервана!";
            headerObj.style.color = "#FF006E";
        }
        if (subtitleObj) subtitleObj.textContent = "Все игроки покинули сессию.";

        // 👇 1. СКРЫВАЕМ ШАПКУ ТАБЛИЦЫ 👇
        const tableHeader = document.querySelector('.results-row.header');
        if (tableHeader) tableHeader.style.display = 'none';

        // 👇 2. ДОБАВЛЯЕМ grid-column: 1 / -1 👇
        list.innerHTML = `
            <div style="grid-column: 1 / -1; justify-content: center; text-align: center; color: #e74c3c; font-weight: 600; padding: 20px;">
                Игра удалена, результаты не сохранены, так как не осталось ни одного участника.
            </div>
        `;

        const createNewBtn = document.querySelector('.results-footer .btn-secondary');
        if (createNewBtn) createNewBtn.style.display = 'none';

        modal.style.display = 'flex';
    }

    // Функция удаления игрока из списка на экране
    function removePlayerFromGame(vk_id) {
        // У тебя в game_view.html список участников рендерится с data-username="{{ vk_id }}"
        const playerEl = document.querySelector(`.player-item[data-username="${vk_id}"]`);

        if (playerEl) {
            // Красивая анимация исчезновения
            playerEl.style.transition = "all 0.3s ease";
            playerEl.style.opacity = "0";
            playerEl.style.transform = "scale(0.9)";

            // Удаляем из DOM после завершения анимации
            setTimeout(() => {
                playerEl.remove();
            }, 300);
        }
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