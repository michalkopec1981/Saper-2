/**
 * HOST CORE MODULE
 * Rdzen panelu hosta - tłumaczenia, Socket.IO, sterowanie grą
 *
 * Eksportuje do window: translations, socket, currentLanguage, EVENT_ID, IS_SUPERHOST
 * Funkcje: formatTime, translatePage, updateUI, sendGameControl
 */

// =====================================================================
// TRANSLATIONS
// =====================================================================
const translations = {
    pl: {
        host_title: 'ORGANIZACJA GRY',
        open_display: 'Otwórz Ekran Gry',
        tab_game: 'Gra',
        tab_players: 'Gracze',
        tab_questions: 'Pytania runda 1',
        tab_minigames: 'Minigry',
        tab_qrcodes: 'Kody QR',
        tab_password: 'Hasło',
        tab_photo: 'Foto',
        tab_ar: 'AR',
        tab_fortune: 'Wróżka AI',
        fortune_title: 'Wróżka AI - atrakcja wykorzystująca sztuczną inteligencję',
        fortune_description: 'Gracze po zeskanowaniu kodu QR otrzymują możliwość opisania ostatniego snu, by uzyskać przepowiednię.',
        tab_display: 'Wyświetlacz',
        tab_language: 'Język',
        password_tab: 'Hasło do odsłonięcia',
        password_description: 'Tutaj będzie widoczne hasło, które gracze muszą odsłonić podczas gry.',
        photo_tab: 'Galeria zdjęć',
        photo_description: 'Tutaj będą widoczne zdjęcia przesłane przez graczy.',
        ar_tab: 'Rozszerzona rzeczywistość (AR)',
        ar_description: 'Tutaj będą dostępne funkcje AR.',
        display_tab: 'Ustawienia wyświetlacza',
        display_screens: 'Liczba ekranów zewnętrznych:',
        one_screen: '1 Ekran',
        two_screens: '2 Ekrany',
        three_screens: '3 Ekrany',
        four_screens: '4 Ekrany',
        language_tab: 'Ustawienia języka',
        game_info: 'Informacje o grze',
        player_count: 'Liczba graczy:',
        completion_percentage: 'Procent ukończenia:',
        language_host_label: 'Język prowadzącego:',
        time_left: 'Czas do końca:',
        time_net: 'Czas gry (netto):',
        time_gross: 'Czas gry (brutto):',
        current_bonus: 'Aktualna premia:',
        current_speed: 'Aktualne tempo:',
        game_status_label: 'Stan gry:',
        game_status_waiting: 'Oczekiwanie na Start',
        game_status_active: 'Start. Gra aktywna',
        game_status_paused: 'Pauza',
        game_status_stopped: 'Stop. Zakończenie gry',
        pre_game_settings: 'Obsługa gry',
        game_duration_label: 'Czas gry (minuty):',
        game_duration_help: 'Przed grą: ustaw czas. Podczas gry: zmień czas (wymaga hasła)',
        set_time_btn: 'OK',
        player_language: 'Język graczy',
        host_language: 'Język prowadzącego',
        lang_polish: 'Język polski',
        lang_english: 'Język angielski',
        lang_german: 'Język niemiecki',
        start_game: 'Start Gry',
        in_game_settings: 'Tempo gry oraz punktacja',
        points_bonus: 'Premia punktowa:',
        time_speed: 'Tempo czasu:',
        pause: 'Pauza',
        resume: 'Wznów',
        force_win: 'Przedwczesna wygrana',
        stop_game: 'Stop Gry',
        reset_game: 'Reset Gry',
        quick_access: 'Szybki dostęp do zakładek:',
        questions_management: 'Zarządzanie pytaniami',
        players_management: 'Zarządzanie graczami',
        add_question: 'Dodaj pytanie',
        question_modal_title: 'Dodaj pytanie',
        question_text: 'Treść pytania:',
        answers: 'Odpowiedzi:',
        difficulty_level: 'Poziom trudności:',
        easy: 'Łatwy',
        medium: 'Średni',
        hard: 'Trudny',
        letter_reveal: 'Litera do odsłonięcia:',
        cancel: 'Anuluj',
        save: 'Zapisz',
        edit: 'Edytuj',
        delete: 'Usuń',
        shown: 'Wyświetlono',
        correct: 'Poprawne',
        times: 'razy',
        admin_impersonate: 'Jesteś zalogowany jako Admin w panelu Hosta.',
        back_to_admin: 'Powrót do panelu Admina',
        warn: 'Ostrzeż',
        warnings: 'Ostrzeżenia',
        send_player_message: 'Wyślij wiadomość',
        message_to_player: 'Wiadomość do gracza',
        message_content: 'Treść wiadomości (max 120 znaków):',
        send: 'Wyślij',
        question_category: 'Kategoria pytania:',
        category_company: 'Firmowe',
        category_world: 'Światowe',
        host_messages: 'Komunikaty na ekran gry',
        messages_description: 'Wyślij komunikat, który pojawi się na głównym ekranie gry. Użyj tego, aby przekazać ważne informacje wszystkim uczestnikom.',
        message_label: 'Treść komunikatu (max 500 znaków):',
        send_message: 'Wyślij komunikat',
        password_preview: 'Hasło',
        tab_timing: 'Czas i tempo',
        timing_settings: 'Czas i tempo gry',
        display_panel: 'Wyświetlacz',
        display_panel_description: 'Otwórz ekrany gry lub przejdź do ustawień wyświetlacza.',
        display_settings: 'Ustawienia',
    },
    en: {
        host_title: 'GAME ORGANIZATION',
        open_display: 'Open Game Display',
        tab_game: 'Game',
        tab_players: 'Players',
        tab_questions: 'Questions',
        tab_minigames: 'Minigames',
        tab_qrcodes: 'QR Codes',
        tab_password: 'Password',
        tab_photo: 'Photo',
        tab_ar: 'AR',
        tab_fortune: 'Fortune Teller AI',
        fortune_title: 'Fortune Teller AI - attraction using artificial intelligence',
        fortune_description: 'Players after scanning the QR code get the opportunity to describe their last dream to get a prediction.',
        tab_display: 'Display',
        tab_language: 'Language',
        password_tab: 'Password to reveal',
        password_description: 'Here you will see the password that players must reveal during the game.',
        photo_tab: 'Photo gallery',
        photo_description: 'Here you will see photos uploaded by players.',
        ar_tab: 'Augmented Reality (AR)',
        ar_description: 'AR features will be available here.',
        display_tab: 'Display settings',
        display_screens: 'Number of external screens:',
        one_screen: '1 Screen',
        two_screens: '2 Screens',
        three_screens: '3 Screens',
        four_screens: '4 Screens',
        language_tab: 'Language settings',
        game_info: 'Game information',
        player_count: 'Number of players:',
        completion_percentage: 'Completion percentage:',
        language_host_label: 'Host language:',
        time_left: 'Time left:',
        time_net: 'Game time (net):',
        time_gross: 'Game time (gross):',
        current_bonus: 'Current bonus:',
        current_speed: 'Current speed:',
        game_status_label: 'Game status:',
        game_status_waiting: 'Waiting for Start',
        game_status_active: 'Start. Game active',
        game_status_paused: 'Pause',
        game_status_stopped: 'Stop. Game ended',
        pre_game_settings: 'Game Control',
        game_duration_label: 'Game time (minutes):',
        game_duration_help: 'Before game: set time. During game: change time (requires password)',
        set_time_btn: 'OK',
        player_language: 'Players language',
        host_language: 'Host language',
        lang_polish: 'Polish language',
        lang_english: 'English language',
        lang_german: 'German language',
        start_game: 'Start Game',
        in_game_settings: 'Game Speed and Scoring',
        points_bonus: 'Points bonus:',
        time_speed: 'Time speed:',
        pause: 'Pause',
        resume: 'Resume',
        force_win: 'Force Win',
        stop_game: 'Stop Game',
        reset_game: 'Reset Game',
        quick_access: 'Quick access to tabs:',
        questions_management: 'Questions management',
        players_management: 'Players management',
        add_question: 'Add question',
        question_modal_title: 'Add question',
        question_text: 'Question text:',
        answers: 'Answers:',
        difficulty_level: 'Difficulty level:',
        easy: 'Easy',
        medium: 'Medium',
        hard: 'Hard',
        letter_reveal: 'Letter to reveal:',
        cancel: 'Cancel',
        save: 'Save',
        edit: 'Edit',
        delete: 'Delete',
        shown: 'Shown',
        correct: 'Correct',
        times: 'times',
        admin_impersonate: 'You are logged in as Admin in Host panel.',
        back_to_admin: 'Back to Admin panel',
        warn: 'Warn',
        warnings: 'Warnings',
        send_player_message: 'Send message',
        message_to_player: 'Message to player',
        message_content: 'Message content (max 120 characters):',
        send: 'Send',
        question_category: 'Question category:',
        category_company: 'Company',
        category_world: 'World',
        host_messages: 'Messages on game screen',
        messages_description: 'Send a message that will appear on the main game screen. Use this to share important information with all participants.',
        message_label: 'Message content (max 500 characters):',
        send_message: 'Send message',
        password_preview: 'Password',
        tab_timing: 'Time & Speed',
        timing_settings: 'Game Time and Speed',
        display_panel: 'Display',
        display_panel_description: 'Open game screens or go to display settings.',
        display_settings: 'Settings',
    },
    de: {
        host_title: 'SPIELORGANISATION',
        open_display: 'Spielbildschirm öffnen',
        tab_game: 'Spiel',
        tab_players: 'Spieler',
        tab_questions: 'Fragen',
        tab_minigames: 'Minispiele',
        tab_qrcodes: 'QR-Codes',
        tab_password: 'Passwort',
        tab_photo: 'Foto',
        tab_ar: 'AR',
        tab_fortune: 'Wahrsagerin AI',
        fortune_title: 'Wahrsagerin AI - Attraktion mit künstlicher Intelligenz',
        fortune_description: 'Spieler erhalten nach dem Scannen des QR-Codes die Möglichkeit, ihren letzten Traum zu beschreiben, um eine Vorhersage zu erhalten.',
        tab_display: 'Anzeige',
        tab_language: 'Sprache',
        password_tab: 'Zu enthüllendes Passwort',
        password_description: 'Hier sehen Sie das Passwort, das die Spieler während des Spiels aufdecken müssen.',
        photo_tab: 'Fotogalerie',
        photo_description: 'Hier sehen Sie von Spielern hochgeladene Fotos.',
        ar_tab: 'Erweiterte Realität (AR)',
        ar_description: 'AR-Funktionen werden hier verfügbar sein.',
        display_tab: 'Anzeigeeinstellungen',
        display_screens: 'Anzahl externer Bildschirme:',
        one_screen: '1 Bildschirm',
        two_screens: '2 Bildschirme',
        three_screens: '3 Bildschirme',
        four_screens: '4 Bildschirme',
        language_tab: 'Spracheinstellungen',
        game_info: 'Spielinformationen',
        player_count: 'Anzahl der Spieler:',
        completion_percentage: 'Abschlussrate:',
        language_host_label: 'Moderatorsprache:',
        time_left: 'Verbleibende Zeit:',
        time_net: 'Spielzeit (netto):',
        time_gross: 'Spielzeit (brutto):',
        current_bonus: 'Aktueller Bonus:',
        current_speed: 'Aktuelle Geschwindigkeit:',
        game_status_label: 'Spielstatus:',
        game_status_waiting: 'Warten auf Start',
        game_status_active: 'Start. Spiel aktiv',
        game_status_paused: 'Pause',
        game_status_stopped: 'Stopp. Spiel beendet',
        pre_game_settings: 'Spielsteuerung',
        game_duration_label: 'Spielzeit (Minuten):',
        game_duration_help: 'Vor dem Spiel: Zeit einstellen. Während des Spiels: Zeit ändern (erfordert Passwort)',
        set_time_btn: 'OK',
        player_language: 'Spielersprache',
        host_language: 'Moderatorsprache',
        lang_polish: 'Polnische Sprache',
        lang_english: 'Englische Sprache',
        lang_german: 'Deutsche Sprache',
        start_game: 'Spiel starten',
        in_game_settings: 'Spielgeschwindigkeit und Punktzahl',
        points_bonus: 'Punktebonus:',
        time_speed: 'Zeitgeschwindigkeit:',
        pause: 'Pause',
        resume: 'Fortsetzen',
        force_win: 'Erzwungener Sieg',
        stop_game: 'Spiel stoppen',
        reset_game: 'Spiel zurücksetzen',
        quick_access: 'Schnellzugriff auf Registerkarten:',
        questions_management: 'Fragenverwaltung',
        players_management: 'Spielerverwaltung',
        add_question: 'Frage hinzufügen',
        question_modal_title: 'Frage hinzufügen',
        question_text: 'Fragetext:',
        answers: 'Antworten:',
        difficulty_level: 'Schwierigkeitsgrad:',
        easy: 'Einfach',
        medium: 'Mittel',
        hard: 'Schwer',
        letter_reveal: 'Zu enthüllender Buchstabe:',
        cancel: 'Abbrechen',
        save: 'Speichern',
        edit: 'Bearbeiten',
        delete: 'Löschen',
        shown: 'Angezeigt',
        correct: 'Richtig',
        times: 'Mal',
        admin_impersonate: 'Sie sind als Admin im Host-Panel angemeldet.',
        back_to_admin: 'Zurück zum Admin-Panel',
        warn: 'Warnen',
        warnings: 'Warnungen',
        question_category: 'Fragenkategorie:',
        category_company: 'Firma',
        category_world: 'Welt',
        host_messages: 'Nachrichten auf dem Spielbildschirm',
        messages_description: 'Senden Sie eine Nachricht, die auf dem Hauptspielbildschirm erscheint. Verwenden Sie dies, um wichtige Informationen mit allen Teilnehmern zu teilen.',
        message_label: 'Nachrichteninhalt (max. 500 Zeichen):',
        send_message: 'Nachricht senden',
        password_preview: 'Passwort',
        tab_timing: 'Zeit & Tempo',
        timing_settings: 'Spielzeit und Geschwindigkeit',
        display_panel: 'Anzeige',
        display_panel_description: 'Spielbildschirme öffnen oder zu den Anzeigeeinstellungen wechseln.',
        display_settings: 'Einstellungen',
    }
};

// =====================================================================
// GLOBAL STATE
// =====================================================================
let currentLanguage = 'pl';
let isTimerRunning = false;
let isGameActive = false;

// =====================================================================
// UTILITY FUNCTIONS
// =====================================================================
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function translatePage(lang) {
    currentLanguage = lang;
    window.currentLanguage = lang;
    document.querySelectorAll('[data-translate]').forEach(el => {
        const key = el.getAttribute('data-translate');
        if (translations[lang][key]) {
            if (el.tagName === 'INPUT' && el.type === 'button') {
                el.value = translations[lang][key];
            } else {
                el.textContent = translations[lang][key];
            }
        }
    });

    const pauseBtn = document.getElementById('pause-btn');
    if (pauseBtn && (pauseBtn.textContent.includes('Wznów') || pauseBtn.textContent.includes('Resume'))) {
        pauseBtn.textContent = translations[lang]['resume'];
    }

    updateGameStatusText();
}

function updateGameStatusText() {
    const statusEl = document.getElementById('info-game-status');
    if (!statusEl) return;

    const currentStatus = statusEl.dataset.status;
    if (!currentStatus) return;

    const statusTexts = {
        'waiting': translations[currentLanguage].game_status_waiting,
        'active': translations[currentLanguage].game_status_active,
        'paused': translations[currentLanguage].game_status_paused,
        'stopped': translations[currentLanguage].game_status_stopped
    };

    statusEl.textContent = statusTexts[currentStatus] || statusTexts['waiting'];
}

async function sendGameControl(control, value = null) {
    console.log('Sending game control:', control, value);
    try {
        const response = await fetch('/api/host/game_control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ control, value })
        });
        if (!response.ok) throw new Error('Server error');
        const result = await response.json();
        console.log('Game control response:', result);
    } catch (error) {
        console.error('Control error:', error);
    }
}

function updateUI(state) {
    console.log('Updating UI with state:', state);

    const infoElements = {
        playerCount: document.getElementById('info-player-count'),
        completionPercentage: document.getElementById('info-completion-percentage'),
        language: document.getElementById('info-language'),
        timeLeft: document.getElementById('info-time-left'),
        timeElapsed: document.getElementById('info-time-elapsed'),
        timeElapsedPauses: document.getElementById('info-time-elapsed-pauses'),
        bonus: document.getElementById('info-bonus'),
        speed: document.getElementById('info-speed'),
        gameStatus: document.getElementById('info-game-status')
    };

    if (infoElements.playerCount) infoElements.playerCount.textContent = state.player_count || 0;

    if (infoElements.completionPercentage) {
        infoElements.completionPercentage.textContent = `${state.completion_percentage || 0}%`;
    }

    if (infoElements.language) {
        const langText = state.language_host === 'en' ? 'English' : 'Polski';
        infoElements.language.textContent = langText;
    }

    if (infoElements.bonus) {
        const bonusVal = state.bonus_multiplier || 1;
        infoElements.bonus.textContent = bonusVal > 1 ? `x${bonusVal}` : 'Brak';

        document.querySelectorAll('[data-control="bonus"]').forEach(btn => {
            btn.classList.toggle('active-modifier', btn.dataset.value === String(bonusVal));
        });
    }

    if (infoElements.speed) {
        const speedVal = state.time_speed || 1;
        infoElements.speed.textContent = `x${speedVal}`;

        document.querySelectorAll('[data-control="speed"]').forEach(btn => {
            btn.classList.toggle('active-modifier', btn.dataset.value === String(speedVal));
        });
    }

    if (infoElements.gameStatus) {
        const statusEl = infoElements.gameStatus;
        const status = state.game_status || 'waiting';
        statusEl.dataset.status = status;

        statusEl.classList.remove('status-waiting', 'status-active', 'status-paused', 'status-stopped');
        statusEl.classList.add(`status-${status}`);

        updateGameStatusText();
    }

    const pauseBtn = document.getElementById('pause-btn');
    if (pauseBtn) {
        isTimerRunning = state.is_timer_running;
        pauseBtn.textContent = state.is_timer_running
            ? translations[currentLanguage].pause
            : translations[currentLanguage].resume;
    }

    isGameActive = state.game_active;
    window.isGameActive = isGameActive;

    toggleGameButtons(state.game_active);

    const preGameFieldset = document.getElementById('pre-game-settings');
    const inGameFieldset = document.getElementById('in-game-settings');
    const timingFieldset = document.getElementById('timing-settings');
    const setTimeBtn = document.getElementById('set-time-btn-2');

    if (state.game_active) {
        if (preGameFieldset) preGameFieldset.disabled = false;
        if (inGameFieldset) inGameFieldset.disabled = false;
        if (timingFieldset) timingFieldset.disabled = false;
        if (setTimeBtn) setTimeBtn.textContent = translations[currentLanguage].set_time_btn || 'OK';
    } else {
        if (preGameFieldset) preGameFieldset.disabled = false;
        if (inGameFieldset) inGameFieldset.disabled = true;
        if (timingFieldset) timingFieldset.disabled = true;
        if (setTimeBtn) setTimeBtn.textContent = translations[currentLanguage].set_time_btn || 'OK';
    }

    const passwordDisplay = document.getElementById('current-password-display');
    if (passwordDisplay && state.password) {
        passwordDisplay.textContent = state.password.split('').join(' ');
    }
}

function toggleGameButtons(gameActive) {
    const startGameBtn = document.getElementById('start-game');
    const pauseGameBtn = document.getElementById('pause-btn');
    const stopGameBtn = document.getElementById('stop-game');
    const resetGameBtn = document.getElementById('reset-game');

    if (gameActive) {
        if (startGameBtn) {
            startGameBtn.disabled = true;
            startGameBtn.classList.add('opacity-50');
        }
        if (pauseGameBtn) {
            pauseGameBtn.disabled = false;
            pauseGameBtn.classList.remove('opacity-50');
        }
        if (stopGameBtn) {
            stopGameBtn.disabled = false;
            stopGameBtn.classList.remove('opacity-50');
        }
        if (resetGameBtn) {
            resetGameBtn.disabled = false;
            resetGameBtn.classList.remove('opacity-50');
        }
    } else {
        if (startGameBtn) {
            startGameBtn.disabled = false;
            startGameBtn.classList.remove('opacity-50');
        }
        if (pauseGameBtn) {
            pauseGameBtn.disabled = true;
            pauseGameBtn.classList.add('opacity-50');
        }
        if (stopGameBtn) {
            stopGameBtn.disabled = true;
            stopGameBtn.classList.add('opacity-50');
        }
        if (resetGameBtn) {
            resetGameBtn.disabled = true;
            resetGameBtn.classList.add('opacity-50');
        }
    }
}

// =====================================================================
// DOM CONTENT LOADED - CORE INITIALIZATION
// =====================================================================
document.addEventListener('DOMContentLoaded', function () {
    // Get config from HTML data attributes
    const configEl = document.getElementById('host-config');
    window.EVENT_ID = configEl ? configEl.dataset.eventId : null;
    window.IS_SUPERHOST = configEl ? configEl.dataset.isSuperhost === 'true' : false;

    console.log('HOST CORE INITIALIZING - Event ID:', window.EVENT_ID);

    // Initialize Socket.IO
    const socket = io();
    window.socket = socket;

    // Socket.IO event handlers
    socket.on('connect', () => {
        console.log('Socket connected, joining room for event:', window.EVENT_ID);
        socket.emit('join', { event_id: window.EVENT_ID });
    });

    socket.on('disconnect', () => {
        console.log('Socket disconnected');
    });

    socket.on('game_state_update', (state) => {
        console.log('Game state update received:', state);
        updateUI(state);
    });

    socket.on('timer_tick', (data) => {
        const timeLeft = document.getElementById('info-time-left');
        const timeElapsed = document.getElementById('info-time-elapsed');
        const timeElapsedPauses = document.getElementById('info-time-elapsed-pauses');

        if (timeLeft) timeLeft.textContent = formatTime(data.time_left);
        if (timeElapsed) timeElapsed.textContent = formatTime(data.time_elapsed);
        if (timeElapsedPauses) timeElapsedPauses.textContent = formatTime(data.time_elapsed_with_pauses);
    });

    socket.on('game_over', () => {
        alert('Czas minął! Gra zakończona.');
    });

    socket.on('game_forced_win', (data) => {
        alert(data.message);
    });

    socket.on('password_update', (password) => {
        const passwordDisplay = document.getElementById('current-password-display');
        if (passwordDisplay) {
            passwordDisplay.textContent = password.split('').join(' ');
        }
        if (typeof window.loadPasswordState === 'function') {
            window.loadPasswordState();
        }
    });

    socket.on('leaderboard_update', (players) => {
        console.log('Leaderboard update received:', players);
        if (typeof window.loadPlayers === 'function') {
            window.loadPlayers();
        }
    });

    // Initial state load
    console.log('Loading initial state...');
    fetch('/api/host/state')
        .then(res => res.json())
        .then(state => {
            console.log('Initial state loaded:', state);
            updateUI(state);
            if (state.language_host === 'en') {
                translatePage('en');
                document.querySelectorAll('#lang-host-controls button').forEach(b => b.classList.remove('active-modifier'));
                document.querySelector('#lang-host-controls button[data-value="en"]')?.classList.add('active-modifier');
            }
            if (state.language_player === 'en') {
                document.querySelectorAll('#lang-player-controls button').forEach(b => b.classList.remove('active-modifier'));
                document.querySelector('#lang-player-controls button[data-value="en"]')?.classList.add('active-modifier');
            }
        })
        .catch(error => console.error('Error loading initial state:', error));

    // =====================================================================
    // GAME CONTROL EVENT LISTENERS
    // =====================================================================

    // Set time button
    document.getElementById('set-time-btn-2')?.addEventListener('click', async () => {
        const minutes = parseInt(document.getElementById('game-duration-input-2').value);

        if (isNaN(minutes) || minutes < 1) {
            alert('Proszę wprowadzić poprawny czas gry (minimum 1 minuta).');
            return;
        }

        if (!window.isGameActive) {
            alert(`Czas gry ustawiony na ${minutes} minut. Kliknij "Start Gry", aby rozpocząć.`);
        } else {
            const password = prompt('Wprowadź hasło Hosta, aby zmienić czas gry:');
            if (!password) return;

            if (!confirm(`Czy na pewno chcesz zmienić czas gry na ${minutes} minut?`)) {
                return;
            }

            try {
                const response = await fetch('/api/host/adjust_time', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        new_minutes: minutes,
                        password: password
                    })
                });

                const result = await response.json();

                if (!response.ok) {
                    throw new Error(result.error || 'Błąd zmiany czasu');
                }

                alert(result.message || 'Czas gry został zmieniony!');
            } catch (error) {
                alert('Błąd: ' + error.message);
            }
        }
    });

    // Start game button
    document.getElementById('start-game')?.addEventListener('click', async () => {
        const minutes = parseInt(document.getElementById('game-duration-input-2').value);

        if (isNaN(minutes) || minutes < 1) {
            alert('Proszę wprowadzić poprawny czas gry (minimum 1 minuta).');
            return;
        }

        if (!confirm(`Czy na pewno chcesz rozpocząć nową grę na ${minutes} minut?`)) {
            return;
        }

        try {
            const response = await fetch('/api/host/start_game', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ minutes })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Nieznany błąd uruchamiania gry');
            }

            alert(result.message || 'Gra rozpoczęta!');
        } catch (error) {
            alert('Błąd podczas uruchamiania gry: ' + error.message);
        }
    });

    // Stop game button
    document.getElementById('stop-game')?.addEventListener('click', async () => {
        const password = prompt('Wprowadź hasło Hosta, aby zakończyć grę:');
        if (!password) return;

        try {
            const response = await fetch('/api/host/stop_game', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Błąd zatrzymywania gry');
            }

            alert(result.message || 'Gra zatrzymana');
        } catch (error) {
            alert('Błąd: ' + error.message);
        }
    });

    // Reset game button
    document.getElementById('reset-game')?.addEventListener('click', async () => {
        const password = prompt('Wprowadź hasło Hosta, aby zresetować grę:');
        if (!password) return;

        if (!confirm('Czy na pewno chcesz zresetować całą grę? To usunie wszystkich graczy, pytania i dane gry!')) {
            return;
        }

        try {
            const response = await fetch(`/api/admin/event/${window.EVENT_ID}/reset`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.message || 'Błąd resetowania gry');
            }

            alert(result.message || 'Gra została zresetowana');
            location.reload();
        } catch (error) {
            alert('Błąd: ' + error.message);
        }
    });

    // In-game controls (bonus, speed, pause)
    document.getElementById('game-controls')?.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-control]');
        if (!btn) return;

        const control = btn.dataset.control;
        const value = btn.dataset.value;

        sendGameControl(control, value);
    });

    // Language controls
    document.getElementById('lang-host-controls')?.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-value]');
        if (btn) {
            const lang = btn.dataset.value;
            translatePage(lang);
            sendGameControl('language_host', lang);

            document.querySelectorAll('#lang-host-controls button').forEach(b => b.classList.remove('active-modifier'));
            btn.classList.add('active-modifier');
        }
    });

    document.getElementById('lang-player-controls')?.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-value]');
        if (btn) {
            const lang = btn.dataset.value;
            sendGameControl('language_player', lang);

            document.querySelectorAll('#lang-player-controls button').forEach(b => b.classList.remove('active-modifier'));
            btn.classList.add('active-modifier');
        }
    });

    // Quick tab access
    document.querySelectorAll('.quick-tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            const tabButton = document.querySelector(`button[data-bs-target="#${tabName}"]`);
            if (tabButton) {
                const tab = new bootstrap.Tab(tabButton);
                tab.show();
            }
        });
    });

    // Password card click -> go to password tab
    const passwordCard = document.getElementById('password-preview-card');
    if (passwordCard) {
        passwordCard.addEventListener('click', () => {
            const passwordTab = document.querySelector('button[data-bs-target="#password"]');
            if (passwordTab) {
                const tab = new bootstrap.Tab(passwordTab);
                tab.show();
            }
        });
    }

    // Host messages
    const messageInput = document.getElementById('host-message-input');
    const charCount = document.getElementById('message-char-count');
    const sendMessageBtn = document.getElementById('send-message-btn');
    const messageStatus = document.getElementById('message-status');

    if (messageInput && charCount) {
        messageInput.addEventListener('input', () => {
            charCount.textContent = messageInput.value.length;
        });
    }

    if (sendMessageBtn) {
        sendMessageBtn.addEventListener('click', async () => {
            const message = messageInput.value.trim();

            if (!message) {
                messageStatus.innerHTML = '<div class="alert alert-warning">Wpisz treść komunikatu</div>';
                setTimeout(() => messageStatus.innerHTML = '', 3000);
                return;
            }

            sendMessageBtn.disabled = true;
            sendMessageBtn.textContent = 'Wysyłanie...';

            try {
                const response = await fetch('/api/host/send_message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message })
                });

                const result = await response.json();

                if (!response.ok) {
                    throw new Error(result.error || 'Błąd wysyłania');
                }

                messageStatus.innerHTML = '<div class="alert alert-success">Komunikat wysłany!</div>';
                messageInput.value = '';
                charCount.textContent = '0';

                setTimeout(() => messageStatus.innerHTML = '', 3000);
            } catch (error) {
                messageStatus.innerHTML = `<div class="alert alert-danger">${error.message}</div>`;
            } finally {
                sendMessageBtn.disabled = false;
                sendMessageBtn.textContent = translations[currentLanguage].send_message || 'Wyślij komunikat';
            }
        });
    }

    console.log('HOST CORE INITIALIZED');
});

// =====================================================================
// EXPORTS TO WINDOW
// =====================================================================
window.translations = translations;
window.currentLanguage = currentLanguage;
window.formatTime = formatTime;
window.translatePage = translatePage;
window.updateUI = updateUI;
window.sendGameControl = sendGameControl;
window.toggleGameButtons = toggleGameButtons;
window.updateGameStatusText = updateGameStatusText;
