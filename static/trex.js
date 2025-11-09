class TRexGame {
    constructor(canvasId, playerId, eventId, initialScore = 0) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.playerId = playerId;
        this.eventId = eventId;
        this.gameRunning = false;
        this.initialScore = initialScore;
        this.totalScore = initialScore;
        this.sessionScore = 0;

        // Rozmiar canvas
        this.canvasWidth = 800;
        this.canvasHeight = 400;

        // Dinozaur
        this.dino = {
            x: 50,
            y: 0,
            width: 40,
            height: 50,
            velocityY: 0,
            jumping: false
        };

        // Fizyka
        this.gravity = 0.6;
        this.jumpStrength = -12;
        this.groundY = this.canvasHeight - 100;

        // Przeszkody
        this.obstacles = [];
        this.obstacleSpeed = 4; // Umiarkowana prędkość
        this.obstacleSpawnTimer = 0;
        this.obstacleSpawnInterval = 100; // Co ile klatek spawnie się przeszkoda

        // Punktacja
        this.score = 0;
        this.obstaclesPassed = 0;
        this.pointsPerObstacle = 1;

        // Przyciski kontrolne
        this.setupControls();
    }

    setupControls() {
        // Przycisk skoku
        const jumpBtn = document.getElementById('trex-jump-btn');
        if (jumpBtn) {
            jumpBtn.addEventListener('click', () => this.jump());
            jumpBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                this.jump();
            });
        }

        // Klawiatura (opcjonalnie)
        document.addEventListener('keydown', (e) => {
            if (this.gameRunning && (e.code === 'Space' || e.code === 'ArrowUp')) {
                e.preventDefault();
                this.jump();
            }
        });
    }

    jump() {
        if (!this.dino.jumping) {
            this.dino.velocityY = this.jumpStrength;
            this.dino.jumping = true;
        }
    }

    start() {
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());

        this.dino.y = this.groundY;
        this.gameRunning = true;
        this.gameLoop();
    }

    resizeCanvas() {
        const container = this.canvas.parentElement;
        const maxWidth = Math.min(container.clientWidth - 20, this.canvasWidth);
        const maxHeight = Math.min(container.clientHeight - 20, this.canvasHeight);

        const scale = Math.min(maxWidth / this.canvasWidth, maxHeight / this.canvasHeight);

        this.canvas.width = this.canvasWidth;
        this.canvas.height = this.canvasHeight;
        this.canvas.style.width = (this.canvasWidth * scale) + 'px';
        this.canvas.style.height = (this.canvasHeight * scale) + 'px';
    }

    update() {
        // Aktualizuj dinozaura
        this.dino.velocityY += this.gravity;
        this.dino.y += this.dino.velocityY;

        // Sprawdź czy dinozaur dotknął ziemi
        if (this.dino.y >= this.groundY) {
            this.dino.y = this.groundY;
            this.dino.velocityY = 0;
            this.dino.jumping = false;
        }

        // Spawn przeszkód
        this.obstacleSpawnTimer++;
        if (this.obstacleSpawnTimer >= this.obstacleSpawnInterval) {
            this.spawnObstacle();
            this.obstacleSpawnTimer = 0;
            // Losowa częstotliwość spawnu
            this.obstacleSpawnInterval = 80 + Math.random() * 60;
        }

        // Aktualizuj przeszkody
        for (let i = this.obstacles.length - 1; i >= 0; i--) {
            const obstacle = this.obstacles[i];
            obstacle.x -= this.obstacleSpeed;

            // Sprawdź kolizję
            if (this.checkCollision(this.dino, obstacle)) {
                this.endGame();
                return;
            }

            // Sprawdź czy przeszkoda została pokonana
            if (!obstacle.passed && obstacle.x + obstacle.width < this.dino.x) {
                obstacle.passed = true;
                this.obstaclesPassed++;
                this.score++;
                this.sessionScore++;
                this.updateScoreDisplay();

                // Sprawdź czy osiągnięto 20 punktów
                if (this.sessionScore >= 20) {
                    this.completeGame();
                    return;
                }
            }

            // Usuń przeszkody poza ekranem
            if (obstacle.x + obstacle.width < 0) {
                this.obstacles.splice(i, 1);
            }
        }
    }

    spawnObstacle() {
        const types = ['cactus', 'bird'];
        const type = types[Math.floor(Math.random() * types.length)];

        const obstacle = {
            x: this.canvasWidth,
            width: 20 + Math.random() * 20,
            height: 30 + Math.random() * 30,
            type: type,
            passed: false
        };

        if (type === 'bird') {
            // Ptak leci na różnych wysokościach
            obstacle.y = this.groundY - 80 - Math.random() * 60;
        } else {
            // Kaktus na ziemi
            obstacle.y = this.groundY + this.dino.height - obstacle.height;
        }

        this.obstacles.push(obstacle);
    }

    checkCollision(dino, obstacle) {
        return dino.x < obstacle.x + obstacle.width &&
               dino.x + dino.width > obstacle.x &&
               dino.y < obstacle.y + obstacle.height &&
               dino.y + dino.height > obstacle.y;
    }

    draw() {
        // Wyczyść canvas
        this.ctx.fillStyle = '#f7f7f7';
        this.ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight);

        // Rysuj ziemię
        this.ctx.fillStyle = '#535353';
        this.ctx.fillRect(0, this.groundY + this.dino.height, this.canvasWidth, 2);

        // Rysuj dinozaura (prosty prostokąt)
        this.ctx.fillStyle = '#535353';
        this.ctx.fillRect(this.dino.x, this.dino.y, this.dino.width, this.dino.height);

        // Oko dinozaura
        this.ctx.fillStyle = '#fff';
        this.ctx.fillRect(this.dino.x + 30, this.dino.y + 10, 5, 5);

        // Rysuj przeszkody
        for (const obstacle of this.obstacles) {
            if (obstacle.type === 'cactus') {
                // Kaktus (zielony)
                this.ctx.fillStyle = '#2d5016';
                this.ctx.fillRect(obstacle.x, obstacle.y, obstacle.width, obstacle.height);

                // Kolce
                this.ctx.fillStyle = '#1a3010';
                for (let i = 0; i < 3; i++) {
                    this.ctx.fillRect(
                        obstacle.x + i * obstacle.width / 3,
                        obstacle.y + obstacle.height / 3,
                        obstacle.width / 4,
                        obstacle.height / 6
                    );
                }
            } else {
                // Ptak (brązowy)
                this.ctx.fillStyle = '#8B4513';
                this.ctx.fillRect(obstacle.x, obstacle.y, obstacle.width, obstacle.height / 2);

                // Skrzydła
                this.ctx.fillRect(obstacle.x - 5, obstacle.y + 5, obstacle.width / 3, obstacle.height / 4);
                this.ctx.fillRect(obstacle.x + obstacle.width - 5, obstacle.y + 5, obstacle.width / 3, obstacle.height / 4);
            }
        }

        // Wyświetl punkty sesji
        this.ctx.fillStyle = '#535353';
        this.ctx.font = 'bold 24px Arial';
        this.ctx.textAlign = 'right';
        this.ctx.fillText(`Punkty: ${this.score}`, this.canvasWidth - 20, 40);
    }

    updateScoreDisplay() {
        const scoreDisplay = document.getElementById('trex-score');
        if (scoreDisplay) {
            scoreDisplay.textContent = this.initialScore + this.sessionScore;
        }
    }

    gameLoop() {
        if (!this.gameRunning) return;

        this.update();
        this.draw();

        requestAnimationFrame(() => this.gameLoop());
    }

    async completeGame() {
        this.gameRunning = false;

        try {
            const response = await fetch('/api/player/minigame/complete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    player_id: this.playerId,
                    game_type: 'trex',
                    score: this.sessionScore
                })
            });

            const result = await response.json();

            if (response.ok) {
                alert(`🎉 Gratulacje! Ukończyłeś grę T-Rex!\n\nZdobyte punkty: ${this.sessionScore}\nŁączny wynik: ${result.total_score}/20`);

                // Wróć do głównego widoku
                document.getElementById('trex-game-view').style.display = 'none';
                document.getElementById('main-view').style.display = 'block';
            } else {
                alert('Błąd: ' + result.error);
            }
        } catch (error) {
            console.error('Error completing T-Rex game:', error);
            alert('Błąd podczas zapisywania wyniku');
        }
    }

    async endGame() {
        this.gameRunning = false;

        // Jeśli zdobył jakieś punkty, zapisz je
        if (this.sessionScore > 0) {
            try {
                const response = await fetch('/api/player/minigame/complete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        player_id: this.playerId,
                        game_type: 'trex',
                        score: this.sessionScore
                    })
                });

                const result = await response.json();

                if (response.ok) {
                    alert(`💥 Game Over!\n\nZdobyte punkty: ${this.sessionScore}\nŁączny wynik: ${result.total_score}/20\n\nSpróbuj ponownie!`);
                }
            } catch (error) {
                console.error('Error saving T-Rex score:', error);
            }
        } else {
            alert('💥 Game Over! Spróbuj ponownie!');
        }

        // Reset widoku startowego
        document.getElementById('trex-start-section').style.display = 'block';
        document.getElementById('trex-jump-control').style.display = 'none';
        document.getElementById('trex-exit-btn').style.display = 'none';
        document.getElementById('trex-start-btn').textContent = 'SPRÓBUJ PONOWNIE';
    }
}
