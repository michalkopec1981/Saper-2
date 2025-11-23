// ===================================================================
// DEVICE FINGERPRINTING - zapobiega wielokrotnej rejestracji
// ===================================================================
function generateDeviceFingerprint() {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillText('🎮 Saper QR', 0, 0);
    const canvasData = canvas.toDataURL();

    const fingerprint = {
        userAgent: navigator.userAgent,
        language: navigator.language,
        languages: navigator.languages ? navigator.languages.join(',') : '',
        platform: navigator.platform,
        screenResolution: `${screen.width}x${screen.height}x${screen.colorDepth}`,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        timezoneOffset: new Date().getTimezoneOffset(),
        canvasHash: simpleHash(canvasData),
        touchSupport: 'ontouchstart' in window,
        cookieEnabled: navigator.cookieEnabled,
        doNotTrack: navigator.doNotTrack,
        hardwareConcurrency: navigator.hardwareConcurrency || 0,
        deviceMemory: navigator.deviceMemory || 0,
        maxTouchPoints: navigator.maxTouchPoints || 0
    };

    return simpleHash(JSON.stringify(fingerprint));
}

function simpleHash(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    return Math.abs(hash).toString(36);
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 PLAYER.HTML LOADED - VERSION 3.0 WITH GLOBAL SSO');  // ← MARKER WERSJI

    const eventId = {{ event_id }};
    const qrCode = "{{ qr_code }}";
    let playerId = localStorage.getItem(`saperPlayerId_${eventId}`);
    let playerName = localStorage.getItem(`saperPlayerName_${eventId}`);
    let currentQuestionId = null;

    // ✅ Wygeneruj fingerprint urządzenia
    const deviceFingerprint = generateDeviceFingerprint();
    console.log('🔐 Device fingerprint:', deviceFingerprint);

    const socket = io();

    // Elements
    const nameInputSection = document.getElementById('name-input-section');
    const gameView = document.getElementById('game-view');
    const quizSection = document.getElementById('quiz-section');
    const messageSection = document.getElementById('message-section');
    const photoCaptureView = document.getElementById('photo-capture-view');
    const aiCategorySelection = document.getElementById('ai-category-selection');
    const aiCategoriesButtons = document.getElementById('ai-categories-buttons');
    const playerNameInput = document.getElementById('player-name');
    const registerBtn = document.getElementById('register-btn');
    const playerNameDisplay = document.getElementById('player-name-display');
    const playerScoreDisplay = document.getElementById('player-score');
    const questionEl = document.getElementById('question');
    const answersEl = document.getElementById('answers');

    let isAIQuestion = false;

    // Photo capture elements
    const cameraFeed = document.getElementById('camera-feed');
    const captureBtn = document.getElementById('capture-btn');
    const cancelPhotoBtn = document.getElementById('cancel-photo-btn');
    const photoCanvas = document.getElementById('photo-canvas');

    // ===================================================================
    // INICJALIZACJA Z WERYFIKACJĄ GRACZA
    // ===================================================================

    // Funkcja weryfikująca czy gracz istnieje w bazie danych
    async function verifyPlayerExists(playerId) {
        try {
            const response = await fetch(`/api/event/${eventId}/players`);
            if (!response.ok) return false;

            const data = await response.json();
            return data.players.some(p => p.id == playerId);
        } catch (error) {
            console.error('Error verifying player:', error);
            return false;
        }
    }

    // ✅ Funkcja sprawdzająca czy backend rozpoznaje gracza po IP + fingerprint
    async function checkAutoLoginByFingerprint() {
        console.log('🔍 === CHECKING AUTO-LOGIN ===');
        console.log('   EventId:', eventId);
        console.log('   DeviceFingerprint:', deviceFingerprint);

        try {
            console.log('   Sending request to /api/player/check_auto_login...');
            const response = await fetch('/api/player/check_auto_login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    event_id: eventId,
                    device_fingerprint: deviceFingerprint
                })
            });

            const data = await response.json();
            console.log('   Response from backend:', data);

            // Jeśli backend rozpoznał gracza (exact lub fingerprint match)
            if (data.recognized && data.id) {
                console.log(`✅ AUTO-LOGIN SUCCESS: ${data.match_type} match - ${data.name}`);

                // Zapisz dane gracza
                playerId = data.id;
                playerName = data.name;
                localStorage.setItem(`saperPlayerId_${eventId}`, playerId);
                localStorage.setItem(`saperPlayerName_${eventId}`, playerName);
                console.log('   Saved to localStorage:', playerId, playerName);

                // Zaloguj automatycznie
                playerNameDisplay.textContent = playerName;
                playerScoreDisplay.textContent = data.score;

                showMessage(data.message || `Witaj ponownie, ${playerName}!`, 'success');

                // ✅ SSO: Wywołaj zunifikowaną funkcję loginSuccess
                loginSuccess();

                return true;  // Auto-login się udał
            }

            console.log('❌ AUTO-LOGIN FAILED: Backend nie rozpoznał gracza');
            return false;  // Backend nie rozpoznał gracza
        } catch (error) {
            console.error('❌ AUTO-LOGIN ERROR:', error);
            return false;
        }
    }

    // Inicjalizacja przy załadowaniu strony
    (async function initializePlayer() {
        console.log('🔍 Initializing player...');

        if (playerId && playerName) {
            console.log(`📦 Found player in localStorage: ${playerName} (ID: ${playerId})`);

            // ✅ KLUCZOWA ZMIANA: Sprawdź czy gracz nadal istnieje w bazie
            const exists = await verifyPlayerExists(playerId);

            if (exists) {
                console.log('✅ Player verified in database - auto-login');
                playerNameDisplay.textContent = playerName;

                // ✅ SSO: Wywołaj zunifikowaną funkcję loginSuccess
                loginSuccess();
            } else {
                console.log('❌ Player not found in database (reset?) - clearing localStorage');
                // Gracz został usunięty (np. po resecie gry)
                localStorage.removeItem(`saperPlayerId_${eventId}`);
                localStorage.removeItem(`saperPlayerName_${eventId}`);
                playerId = null;
                playerName = '';

                // Pokaż komunikat i formularz rejestracji
                showMessage('⚠️ Twoje dane wygasły po resecie gry. Zarejestruj się ponownie.', 'warning');
                nameInputSection.style.display = 'block';
                gameView.style.display = 'none';

                // ✅ Sprawdź auto-login przez fingerprint
                await checkAutoLoginByFingerprint();
            }
        } else {
            console.log('❌ No player found in localStorage');

            // ✅ NOWA LOGIKA: Sprawdź czy backend rozpoznaje gracza po fingerprint ZANIM pokażesz formularz
            const autoLoggedIn = await checkAutoLoginByFingerprint();

            if (!autoLoggedIn) {
                console.log('📝 Showing registration form');
                nameInputSection.style.display = 'block';
                gameView.style.display = 'none';
            }
        }
    })();

    // Helper functions
    function showMessage(text, type = 'info') {
        messageSection.textContent = text;
        messageSection.className = `alert alert-${type}`;
        messageSection.style.display = 'block';
        quizSection.style.display = 'none';
    }

    // ✅ SSO: Zunifikowana funkcja po udanym logowaniu
    // Automatycznie wykonuje akcję z kodu QR
    function loginSuccess() {
        console.log('✅ Login success - executing QR action:', qrCode);
        // Ukryj formularz, pokaż grę
        nameInputSection.style.display = 'none';
        gameView.style.display = 'block';
        // Automatycznie zeskanuj kod QR (który może być wirtualnym kodem akcji)
        scanQrCode();
    }

    function displayQuestion(question) {
        currentQuestionId = question.id;
        questionEl.textContent = question.text;
        answersEl.innerHTML = '';
        const options = [
            { key: 'a', text: question.option_a },
            { key: 'b', text: question.option_b },
            { key: 'c', text: question.option_c }
        ];
        options.forEach(opt => {
            if (opt.text) {
                const btn = document.createElement('button');
                btn.className = 'btn btn-outline-secondary btn-lg';
                btn.textContent = `${opt.key.toUpperCase()}) ${opt.text}`;
                btn.dataset.answer = opt.key.toUpperCase();
                answersEl.appendChild(btn);
            }
        });
        messageSection.style.display = 'none';
        aiCategorySelection.style.display = 'none';
        quizSection.style.display = 'block';
    }

    // Wyświetl kategorie AI do wyboru
    async function displayAICategories(categories) {
        aiCategoriesButtons.innerHTML = '';

        if (!categories || categories.length === 0) {
            showMessage('Brak dostępnych kategorii AI', 'info');
            return;
        }

        categories.forEach(cat => {
            const btn = document.createElement('button');
            btn.className = 'btn btn-primary btn-lg';
            btn.textContent = cat.name;
            btn.onclick = () => selectAICategory(cat.id);
            aiCategoriesButtons.appendChild(btn);
        });

        messageSection.style.display = 'none';
        quizSection.style.display = 'none';
        aiCategorySelection.style.display = 'block';
    }

    // Wybór kategorii AI i pobranie pytania
    async function selectAICategory(categoryId) {
        try {
            const response = await fetch('/api/player/ai/get_question', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    player_id: parseInt(playerId),
                    category_id: categoryId,
                    event_id: parseInt(eventId)
                })
            });

            const data = await response.json();

            if (!response.ok) {
                showMessage(data.error || 'Błąd pobierania pytania', 'danger');
                return;
            }

            if (data.status === 'info') {
                showMessage(data.message, 'info');
                aiCategorySelection.style.display = 'none';
                return;
            }

            if (data.status === 'question') {
                isAIQuestion = true;
                displayQuestion(data.question);
            }
        } catch (error) {
            console.error('Error selecting AI category:', error);
            showMessage('Błąd połączenia z serwerem', 'danger');
        }
    }

    // Register player
    registerBtn.addEventListener('click', async () => {
        const name = playerNameInput.value.trim();
        if (!name) {
            alert('Proszę podać imię lub nazwę drużyny.');
            return;
        }

        try {
            const response = await fetch('/api/player/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    event_id: eventId,
                    device_fingerprint: deviceFingerprint  // ← Wyślij fingerprint
                })
            });

            const data = await response.json();

            // ✅ Obsługa istniejącego gracza (exact/fingerprint match)
            if (data.existing && data.match_type) {
                console.log(`✅ ${data.match_type} match - auto-login as ${data.name}`);

                playerId = data.id;
                playerName = data.name;
                localStorage.setItem(`saperPlayerId_${eventId}`, playerId);
                localStorage.setItem(`saperPlayerName_${eventId}`, playerName);

                playerNameDisplay.textContent = playerName;
                playerScoreDisplay.textContent = data.score;

                nameInputSection.style.display = 'none';
                gameView.style.display = 'block';

                showMessage(data.message, 'success');
                scanQrCode();
                return;
            }

            // ✅ Obsługa limitu urządzenia (403)
            if (response.status === 403 && data.limit_type === 'device' && data.existing_player) {
                const existingName = data.existing_player.name;
                const existingScore = data.existing_player.score;

                const continueAsExisting = confirm(
                    `${data.error}\n\n` +
                    `Z tego urządzenia gra już: ${existingName} (${existingScore} pkt)\n\n` +
                    `Czy chcesz kontynuować jako ${existingName}?`
                );

                if (continueAsExisting) {
                    playerId = data.existing_player.id;
                    playerName = data.existing_player.name;
                    localStorage.setItem(`saperPlayerId_${eventId}`, playerId);
                    localStorage.setItem(`saperPlayerName_${eventId}`, playerName);

                    playerNameDisplay.textContent = playerName;
                    playerScoreDisplay.textContent = data.existing_player.score;

                    showMessage(`Witaj ponownie, ${playerName}!`, 'success');

                    // ✅ SSO: Wywołaj zunifikowaną funkcję loginSuccess
                    loginSuccess();
                } else {
                    showMessage('Skontaktuj się z organizatorem.', 'warning');
                }
                return;
            }

            if (!response.ok) {
                alert(data.error || 'Błąd rejestracji');
                return;
            }

            // ✅ Nowy gracz zarejestrowany
            playerId = data.id;
            playerName = data.name;
            localStorage.setItem(`saperPlayerId_${eventId}`, playerId);
            localStorage.setItem(`saperPlayerName_${eventId}`, playerName);

            playerNameDisplay.textContent = playerName;
            playerScoreDisplay.textContent = data.score;

            showMessage('✅ Rejestracja pomyślna!', 'success');

            // ✅ SSO: Wywołaj zunifikowaną funkcję loginSuccess
            loginSuccess();

        } catch (error) {
            console.error('Registration error:', error);
            alert('Błąd połączenia z serwerem: ' + error.message);
        }
    });

    // Scan QR code
    async function scanQrCode() {
        console.log('Scanning QR code:', qrCode, 'Player ID:', playerId, 'Event ID:', eventId);
        
        if (!playerId) {
            showMessage('Błąd: Brak ID gracza. Spróbuj ponownie zarejestrować się.', 'danger');
            return;
        }

        try {
            const response = await fetch('/api/player/scan_qr', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    player_id: parseInt(playerId), 
                    qr_code: qrCode,
                    event_id: parseInt(eventId)
                })
            });

            const data = await response.json();
            console.log('Scan QR response:', data);

            // ✅ Obsługa wygasłych danych gracza (po resecie gry)
            if (data.clear_storage) {
                console.log('Clearing expired player data from localStorage');
                localStorage.removeItem(`saperPlayerId_${eventId}`);
                localStorage.removeItem(`saperPlayerName_${eventId}`);
                showMessage(data.message + ' Strona zostanie odświeżona...', 'warning');
                setTimeout(() => location.reload(), 3000);
                return;
            }

            if (response.status === 429) {
                showMessage(data.message, 'warning');
                return;
            }

            if (!response.ok) {
                showMessage(data.message || 'Błąd skanowania', 'danger');
                return;
            }

            if (data.status === 'question') {
                isAIQuestion = false;
                displayQuestion(data.question);
            } else if (data.status === 'ai_categories') {
                // Pokazuje wybór kategorii AI
                displayAICategories(data.categories);
            } else if (data.status === 'photo_challenge') {
                startPhotoChallenge();
            } else if (data.status === 'minigame') {
                const currentScore = data.current_score || 0;

                if (data.game === 'tetris') {
                    startTetrisGame(currentScore);
                } else if (data.game === 'arkanoid') {
                    startArkanoidGame(currentScore);
                } else if (data.game === 'snake') {
                    startSnakeGame(currentScore);
                } else if (data.game === 'trex') {
                    startTRexGame(currentScore);
                }
            } else if (data.status === 'info' || data.status === 'error') {
                showMessage(data.message, data.status === 'error' ? 'danger' : 'info');
                if (data.score !== undefined) {
                    playerScoreDisplay.textContent = data.score;
                }
            }
        } catch (error) {
            console.error('Scan QR error:', error);
            showMessage('Błąd połączenia z serwerem: ' + error.message, 'danger');
        }
    }

    // Answer question
    answersEl.addEventListener('click', async (event) => {
        if (event.target.tagName === 'BUTTON') {
            const answer = event.target.dataset.answer;
            try {
                // Różne endpointy dla pytań AI i normalnych
                const endpoint = isAIQuestion ? '/api/player/ai/answer' : '/api/player/answer';

                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        player_id: parseInt(playerId),
                        question_id: currentQuestionId,
                        answer
                    })
                });

                const data = await response.json();
                playerScoreDisplay.textContent = data.score;

                if (isAIQuestion) {
                    // Pytania AI
                    if (data.correct) {
                        showMessage(data.message || '✅ Poprawna odpowiedź! +5 punktów', 'success');
                    } else {
                        showMessage(data.message || '❌ Niepoprawna odpowiedź', 'danger');
                    }
                } else {
                    // Pytania normalne
                    if (data.correct) {
                        showMessage(`✅ Dobrze! Zdobywasz punkty i literę: ${data.letter}`, 'success');
                    } else {
                        showMessage('❌ Zła odpowiedź. Tracisz 5 punktów.', 'danger');
                    }
                }
            } catch (error) {
                showMessage('Błąd połączenia z serwerem', 'danger');
            }
        }
    });

    // 📸 Photo challenge - RÓŻOWY KOD QR
    function startPhotoChallenge() {
        console.log('📸 Starting photo challenge...');
        
        // Ukryj główny widok gry
        document.getElementById('main-view').style.display = 'none';
        
        // Pokaż widok aparatu
        photoCaptureView.style.display = 'block';

        // Uruchom kamerę selfie (front camera)
        navigator.mediaDevices.getUserMedia({ 
            video: { 
                facingMode: 'user' // Kamera przednia (selfie)
            } 
        })
        .then(stream => {
            cameraFeed.srcObject = stream;
            console.log('✅ Kamera uruchomiona');
        })
        .catch(err => {
            console.error('❌ Błąd dostępu do kamery:', err);
            alert('Nie można uzyskać dostępu do kamery: ' + err.message);
            
            // Powrót do głównego widoku
            photoCaptureView.style.display = 'none';
            document.getElementById('main-view').style.display = 'block';
            gameView.style.display = 'block';
        });
    }

    // 📸 Zrób zdjęcie
    captureBtn.addEventListener('click', async () => {
        console.log('📸 Capturing photo...');
        
        const context = photoCanvas.getContext('2d');
        photoCanvas.width = cameraFeed.videoWidth;
        photoCanvas.height = cameraFeed.videoHeight;
        context.drawImage(cameraFeed, 0, 0);

        photoCanvas.toBlob(async (blob) => {
            const formData = new FormData();
            formData.append('photo', blob, 'photo.jpg');
            formData.append('player_id', playerId);

            try {
                console.log('📤 Uploading photo...');
                
                const response = await fetch('/api/player/upload_photo', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();
                console.log('✅ Photo uploaded:', data);
                
                // Stop camera
                const stream = cameraFeed.srcObject;
                if (stream) {
                    stream.getTracks().forEach(track => track.stop());
                }

                // Powrót do głównego widoku
                photoCaptureView.style.display = 'none';
                document.getElementById('main-view').style.display = 'block';
                gameView.style.display = 'block';
                
                // Aktualizuj wynik
                playerScoreDisplay.textContent = data.score;
                showMessage(data.message, 'success');
                
            } catch (error) {
                console.error('❌ Upload error:', error);
                alert('Błąd wysyłania zdjęcia: ' + error.message);
            }
        }, 'image/jpeg', 0.8); // 80% jakości JPEG
    });

    // 📸 Anuluj zdjęcie
    cancelPhotoBtn.addEventListener('click', () => {
        console.log('❌ Photo cancelled');
        
        // Stop camera
        const stream = cameraFeed.srcObject;
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
        
        // Powrót do głównego widoku
        photoCaptureView.style.display = 'none';
        document.getElementById('main-view').style.display = 'block';
        gameView.style.display = 'block';
    });

    // 🎮 Tetris game
    function startTetrisGame(currentScore = 0) {
        // Ukryj główny widok
        document.getElementById('main-view').style.display = 'none';
        
        // Pokaż widok Tetris (full screen)
        const tetrisView = document.getElementById('tetris-game-view');
        tetrisView.style.display = 'block';
        
        // Ustaw nazwę gracza i wynik
        document.getElementById('tetris-player-name').textContent = playerName;
        document.getElementById('tetris-score').textContent = currentScore;
        
        let tetrisGame;
        
        // Przycisk Start
        document.getElementById('tetris-start-btn').onclick = () => {
            tetrisGame = new TetrisGame('tetris-canvas', playerId, eventId, currentScore);
            tetrisGame.start();
            
            // Ukryj sekcję startu, pokaż kontrolki po bokach i przycisk wyjścia
            document.getElementById('tetris-start-section').style.display = 'none';
            document.getElementById('tetris-left-controls').style.display = 'block';
            document.getElementById('tetris-right-controls').style.display = 'block';
            document.getElementById('tetris-exit-btn').style.display = 'block';
        };
        
        // Przycisk Wróć (na ekranie startowym)
        document.getElementById('tetris-back-btn').onclick = () => {
            if (tetrisGame) {
                tetrisGame.gameRunning = false;
            }
            
            // Ukryj Tetris
            tetrisView.style.display = 'none';
            
            // Pokaż główny widok
            document.getElementById('main-view').style.display = 'block';
            gameView.style.display = 'block';
            
            // Resetuj widok Tetris
            document.getElementById('tetris-start-section').style.display = 'block';
            document.getElementById('tetris-left-controls').style.display = 'none';
            document.getElementById('tetris-right-controls').style.display = 'none';
            document.getElementById('tetris-exit-btn').style.display = 'none';
            document.getElementById('tetris-start-btn').style.display = 'inline-block';
        };
        
        // Przycisk Wyjdź z gry (podczas gry)
        document.getElementById('tetris-exit-btn').onclick = () => {
            if (confirm('Czy na pewno chcesz wyjść z gry? Postęp zostanie zapisany.')) {
                if (tetrisGame) {
                    tetrisGame.gameRunning = false;
                }
                
                // Ukryj Tetris
                tetrisView.style.display = 'none';
                
                // Pokaż główny widok
                document.getElementById('main-view').style.display = 'block';
                gameView.style.display = 'block';
                
                // Resetuj widok Tetris
                document.getElementById('tetris-start-section').style.display = 'block';
                document.getElementById('tetris-left-controls').style.display = 'none';
                document.getElementById('tetris-right-controls').style.display = 'none';
                document.getElementById('tetris-exit-btn').style.display = 'none';
                document.getElementById('tetris-start-btn').style.display = 'inline-block';
                document.getElementById('tetris-start-btn').textContent = 'KONTYNUUJ GRĘ';
            }
        };
    }

    // 🎮 Arkanoid game
    function startArkanoidGame(currentScore = 0) {
        // Ukryj główny widok
        document.getElementById('main-view').style.display = 'none';
        
        // Pokaż widok Arkanoid (full screen)
        const arkanoidView = document.getElementById('arkanoid-game-view');
        arkanoidView.style.display = 'block';
        
        // Ustaw nazwę gracza i wynik
        document.getElementById('arkanoid-player-name').textContent = playerName;
        document.getElementById('arkanoid-score').textContent = currentScore;
        
        let arkanoidGame;
        
        // Przycisk Start
        document.getElementById('arkanoid-start-btn').onclick = () => {
            arkanoidGame = new ArkanoidGame('arkanoid-canvas', playerId, eventId, currentScore);
            arkanoidGame.start();
            
            // Ukryj sekcję startu, pokaż kontrolki po bokach i przycisk wyjścia
            document.getElementById('arkanoid-start-section').style.display = 'none';
            document.getElementById('arkanoid-left-controls').style.display = 'block';
            document.getElementById('arkanoid-right-controls').style.display = 'block';
            document.getElementById('arkanoid-exit-btn').style.display = 'block';
        };
        
        // Przycisk Wróć (na ekranie startowym)
        document.getElementById('arkanoid-back-btn').onclick = () => {
            if (arkanoidGame) {
                arkanoidGame.gameRunning = false;
                arkanoidGame.paddleMoving = 0; // Stop ruchu paletki
            }
            
            // Ukryj Arkanoid
            arkanoidView.style.display = 'none';
            
            // Pokaż główny widok
            document.getElementById('main-view').style.display = 'block';
            gameView.style.display = 'block';
            
            // Resetuj widok Arkanoid
            document.getElementById('arkanoid-start-section').style.display = 'block';
            document.getElementById('arkanoid-left-controls').style.display = 'none';
            document.getElementById('arkanoid-right-controls').style.display = 'none';
            document.getElementById('arkanoid-exit-btn').style.display = 'none';
            document.getElementById('arkanoid-start-btn').style.display = 'inline-block';
        };
        
        // Przycisk Wyjdź z gry (podczas gry)
        document.getElementById('arkanoid-exit-btn').onclick = () => {
            if (confirm('Czy na pewno chcesz wyjść z gry? Postęp zostanie zapisany.')) {
                if (arkanoidGame) {
                    arkanoidGame.gameRunning = false;
                    arkanoidGame.paddleMoving = 0; // Stop ruchu paletki
                }
                
                // Ukryj Arkanoid
                arkanoidView.style.display = 'none';
                
                // Pokaż główny widok
                document.getElementById('main-view').style.display = 'block';
                gameView.style.display = 'block';
                
                // Resetuj widok Arkanoid
                document.getElementById('arkanoid-start-section').style.display = 'block';
                document.getElementById('arkanoid-left-controls').style.display = 'none';
                document.getElementById('arkanoid-right-controls').style.display = 'none';
                document.getElementById('arkanoid-exit-btn').style.display = 'none';
                document.getElementById('arkanoid-start-btn').style.display = 'inline-block';
                document.getElementById('arkanoid-start-btn').textContent = 'KONTYNUUJ GRĘ';
            }
        };
    }

    // 🐍 Snake game
    function startSnakeGame(currentScore = 0) {
        // Ukryj główny widok
        document.getElementById('main-view').style.display = 'none';

        // Pokaż widok Snake (full screen)
        const snakeView = document.getElementById('snake-game-view');
        snakeView.style.display = 'block';

        // Ustaw nazwę gracza i wynik
        document.getElementById('snake-player-name').textContent = playerName;
        document.getElementById('snake-score').textContent = currentScore;

        let snakeGame;

        // Przycisk Start
        document.getElementById('snake-start-btn').onclick = () => {
            snakeGame = new SnakeGame('snake-canvas', playerId, eventId, currentScore);
            snakeGame.start();

            // Ukryj sekcję startu, pokaż kontrolki po bokach i przycisk wyjścia
            document.getElementById('snake-start-section').style.display = 'none';
            document.getElementById('snake-left-controls').style.display = 'block';
            document.getElementById('snake-right-controls').style.display = 'block';
            document.getElementById('snake-exit-btn').style.display = 'block';
        };

        // Przycisk Wróć (na ekranie startowym)
        document.getElementById('snake-back-btn').onclick = () => {
            if (snakeGame) {
                snakeGame.gameRunning = false;
            }

            // Ukryj Snake
            snakeView.style.display = 'none';

            // Pokaż główny widok
            document.getElementById('main-view').style.display = 'block';

            // Reset widoku startowego Snake
            document.getElementById('snake-start-section').style.display = 'block';
            document.getElementById('snake-left-controls').style.display = 'none';
            document.getElementById('snake-right-controls').style.display = 'none';
            document.getElementById('snake-exit-btn').style.display = 'none';
            document.getElementById('snake-start-btn').style.display = 'inline-block';
        };

        // Przycisk Wyjdź z gry (podczas gry)
        document.getElementById('snake-exit-btn').onclick = () => {
            if (confirm('Czy na pewno chcesz wyjść z gry? Postęp zostanie zapisany.')) {
                if (snakeGame) {
                    snakeGame.gameRunning = false;
                }

                // Ukryj Snake
                snakeView.style.display = 'none';

                // Pokaż główny widok
                document.getElementById('main-view').style.display = 'block';

                // Reset widoku startowego Snake
                document.getElementById('snake-start-section').style.display = 'block';
                document.getElementById('snake-left-controls').style.display = 'none';
                document.getElementById('snake-right-controls').style.display = 'none';
                document.getElementById('snake-exit-btn').style.display = 'none';
                document.getElementById('snake-start-btn').style.display = 'inline-block';
                document.getElementById('snake-start-btn').textContent = 'KONTYNUUJ GRĘ';
            }
        };
    }

    function startTRexGame(currentScore = 0) {
        // Ukryj główny widok
        document.getElementById('main-view').style.display = 'none';

        // Pokaż widok T-Rex (full screen)
        const trexView = document.getElementById('trex-game-view');
        trexView.style.display = 'block';

        // Ustaw nazwę gracza i wynik
        document.getElementById('trex-player-name').textContent = playerName;
        document.getElementById('trex-score').textContent = currentScore;

        let trexGame;

        // Przycisk Start
        document.getElementById('trex-start-btn').onclick = () => {
            trexGame = new TRexGame('trex-canvas', playerId, eventId, currentScore);
            trexGame.start();

            // Ukryj sekcję startu, pokaż kontrolkę skoku i przycisk wyjścia
            document.getElementById('trex-start-section').style.display = 'none';
            document.getElementById('trex-jump-control').style.display = 'block';
            document.getElementById('trex-exit-btn').style.display = 'block';
        };

        // Przycisk Wróć (na ekranie startowym)
        document.getElementById('trex-back-btn').onclick = () => {
            if (trexGame) {
                trexGame.gameRunning = false;
            }

            // Ukryj T-Rex
            trexView.style.display = 'none';

            // Pokaż główny widok
            document.getElementById('main-view').style.display = 'block';

            // Reset widoku startowego T-Rex
            document.getElementById('trex-start-section').style.display = 'block';
            document.getElementById('trex-jump-control').style.display = 'none';
            document.getElementById('trex-exit-btn').style.display = 'none';
            document.getElementById('trex-start-btn').style.display = 'inline-block';
        };

        // Przycisk Wyjdź z gry (podczas gry)
        document.getElementById('trex-exit-btn').onclick = () => {
            if (confirm('Czy na pewno chcesz wyjść z gry? Postęp zostanie zapisany.')) {
                if (trexGame) {
                    trexGame.gameRunning = false;
                }

                // Ukryj T-Rex
                trexView.style.display = 'none';

                // Pokaż główny widok
                document.getElementById('main-view').style.display = 'block';

                // Reset widoku startowego T-Rex
                document.getElementById('trex-start-section').style.display = 'block';
                document.getElementById('trex-jump-control').style.display = 'none';
                document.getElementById('trex-exit-btn').style.display = 'none';
                document.getElementById('trex-start-btn').style.display = 'inline-block';
                document.getElementById('trex-start-btn').textContent = 'KONTYNUUJ GRĘ';
            }
        };
    }

    // Socket.IO
    socket.on('connect', () => {
        console.log('Socket connected');
        socket.emit('join', { event_id: eventId });
    });

    socket.on('game_over', () => {
        showMessage('⏰ Czas minął! Gra zakończona.', 'danger');
    });

    socket.on('game_forced_win', (data) => {
        showMessage(data.message, 'success');
    });

    // Odbieranie wiadomości od hosta
    socket.on('host_message', (data) => {
        // Sprawdź czy wiadomość jest skierowana do tego gracza
        if (data.player_id === parseInt(playerId)) {
            // Wyświetl wiadomość jako alert z większym textboxem
            const messageHtml = `
                <div style="background: #fff3cd; border: 2px solid #ffc107; padding: 20px; border-radius: 10px; max-width: 400px; margin: 20px auto; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h4 style="color: #856404; margin-bottom: 15px;">📬 Wiadomość od Organizatora</h4>
                    <p style="color: #333; font-size: 1.1rem; line-height: 1.5; margin: 0;">${data.message}</p>
                </div>
            `;

            // Użyj messageSection do wyświetlenia wiadomości
            messageSection.innerHTML = messageHtml;
            messageSection.className = 'alert alert-warning';
            messageSection.style.display = 'block';
            quizSection.style.display = 'none';

            // Auto-ukryj po 10 sekundach
            setTimeout(() => {
                messageSection.style.display = 'none';
            }, 10000);
        }
    });

    // Reset player data button
    document.getElementById('reset-player-btn')?.addEventListener('click', () => {
        if (confirm('Czy na pewno chcesz wyczyścić swoje dane i zarejestrować się ponownie?')) {
            localStorage.removeItem(`saperPlayerId_${eventId}`);
            localStorage.removeItem(`saperPlayerName_${eventId}`);
            location.reload();
        }
    });

    // ✅ STARA INICJALIZACJA ZOSTAŁA USUNIĘTA
    // Inicjalizacja odbywa się teraz w funkcji initializePlayer() (linie ~308-341)
    // która weryfikuje gracza w bazie danych przed auto-logowaniem
});
