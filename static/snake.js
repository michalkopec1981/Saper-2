class SnakeGame {
    constructor(canvasId, playerId, eventId, currentScore = 0) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.playerId = playerId;
        this.eventId = eventId;

        // Wymiary - dostosowane do ekranu mobilnego
        this.gridSize = 20;
        this.calculateCanvasSize();

        // Ustaw początkowy wynik z serwera
        this.score = currentScore;

        // Stan gry
        this.gameOver = false;
        this.gameRunning = false;
        this.speed = 150; // ms - czas między ruchami
        this.lastMove = 0;

        // Wąż
        this.snake = [];
        this.direction = { x: 1, y: 0 };
        this.nextDirection = { x: 1, y: 0 };

        // Jedzenie
        this.food = { x: 0, y: 0 };

        // Kolory
        this.snakeColor = '#0DFF72';
        this.foodColor = '#FF0D72';
        this.gridColor = '#222';

        this.setupControls();
        this.setupTouchControls();
    }

    calculateCanvasSize() {
        // Oblicz rozmiar canvas bazując na dostępnej przestrzeni
        const availableHeight = window.innerHeight * 0.84 - 4;
        const availableWidth = Math.min(window.innerHeight * 0.84 - 4, window.innerWidth - 142);

        // Oblicz blockSize tak, aby plansza była kwadratowa i zmieściła się w dostępnej przestrzeni
        const maxSize = Math.min(availableWidth, availableHeight);
        const blockSize = Math.floor(maxSize / this.gridSize);

        // Ustaw wymiary canvas (kwadratowa plansza)
        this.blockSize = Math.min(blockSize, 30);
        this.canvas.width = this.gridSize * this.blockSize;
        this.canvas.height = this.gridSize * this.blockSize;

        this.cols = this.gridSize;
        this.rows = this.gridSize;
    }

    setupControls() {
        // Sterowanie klawiaturą (dla komputerów)
        document.addEventListener('keydown', (e) => {
            if (!this.gameRunning || this.gameOver) return;

            switch(e.key) {
                case 'ArrowLeft':
                    if (this.direction.x === 0) {
                        this.nextDirection = { x: -1, y: 0 };
                    }
                    e.preventDefault();
                    break;
                case 'ArrowRight':
                    if (this.direction.x === 0) {
                        this.nextDirection = { x: 1, y: 0 };
                    }
                    e.preventDefault();
                    break;
                case 'ArrowUp':
                    if (this.direction.y === 0) {
                        this.nextDirection = { x: 0, y: -1 };
                    }
                    e.preventDefault();
                    break;
                case 'ArrowDown':
                    if (this.direction.y === 0) {
                        this.nextDirection = { x: 0, y: 1 };
                    }
                    e.preventDefault();
                    break;
            }
        });
    }

    setupTouchControls() {
        // Przyciski dotykowe dla urządzeń mobilnych
        const leftBtn = document.getElementById('snake-left-btn');
        const rightBtn = document.getElementById('snake-right-btn');
        const upBtn = document.getElementById('snake-up-btn');
        const downBtn = document.getElementById('snake-down-btn');

        if (leftBtn) {
            leftBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver && this.direction.x === 0) {
                    this.nextDirection = { x: -1, y: 0 };
                }
            });
            leftBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver && this.direction.x === 0) {
                    this.nextDirection = { x: -1, y: 0 };
                }
            });
        }

        if (rightBtn) {
            rightBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver && this.direction.x === 0) {
                    this.nextDirection = { x: 1, y: 0 };
                }
            });
            rightBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver && this.direction.x === 0) {
                    this.nextDirection = { x: 1, y: 0 };
                }
            });
        }

        if (upBtn) {
            upBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver && this.direction.y === 0) {
                    this.nextDirection = { x: 0, y: -1 };
                }
            });
            upBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver && this.direction.y === 0) {
                    this.nextDirection = { x: 0, y: -1 };
                }
            });
        }

        if (downBtn) {
            downBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver && this.direction.y === 0) {
                    this.nextDirection = { x: 0, y: 1 };
                }
            });
            downBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver && this.direction.y === 0) {
                    this.nextDirection = { x: 0, y: 1 };
                }
            });
        }
    }

    start() {
        // Inicjalizuj węża na środku planszy
        const centerX = Math.floor(this.cols / 2);
        const centerY = Math.floor(this.rows / 2);

        this.snake = [
            { x: centerX, y: centerY },
            { x: centerX - 1, y: centerY },
            { x: centerX - 2, y: centerY }
        ];

        this.direction = { x: 1, y: 0 };
        this.nextDirection = { x: 1, y: 0 };
        this.gameOver = false;
        this.gameRunning = true;

        this.spawnFood();
        this.updateScore();
        this.gameLoop();
    }

    gameLoop(timestamp = 0) {
        if (!this.gameRunning || this.gameOver) return;

        // Ruch węża co określony czas
        if (timestamp - this.lastMove > this.speed) {
            this.update();
            this.lastMove = timestamp;
        }

        this.draw();
        requestAnimationFrame((ts) => this.gameLoop(ts));
    }

    update() {
        // Aktualizuj kierunek
        this.direction = { ...this.nextDirection };

        // Oblicz nową pozycję głowy
        const head = { ...this.snake[0] };
        head.x += this.direction.x;
        head.y += this.direction.y;

        // Sprawdź kolizję ze ścianami
        if (head.x < 0 || head.x >= this.cols || head.y < 0 || head.y >= this.rows) {
            this.endGame();
            return;
        }

        // Sprawdź kolizję z własnym ciałem
        for (let i = 0; i < this.snake.length; i++) {
            if (head.x === this.snake[i].x && head.y === this.snake[i].y) {
                this.endGame();
                return;
            }
        }

        // Dodaj nową głowę
        this.snake.unshift(head);

        // Sprawdź czy wąż zjadł jedzenie
        if (head.x === this.food.x && head.y === this.food.y) {
            // Zwiększ wynik
            this.score += 1;
            this.updateScore();

            // Przyspiesz grę co 5 punktów
            if (this.score % 5 === 0 && this.speed > 80) {
                this.speed -= 10;
            }

            // Spawn nowego jedzenia
            this.spawnFood();

            // Sprawdź czy osiągnięto cel (20 punktów)
            if (this.score >= 20) {
                this.winGame();
            }
        } else {
            // Usuń ogon (wąż się nie wydłuża)
            this.snake.pop();
        }
    }

    spawnFood() {
        let validPosition = false;

        while (!validPosition) {
            this.food.x = Math.floor(Math.random() * this.cols);
            this.food.y = Math.floor(Math.random() * this.rows);

            // Sprawdź czy jedzenie nie jest na wężu
            validPosition = true;
            for (let segment of this.snake) {
                if (segment.x === this.food.x && segment.y === this.food.y) {
                    validPosition = false;
                    break;
                }
            }
        }
    }

    draw() {
        // Wyczyść canvas
        this.ctx.fillStyle = '#000';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Rysuj siatkę
        this.ctx.strokeStyle = this.gridColor;
        this.ctx.lineWidth = 1;
        for (let i = 0; i <= this.cols; i++) {
            this.ctx.beginPath();
            this.ctx.moveTo(i * this.blockSize, 0);
            this.ctx.lineTo(i * this.blockSize, this.canvas.height);
            this.ctx.stroke();
        }
        for (let i = 0; i <= this.rows; i++) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, i * this.blockSize);
            this.ctx.lineTo(this.canvas.width, i * this.blockSize);
            this.ctx.stroke();
        }

        // Rysuj jedzenie
        this.ctx.fillStyle = this.foodColor;
        this.ctx.beginPath();
        this.ctx.arc(
            this.food.x * this.blockSize + this.blockSize / 2,
            this.food.y * this.blockSize + this.blockSize / 2,
            this.blockSize / 2 - 2,
            0,
            Math.PI * 2
        );
        this.ctx.fill();

        // Rysuj węża
        for (let i = 0; i < this.snake.length; i++) {
            const segment = this.snake[i];

            // Głowa jest jaśniejsza
            if (i === 0) {
                this.ctx.fillStyle = '#0DFF72';
            } else {
                this.ctx.fillStyle = '#0DC2FF';
            }

            this.ctx.fillRect(
                segment.x * this.blockSize + 1,
                segment.y * this.blockSize + 1,
                this.blockSize - 2,
                this.blockSize - 2
            );

            // Efekt 3D
            this.ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
            this.ctx.fillRect(
                segment.x * this.blockSize + 1,
                segment.y * this.blockSize + 1,
                this.blockSize - 2,
                3
            );
        }
    }

    updateScore() {
        const scoreEl = document.getElementById('snake-score');
        if (scoreEl) {
            scoreEl.textContent = this.score;
        }
    }

    async winGame() {
        this.gameRunning = false;
        this.gameOver = true;

        // Wyświetl komunikat
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
        this.ctx.fillRect(0, this.canvas.height / 2 - 60, this.canvas.width, 120);

        this.ctx.fillStyle = '#FFD700';
        this.ctx.font = 'bold 24px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('WYGRAŁEŚ!', this.canvas.width / 2, this.canvas.height / 2 - 20);

        this.ctx.fillStyle = '#FFF';
        this.ctx.font = '16px Arial';
        this.ctx.fillText(`Punkty: ${this.score}`, this.canvas.width / 2, this.canvas.height / 2 + 10);
        this.ctx.fillText('Otrzymujesz nagrodę...', this.canvas.width / 2, this.canvas.height / 2 + 40);

        // Wyślij wynik do serwera
        try {
            const response = await fetch('/api/player/minigame/complete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    player_id: this.playerId,
                    game_type: 'snake',
                    score: this.score
                })
            });

            const result = await response.json();

            if (result.success) {
                // Pokaż komunikat o nagrodzie
                setTimeout(() => {
                    alert(result.message);

                    // Zaktualizuj wyświetlane punkty gracza
                    const scoreEl = document.getElementById('player-score');
                    if (scoreEl) {
                        scoreEl.textContent = result.total_score;
                    }

                    // Wróć do głównego widoku
                    document.getElementById('snake-game-view').style.display = 'none';
                    document.getElementById('game-view').style.display = 'block';

                    // Pokaż wiadomość
                    const messageSection = document.getElementById('message-section');
                    if (messageSection) {
                        messageSection.className = 'alert alert-success';
                        messageSection.innerHTML = `
                            <h4>🎉 Gratulacje!</h4>
                            <p>${result.message}</p>
                            <p><strong>Twoje punkty: ${result.total_score}</strong></p>
                        `;
                        messageSection.style.display = 'block';
                    }
                }, 2000);
            } else {
                alert('Błąd: ' + (result.error || 'Nie udało się zapisać wyniku'));
            }
        } catch (error) {
            console.error('Błąd podczas wysyłania wyniku:', error);
            alert('Błąd połączenia z serwerem');
        }
    }

    endGame() {
        this.gameRunning = false;
        this.gameOver = true;

        // Wyświetl komunikat o przegranej
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
        this.ctx.fillRect(0, this.canvas.height / 2 - 60, this.canvas.width, 120);

        this.ctx.fillStyle = '#FF0000';
        this.ctx.font = 'bold 28px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('GAME OVER', this.canvas.width / 2, this.canvas.height / 2 - 10);

        this.ctx.fillStyle = '#FFF';
        this.ctx.font = '18px Arial';
        this.ctx.fillText(`Punkty: ${this.score}/20`, this.canvas.width / 2, this.canvas.height / 2 + 20);

        // Przywróć przycisk Start
        setTimeout(() => {
            document.getElementById('snake-start-btn').style.display = 'inline-block';
            document.getElementById('snake-start-btn').textContent = 'Spróbuj ponownie';
        }, 1000);
    }
}

// Eksportuj klasę (jeśli używasz modułów)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SnakeGame;
}
