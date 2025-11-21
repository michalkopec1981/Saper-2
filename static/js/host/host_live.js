/**
 * HOST LIVE MODULE
 * Cały tryb Na Żywo
 * Funkcje: loadLiveSession, createLiveQuestion, startLiveQuestion, timer
 * Ekrany 1-5 trybu live
 *
 * Używa: window.socket, window.EVENT_ID
 * Eksportuje: loadLiveSession, saveLiveSettings, createLiveQuestion, startLiveQuestion
 */

document.addEventListener('DOMContentLoaded', function () {
    const socket = window.socket;

    let liveSession = null;
    let liveTimerInterval = null;
    let activeQuestionId = null;

    // =====================================================================
    // LOAD LIVE SESSION
    // =====================================================================
    async function loadLiveSession() {
        try {
            const response = await fetch('/api/host/live/session');
            const data = await response.json();
            liveSession = data;

            const enabledCheckbox = document.getElementById('live-enabled');
            const statusBadge = document.getElementById('live-status');
            const separateScorePoolCheckbox = document.getElementById('live-separate-score-pool');

            if (enabledCheckbox) {
                enabledCheckbox.checked = data.is_enabled;
                statusBadge.textContent = data.is_enabled ? 'Aktywna' : 'Nieaktywna';
                statusBadge.className = data.is_enabled ? 'badge bg-success' : 'badge bg-secondary';
            }

            if (separateScorePoolCheckbox) {
                separateScorePoolCheckbox.checked = data.separate_score_pool || false;
            }

            const resultMode = data.result_mode || 'auto';
            const resultModeRadio = document.getElementById(`live-result-${resultMode}`);
            if (resultModeRadio) {
                resultModeRadio.checked = true;
            }

            if (data.qr_code) {
                const qrContainer = document.getElementById('live-qr-code');
                if (qrContainer && typeof QRCode !== 'undefined') {
                    qrContainer.innerHTML = '';
                    const liveUrl = `${window.location.origin}/live/${window.EVENT_ID}/${data.qr_code}`;
                    new QRCode(qrContainer, {
                        text: liveUrl,
                        width: 200,
                        height: 200
                    });
                }

                const screen5Link = document.getElementById('live-screen5-link');
                if (screen5Link) {
                    const screen5Url = `${window.location.origin}/live/screen5/${window.EVENT_ID}`;
                    screen5Link.href = screen5Url;
                    screen5Link.textContent = screen5Url;
                }
            }

            const backupQRBtn = document.getElementById('live-backup-qr-btn');
            if (backupQRBtn) {
                backupQRBtn.disabled = !data.backup_qr_code;
            }

            loadLiveQuestions();
        } catch (error) {
            console.error('Error loading live session:', error);
        }
    }

    // =====================================================================
    // SAVE LIVE SETTINGS
    // =====================================================================
    async function saveLiveSettings() {
        const enabled = document.getElementById('live-enabled').checked;
        const separateScorePool = document.getElementById('live-separate-score-pool').checked;
        const resultMode = document.querySelector('input[name="live-result-mode"]:checked').value;

        try {
            const response = await fetch('/api/host/live/session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    is_enabled: enabled,
                    separate_score_pool: separateScorePool,
                    result_mode: resultMode
                })
            });

            if (response.ok) {
                console.log('Ustawienia zapisane');
                loadLiveSession();
            } else {
                alert('Błąd zapisu ustawień');
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            alert('Błąd zapisu ustawień: ' + error.message);
        }
    }

    // =====================================================================
    // EVENT LISTENERS - SETTINGS
    // =====================================================================
    document.getElementById('live-enabled')?.addEventListener('change', function (e) {
        const statusBadge = document.getElementById('live-status');
        if (e.target.checked) {
            statusBadge.textContent = 'Aktywna';
            statusBadge.className = 'badge bg-success';
        } else {
            statusBadge.textContent = 'Nieaktywna';
            statusBadge.className = 'badge bg-secondary';
        }
        saveLiveSettings();
    });

    document.getElementById('live-separate-score-pool')?.addEventListener('change', saveLiveSettings);

    document.querySelectorAll('input[name="live-result-mode"]').forEach(radio => {
        radio.addEventListener('change', saveLiveSettings);
    });

    // =====================================================================
    // SCREEN 5 BUTTON
    // =====================================================================
    document.getElementById('live-show-screen5-btn')?.addEventListener('click', function () {
        const link = document.getElementById('live-screen5-link').href;
        if (link && link !== '#') {
            window.open(link, '_blank');
        }
    });

    // =====================================================================
    // BACKUP QR BUTTONS
    // =====================================================================
    document.getElementById('live-generate-backup-qr-btn')?.addEventListener('click', async function () {
        try {
            const response = await fetch('/api/host/live/backup-qr/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.ok) {
                alert('Zapasowy kod QR został wygenerowany!');
                loadLiveSession();
            } else {
                alert('Błąd generowania zapasowego kodu QR');
            }
        } catch (error) {
            console.error('Error generating backup QR:', error);
            alert('Błąd: ' + error.message);
        }
    });

    document.getElementById('live-backup-qr-btn')?.addEventListener('click', function () {
        if (liveSession && liveSession.backup_qr_code) {
            const liveUrl = `${window.location.origin}/live/${window.EVENT_ID}/${liveSession.backup_qr_code}`;
            window.open(`/player_qr_preview/${window.EVENT_ID}?url=${encodeURIComponent(liveUrl)}&title=Tryb Na Żywo (Zapasowy)`, '_blank');
        }
    });

    // =====================================================================
    // SHOW STATISTICS BUTTON
    // =====================================================================
    document.getElementById('live-show-statistics-btn')?.addEventListener('click', async function () {
        if (!activeQuestionId) {
            alert('Brak zakończonego pytania do wyświetlenia statystyk');
            return;
        }

        try {
            const response = await fetch(`/api/host/live/question/${activeQuestionId}/show-statistics`, {
                method: 'POST'
            });

            if (response.ok) {
                alert('Statystyki zostały wysłane na ekran 5');
            } else {
                alert('Błąd wyświetlania statystyk');
            }
        } catch (error) {
            console.error('Error showing statistics:', error);
            alert('Błąd: ' + error.message);
        }
    });

    // =====================================================================
    // DYNAMIC ANSWER FIELDS
    // =====================================================================
    document.getElementById('live-add-answer-btn')?.addEventListener('click', function () {
        const container = document.getElementById('live-answers-container');
        const currentCount = container.querySelectorAll('.live-answer-item').length;
        const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

        if (currentCount < 26) {
            const newLetter = letters[currentCount];
            const newItem = document.createElement('div');
            newItem.className = 'input-group mb-2 live-answer-item';
            newItem.innerHTML = `
                <span class="input-group-text">Odpowiedź ${newLetter}</span>
                <input type="text" class="form-control live-answer-input" placeholder="Opcjonalnie">
                <div class="input-group-text">
                    <input class="form-check-input live-correct-checkbox mt-0" type="checkbox" title="Poprawna odpowiedź">
                    <span class="ms-2 small">Poprawna</span>
                </div>
                <button class="btn btn-danger live-remove-answer-btn" type="button">×</button>
            `;

            const removeBtn = newItem.querySelector('.live-remove-answer-btn');
            removeBtn.addEventListener('click', function () {
                newItem.remove();
                updateLiveAnswerLabels();
                updateLiveRemoveButtons();
            });

            container.appendChild(newItem);
            updateLiveRemoveButtons();
        }
    });

    function updateLiveAnswerLabels() {
        const items = document.querySelectorAll('#live-answers-container .live-answer-item');
        const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
        items.forEach((item, index) => {
            const label = item.querySelector('.input-group-text');
            if (label) {
                label.textContent = `Odpowiedź ${letters[index]}`;
            }
        });
    }

    function updateLiveRemoveButtons() {
        const items = document.querySelectorAll('#live-answers-container .live-answer-item');
        items.forEach((item) => {
            const removeBtn = item.querySelector('.live-remove-answer-btn');
            if (removeBtn) {
                if (items.length > 2) {
                    removeBtn.style.display = 'block';
                    if (!removeBtn.hasAttribute('data-listener')) {
                        removeBtn.setAttribute('data-listener', 'true');
                        removeBtn.addEventListener('click', function () {
                            item.remove();
                            updateLiveAnswerLabels();
                            updateLiveRemoveButtons();
                        });
                    }
                } else {
                    removeBtn.style.display = 'none';
                }
            }
        });
    }

    // =====================================================================
    // CREATE LIVE QUESTION
    // =====================================================================
    async function createLiveQuestion() {
        const questionText = document.getElementById('live-new-question-text').value;
        const timeLimit = parseInt(document.getElementById('live-new-time-limit').value);

        const answerItems = document.querySelectorAll('#live-answers-container .live-answer-item');
        const options = {};
        const correctAnswers = [];
        const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

        answerItems.forEach((item, index) => {
            const input = item.querySelector('.live-answer-input');
            const checkbox = item.querySelector('.live-correct-checkbox');
            const letter = letters[index];

            if (input && input.value.trim()) {
                options[`option_${letter.toLowerCase()}`] = input.value.trim();

                if (checkbox && checkbox.checked) {
                    correctAnswers.push(letter);
                }
            }
        });

        try {
            const response = await fetch('/api/host/live/question', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question_text: questionText,
                    ...options,
                    correct_answers: correctAnswers,
                    time_limit: timeLimit
                })
            });

            if (response.ok) {
                console.log('Pytanie dodane');
                document.getElementById('live-new-question-text').value = '';
                document.getElementById('live-new-time-limit').value = '30';

                const container = document.getElementById('live-answers-container');
                container.innerHTML = `
                    <div class="input-group mb-2 live-answer-item">
                        <span class="input-group-text">Odpowiedź A</span>
                        <input type="text" class="form-control live-answer-input" placeholder="Opcjonalnie">
                        <div class="input-group-text">
                            <input class="form-check-input live-correct-checkbox mt-0" type="checkbox" title="Poprawna odpowiedź">
                            <span class="ms-2 small">Poprawna</span>
                        </div>
                        <button class="btn btn-danger live-remove-answer-btn" type="button" style="display: none;">×</button>
                    </div>
                    <div class="input-group mb-2 live-answer-item">
                        <span class="input-group-text">Odpowiedź B</span>
                        <input type="text" class="form-control live-answer-input" placeholder="Opcjonalnie">
                        <div class="input-group-text">
                            <input class="form-check-input live-correct-checkbox mt-0" type="checkbox" title="Poprawna odpowiedź">
                            <span class="ms-2 small">Poprawna</span>
                        </div>
                        <button class="btn btn-danger live-remove-answer-btn" type="button" style="display: none;">×</button>
                    </div>
                `;
                updateLiveRemoveButtons();

                loadLiveQuestions();
            } else {
                const data = await response.json();
                alert('Błąd: ' + (data.error || 'Nie udało się dodać pytania'));
            }
        } catch (error) {
            console.error('Error creating question:', error);
            alert('Błąd tworzenia pytania: ' + error.message);
        }
    }

    // =====================================================================
    // LOAD LIVE QUESTIONS
    // =====================================================================
    async function loadLiveQuestions() {
        try {
            const response = await fetch('/api/host/live/questions');
            const data = await response.json();
            const container = document.getElementById('live-questions-list');

            if (data.questions && data.questions.length > 0) {
                container.innerHTML = data.questions.map(q => {
                    const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
                    let optionsHtml = '';
                    for (let i = 0; i < letters.length; i++) {
                        const letter = letters[i].toLowerCase();
                        const optionKey = `option_${letter}`;
                        if (q[optionKey]) {
                            optionsHtml += `<small>${letters[i]}: ${q[optionKey]}</small><br>`;
                        }
                    }

                    let correctAnswersHtml = '';
                    if (q.is_revealed && q.correct_answer) {
                        correctAnswersHtml = `<br><small class="text-success">Poprawna: ${q.correct_answer} (${q.correct_answers || 0} poprawnych)</small>`;
                    }

                    return `
                        <div class="card mb-2 ${q.is_active ? 'border-warning' : ''}">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-start">
                                    <div class="flex-grow-1">
                                        <p class="mb-1"><strong>${q.question_text || '(Pytanie czytane ze sceny)'}</strong></p>
                                        ${optionsHtml}
                                        <small class="text-muted">Limit: ${q.time_limit}s | Odpowiedzi: ${q.total_answers || 0}</small>
                                        ${correctAnswersHtml}
                                    </div>
                                    <div class="btn-group-vertical ms-2">
                                        ${!q.is_active && !q.is_revealed ? `
                                            <button class="btn btn-sm btn-success" onclick="startLiveQuestion(${q.id})">▶ Start</button>
                                        ` : ''}
                                        ${q.is_active ? `<span class="badge bg-warning">Aktywne</span>` : ''}
                                        ${q.is_revealed ? `<span class="badge bg-info">Zakończone</span>` : ''}
                                        <button class="btn btn-sm btn-danger" onclick="deleteLiveQuestion(${q.id})">🗑</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                container.innerHTML = '<p class="text-muted text-center">Brak pytań. Dodaj nowe pytanie powyżej.</p>';
            }
        } catch (error) {
            console.error('Error loading questions:', error);
        }
    }

    // =====================================================================
    // START LIVE QUESTION
    // =====================================================================
    async function startLiveQuestion(questionId) {
        try {
            const response = await fetch(`/api/host/live/question/${questionId}/start`, {
                method: 'POST'
            });

            if (response.ok) {
                activeQuestionId = questionId;
                console.log('Pytanie uruchomione');
                loadLiveQuestions();
                showActiveQuestionPanel(questionId);
                startLiveTimer();
            } else {
                alert('Błąd uruchamiania pytania');
            }
        } catch (error) {
            console.error('Error starting question:', error);
            alert('Błąd uruchamiania pytania: ' + error.message);
        }
    }

    // =====================================================================
    // ACTIVE QUESTION PANEL
    // =====================================================================
    async function showActiveQuestionPanel(questionId) {
        try {
            const response = await fetch('/api/host/live/questions');
            const data = await response.json();
            const question = data.questions.find(q => q.id === questionId);

            if (!question) return;

            const questionTextEl = document.getElementById('live-active-q-text');
            if (questionTextEl) {
                questionTextEl.textContent = question.question_text || '(Pytanie czytane ze sceny)';
            }

            const optionsEl = document.getElementById('live-active-options');
            if (optionsEl) {
                const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
                let optionsHtml = '';
                for (let i = 0; i < letters.length; i++) {
                    const letter = letters[i].toLowerCase();
                    const optionKey = `option_${letter}`;
                    if (question[optionKey]) {
                        optionsHtml += `<div><strong>${letters[i]}:</strong> ${question[optionKey]}</div>`;
                    }
                }
                optionsEl.innerHTML = optionsHtml;
            }

            const buttonsContainer = document.getElementById('live-reveal-buttons');
            if (buttonsContainer) {
                const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
                let buttonsHtml = '';
                for (let i = 0; i < letters.length; i++) {
                    const letter = letters[i].toLowerCase();
                    const optionKey = `option_${letter}`;
                    if (question[optionKey]) {
                        buttonsHtml += `<button type="button" class="btn btn-outline-primary live-reveal-btn" data-answer="${letters[i]}">${letters[i]}</button>`;
                    }
                }
                buttonsContainer.innerHTML = buttonsHtml;

                const selectedAnswers = new Set();
                buttonsContainer.querySelectorAll('.live-reveal-btn').forEach(btn => {
                    btn.addEventListener('click', function () {
                        const answer = this.dataset.answer;
                        if (selectedAnswers.has(answer)) {
                            selectedAnswers.delete(answer);
                            this.classList.remove('btn-success');
                            this.classList.add('btn-outline-primary');
                        } else {
                            selectedAnswers.add(answer);
                            this.classList.remove('btn-outline-primary');
                            this.classList.add('btn-success');
                        }
                    });
                });

                const revealBtn = document.createElement('button');
                revealBtn.className = 'btn btn-danger w-100 mt-2';
                revealBtn.textContent = 'Ujawnij wybrane odpowiedzi';
                revealBtn.onclick = function () {
                    if (selectedAnswers.size === 0) {
                        alert('Wybierz przynajmniej jedną poprawną odpowiedź');
                        return;
                    }
                    revealAnswers(Array.from(selectedAnswers));
                };
                buttonsContainer.appendChild(revealBtn);
            }

            const card = document.getElementById('live-active-question-card');
            card.style.display = 'block';
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } catch (error) {
            console.error('Error showing active question panel:', error);
        }
    }

    function hideActiveQuestionPanel() {
        const card = document.getElementById('live-active-question-card');
        card.style.display = 'none';
        if (liveTimerInterval) {
            clearInterval(liveTimerInterval);
            liveTimerInterval = null;
        }
    }

    // =====================================================================
    // LIVE TIMER
    // =====================================================================
    function startLiveTimer() {
        if (liveTimerInterval) {
            clearInterval(liveTimerInterval);
        }

        let timeRemaining = 30;
        const timerDisplay = document.getElementById('live-timer-display');

        liveTimerInterval = setInterval(() => {
            timeRemaining--;
            if (timerDisplay) {
                timerDisplay.textContent = timeRemaining;
            }

            if (timeRemaining <= 0) {
                clearInterval(liveTimerInterval);
                liveTimerInterval = null;
            }
        }, 1000);
    }

    // =====================================================================
    // REVEAL ANSWERS
    // =====================================================================
    async function revealAnswer(answer) {
        return revealAnswers([answer]);
    }

    async function revealAnswers(answers) {
        if (!activeQuestionId) return;

        try {
            const response = await fetch(`/api/host/live/question/${activeQuestionId}/reveal`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    correct_answer: answers.join(','),
                    correct_answers: answers
                })
            });

            if (response.ok) {
                console.log(`Poprawne odpowiedzi: ${answers.join(', ')}`);
                activeQuestionId = null;
                hideActiveQuestionPanel();
                loadLiveQuestions();
            } else {
                alert('Błąd ujawniania odpowiedzi');
            }
        } catch (error) {
            console.error('Error revealing answer:', error);
            alert('Błąd ujawniania odpowiedzi: ' + error.message);
        }
    }

    // =====================================================================
    // DELETE LIVE QUESTION
    // =====================================================================
    async function deleteLiveQuestion(questionId) {
        if (!confirm('Czy na pewno chcesz usunąć to pytanie?')) return;

        try {
            const response = await fetch(`/api/host/live/question/${questionId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                console.log('Pytanie usunięte');
                loadLiveQuestions();
            } else {
                alert('Błąd usuwania pytania');
            }
        } catch (error) {
            console.error('Error deleting question:', error);
            alert('Błąd usuwania pytania: ' + error.message);
        }
    }

    // =====================================================================
    // OPEN LIVE QR PREVIEW
    // =====================================================================
    function openLiveQRPreview() {
        if (liveSession && liveSession.qr_code) {
            const liveUrl = `${window.location.origin}/live/${window.EVENT_ID}/${liveSession.qr_code}`;
            window.open(`/player_qr_preview/${window.EVENT_ID}?url=${encodeURIComponent(liveUrl)}&title=Tryb Na Żywo`, '_blank');
        }
    }

    // =====================================================================
    // SEND TO SCREEN 5
    // =====================================================================
    document.getElementById('live-send-to-screen5-btn')?.addEventListener('click', async () => {
        const btn = document.getElementById('live-send-to-screen5-btn');

        btn.disabled = true;
        btn.textContent = 'Wysyłanie...';

        try {
            if (!liveSession || !liveSession.qr_code) {
                throw new Error('Brak sesji live. Upewnij się że tryb live jest włączony.');
            }

            const liveUrl = `${window.location.origin}/live/${window.EVENT_ID}/${liveSession.qr_code}`;

            const response = await fetch('/api/display/screen5/send_qr', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: 'live',
                    url: liveUrl,
                    description: 'Dołącz do trybu live'
                })
            });

            if (!response.ok) {
                throw new Error('Błąd wysyłania kodu QR');
            }

            alert('Kod QR został wysłany na ekran 5!');
        } catch (error) {
            alert('Błąd: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Wyślij kod na ekran numer 5';
        }
    });

    // =====================================================================
    // SOCKET LISTENERS
    // =====================================================================
    if (socket) {
        socket.on('live_question_started', function (data) {
            console.log('Live question started:', data);
            loadLiveQuestions();
        });

        socket.on('live_answer_revealed', function (data) {
            console.log('Live answer revealed:', data);
            loadLiveQuestions();
        });

        socket.on('live_questions_reset', function (data) {
            console.log('Live questions reset by admin');
            loadLiveQuestions();
            hideActiveQuestionPanel();
        });
    }

    // =====================================================================
    // TAB EVENT LISTENER
    // =====================================================================
    document.querySelector('button[data-bs-target="#live"]')?.addEventListener('click', loadLiveSession);

    // =====================================================================
    // INITIALIZE
    // =====================================================================
    loadLiveSession();

    // =====================================================================
    // EXPORTS
    // =====================================================================
    window.loadLiveSession = loadLiveSession;
    window.saveLiveSettings = saveLiveSettings;
    window.createLiveQuestion = createLiveQuestion;
    window.startLiveQuestion = startLiveQuestion;
    window.deleteLiveQuestion = deleteLiveQuestion;
    window.revealAnswer = revealAnswer;
    window.revealAnswers = revealAnswers;
    window.openLiveQRPreview = openLiveQRPreview;
});
