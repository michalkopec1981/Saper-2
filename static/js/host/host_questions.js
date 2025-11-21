/**
 * HOST QUESTIONS MODULE
 * Obsługa pytań dla wszystkich rund (1, 2, 3)
 * Kody QR pytań, punktacja, timery
 *
 * Używa: window.translations, window.currentLanguage, window.EVENT_ID
 * Eksportuje: loadQuestions, loadQuestionsR2, loadQuestionsR3, updateQuestionsSetting
 */

document.addEventListener('DOMContentLoaded', function () {
    let currentEditingQuestionId = null;
    let currentEditingQuestionIdR2 = null;
    let currentEditingQuestionIdR3 = null;
    let currentEditingQuestionRound = 1;
    let questionModal = null;

    // Initialize modal
    const modalEl = document.getElementById('questionModal');
    if (modalEl) {
        questionModal = new bootstrap.Modal(modalEl);
    }

    // =====================================================================
    // QUESTIONS ROUND 1
    // =====================================================================
    function loadQuestions() {
        const translations = window.translations;
        const currentLanguage = window.currentLanguage || 'pl';

        fetch('/api/host/questions')
            .then(res => res.json())
            .then(questions => {
                const list = document.getElementById('questions-list');
                if (!list) return;

                if (questions.length === 0) {
                    list.innerHTML = `<p class="text-muted">${translations[currentLanguage].add_question}</p>`;
                    return;
                }

                list.innerHTML = questions.map((q, index) => {
                    const percentage = q.times_shown > 0 ? Math.round((q.times_correct / q.times_shown) * 100) : 0;
                    return `
                        <div class="question-item d-flex align-items-start">
                            <div class="me-3">
                                <strong>${index + 1}.</strong>
                            </div>
                            <div class="flex-grow-1">
                                <p class="mb-2">${q.text}</p>
                                <div class="question-stats">
                                    <span class="badge bg-info">${translations[currentLanguage][q.difficulty] || q.difficulty}</span>
                                    <span>${translations[currentLanguage].shown}: ${q.times_shown}</span> |
                                    <span>${translations[currentLanguage].correct}: ${q.times_correct}</span> |
                                    <span>${percentage}%</span>
                                </div>
                            </div>
                            <div>
                                <button class="btn btn-sm btn-outline-primary me-2 edit-question-btn" data-id="${q.id}">${translations[currentLanguage].edit}</button>
                                <button class="btn btn-sm btn-outline-danger delete-question-btn" data-id="${q.id}">${translations[currentLanguage].delete}</button>
                            </div>
                        </div>
                    `;
                }).join('');

                document.querySelectorAll('.edit-question-btn').forEach(btn => {
                    btn.addEventListener('click', () => editQuestion(parseInt(btn.dataset.id)));
                });
                document.querySelectorAll('.delete-question-btn').forEach(btn => {
                    btn.addEventListener('click', () => deleteQuestion(parseInt(btn.dataset.id)));
                });
            });
    }

    async function editQuestion(id) {
        const translations = window.translations;
        const currentLanguage = window.currentLanguage || 'pl';

        try {
            const response = await fetch('/api/host/questions');
            const questions = await response.json();
            const question = questions.find(q => q.id === id);

            if (!question) return;

            currentEditingQuestionId = id;
            currentEditingQuestionRound = 1;
            document.getElementById('modal-question-text').value = question.text;
            document.getElementById('modal-answer-a').value = question.answers[0];
            document.getElementById('modal-answer-b').value = question.answers[1];
            document.getElementById('modal-answer-c').value = question.answers[2];
            document.getElementById('modal-letter').value = question.letterToReveal;

            document.getElementById(`correct-${question.correctAnswer.toLowerCase()}`).checked = true;

            document.querySelectorAll('#difficulty-buttons .btn').forEach(b => b.classList.remove('active'));
            document.querySelector(`#difficulty-buttons .btn[data-difficulty="${question.difficulty}"]`)?.classList.add('active');

            document.querySelectorAll('#category-buttons .btn').forEach(b => b.classList.remove('active'));
            document.querySelector(`#category-buttons .btn[data-category="${question.category}"]`)?.classList.add('active');

            document.querySelector('.modal-title').textContent = translations[currentLanguage].edit + ' ' + translations[currentLanguage].question_text.toLowerCase();
            questionModal.show();
        } catch (error) {
            alert('Błąd ładowania pytania: ' + error.message);
        }
    }

    async function deleteQuestion(id) {
        if (!confirm('Czy na pewno chcesz usunąć to pytanie?')) return;

        try {
            const response = await fetch(`/api/host/question/${id}`, { method: 'DELETE' });
            if (!response.ok) throw new Error('Błąd usuwania pytania');
            loadQuestions();
        } catch (error) {
            alert('Błąd: ' + error.message);
        }
    }

    // =====================================================================
    // QUESTIONS ROUND 2
    // =====================================================================
    function loadQuestionsR2() {
        const translations = window.translations;
        const currentLanguage = window.currentLanguage || 'pl';

        fetch('/api/host/questions?round=2')
            .then(res => res.json())
            .then(questions => {
                const list = document.getElementById('r2-questions-list');
                if (!list) return;

                if (questions.length === 0) {
                    list.innerHTML = `<p class="text-muted">${translations[currentLanguage].add_question}</p>`;
                    return;
                }

                list.innerHTML = questions.map((q, index) => {
                    const percentage = q.times_shown > 0 ? Math.round((q.times_correct / q.times_shown) * 100) : 0;
                    return `
                        <div class="question-item d-flex align-items-start">
                            <div class="me-3"><strong>${index + 1}.</strong></div>
                            <div class="flex-grow-1">
                                <p class="mb-2">${q.text}</p>
                                <div class="question-stats">
                                    <span class="badge bg-info">${translations[currentLanguage][q.difficulty] || q.difficulty}</span>
                                    <span>${translations[currentLanguage].shown}: ${q.times_shown}</span> |
                                    <span>${translations[currentLanguage].correct}: ${q.times_correct}</span> |
                                    <span>${percentage}%</span>
                                </div>
                            </div>
                            <div>
                                <button class="btn btn-sm btn-outline-primary me-2 edit-question-r2-btn" data-id="${q.id}">Edytuj</button>
                                <button class="btn btn-sm btn-outline-danger delete-question-r2-btn" data-id="${q.id}">Usuń</button>
                            </div>
                        </div>
                    `;
                }).join('');

                document.querySelectorAll('.edit-question-r2-btn').forEach(btn => {
                    btn.addEventListener('click', () => editQuestionR2(parseInt(btn.dataset.id)));
                });
                document.querySelectorAll('.delete-question-r2-btn').forEach(btn => {
                    btn.addEventListener('click', () => deleteQuestionR2(parseInt(btn.dataset.id)));
                });
            });
    }

    async function editQuestionR2(id) {
        try {
            const response = await fetch('/api/host/questions?round=2');
            const questions = await response.json();
            const question = questions.find(q => q.id === id);

            if (!question) return;

            currentEditingQuestionIdR2 = id;
            currentEditingQuestionRound = 2;
            document.getElementById('modal-question-text').value = question.text;
            document.getElementById('modal-answer-a').value = question.answers[0];
            document.getElementById('modal-answer-b').value = question.answers[1];
            document.getElementById('modal-answer-c').value = question.answers[2];
            document.getElementById('modal-letter').value = question.letterToReveal;

            document.getElementById(`correct-${question.correctAnswer.toLowerCase()}`).checked = true;

            document.querySelectorAll('#difficulty-buttons .btn').forEach(b => b.classList.remove('active'));
            document.querySelector(`#difficulty-buttons .btn[data-difficulty="${question.difficulty}"]`)?.classList.add('active');

            document.querySelectorAll('#category-buttons .btn').forEach(b => b.classList.remove('active'));
            document.querySelector(`#category-buttons .btn[data-category="${question.category}"]`)?.classList.add('active');

            document.querySelector('.modal-title').textContent = 'Edytuj pytanie - Runda 2';
            questionModal.show();
        } catch (error) {
            alert('Błąd ładowania pytania: ' + error.message);
        }
    }

    async function deleteQuestionR2(id) {
        if (!confirm('Czy na pewno chcesz usunąć to pytanie?')) return;

        try {
            const response = await fetch(`/api/host/question/${id}?round=2`, { method: 'DELETE' });
            if (!response.ok) throw new Error('Błąd usuwania pytania');
            loadQuestionsR2();
        } catch (error) {
            alert('Błąd: ' + error.message);
        }
    }

    // =====================================================================
    // QUESTIONS ROUND 3
    // =====================================================================
    function loadQuestionsR3() {
        const translations = window.translations;
        const currentLanguage = window.currentLanguage || 'pl';

        fetch('/api/host/questions?round=3')
            .then(res => res.json())
            .then(questions => {
                const list = document.getElementById('r3-questions-list');
                if (!list) return;

                if (questions.length === 0) {
                    list.innerHTML = `<p class="text-muted">${translations[currentLanguage].add_question}</p>`;
                    return;
                }

                list.innerHTML = questions.map((q, index) => {
                    const percentage = q.times_shown > 0 ? Math.round((q.times_correct / q.times_shown) * 100) : 0;
                    return `
                        <div class="question-item d-flex align-items-start">
                            <div class="me-3"><strong>${index + 1}.</strong></div>
                            <div class="flex-grow-1">
                                <p class="mb-2">${q.text}</p>
                                <div class="question-stats">
                                    <span class="badge bg-info">${translations[currentLanguage][q.difficulty] || q.difficulty}</span>
                                    <span>${translations[currentLanguage].shown}: ${q.times_shown}</span> |
                                    <span>${translations[currentLanguage].correct}: ${q.times_correct}</span> |
                                    <span>${percentage}%</span>
                                </div>
                            </div>
                            <div>
                                <button class="btn btn-sm btn-outline-primary me-2 edit-question-r3-btn" data-id="${q.id}">Edytuj</button>
                                <button class="btn btn-sm btn-outline-danger delete-question-r3-btn" data-id="${q.id}">Usuń</button>
                            </div>
                        </div>
                    `;
                }).join('');

                document.querySelectorAll('.edit-question-r3-btn').forEach(btn => {
                    btn.addEventListener('click', () => editQuestionR3(parseInt(btn.dataset.id)));
                });
                document.querySelectorAll('.delete-question-r3-btn').forEach(btn => {
                    btn.addEventListener('click', () => deleteQuestionR3(parseInt(btn.dataset.id)));
                });
            });
    }

    async function editQuestionR3(id) {
        try {
            const response = await fetch('/api/host/questions?round=3');
            const questions = await response.json();
            const question = questions.find(q => q.id === id);

            if (!question) return;

            currentEditingQuestionIdR3 = id;
            currentEditingQuestionRound = 3;
            document.getElementById('modal-question-text').value = question.text;
            document.getElementById('modal-answer-a').value = question.answers[0];
            document.getElementById('modal-answer-b').value = question.answers[1];
            document.getElementById('modal-answer-c').value = question.answers[2];
            document.getElementById('modal-letter').value = question.letterToReveal;

            document.getElementById(`correct-${question.correctAnswer.toLowerCase()}`).checked = true;

            document.querySelectorAll('#difficulty-buttons .btn').forEach(b => b.classList.remove('active'));
            document.querySelector(`#difficulty-buttons .btn[data-difficulty="${question.difficulty}"]`)?.classList.add('active');

            document.querySelectorAll('#category-buttons .btn').forEach(b => b.classList.remove('active'));
            document.querySelector(`#category-buttons .btn[data-category="${question.category}"]`)?.classList.add('active');

            document.querySelector('.modal-title').textContent = 'Edytuj pytanie - Runda 3';
            questionModal.show();
        } catch (error) {
            alert('Błąd ładowania pytania: ' + error.message);
        }
    }

    async function deleteQuestionR3(id) {
        if (!confirm('Czy na pewno chcesz usunąć to pytanie?')) return;

        try {
            const response = await fetch(`/api/host/question/${id}?round=3`, { method: 'DELETE' });
            if (!response.ok) throw new Error('Błąd usuwania pytania');
            loadQuestionsR3();
        } catch (error) {
            alert('Błąd: ' + error.message);
        }
    }

    // =====================================================================
    // ADD/SAVE QUESTION BUTTONS
    // =====================================================================
    document.getElementById('add-question-btn')?.addEventListener('click', () => {
        const translations = window.translations;
        const currentLanguage = window.currentLanguage || 'pl';

        currentEditingQuestionId = null;
        currentEditingQuestionRound = 1;
        document.getElementById('modal-question-text').value = '';
        document.getElementById('modal-answer-a').value = '';
        document.getElementById('modal-answer-b').value = '';
        document.getElementById('modal-answer-c').value = '';
        document.getElementById('modal-letter').value = 'X';
        document.querySelectorAll('input[name="correct-answer"]').forEach(r => r.checked = false);
        document.getElementById('correct-a').checked = true;
        document.querySelectorAll('#difficulty-buttons .btn').forEach(b => b.classList.remove('active'));
        document.querySelector('#difficulty-buttons .btn[data-difficulty="easy"]')?.classList.add('active');
        document.querySelectorAll('#category-buttons .btn').forEach(b => b.classList.remove('active'));
        document.querySelector('#category-buttons .btn[data-category="company"]')?.classList.add('active');
        document.querySelector('.modal-title').textContent = translations[currentLanguage].question_modal_title;
        questionModal.show();
    });

    document.getElementById('r2-add-question-btn')?.addEventListener('click', () => {
        currentEditingQuestionIdR2 = null;
        currentEditingQuestionRound = 2;
        document.getElementById('modal-question-text').value = '';
        document.getElementById('modal-answer-a').value = '';
        document.getElementById('modal-answer-b').value = '';
        document.getElementById('modal-answer-c').value = '';
        document.getElementById('modal-letter').value = 'X';
        document.querySelectorAll('input[name="correct-answer"]').forEach(r => r.checked = false);
        document.getElementById('correct-a').checked = true;
        document.querySelectorAll('#difficulty-buttons .btn').forEach(b => b.classList.remove('active'));
        document.querySelector('#difficulty-buttons .btn[data-difficulty="easy"]')?.classList.add('active');
        document.querySelectorAll('#category-buttons .btn').forEach(b => b.classList.remove('active'));
        document.querySelector('#category-buttons .btn[data-category="company"]')?.classList.add('active');
        document.querySelector('.modal-title').textContent = 'Dodaj pytanie - Runda 2';
        questionModal.show();
    });

    document.getElementById('r3-add-question-btn')?.addEventListener('click', () => {
        currentEditingQuestionIdR3 = null;
        currentEditingQuestionRound = 3;
        document.getElementById('modal-question-text').value = '';
        document.getElementById('modal-answer-a').value = '';
        document.getElementById('modal-answer-b').value = '';
        document.getElementById('modal-answer-c').value = '';
        document.getElementById('modal-letter').value = 'X';
        document.querySelectorAll('input[name="correct-answer"]').forEach(r => r.checked = false);
        document.getElementById('correct-a').checked = true;
        document.querySelectorAll('#difficulty-buttons .btn').forEach(b => b.classList.remove('active'));
        document.querySelector('#difficulty-buttons .btn[data-difficulty="easy"]')?.classList.add('active');
        document.querySelectorAll('#category-buttons .btn').forEach(b => b.classList.remove('active'));
        document.querySelector('#category-buttons .btn[data-category="company"]')?.classList.add('active');
        document.querySelector('.modal-title').textContent = 'Dodaj pytanie - Runda 3';
        questionModal.show();
    });

    document.getElementById('save-question-btn')?.addEventListener('click', async () => {
        const text = document.getElementById('modal-question-text').value.trim();
        const answerA = document.getElementById('modal-answer-a').value.trim();
        const answerB = document.getElementById('modal-answer-b').value.trim();
        const answerC = document.getElementById('modal-answer-c').value.trim();
        const correctAnswer = document.querySelector('input[name="correct-answer"]:checked')?.value;
        const difficulty = document.querySelector('#difficulty-buttons .btn.active')?.dataset.difficulty || 'easy';
        const category = document.querySelector('#category-buttons .btn.active')?.dataset.category || 'company';
        const letter = document.getElementById('modal-letter').value.toUpperCase() || 'X';

        if (!text || !answerA || !answerB || !answerC || !correctAnswer) {
            alert('Wypełnij wszystkie pola!');
            return;
        }

        const payload = {
            text,
            answers: [answerA, answerB, answerC],
            correctAnswer,
            difficulty,
            letterToReveal: letter,
            category: category,
            round: currentEditingQuestionRound
        };

        try {
            let response;
            const roundParam = currentEditingQuestionRound > 1 ? `?round=${currentEditingQuestionRound}` : '';

            let editingId = null;
            if (currentEditingQuestionRound === 2) {
                editingId = currentEditingQuestionIdR2;
            } else if (currentEditingQuestionRound === 3) {
                editingId = currentEditingQuestionIdR3;
            } else {
                editingId = currentEditingQuestionId;
            }

            if (editingId) {
                response = await fetch(`/api/host/question/${editingId}${roundParam}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } else {
                response = await fetch(`/api/host/questions${roundParam}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            }

            if (!response.ok) throw new Error('Błąd zapisu pytania');

            questionModal.hide();

            if (currentEditingQuestionRound === 2) {
                loadQuestionsR2();
            } else if (currentEditingQuestionRound === 3) {
                loadQuestionsR3();
            } else {
                loadQuestions();
            }
        } catch (error) {
            alert('Błąd: ' + error.message);
        }
    });

    // Difficulty buttons
    document.getElementById('difficulty-buttons')?.addEventListener('click', (e) => {
        const btn = e.target.closest('button');
        if (btn) {
            document.querySelectorAll('#difficulty-buttons .btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        }
    });

    // Category buttons
    document.getElementById('category-buttons')?.addEventListener('click', (e) => {
        const btn = e.target.closest('button');
        if (btn) {
            document.querySelectorAll('#category-buttons .btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        }
    });

    // =====================================================================
    // TAB EVENT LISTENERS
    // =====================================================================
    document.querySelector('button[data-bs-target="#questions"]')?.addEventListener('click', loadQuestions);
    document.querySelector('button[data-bs-target="#questions-r2"]')?.addEventListener('click', loadQuestionsR2);
    document.querySelector('button[data-bs-target="#questions-r3"]')?.addEventListener('click', loadQuestionsR3);

    // =====================================================================
    // POINTS SETTINGS
    // =====================================================================
    window.updateQuestionsSetting = async function(setting) {
        let value, endpoint;
        const eventId = window.EVENT_ID;

        if (setting === 'easy_points') {
            value = parseInt(document.getElementById('questions-easy-points').value);
            endpoint = `/api/host/questions/easy-points/${eventId}`;
        } else if (setting === 'medium_points') {
            value = parseInt(document.getElementById('questions-medium-points').value);
            endpoint = `/api/host/questions/medium-points/${eventId}`;
        } else if (setting === 'hard_points') {
            value = parseInt(document.getElementById('questions-hard-points').value);
            endpoint = `/api/host/questions/hard-points/${eventId}`;
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

    window.updateR2QuestionsSetting = async function(setting) {
        let value, endpoint;
        const eventId = window.EVENT_ID;

        if (setting === 'easy_points') {
            value = parseInt(document.getElementById('r2-questions-easy-points').value);
            endpoint = `/api/host/questions/easy-points/${eventId}?round=2`;
        } else if (setting === 'medium_points') {
            value = parseInt(document.getElementById('r2-questions-medium-points').value);
            endpoint = `/api/host/questions/medium-points/${eventId}?round=2`;
        } else if (setting === 'hard_points') {
            value = parseInt(document.getElementById('r2-questions-hard-points').value);
            endpoint = `/api/host/questions/hard-points/${eventId}?round=2`;
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

    window.updateR3QuestionsSetting = async function(setting) {
        let value, endpoint;
        const eventId = window.EVENT_ID;

        if (setting === 'easy_points') {
            value = parseInt(document.getElementById('r3-questions-easy-points').value);
            endpoint = `/api/host/questions/easy-points/${eventId}?round=3`;
        } else if (setting === 'medium_points') {
            value = parseInt(document.getElementById('r3-questions-medium-points').value);
            endpoint = `/api/host/questions/medium-points/${eventId}?round=3`;
        } else if (setting === 'hard_points') {
            value = parseInt(document.getElementById('r3-questions-hard-points').value);
            endpoint = `/api/host/questions/hard-points/${eventId}?round=3`;
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
    // EXPORTS
    // =====================================================================
    window.loadQuestions = loadQuestions;
    window.loadQuestionsR2 = loadQuestionsR2;
    window.loadQuestionsR3 = loadQuestionsR3;
});
