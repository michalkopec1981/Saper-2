document.addEventListener('DOMContentLoaded', function() {
    const eventsContainer = document.getElementById('events-container');
    const addEventBtn = document.getElementById('add-event-btn');
    const statusContainer = document.getElementById('status-container');

    async function fetchApi(url, options = {}) {
        const isFormData = options.body instanceof FormData;
        if (!isFormData && options.body) {
            options.headers = { 'Content-Type': 'application/json', ...options.headers };
            options.body = JSON.stringify(options.body);
        }

        try {
            const response = await fetch(url, options);
            const data = await response.json().catch(() => null);
            if (!response.ok) throw new Error(data ? (data.message || data.error) : `Błąd serwera: ${response.status}`);
            return data;
        } catch (error) {
            showStatus(`Błąd API: ${error.message}`, 'danger');
            console.error('API Error:', error);
            return null;
        }
    }

    function showStatus(message, type = 'success', duration = 4000) {
        statusContainer.innerHTML = `<div class="alert alert-${type} alert-dismissible fade show" role="alert">${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>`;
        setTimeout(() => {
            const alert = statusContainer.querySelector('.alert');
            if (alert) bootstrap.Alert.getOrCreateInstance(alert).close();
        }, duration);
    }

    function createEventPanel(event) {
        const panel = document.createElement('div');
        panel.className = 'card mb-3';
        panel.dataset.eventId = event.id;

        const deleteBtnVisibility = event.id > 1 ? '' : 'style="display: none;"';
        const logoContent = event.logo_url 
            ? `<img src="${event.logo_url}" class="event-logo-preview">`
            : `<span class="logo-placeholder">Brak logo</span>`;
        const deleteLogoBtnVisibility = event.logo_url ? '' : 'style="display: none;"';

        // Logika statusu gry
        const status = event.game_status || { status_text: 'Brak Danych' };
        let statusClass = 'status-default';
        if (status.status_text === 'Start') statusClass = 'status-start';
        else if (status.status_text === 'Pauza') statusClass = 'status-pauza';
        else if (status.status_text === 'Koniec') statusClass = 'status-koniec';
        else if (status.status_text === 'Przygotowanie') statusClass = 'status-przygotowanie';

        panel.innerHTML = `
            <div class="card-body">
                <div class="row g-3 align-items-start">
                    <div class="col-lg-9">
                        <div class="row g-3">
                            <div class="col-md-3"><label class="form-label">Nazwa Eventu</label><input type="text" class="form-control event-name" value="${event.name || ''}"></div>
                            <div class="col-md-3"><label class="form-label">Login Hosta</label><input type="text" class="form-control event-login" value="${event.login || ''}"></div>
                            <div class="col-md-3"><label class="form-label">Hasło Hosta</label><input type="text" class="form-control event-password" value="${event.password || ''}"></div>
                            <div class="col-md-3"><label class="form-label">Data</label><input type="date" class="form-control event-date" value="${event.event_date || ''}"></div>
                            <div class="col-md-12"><label class="form-label">Uwagi</label><textarea class="form-control notes-textarea event-notes" rows="1">${event.notes || ''}</textarea></div>
                        </div>
                    </div>
                    <div class="col-lg-3 d-flex flex-column align-items-center">
                        <div class="d-flex gap-2 mb-2">
                            <button class="btn btn-sm btn-light border btn-logo btn-fixed-width">Logo</button>
                            <button class="btn btn-sm btn-light border btn-delete-logo btn-fixed-width" ${deleteLogoBtnVisibility}>Usuń Logo</button>
                        </div>
                        <div class="logo-area">${logoContent}</div>
                    </div>
                </div>
                <hr class="my-3">
                <div class="d-flex align-items-center flex-wrap justify-content-between">
                    <div class="d-flex align-items-center">
                        <span class="status-badge ${statusClass}">STAN GRY: ${status.status_text}</span>
                    </div>
                    <div class="d-flex align-items-center gap-2 flex-wrap justify-content-end">
                        <div class="form-check form-switch">
                            <input class="form-check-input event-superhost" type="checkbox" role="switch" id="superhost-${event.id}" ${event.is_superhost ? 'checked' : ''}>
                            <label class="form-check-label" for="superhost-${event.id}">Uprawnienia Superhost</label>
                        </div>
                        <input type="file" class="logo-upload-input" style="display: none;" accept="image/png, image/jpeg">
                        <button class="btn btn-sm btn-danger btn-delete btn-fixed-width" ${deleteBtnVisibility}>Usuń Event</button>
                        <button class="btn btn-sm btn-danger btn-reset btn-fixed-width">Reset Gry</button>
                        <a href="/admin/impersonate/${event.id}" target="_blank" class="btn btn-sm btn-secondary btn-fixed-width">Panel Hosta</a>
                        <button class="btn btn-sm btn-success btn-save btn-fixed-width">Zapisz Zmiany</button>
                    </div>
                </div>
            </div>`;

        // Auto-resize textarea
        const textarea = panel.querySelector('.notes-textarea');
        textarea.addEventListener('input', () => {
            textarea.style.height = 'auto';
            textarea.style.height = (textarea.scrollHeight) + 'px';
        });
        // Initial resize
        setTimeout(() => textarea.dispatchEvent(new Event('input')), 0);

        return panel;
    }

    async function loadEvents() {
        const events = await fetchApi('/api/admin/events');
        if (events) {
            eventsContainer.innerHTML = '';
            events.forEach(event => eventsContainer.appendChild(createEventPanel(event)));
        } else {
            eventsContainer.innerHTML = '<div class="alert alert-warning">Nie udało się załadować eventów.</div>';
        }
    }

    addEventBtn.addEventListener('click', async () => {
        addEventBtn.disabled = true;
        const newEvent = await fetchApi('/api/admin/events', { method: 'POST' });
        if (newEvent) {
            eventsContainer.appendChild(createEventPanel(newEvent));
            showStatus(`Dodano pomyślnie ${newEvent.name}.`);
        }
        addEventBtn.disabled = false;
    });

    eventsContainer.addEventListener('click', async (e) => {
        const target = e.target;
        const panel = target.closest('.card');
        if (!panel) return;
        const eventId = panel.dataset.eventId;

        if (target.classList.contains('btn-logo')) {
            panel.querySelector('.logo-upload-input').click();
        }

        if (target.classList.contains('btn-delete-logo')) {
            const confirmed = confirm(`Czy na pewno chcesz usunąć logo dla Eventu ${eventId}?`);
            if (confirmed) {
                const result = await fetchApi(`/api/admin/event/${eventId}/delete_logo`, { method: 'POST' });
                if (result) {
                    const logoArea = panel.querySelector('.logo-area');
                    logoArea.innerHTML = `<span class="logo-placeholder">Brak logo</span>`;
                    target.style.display = 'none';
                    showStatus(result.message);
                }
            }
        }

        if (target.classList.contains('btn-save')) {
            const payload = {
                name: panel.querySelector('.event-name').value,
                login: panel.querySelector('.event-login').value,
                password: panel.querySelector('.event-password').value,
                is_superhost: panel.querySelector('.event-superhost').checked,
                event_date: panel.querySelector('.event-date').value,
                notes: panel.querySelector('.event-notes').value
            };
            const result = await fetchApi(`/api/admin/event/${eventId}`, { method: 'PUT', body: payload });
            if (result) {
                 showStatus(`Zapisano zmiany dla Eventu ${eventId}.`);
                 const updatedPanel = createEventPanel(result);
                 panel.replaceWith(updatedPanel);
            }
        }

        if (target.classList.contains('btn-reset')) {
            const hostPassword = panel.querySelector('.event-password').value;
            const enteredPassword = prompt(`Aby zresetować grę dla Eventu ${eventId}, wpisz hasło Hosta:`);
            if (enteredPassword !== null) {
                if (enteredPassword === hostPassword) {
                    const result = await fetchApi(`/api/admin/event/${eventId}/reset`, { method: 'POST' });
                    if (result) {
                        showStatus(result.message, 'warning');
                        loadEvents();
                    }
                } else if (enteredPassword) {
                    showStatus('Nieprawidłowe hasło. Resetowanie gry anulowane.', 'danger');
                }
            }
        }

        if (target.classList.contains('btn-delete')) {
            const hostPassword = panel.querySelector('.event-password').value;
            const enteredPassword = prompt(`Aby USUNĄĆ Event ${eventId}, wpisz hasło Hosta:`);
             if (enteredPassword !== null) {
                if (enteredPassword === hostPassword) {
                    const result = await fetchApi(`/api/admin/event/${eventId}`, { method: 'DELETE' });
                    if (result) {
                        panel.remove();
                        showStatus(result.message, 'success');
                    }
                } else if (enteredPassword) {
                    showStatus('Nieprawidłowe hasło. Usuwanie eventu anulowane.', 'danger');
                }
            }
        }
    });

    eventsContainer.addEventListener('change', async (e) => {
        if (e.target.classList.contains('logo-upload-input')) {
            const file = e.target.files[0];
            if (!file) return;

            const panel = e.target.closest('.card');
            const eventId = panel.dataset.eventId;
            const formData = new FormData();
            formData.append('logo', file);

            const result = await fetchApi(`/api/admin/event/${eventId}/upload_logo`, { method: 'POST', body: formData });

            if (result && result.logo_url) {
                const logoArea = panel.querySelector('.logo-area');
                logoArea.innerHTML = `<img src="${result.logo_url}?t=${new Date().getTime()}" class="event-logo-preview">`;
                panel.querySelector('.btn-delete-logo').style.display = 'inline-block';
                showStatus('Logo zostało zaktualizowane.');
            }
        }
    });

    loadEvents();

    // ========================================
    // DARK MODE TOGGLE
    // ========================================

    const darkModeToggle = document.getElementById('dark-mode-toggle');
    const darkModeStatus = document.getElementById('dark-mode-status');

    // Function to apply dark mode
    function applyDarkMode(enabled) {
        if (enabled) {
            document.body.classList.add('dark-mode');
            darkModeStatus.textContent = 'Włączony';
            darkModeStatus.className = 'badge bg-success';
        } else {
            document.body.classList.remove('dark-mode');
            darkModeStatus.textContent = 'Wyłączony';
            darkModeStatus.className = 'badge bg-secondary';
        }
    }

    // Load dark mode preference from localStorage (default: enabled)
    const darkModeEnabled = localStorage.getItem('darkModeAdmin') !== 'false';
    if (darkModeToggle) {
        darkModeToggle.checked = darkModeEnabled;
        applyDarkMode(darkModeEnabled);

        // Dark mode toggle event listener
        darkModeToggle.addEventListener('change', (e) => {
            const enabled = e.target.checked;
            applyDarkMode(enabled);
            localStorage.setItem('darkModeAdmin', enabled ? 'true' : 'false');
        });
    }
});
