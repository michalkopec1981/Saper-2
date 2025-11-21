/**
 * HOST MINIGAMES MODULE
 * Toggle gier: Tetris, Snake, Arkanoid, T-Rex
 * Ustawienia minigier (punktacja), tryby testowe
 *
 * Używa: window.translations, window.currentLanguage
 * Eksportuje: loadMinigamesStatus, loadMinigamesSettings, updateMinigameSetting
 */

document.addEventListener('DOMContentLoaded', function () {

    // =====================================================================
    // LOAD MINIGAMES STATUS
    // =====================================================================
    function loadMinigamesStatus() {
        fetch('/api/host/minigames/status')
            .then(res => res.json())
            .then(data => {
                // Tetris
                const tetrisToggle = document.getElementById('tetris-toggle');
                const tetrisStatus = document.getElementById('tetris-status');
                if (tetrisToggle && tetrisStatus) {
                    tetrisToggle.checked = data.tetris_enabled;
                    tetrisStatus.textContent = data.tetris_enabled ? 'Aktywny' : 'Nieaktywny';
                    tetrisStatus.className = data.tetris_enabled ? 'badge bg-success' : 'badge bg-secondary';
                }

                // Arkanoid
                const arkanoidToggle = document.getElementById('arkanoid-toggle');
                const arkanoidStatus = document.getElementById('arkanoid-status');
                if (arkanoidToggle && arkanoidStatus) {
                    arkanoidToggle.checked = data.arkanoid_enabled;
                    arkanoidStatus.textContent = data.arkanoid_enabled ? 'Aktywny' : 'Nieaktywny';
                    arkanoidStatus.className = data.arkanoid_enabled ? 'badge bg-success' : 'badge bg-secondary';
                }

                // Snake
                const snakeToggle = document.getElementById('snake-toggle');
                const snakeStatus = document.getElementById('snake-status');
                if (snakeToggle && snakeStatus) {
                    snakeToggle.checked = data.snake_enabled;
                    snakeStatus.textContent = data.snake_enabled ? 'Aktywny' : 'Nieaktywny';
                    snakeStatus.className = data.snake_enabled ? 'badge bg-success' : 'badge bg-secondary';
                }

                // T-Rex
                const trexToggle = document.getElementById('trex-toggle');
                const trexStatus = document.getElementById('trex-status');
                if (trexToggle && trexStatus) {
                    trexToggle.checked = data.trex_enabled;
                    trexStatus.textContent = data.trex_enabled ? 'Aktywny' : 'Nieaktywny';
                    trexStatus.className = data.trex_enabled ? 'badge bg-success' : 'badge bg-secondary';
                }
            });
    }

    // =====================================================================
    // GAME TOGGLES
    // =====================================================================
    async function toggleMinigame(gameType, enabled, statusEl, infoEl, toggle) {
        try {
            const response = await fetch('/api/host/minigames/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ game_type: gameType, enabled })
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            statusEl.textContent = enabled ? 'Aktywny' : 'Nieaktywny';
            statusEl.className = enabled ? 'badge bg-success' : 'badge bg-secondary';
            infoEl.textContent = result.message;
            infoEl.style.display = 'block';
            setTimeout(() => { infoEl.style.display = 'none'; }, 3000);
        } catch (error) {
            alert('Błąd: ' + error.message);
            toggle.checked = !enabled;
        }
    }

    document.getElementById('tetris-toggle')?.addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        const statusEl = document.getElementById('tetris-status');
        const infoEl = document.getElementById('minigames-info');
        await toggleMinigame('tetris', enabled, statusEl, infoEl, e.target);
    });

    document.getElementById('arkanoid-toggle')?.addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        const statusEl = document.getElementById('arkanoid-status');
        const infoEl = document.getElementById('minigames-info');
        await toggleMinigame('arkanoid', enabled, statusEl, infoEl, e.target);
    });

    document.getElementById('snake-toggle')?.addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        const statusEl = document.getElementById('snake-status');
        const infoEl = document.getElementById('minigames-info');
        await toggleMinigame('snake', enabled, statusEl, infoEl, e.target);
    });

    document.getElementById('trex-toggle')?.addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        const statusEl = document.getElementById('trex-status');
        const infoEl = document.getElementById('minigames-info');
        await toggleMinigame('trex', enabled, statusEl, infoEl, e.target);
    });

    // =====================================================================
    // MINIGAME SETTINGS
    // =====================================================================
    async function updateMinigameSetting(settingType) {
        const infoEl = document.getElementById('minigames-info');
        let value, settingName;

        if (settingType === 'completion_points') {
            value = document.getElementById('minigame-completion-points').value;
            settingName = 'Liczba punktów za przejście gry';
        } else if (settingType === 'target_points') {
            value = document.getElementById('minigame-target-points').value;
            settingName = 'Liczba punktów do zdobycia w grze';
        }

        try {
            const response = await fetch('/api/host/minigames/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ setting_type: settingType, value: parseInt(value) })
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);

            if (settingType === 'completion_points') {
                const completionDisplay = document.getElementById('minigame-completion-display');
                if (completionDisplay) completionDisplay.textContent = value;
            } else if (settingType === 'target_points') {
                const targetDisplay = document.getElementById('minigame-target-display');
                if (targetDisplay) targetDisplay.textContent = value;
            }

            infoEl.textContent = `${settingName} zaktualizowane: ${value}`;
            infoEl.className = 'alert alert-success mt-3';
            infoEl.style.display = 'block';
            setTimeout(() => { infoEl.style.display = 'none'; }, 3000);
        } catch (error) {
            alert('Błąd: ' + error.message);
        }
    }

    document.getElementById('minigame-player-choice')?.addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        const statusEl = document.getElementById('minigame-choice-status');
        const infoEl = document.getElementById('minigames-info');

        try {
            const response = await fetch('/api/host/minigames/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ setting_type: 'player_choice', value: enabled })
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);

            statusEl.textContent = enabled ? 'Wybór gracza' : 'Losowa kolejność';
            statusEl.className = enabled ? 'badge bg-success' : 'badge bg-secondary';

            infoEl.textContent = enabled
                ? 'Gracze będą mogli wybrać grę po zeskanowaniu kodu QR'
                : 'Gry będą uruchamiane w losowej kolejności';
            infoEl.className = 'alert alert-success mt-3';
            infoEl.style.display = 'block';
            setTimeout(() => { infoEl.style.display = 'none'; }, 3000);
        } catch (error) {
            alert('Błąd: ' + error.message);
            e.target.checked = !enabled;
        }
    });

    function loadMinigamesSettings() {
        fetch('/api/host/minigames/settings')
            .then(res => res.json())
            .then(data => {
                const completionPointsInput = document.getElementById('minigame-completion-points');
                if (completionPointsInput && data.completion_points !== undefined) {
                    completionPointsInput.value = data.completion_points;
                }

                const targetPointsInput = document.getElementById('minigame-target-points');
                if (targetPointsInput && data.target_points !== undefined) {
                    targetPointsInput.value = data.target_points;
                }

                const playerChoiceToggle = document.getElementById('minigame-player-choice');
                const playerChoiceStatus = document.getElementById('minigame-choice-status');
                if (playerChoiceToggle && playerChoiceStatus && data.player_choice !== undefined) {
                    playerChoiceToggle.checked = data.player_choice;
                    playerChoiceStatus.textContent = data.player_choice ? 'Wybór gracza' : 'Losowa kolejność';
                    playerChoiceStatus.className = data.player_choice ? 'badge bg-success' : 'badge bg-secondary';
                }

                const targetDisplay = document.getElementById('minigame-target-display');
                const completionDisplay = document.getElementById('minigame-completion-display');
                if (targetDisplay && data.target_points !== undefined) {
                    targetDisplay.textContent = data.target_points;
                }
                if (completionDisplay && data.completion_points !== undefined) {
                    completionDisplay.textContent = data.completion_points;
                }
            })
            .catch(error => console.error('Błąd ładowania ustawień minigrów:', error));
    }

    // =====================================================================
    // TEST MODES
    // =====================================================================

    // Tetris Test Mode
    document.getElementById('tetris-test-btn')?.addEventListener('click', () => {
        document.getElementById('tetris-test-view').style.display = 'block';
    });

    document.getElementById('tetris-test-start-btn')?.addEventListener('click', () => {
        if (typeof TetrisGame !== 'undefined') {
            const tetrisGame = new TetrisGame('tetris-test-canvas', 0, 0, 0);
            tetrisGame.start();
        }
        document.getElementById('tetris-test-start-section').style.display = 'none';
        document.getElementById('tetris-test-left-controls').style.display = 'block';
        document.getElementById('tetris-test-right-controls').style.display = 'block';
        document.getElementById('tetris-test-exit-btn').style.display = 'block';
    });

    document.getElementById('tetris-test-close-btn')?.addEventListener('click', () => {
        document.getElementById('tetris-test-view').style.display = 'none';
        document.getElementById('tetris-test-start-section').style.display = 'block';
        document.getElementById('tetris-test-left-controls').style.display = 'none';
        document.getElementById('tetris-test-right-controls').style.display = 'none';
        document.getElementById('tetris-test-exit-btn').style.display = 'none';
    });

    document.getElementById('tetris-test-exit-btn')?.addEventListener('click', () => {
        if (confirm('Czy na pewno chcesz zakończyć test?')) {
            document.getElementById('tetris-test-view').style.display = 'none';
            document.getElementById('tetris-test-start-section').style.display = 'block';
            document.getElementById('tetris-test-left-controls').style.display = 'none';
            document.getElementById('tetris-test-right-controls').style.display = 'none';
            document.getElementById('tetris-test-exit-btn').style.display = 'none';
        }
    });

    // Arkanoid Test Mode
    document.getElementById('arkanoid-test-btn')?.addEventListener('click', () => {
        document.getElementById('arkanoid-test-view').style.display = 'block';
    });

    document.getElementById('arkanoid-test-start-btn')?.addEventListener('click', () => {
        if (typeof ArkanoidGame !== 'undefined') {
            const arkanoidGame = new ArkanoidGame('arkanoid-test-canvas', 0, 0, 0);
            arkanoidGame.start();
        }
        document.getElementById('arkanoid-test-start-section').style.display = 'none';
        document.getElementById('arkanoid-test-left-controls').style.display = 'block';
        document.getElementById('arkanoid-test-right-controls').style.display = 'block';
        document.getElementById('arkanoid-test-exit-btn').style.display = 'block';
    });

    document.getElementById('arkanoid-test-close-btn')?.addEventListener('click', () => {
        document.getElementById('arkanoid-test-view').style.display = 'none';
        document.getElementById('arkanoid-test-start-section').style.display = 'block';
        document.getElementById('arkanoid-test-left-controls').style.display = 'none';
        document.getElementById('arkanoid-test-right-controls').style.display = 'none';
        document.getElementById('arkanoid-test-exit-btn').style.display = 'none';
    });

    document.getElementById('arkanoid-test-exit-btn')?.addEventListener('click', () => {
        if (confirm('Czy na pewno chcesz zakończyć test?')) {
            document.getElementById('arkanoid-test-view').style.display = 'none';
            document.getElementById('arkanoid-test-start-section').style.display = 'block';
            document.getElementById('arkanoid-test-left-controls').style.display = 'none';
            document.getElementById('arkanoid-test-right-controls').style.display = 'none';
            document.getElementById('arkanoid-test-exit-btn').style.display = 'none';
        }
    });

    // Snake Test Mode
    document.getElementById('snake-test-btn')?.addEventListener('click', () => {
        document.getElementById('snake-test-view').style.display = 'block';
    });

    document.getElementById('snake-test-start-btn')?.addEventListener('click', () => {
        if (typeof SnakeGame !== 'undefined') {
            const snakeGame = new SnakeGame('snake-test-canvas', 0, 0, 0);
            snakeGame.start();
        }
        document.getElementById('snake-test-start-section').style.display = 'none';
        document.getElementById('snake-test-left-controls').style.display = 'block';
        document.getElementById('snake-test-right-controls').style.display = 'block';
        document.getElementById('snake-test-exit-btn').style.display = 'block';
    });

    document.getElementById('snake-test-close-btn')?.addEventListener('click', () => {
        document.getElementById('snake-test-view').style.display = 'none';
        document.getElementById('snake-test-start-section').style.display = 'block';
        document.getElementById('snake-test-left-controls').style.display = 'none';
        document.getElementById('snake-test-right-controls').style.display = 'none';
        document.getElementById('snake-test-exit-btn').style.display = 'none';
    });

    document.getElementById('snake-test-exit-btn')?.addEventListener('click', () => {
        if (confirm('Czy na pewno chcesz zakończyć test?')) {
            document.getElementById('snake-test-view').style.display = 'none';
            document.getElementById('snake-test-start-section').style.display = 'block';
            document.getElementById('snake-test-left-controls').style.display = 'none';
            document.getElementById('snake-test-right-controls').style.display = 'none';
            document.getElementById('snake-test-exit-btn').style.display = 'none';
        }
    });

    // T-Rex Test Mode
    document.getElementById('trex-test-btn')?.addEventListener('click', () => {
        document.getElementById('trex-test-view').style.display = 'block';
    });

    document.getElementById('trex-test-start-btn')?.addEventListener('click', () => {
        if (typeof TRexGame !== 'undefined') {
            const trexGame = new TRexGame('trex-test-canvas', 0, 0, 0);
            trexGame.start();
        }
        document.getElementById('trex-test-start-section').style.display = 'none';
        document.getElementById('trex-test-jump-control').style.display = 'block';
        document.getElementById('trex-test-exit-btn').style.display = 'block';
    });

    document.getElementById('trex-test-close-btn')?.addEventListener('click', () => {
        document.getElementById('trex-test-view').style.display = 'none';
        document.getElementById('trex-test-start-section').style.display = 'block';
        document.getElementById('trex-test-jump-control').style.display = 'none';
        document.getElementById('trex-test-exit-btn').style.display = 'none';
    });

    document.getElementById('trex-test-exit-btn')?.addEventListener('click', () => {
        if (confirm('Czy na pewno chcesz zakończyć test?')) {
            document.getElementById('trex-test-view').style.display = 'none';
            document.getElementById('trex-test-start-section').style.display = 'block';
            document.getElementById('trex-test-jump-control').style.display = 'none';
            document.getElementById('trex-test-exit-btn').style.display = 'none';
        }
    });

    // =====================================================================
    // TAB EVENT LISTENERS
    // =====================================================================
    document.querySelector('button[data-bs-target="#minigames"]')?.addEventListener('click', () => {
        loadMinigamesStatus();
        loadMinigamesSettings();
    });

    // =====================================================================
    // EXPORTS
    // =====================================================================
    window.loadMinigamesStatus = loadMinigamesStatus;
    window.loadMinigamesSettings = loadMinigamesSettings;
    window.updateMinigameSetting = updateMinigameSetting;
});
