// Translations
const translations = {
    pl: {
        time_remaining: 'Czas do końca',
        active_players: 'Aktywni gracze',
        your_points: 'Twoje punkty',
        points_earned: 'Zdobyte punkty',
        points_available: 'Możliwe punkty',
        time_speed: 'Tempo czasu',
        point_bonus: 'Premia punktowa',
        btn_password: 'Hasło',
        btn_scan: 'Skanuj',
        btn_selfie: 'Selfie',
        password_title: 'Hasło do odkrycia',
        scan_title: 'Skanuj kod QR',
        scan_instruction: 'Skieruj kamerę na kod QR',
        selfie_title: 'Galeria zabawnych selfie',
        vote: 'Zagłosuj',
        voted: 'Zagłosowano'
    },
    en: {
        time_remaining: 'Time Remaining',
        active_players: 'Active Players',
        your_points: 'Your Points',
        points_earned: 'Points Earned',
        points_available: 'Available Points',
        time_speed: 'Time Speed',
        point_bonus: 'Point Bonus',
        btn_password: 'Password',
        btn_scan: 'Scan',
        btn_selfie: 'Selfies',
        password_title: 'Password to Discover',
        scan_title: 'Scan QR Code',
        scan_instruction: 'Point camera at QR code',
        selfie_title: 'Funny Selfie Gallery',
        vote: 'Vote',
        voted: 'Voted'
    },
    de: {
        time_remaining: 'Verbleibende Zeit',
        active_players: 'Aktive Spieler',
        your_points: 'Deine Punkte',
        points_earned: 'Verdiente Punkte',
        points_available: 'Verfügbare Punkte',
        time_speed: 'Zeitgeschwindigkeit',
        point_bonus: 'Punktebonus',
        btn_password: 'Passwort',
        btn_scan: 'Scannen',
        btn_selfie: 'Selfies',
        password_title: 'Passwort zu entdecken',
        scan_title: 'QR-Code scannen',
        scan_instruction: 'Richten Sie die Kamera auf den QR-Code',
        selfie_title: 'Lustige Selfie-Galerie',
        vote: 'Abstimmen',
        voted: 'Abgestimmt'
    }
};

document.addEventListener('DOMContentLoaded', function() {
    const eventId = {{ event_id }};
    const playerId = {{ player_id }};
    let currentLang = localStorage.getItem('dashboard_lang') || 'pl';
    let html5QrCode = null;
    let votedPhotos = JSON.parse(localStorage.getItem(`voted_photos_${eventId}`) || '[]');

    const socket = io();

    // Initialize
    socket.on('connect', () => {
        console.log('Connected to server');
        socket.emit('join', { event_id: eventId });
        loadGameData();
    });

    // Language switching
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            currentLang = btn.dataset.lang;
            localStorage.setItem('dashboard_lang', currentLang);
            updateLanguage();

            document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });

        if (btn.dataset.lang === currentLang) {
            btn.classList.add('active');
        }
    });

    function updateLanguage() {
        const trans = translations[currentLang];
        document.querySelectorAll('[data-lang]').forEach(el => {
            const key = el.dataset.lang;
            if (trans[key]) {
                if (el.tagName === 'BUTTON' && el.querySelector('span[data-lang]')) {
                    el.querySelector('span[data-lang]').textContent = trans[key];
                } else {
                    el.textContent = trans[key];
                }
            }
        });
    }

    // Load game data
    async function loadGameData() {
        try {
            const response = await fetch(`/api/player_dashboard/state?event_id=${eventId}&player_id=${playerId}`);
            const data = await response.json();

            if (data.error) {
                console.error('Error loading game data:', data.error);
                return;
            }

            updateDashboard(data);
        } catch (error) {
            console.error('Failed to load game data:', error);
        }
    }

    function updateDashboard(data) {
        // Game name
        document.getElementById('game-name').textContent = data.game_name || 'Saper Event';

        // Players
        document.getElementById('active-players').textContent = data.active_players || 0;

        // Points
        document.getElementById('player-points').textContent = data.player_score || 0;
        document.getElementById('total-earned').textContent = data.total_points_earned || 0;
        document.getElementById('points-available').textContent = data.points_available || 0;

        // Multipliers
        document.getElementById('time-speed').textContent = 'x' + (data.time_speed || 1);
        document.getElementById('point-bonus').textContent = 'x' + (data.point_bonus || 1);

        // Timer
        if (data.time_remaining !== undefined) {
            updateTimer(data.time_remaining);
        }

        // Password
        if (data.password_display) {
            document.getElementById('password-display').textContent = data.password_display;
        }

        // Host message
        if (data.host_message && data.host_message.trim()) {
            showMessage(data.host_message);
        } else {
            // Hide message if empty
            const messageBox = document.getElementById('message-box');
            messageBox.classList.remove('visible');
        }
    }

    function updateTimer(seconds) {
        if (seconds < 0) seconds = 0;
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        document.getElementById('timer-display').textContent =
            String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
    }

    function showMessage(text) {
        const messageBox = document.getElementById('message-box');
        const messageText = document.getElementById('message-text');
        messageText.textContent = text;
        messageBox.classList.add('visible');
    }

    // WebSocket events
    socket.on('game_state_update', (data) => {
        updateDashboard(data);
    });

    socket.on('host_message', (data) => {
        if (data.message) {
            showMessage(data.message);
        }
    });

    socket.on('password_update', (data) => {
        if (data.password_display) {
            document.getElementById('password-display').textContent = data.password_display;
        }
    });

    socket.on('timer_tick', (data) => {
        if (data.time_left !== undefined) {
            updateTimer(data.time_left);
        }
    });

    socket.on('leaderboard_update', (data) => {
        // Update player score if in leaderboard
        const player = data.find(p => p.id === playerId);
        if (player) {
            document.getElementById('player-points').textContent = player.score;
        }
    });

    socket.on('game_over', () => {
        showMessage('⏰ Gra zakończona!');
    });

    // Button handlers
    document.getElementById('btn-password').addEventListener('click', () => {
        openModal('password-modal');
    });

    document.getElementById('btn-scan').addEventListener('click', () => {
        openModal('scanner-modal');
        startQRScanner();
    });

    document.getElementById('btn-selfie').addEventListener('click', async () => {
        openModal('selfie-modal');
        await loadSelfies();
    });

    // Modal functions
    function openModal(modalId) {
        document.getElementById(modalId).classList.add('active');
    }

    window.closeModal = function(modalId) {
        document.getElementById(modalId).classList.remove('active');
        if (modalId === 'scanner-modal' && html5QrCode) {
            html5QrCode.stop();
        }
    }

    // QR Scanner
    function startQRScanner() {
        const qrReaderEl = document.getElementById('qr-reader');
        qrReaderEl.innerHTML = '';

        html5QrCode = new Html5Qrcode("qr-reader");

        html5QrCode.start(
            { facingMode: "environment" },
            { fps: 10, qrbox: 250 },
            (decodedText) => {
                console.log('QR Code scanned:', decodedText);
                html5QrCode.stop();
                closeModal('scanner-modal');
                handleQRScan(decodedText);
            },
            (errorMessage) => {
                // Ignore scan errors
            }
        ).catch(err => {
            console.error('Unable to start scanner:', err);
            alert('Nie można uruchomić skanera. Sprawdź uprawnienia do kamery.');
        });
    }

    async function handleQRScan(qrCode) {
        try {
            // Redirect to player page with scanned QR code
            window.location.href = `/player/${eventId}/${qrCode}`;
        } catch (error) {
            console.error('Error handling QR scan:', error);
        }
    }

    // Selfie gallery
    async function loadSelfies() {
        try {
            const response = await fetch(`/api/player/selfies?event_id=${eventId}`);
            const data = await response.json();

            const gallery = document.getElementById('selfie-gallery');
            gallery.innerHTML = '';

            if (!data.selfies || data.selfies.length === 0) {
                gallery.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: #999;">Brak zdjęć</p>';
                return;
            }

            data.selfies.forEach(selfie => {
                const hasVoted = votedPhotos.includes(selfie.id);
                const item = document.createElement('div');
                item.className = 'selfie-item';
                item.innerHTML = `
                    <img src="${selfie.image_url}" alt="${selfie.player_name}">
                    <div class="selfie-info">
                        <div>${selfie.player_name}</div>
                        <div>❤️ ${selfie.votes}</div>
                        <button class="vote-btn" data-id="${selfie.id}" ${hasVoted ? 'disabled' : ''}>
                            ${hasVoted ? translations[currentLang].voted : translations[currentLang].vote}
                        </button>
                    </div>
                `;
                gallery.appendChild(item);
            });

            // Add vote handlers
            document.querySelectorAll('.vote-btn').forEach(btn => {
                btn.addEventListener('click', () => voteSelfie(btn.dataset.id));
            });
        } catch (error) {
            console.error('Error loading selfies:', error);
        }
    }

    async function voteSelfie(photoId) {
        try {
            const response = await fetch('/api/player/selfie/vote', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    photo_id: parseInt(photoId),
                    player_id: playerId,
                    event_id: eventId
                })
            });

            const data = await response.json();

            if (data.success) {
                votedPhotos.push(parseInt(photoId));
                localStorage.setItem(`voted_photos_${eventId}`, JSON.stringify(votedPhotos));
                await loadSelfies(); // Reload gallery
            } else {
                alert(data.message || 'Błąd głosowania');
            }
        } catch (error) {
            console.error('Error voting:', error);
        }
    }

    // Initialize language
    updateLanguage();

    // Refresh data periodically
    setInterval(loadGameData, 5000);
});
