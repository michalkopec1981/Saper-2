/**
 * HOST PLAYERS MODULE
 * Zarządzanie graczami - lista, edycja, ostrzeganie, wiadomości
 * Zabezpieczenia IP/Fingerprint
 *
 * Używa: window.translations, window.socket, window.currentLanguage
 * Eksportuje: loadPlayers, loadSecurityStats, updateSecurityLimits, cleanupDuplicates
 */

document.addEventListener('DOMContentLoaded', function () {
    const socket = window.socket;

    let currentEditPlayerId = null;
    let currentMessagePlayerId = null;

    // =====================================================================
    // LOAD PLAYERS
    // =====================================================================
    function loadPlayers() {
        const translations = window.translations;
        const currentLanguage = window.currentLanguage || 'pl';

        fetch('/api/host/players')
            .then(res => res.json())
            .then(players => {
                const list = document.getElementById('players-list');
                if (!list) return;

                if (players.length === 0) {
                    list.innerHTML = `<p class="text-muted">Brak graczy</p>`;
                    return;
                }

                list.innerHTML = `
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>${translations[currentLanguage].player_count.replace(':', '')}</th>
                                <th>Punkty</th>
                                <th>% ukończenia</th>
                                <th>${translations[currentLanguage].warnings}</th>
                                <th>Akcje</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${players.map(p => `
                                <tr>
                                    <td>${p.name}</td>
                                    <td>${p.score}</td>
                                    <td>${p.completion_percentage !== undefined ? p.completion_percentage + '%' : '-'}</td>
                                    <td>${p.warnings}</td>
                                    <td>
                                        <button class="btn btn-sm btn-info send-message-btn" data-id="${p.id}" data-name="${p.name}">${translations[currentLanguage].send_player_message}</button>
                                        <button class="btn btn-sm btn-warning warn-player-btn" data-id="${p.id}">${translations[currentLanguage].warn}</button>
                                        <button class="btn btn-sm btn-primary edit-player-btn" data-id="${p.id}" data-name="${p.name}" data-score="${p.score}">Edycja</button>
                                        <button class="btn btn-sm btn-danger delete-player-btn" data-id="${p.id}">${translations[currentLanguage].delete}</button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;

                // Attach event listeners
                document.querySelectorAll('.send-message-btn').forEach(btn => {
                    btn.addEventListener('click', () => {
                        openMessageModal(parseInt(btn.dataset.id), btn.dataset.name);
                    });
                });
                document.querySelectorAll('.warn-player-btn').forEach(btn => {
                    btn.addEventListener('click', () => warnPlayer(parseInt(btn.dataset.id)));
                });
                document.querySelectorAll('.edit-player-btn').forEach(btn => {
                    btn.addEventListener('click', () => {
                        openEditPlayerModal(parseInt(btn.dataset.id), btn.dataset.name, parseInt(btn.dataset.score));
                    });
                });
                document.querySelectorAll('.delete-player-btn').forEach(btn => {
                    btn.addEventListener('click', () => deletePlayer(parseInt(btn.dataset.id)));
                });
            });
    }

    // =====================================================================
    // WARN PLAYER
    // =====================================================================
    async function warnPlayer(id) {
        try {
            const response = await fetch(`/api/host/player/${id}/warn`, { method: 'POST' });
            if (!response.ok) throw new Error('Błąd ostrzeżenia gracza');
            loadPlayers();
        } catch (error) {
            alert('Błąd: ' + error.message);
        }
    }

    // =====================================================================
    // DELETE PLAYER
    // =====================================================================
    async function deletePlayer(id) {
        if (!confirm('Czy na pewno chcesz usunąć tego gracza?')) return;

        try {
            const response = await fetch(`/api/host/player/${id}`, { method: 'DELETE' });
            if (!response.ok) throw new Error('Błąd usuwania gracza');
            loadPlayers();
        } catch (error) {
            alert('Błąd: ' + error.message);
        }
    }

    // =====================================================================
    // EDIT PLAYER MODAL
    // =====================================================================
    function openEditPlayerModal(playerId, playerName, playerScore) {
        currentEditPlayerId = playerId;

        document.getElementById('edit-player-name').value = playerName;
        document.getElementById('edit-player-score').value = playerScore;

        const modal = new bootstrap.Modal(document.getElementById('editPlayerModal'));
        modal.show();
    }

    document.getElementById('save-player-edit-btn')?.addEventListener('click', async () => {
        const newName = document.getElementById('edit-player-name').value.trim();
        const newScore = parseInt(document.getElementById('edit-player-score').value);

        if (!newName) {
            alert('Proszę podać nazwę gracza');
            return;
        }

        if (isNaN(newScore) || newScore < 0) {
            alert('Proszę podać prawidłową liczbę punktów');
            return;
        }

        try {
            const response = await fetch(`/api/host/player/${currentEditPlayerId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: newName,
                    score: newScore
                })
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Błąd aktualizacji gracza');
            }

            const modal = bootstrap.Modal.getInstance(document.getElementById('editPlayerModal'));
            modal.hide();

            loadPlayers();
            alert('Gracz został zaktualizowany');
        } catch (error) {
            alert('Błąd: ' + error.message);
        }
    });

    // =====================================================================
    // SEND MESSAGE TO PLAYER
    // =====================================================================
    function openMessageModal(playerId, playerName) {
        const translations = window.translations;
        const currentLanguage = window.currentLanguage || 'pl';
        currentMessagePlayerId = playerId;

        document.getElementById('message-modal-title').textContent =
            translations[currentLanguage].message_to_player + ': ' + playerName;

        document.getElementById('message-content-label').textContent =
            translations[currentLanguage].message_content;

        const messageInput = document.getElementById('player-message-input');
        messageInput.value = '';
        document.getElementById('message-char-count').textContent = '0';

        const modal = new bootstrap.Modal(document.getElementById('sendMessageModal'));
        modal.show();
    }

    document.getElementById('player-message-input')?.addEventListener('input', (e) => {
        const length = e.target.value.length;
        document.getElementById('message-char-count').textContent = length;
    });

    document.getElementById('send-message-to-player-btn')?.addEventListener('click', async () => {
        const message = document.getElementById('player-message-input').value.trim();

        if (!message) {
            alert('Proszę wpisać wiadomość');
            return;
        }

        if (message.length > 120) {
            alert('Wiadomość może mieć maksymalnie 120 znaków');
            return;
        }

        try {
            socket.emit('host_message_to_player', {
                player_id: currentMessagePlayerId,
                message: message,
                event_id: window.EVENT_ID
            });

            const modal = bootstrap.Modal.getInstance(document.getElementById('sendMessageModal'));
            modal.hide();

            alert('Wiadomość wysłana do gracza');
        } catch (error) {
            alert('Błąd wysyłania wiadomości: ' + error.message);
        }
    });

    // =====================================================================
    // SECURITY STATS
    // =====================================================================
    async function loadSecurityStats() {
        try {
            const response = await fetch('/api/host/registration/limits');
            const data = await response.json();

            document.getElementById('limit-ip').value = data.limits.max_players_per_ip;
            document.getElementById('limit-device').value = data.limits.max_players_per_device;

            let html = `
                <div class="row text-center mb-3">
                    <div class="col-md-3">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h3 class="mb-0">${data.stats.total_players}</h3>
                                <small class="text-muted">Graczy</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h3 class="mb-0">${data.stats.unique_ips}</h3>
                                <small class="text-muted">Unikalne IP</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h3 class="mb-0">${data.stats.unique_devices}</h3>
                                <small class="text-muted">Urządzeń</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card ${data.stats.suspicious_devices_count > 0 ? 'bg-warning' : 'bg-success'} text-white">
                            <div class="card-body">
                                <h3 class="mb-0">${data.stats.suspicious_devices_count}</h3>
                                <small>Podejrzanych</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            if (Object.keys(data.suspicious_devices).length > 0) {
                html += '<div class="alert alert-warning"><strong>Podejrzane urządzenia (wiele kont):</strong><ul class="mb-0">';

                for (const [fp, players] of Object.entries(data.suspicious_devices)) {
                    const fpShort = fp.substring(0, 12) + '...';
                    html += `<li><strong>Urządzenie ${fpShort}:</strong> ${players.length} graczy<ul>`;
                    players.forEach(p => {
                        html += `<li>${p.name} (${p.score} pkt, IP: ${p.ip})</li>`;
                    });
                    html += `</ul></li>`;
                }

                html += '</ul></div>';
            }

            if (Object.keys(data.suspicious_ips).length > 0) {
                html += '<div class="alert alert-info"><strong>IP z wieloma graczami (może być OK dla WiFi):</strong><ul class="mb-0">';

                for (const [ip, players] of Object.entries(data.suspicious_ips)) {
                    html += `<li><strong>${ip}:</strong> ${players.length} graczy<ul>`;
                    players.forEach(p => {
                        const fpInfo = p.fingerprint ? ` (Urządzenie: ${p.fingerprint})` : '';
                        html += `<li>${p.name} (${p.score} pkt)${fpInfo}</li>`;
                    });
                    html += `</ul></li>`;
                }

                html += '</ul></div>';
            }

            if (Object.keys(data.suspicious_devices).length === 0 && Object.keys(data.suspicious_ips).length === 0) {
                html += '<div class="alert alert-success">Wszystko wygląda OK! Brak podejrzanych rejestracji.</div>';
            }

            document.getElementById('security-stats').innerHTML = html;

        } catch (error) {
            alert('Błąd ładowania statystyk: ' + error.message);
        }
    }

    async function updateSecurityLimits() {
        const limitIP = parseInt(document.getElementById('limit-ip').value);
        const limitDevice = parseInt(document.getElementById('limit-device').value);

        try {
            const response = await fetch('/api/host/registration/limits', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    max_players_per_ip: limitIP,
                    max_players_per_device: limitDevice
                })
            });

            const data = await response.json();
            alert(data.message || 'Limity zaktualizowane!');
            loadSecurityStats();

        } catch (error) {
            alert('Błąd: ' + error.message);
        }
    }

    async function cleanupDuplicates(strategy) {
        const confirmMessage =
            strategy === 'fingerprint' ? 'Usuń duplikaty według urządzeń? (zostawi najlepszego gracza z każdego urządzenia)' :
            strategy === 'ip' ? 'Usuń duplikaty według IP? (zostawi najlepszych graczy według limitu IP)' :
            'Usuń wszystkie duplikaty? (połączenie obu metod)';

        if (!confirm(confirmMessage)) return;

        try {
            const response = await fetch('/api/host/registration/cleanup_duplicates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ strategy })
            });

            const data = await response.json();
            alert(`${data.message}\n\nUsunięto: ${data.removed_count} graczy`);

            loadSecurityStats();
            loadPlayers();

        } catch (error) {
            alert('Błąd: ' + error.message);
        }
    }

    // =====================================================================
    // TAB EVENT LISTENERS
    // =====================================================================
    document.querySelector('button[data-bs-target="#players"]')?.addEventListener('click', () => {
        loadPlayers();
        setTimeout(() => loadSecurityStats(), 100);
    });

    // =====================================================================
    // EXPORTS
    // =====================================================================
    window.loadPlayers = loadPlayers;
    window.loadSecurityStats = loadSecurityStats;
    window.updateSecurityLimits = updateSecurityLimits;
    window.cleanupDuplicates = cleanupDuplicates;
});
