/**
 * HOST FEATURES MODULE
 * Hasło, AI, AR, Foto, Głosowanie, Wyświetlacz, Dark Mode
 *
 * Używa: window.translations, window.currentLanguage, window.socket, window.EVENT_ID
 * Eksportuje: loadPasswordState, setPassword, revealSelectedLetters, loadAICategories, loadHostPhotoGallery
 */

document.addEventListener('DOMContentLoaded', function () {
    const socket = window.socket;

    // =====================================================================
    // PASSWORD FUNCTIONS
    // =====================================================================
    async function loadPasswordState() {
        try {
            const response = await fetch('/api/host/password');
            const data = await response.json();

            const display = document.getElementById('current-password-display');
            if (display && data.password) {
                display.textContent = data.password.split('').join(' ');
            }

            const letterCheckboxes = document.querySelectorAll('#letter-checkboxes input');
            letterCheckboxes.forEach(checkbox => {
                const index = parseInt(checkbox.dataset.index);
                if (data.revealed_letters && data.revealed_letters[index]) {
                    checkbox.checked = true;
                } else {
                    checkbox.checked = false;
                }
            });
        } catch (error) {
            console.error('Error loading password state:', error);
        }
    }

    async function setPassword() {
        const passwordInput = document.getElementById('password-input');
        const password = passwordInput.value.trim().toUpperCase();

        if (!password) {
            alert('Proszę wprowadzić hasło');
            return;
        }

        try {
            const response = await fetch('/api/host/password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password })
            });

            if (!response.ok) {
                throw new Error('Błąd ustawiania hasła');
            }

            const display = document.getElementById('current-password-display');
            if (display) {
                display.textContent = password.split('').join(' ');
            }

            const container = document.getElementById('letter-checkboxes');
            if (container) {
                container.innerHTML = '';
                for (let i = 0; i < password.length; i++) {
                    const div = document.createElement('div');
                    div.className = 'form-check form-check-inline';
                    div.innerHTML = `
                        <input class="form-check-input" type="checkbox" id="letter-${i}" data-index="${i}">
                        <label class="form-check-label" for="letter-${i}">${password[i]}</label>
                    `;
                    container.appendChild(div);
                }
            }

            passwordInput.value = '';
            alert('Hasło zostało ustawione');
        } catch (error) {
            alert('Błąd: ' + error.message);
        }
    }

    async function revealSelectedLetters() {
        const checkboxes = document.querySelectorAll('#letter-checkboxes input:checked');
        const indices = Array.from(checkboxes).map(cb => parseInt(cb.dataset.index));

        if (indices.length === 0) {
            alert('Wybierz przynajmniej jedną literę do odsłonięcia');
            return;
        }

        try {
            const response = await fetch('/api/host/password/reveal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ indices })
            });

            if (!response.ok) {
                throw new Error('Błąd odsłaniania liter');
            }

            alert('Litery zostały odsłonięte');
        } catch (error) {
            alert('Błąd: ' + error.message);
        }
    }

    document.getElementById('set-password-btn')?.addEventListener('click', setPassword);
    document.getElementById('reveal-letters-btn')?.addEventListener('click', revealSelectedLetters);

    // =====================================================================
    // AI FUNCTIONS
    // =====================================================================
    async function loadAICategories() {
        try {
            const response = await fetch('/api/host/ai/categories');
            const data = await response.json();

            const container = document.getElementById('ai-categories-list');
            if (!container) return;

            if (data.categories && data.categories.length > 0) {
                container.innerHTML = data.categories.map(cat => `
                    <div class="form-check">
                        <input class="form-check-input ai-category-checkbox" type="checkbox"
                               id="ai-cat-${cat.id}" data-id="${cat.id}"
                               ${cat.enabled ? 'checked' : ''}>
                        <label class="form-check-label" for="ai-cat-${cat.id}">
                            ${cat.name} <small class="text-muted">(${cat.question_count} pytań)</small>
                        </label>
                    </div>
                `).join('');

                document.querySelectorAll('.ai-category-checkbox').forEach(checkbox => {
                    checkbox.addEventListener('change', async (e) => {
                        const catId = e.target.dataset.id;
                        const enabled = e.target.checked;

                        try {
                            await fetch('/api/host/ai/categories', {
                                method: 'PUT',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ category_id: catId, enabled })
                            });
                        } catch (error) {
                            console.error('Error updating AI category:', error);
                        }
                    });
                });
            } else {
                container.innerHTML = '<p class="text-muted">Brak kategorii AI</p>';
            }
        } catch (error) {
            console.error('Error loading AI categories:', error);
        }
    }

    // AI toggle
    document.getElementById('ai-enabled')?.addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        const statusEl = document.getElementById('ai-status');
        try {
            const response = await fetch('/api/host/ai/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled })
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            statusEl.textContent = enabled ? 'Aktywna' : 'Nieaktywna';
            statusEl.className = enabled ? 'badge bg-success' : 'badge bg-secondary';
        } catch (error) {
            alert('Błąd: ' + error.message);
            e.target.checked = !enabled;
        }
    });

    // AI Settings
    window.updateAISetting = async function (setting) {
        let value, endpoint;
        const eventId = window.EVENT_ID;

        if (setting === 'easy_points') {
            value = parseInt(document.getElementById('ai-easy-points').value);
            endpoint = `/api/host/ai/easy-points/${eventId}`;
        } else if (setting === 'medium_points') {
            value = parseInt(document.getElementById('ai-medium-points').value);
            endpoint = `/api/host/ai/medium-points/${eventId}`;
        } else if (setting === 'hard_points') {
            value = parseInt(document.getElementById('ai-hard-points').value);
            endpoint = `/api/host/ai/hard-points/${eventId}`;
        }

        if (value < 1 || value > 100) {
            alert('Punkty muszą być w zakresie 1-100');
            return;
        }

        try {
            const response = await fetch(endpoint, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ value })
            });
            const data = await response.json();
            if (response.ok) {
                alert(data.message);
            } else {
                alert('Błąd: ' + data.error);
            }
        } catch (error) {
            alert('Błąd: ' + error.message);
        }
    };

    // =====================================================================
    // PHOTO FUNCTIONS
    // =====================================================================
    async function loadHostPhotoGallery() {
        try {
            const response = await fetch(`/api/photos/${window.EVENT_ID}`);
            const photos = await response.json();

            const gallery = document.getElementById('host-photo-gallery');
            const noPhotosMsg = document.getElementById('no-photos-message');

            if (!gallery) return;

            if (photos.length === 0) {
                gallery.innerHTML = '';
                if (noPhotosMsg) noPhotosMsg.style.display = 'block';
                return;
            }

            if (noPhotosMsg) noPhotosMsg.style.display = 'none';
            gallery.innerHTML = photos.map(photo => `
                <div class="col-md-4 col-sm-6">
                    <div class="card">
                        <img src="${photo.image_url}" class="card-img-top" alt="Photo by ${photo.player_name}" style="height: 250px; object-fit: cover;">
                        <div class="card-body">
                            <h6 class="card-title">${photo.player_name}</h6>
                            <p class="card-text">
                                <span class="badge bg-primary">${photo.votes} polubień</span>
                            </p>
                            <small class="text-muted">${new Date(photo.timestamp).toLocaleString('pl-PL')}</small>
                        </div>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            console.error('Błąd ładowania galerii:', error);
        }
    }

    // Photo toggle
    document.getElementById('photo-enabled')?.addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        const statusEl = document.getElementById('photo-status');
        try {
            const response = await fetch('/api/host/photo/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled })
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            statusEl.textContent = enabled ? 'Aktywna' : 'Nieaktywna';
            statusEl.className = enabled ? 'badge bg-success' : 'badge bg-secondary';
        } catch (error) {
            alert('Błąd: ' + error.message);
            e.target.checked = !enabled;
        }
    });

    // Photo settings
    window.updatePhotoSetting = async function (setting) {
        let value, endpoint;
        const eventId = window.EVENT_ID;

        if (setting === 'selfie_points') {
            value = parseInt(document.getElementById('photo-selfie-points').value);
            if (value < 1 || value > 1000) {
                alert('Punkty muszą być w zakresie 1-1000');
                return;
            }
            endpoint = `/api/host/photo/selfie-points/${eventId}`;
        } else if (setting === 'like_given_points') {
            value = parseInt(document.getElementById('photo-like-given-points').value);
            if (value < 0 || value > 100) {
                alert('Punkty muszą być w zakresie 0-100');
                return;
            }
            endpoint = `/api/host/photo/like-given-points/${eventId}`;
        } else if (setting === 'like_received_points') {
            value = parseInt(document.getElementById('photo-like-received-points').value);
            if (value < 0 || value > 100) {
                alert('Punkty muszą być w zakresie 0-100');
                return;
            }
            endpoint = `/api/host/photo/like-received-points/${eventId}`;
        } else if (setting === 'max_likes') {
            value = parseInt(document.getElementById('photo-max-likes').value);
            if (value < 1 || value > 1000) {
                alert('Wartość musi być w zakresie 1-1000');
                return;
            }
            endpoint = `/api/host/photo/max-likes/${eventId}`;
        }

        try {
            const response = await fetch(endpoint, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ value })
            });
            const data = await response.json();
            if (response.ok) {
                alert(data.message);
            } else {
                alert('Błąd: ' + data.error);
            }
        } catch (error) {
            alert('Błąd: ' + error.message);
        }
    };

    document.querySelector('button[data-bs-target="#photo"]')?.addEventListener('click', function () {
        setTimeout(() => loadHostPhotoGallery(), 100);
    });

    if (socket) {
        socket.on('new_photo', function (data) {
            console.log('New photo received:', data);
            if (document.getElementById('photo').classList.contains('active')) {
                loadHostPhotoGallery();
            }
        });
    }

    // =====================================================================
    // VOTING FUNCTIONS
    // =====================================================================
    let votingQuestions = [];
    let votingEditingIndex = null;

    document.getElementById('voting-enabled')?.addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        const statusEl = document.getElementById('voting-status');
        statusEl.textContent = enabled ? 'Aktywna' : 'Nieaktywna';
        statusEl.className = enabled ? 'badge bg-success' : 'badge bg-secondary';
        console.log('Voting enabled:', enabled);
    });

    document.getElementById('voting-add-question-btn')?.addEventListener('click', function () {
        document.getElementById('voting-question-form').style.display = 'block';
        document.getElementById('voting-add-question-btn').style.display = 'none';
        votingEditingIndex = null;
        votingResetForm();
    });

    document.getElementById('voting-cancel-question-btn')?.addEventListener('click', function () {
        document.getElementById('voting-question-form').style.display = 'none';
        document.getElementById('voting-add-question-btn').style.display = 'block';
        votingResetForm();
    });

    document.getElementById('voting-add-answer-btn')?.addEventListener('click', function () {
        const container = document.getElementById('voting-answers-container');
        const currentCount = container.querySelectorAll('.voting-answer-item').length;

        if (currentCount >= 100) {
            alert('Maksymalna liczba odpowiedzi to 100');
            return;
        }

        const newIndex = currentCount + 1;
        const newAnswerItem = document.createElement('div');
        newAnswerItem.className = 'input-group mb-2 voting-answer-item';
        newAnswerItem.innerHTML = `
            <span class="input-group-text">${newIndex}</span>
            <input type="text" class="form-control voting-answer-input" placeholder="Odpowiedź ${newIndex}">
            <button class="btn btn-danger voting-remove-answer-btn" type="button">×</button>
        `;

        container.appendChild(newAnswerItem);
        votingUpdateRemoveButtons();

        newAnswerItem.querySelector('.voting-remove-answer-btn').addEventListener('click', function () {
            newAnswerItem.remove();
            votingUpdateAnswerNumbers();
            votingUpdateRemoveButtons();
        });
    });

    function votingUpdateAnswerNumbers() {
        const container = document.getElementById('voting-answers-container');
        const items = container.querySelectorAll('.voting-answer-item');
        items.forEach((item, index) => {
            item.querySelector('.input-group-text').textContent = index + 1;
            item.querySelector('.voting-answer-input').placeholder = `Odpowiedź ${index + 1}`;
        });
    }

    function votingUpdateRemoveButtons() {
        const container = document.getElementById('voting-answers-container');
        const items = container.querySelectorAll('.voting-answer-item');
        const showButtons = items.length > 2;

        items.forEach(item => {
            const removeBtn = item.querySelector('.voting-remove-answer-btn');
            removeBtn.style.display = showButtons ? 'block' : 'none';
        });
    }

    document.querySelectorAll('.voting-remove-answer-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const item = btn.closest('.voting-answer-item');
            item.remove();
            votingUpdateAnswerNumbers();
            votingUpdateRemoveButtons();
        });
    });

    document.getElementById('voting-submit-question-btn')?.addEventListener('click', function () {
        const questionText = document.getElementById('voting-question-text').value.trim();

        if (!questionText) {
            alert('Proszę wpisać pytanie');
            return;
        }

        const answerInputs = document.querySelectorAll('.voting-answer-input');
        const answers = [];
        answerInputs.forEach(input => {
            const value = input.value.trim();
            if (value) {
                answers.push(value);
            }
        });

        if (answers.length < 2) {
            alert('Proszę dodać przynajmniej 2 odpowiedzi');
            return;
        }

        const choiceType = document.querySelector('input[name="voting-choice-type"]:checked').value;
        const timeValue = parseInt(document.getElementById('voting-time-value').value);
        const timeUnit = document.getElementById('voting-time-unit').value;
        const resultType = document.querySelector('input[name="voting-result-type"]:checked').value;

        const question = {
            id: votingEditingIndex !== null ? votingQuestions[votingEditingIndex].id : Date.now(),
            question: questionText,
            answers: answers,
            choiceType: choiceType,
            timeValue: timeValue,
            timeUnit: timeUnit,
            resultType: resultType,
            status: 'inactive'
        };

        if (votingEditingIndex !== null) {
            votingQuestions[votingEditingIndex] = question;
            votingEditingIndex = null;
        } else {
            votingQuestions.push(question);
        }

        votingDisplayQuestions();

        document.getElementById('voting-question-form').style.display = 'none';
        document.getElementById('voting-add-question-btn').style.display = 'block';
        votingResetForm();
    });

    function votingResetForm() {
        document.getElementById('voting-question-text').value = '';

        const container = document.getElementById('voting-answers-container');
        container.innerHTML = `
            <div class="input-group mb-2 voting-answer-item">
                <span class="input-group-text">1</span>
                <input type="text" class="form-control voting-answer-input" placeholder="Odpowiedź 1">
                <button class="btn btn-danger voting-remove-answer-btn" type="button" style="display: none;">×</button>
            </div>
            <div class="input-group mb-2 voting-answer-item">
                <span class="input-group-text">2</span>
                <input type="text" class="form-control voting-answer-input" placeholder="Odpowiedź 2">
                <button class="btn btn-danger voting-remove-answer-btn" type="button" style="display: none;">×</button>
            </div>
        `;

        container.querySelectorAll('.voting-remove-answer-btn').forEach(btn => {
            btn.addEventListener('click', function () {
                const item = btn.closest('.voting-answer-item');
                item.remove();
                votingUpdateAnswerNumbers();
                votingUpdateRemoveButtons();
            });
        });

        document.getElementById('voting-single-choice').checked = true;
        document.getElementById('voting-time-value').value = 60;
        document.getElementById('voting-time-unit').value = 'seconds';
        document.getElementById('voting-result-auto').checked = true;
    }

    function votingDisplayQuestions() {
        const listContainer = document.getElementById('voting-questions-list');

        if (votingQuestions.length === 0) {
            listContainer.innerHTML = '<p class="text-muted">Brak dodanych pytań. Kliknij "Dodaj propozycję" aby utworzyć pierwsze pytanie.</p>';
            return;
        }

        listContainer.innerHTML = votingQuestions.map((q, index) => {
            const timeDisplay = q.timeUnit === 'minutes' ? `${q.timeValue} min` : `${q.timeValue} sek`;
            const choiceDisplay = q.choiceType === 'single' ? 'Jeden wybór' : 'Wielokrotny';
            const resultDisplay = q.resultType === 'auto' ? 'Auto' : 'Manual';

            return `
                <div class="card mb-3" style="background: white;">
                    <div class="card-body">
                        <h6 class="card-title mb-3"><strong>Pytanie ${index + 1}:</strong> ${q.question}</h6>

                        <div class="mb-2">
                            <strong>Odpowiedzi:</strong>
                            <ol class="mb-2">
                                ${q.answers.map(a => `<li>${a}</li>`).join('')}
                            </ol>
                        </div>

                        <div class="mb-3">
                            <span class="badge bg-info me-2">${choiceDisplay}</span>
                            <span class="badge bg-secondary me-2">Czas: ${timeDisplay}</span>
                            <span class="badge bg-primary me-2">Wynik: ${resultDisplay}</span>
                            <span class="badge ${q.status === 'active' ? 'bg-success' : q.status === 'finished' ? 'bg-dark' : 'bg-warning'}">${q.status === 'active' ? 'Aktywne' : q.status === 'finished' ? 'Zakończone' : 'Nieaktywne'
                }</span>
                        </div>

                        <div class="btn-group" role="group">
                            <button class="btn btn-sm btn-success" onclick="votingStartQuestion(${index})" ${q.status === 'active' ? 'disabled' : ''}>
                                Start
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="votingStopQuestion(${index})" ${q.status !== 'active' ? 'disabled' : ''}>
                                Stop
                            </button>
                            <button class="btn btn-sm btn-warning" onclick="votingResetQuestion(${index})">
                                Reset
                            </button>
                            <button class="btn btn-sm btn-primary" onclick="votingEditQuestion(${index})" ${q.status === 'active' ? 'disabled' : ''}>
                                Edytuj
                            </button>
                            <button class="btn btn-sm btn-secondary" onclick="votingDeleteQuestion(${index})" ${q.status === 'active' ? 'disabled' : ''}>
                                Usuń
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    window.votingStartQuestion = function (index) {
        votingQuestions[index].status = 'active';
        votingDisplayQuestions();
        console.log('Started question:', votingQuestions[index]);
    };

    window.votingStopQuestion = function (index) {
        votingQuestions[index].status = 'finished';
        votingDisplayQuestions();
        console.log('Stopped question:', votingQuestions[index]);
    };

    window.votingResetQuestion = function (index) {
        votingQuestions[index].status = 'inactive';
        votingDisplayQuestions();
        console.log('Reset question:', votingQuestions[index]);
    };

    window.votingEditQuestion = function (index) {
        const question = votingQuestions[index];
        votingEditingIndex = index;

        document.getElementById('voting-question-text').value = question.question;

        const container = document.getElementById('voting-answers-container');
        container.innerHTML = '';

        question.answers.forEach((answer, i) => {
            const answerItem = document.createElement('div');
            answerItem.className = 'input-group mb-2 voting-answer-item';
            answerItem.innerHTML = `
                <span class="input-group-text">${i + 1}</span>
                <input type="text" class="form-control voting-answer-input" placeholder="Odpowiedź ${i + 1}" value="${answer}">
                <button class="btn btn-danger voting-remove-answer-btn" type="button" ${question.answers.length <= 2 ? 'style="display: none;"' : ''}>×</button>
            `;
            container.appendChild(answerItem);

            answerItem.querySelector('.voting-remove-answer-btn').addEventListener('click', function () {
                answerItem.remove();
                votingUpdateAnswerNumbers();
                votingUpdateRemoveButtons();
            });
        });

        if (question.choiceType === 'single') {
            document.getElementById('voting-single-choice').checked = true;
        } else {
            document.getElementById('voting-multiple-choice').checked = true;
        }

        document.getElementById('voting-time-value').value = question.timeValue;
        document.getElementById('voting-time-unit').value = question.timeUnit;

        if (question.resultType === 'auto') {
            document.getElementById('voting-result-auto').checked = true;
        } else {
            document.getElementById('voting-result-manual').checked = true;
        }

        document.getElementById('voting-question-form').style.display = 'block';
        document.getElementById('voting-add-question-btn').style.display = 'none';
    };

    window.votingDeleteQuestion = function (index) {
        if (confirm('Czy na pewno chcesz usunąć to pytanie?')) {
            votingQuestions.splice(index, 1);
            votingDisplayQuestions();
            console.log('Deleted question at index:', index);
        }
    };

    votingDisplayQuestions();

    // =====================================================================
    // DISPLAY BUTTONS
    // =====================================================================
    document.getElementById('open-display-1-btn')?.addEventListener('click', () => {
        window.open(`/display/${window.EVENT_ID}`, '_blank');
    });

    document.getElementById('open-display-2-btn')?.addEventListener('click', () => {
        window.open(`/display2/${window.EVENT_ID}`, '_blank');
    });

    document.getElementById('open-display-3-btn')?.addEventListener('click', () => {
        window.open(`/photo_player/${window.EVENT_ID}`, '_blank');
    });

    document.getElementById('open-display-4-btn')?.addEventListener('click', () => {
        window.open(`/display4/${window.EVENT_ID}`, '_blank');
    });

    document.getElementById('open-display-settings-btn')?.addEventListener('click', () => {
        const displayTab = document.querySelector('button[data-bs-target="#display"]');
        if (displayTab) {
            displayTab.click();
        }
    });

    // =====================================================================
    // DARK MODE
    // =====================================================================
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    const darkModeStatus = document.getElementById('dark-mode-status');

    function applyDarkMode(enabled) {
        if (enabled) {
            document.body.classList.add('dark-mode');
            if (darkModeStatus) {
                darkModeStatus.textContent = 'Włączony';
                darkModeStatus.className = 'badge bg-success';
            }
        } else {
            document.body.classList.remove('dark-mode');
            if (darkModeStatus) {
                darkModeStatus.textContent = 'Wyłączony';
                darkModeStatus.className = 'badge bg-secondary';
            }
        }
    }

    const darkModeEnabled = localStorage.getItem('darkMode') !== 'false';
    if (darkModeToggle) {
        darkModeToggle.checked = darkModeEnabled;
        applyDarkMode(darkModeEnabled);

        darkModeToggle.addEventListener('change', (e) => {
            const enabled = e.target.checked;
            applyDarkMode(enabled);
            localStorage.setItem('darkMode', enabled ? 'true' : 'false');
        });
    }

    // =====================================================================
    // FORTUNE (WROZKA AI) SETTINGS
    // =====================================================================
    window.updateFortuneSetting = async function (setting) {
        let value, endpoint;

        if (setting === 'word_count') {
            value = parseInt(document.getElementById('fortune-word-count').value);
            if (value < 10 || value > 500) {
                alert('Liczba słów musi być w zakresie 10-500');
                return;
            }
            endpoint = '/api/host/fortune/word-count';
        } else if (setting === 'points') {
            value = parseInt(document.getElementById('fortune-points').value);
            if (value < 1 || value > 100) {
                alert('Punkty muszą być w zakresie 1-100');
                return;
            }
            endpoint = '/api/host/fortune/points';
        } else if (setting === 'player_words') {
            value = parseInt(document.getElementById('fortune-player-words').value);
            if (value < 1 || value > 10) {
                alert('Liczba słów gracza musi być w zakresie 1-10');
                return;
            }
            endpoint = '/api/host/fortune/player-words';
        }

        try {
            const response = await fetch(endpoint, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ value })
            });
            const data = await response.json();
            if (response.ok) {
                alert(data.message);
            } else {
                alert('Błąd: ' + data.error);
            }
        } catch (error) {
            alert('Błąd: ' + error.message);
        }
    };

    // =====================================================================
    // QUESTIONS TOGGLE
    // =====================================================================
    document.getElementById('questions-enabled')?.addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        const statusEl = document.getElementById('questions-status');
        try {
            const response = await fetch('/api/host/questions/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled })
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            statusEl.textContent = enabled ? 'Aktywna' : 'Nieaktywna';
            statusEl.className = enabled ? 'badge bg-success' : 'badge bg-secondary';
        } catch (error) {
            alert('Błąd: ' + error.message);
            e.target.checked = !enabled;
        }
    });

    // =====================================================================
    // MINIGAMES TOGGLE
    // =====================================================================
    document.getElementById('minigames-enabled')?.addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        const statusEl = document.getElementById('minigames-status');
        try {
            const response = await fetch('/api/host/minigames/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled })
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            statusEl.textContent = enabled ? 'Aktywna' : 'Nieaktywna';
            statusEl.className = enabled ? 'badge bg-success' : 'badge bg-secondary';
        } catch (error) {
            alert('Błąd: ' + error.message);
            e.target.checked = !enabled;
        }
    });

    // =====================================================================
    // TAB EVENT LISTENERS
    // =====================================================================
    document.querySelector('button[data-bs-target="#password"]')?.addEventListener('click', loadPasswordState);
    document.querySelector('button[data-bs-target="#ai"]')?.addEventListener('click', loadAICategories);

    // =====================================================================
    // EXPORTS
    // =====================================================================
    window.loadPasswordState = loadPasswordState;
    window.setPassword = setPassword;
    window.revealSelectedLetters = revealSelectedLetters;
    window.loadAICategories = loadAICategories;
    window.loadHostPhotoGallery = loadHostPhotoGallery;
});
