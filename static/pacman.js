class PacManGame {
    constructor(canvasId, playerId, eventId, currentScore = 0) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.playerId = playerId;
        this.eventId = eventId;

        // Wymiary
        this.gridSize = 19; // 19x19 grid

        // Ustaw początkowy wynik z serwera
        this.score = currentScore;
        this.dotsEaten = 0;
        this.totalDots = 0;

        // Stan gry
        this.gameOver = false;
        this.gameWon = false;
        this.gameRunning = false;
        this.speed = 200; // ms
        this.lastMove = 0;

        // PacMan
        this.pacman = {
            x: 9,
            y: 15,
            direction: { x: 0, y: 0 },
            nextDirection: { x: 0, y: 0 },
            mouthOpen: true,
            mouthAngle: 0
        };

        // Duchy (ghosts)
        this.ghosts = [
            { x: 8, y: 7, color: '#FF0000', direction: { x: 1, y: 0 }, name: 'Blinky' },
            { x: 9, y: 7, color: '#FFB8FF', direction: { x: -1, y: 0 }, name: 'Pinky' },
            { x: 10, y: 7, color: '#00FFFF', direction: { x: 1, y: 0 }, name: 'Inky' },
            { x: 11, y: 7, color: '#FFB852', direction: { x: -1, y: 0 }, name: 'Clyde' }
        ];
        this.ghostSpeed = 250; // ms
        this.lastGhostMove = 0;

        // Labirynt (0 = ściana, 1 = kropka, 2 = puste, 3 = power pellet)
        this.maze = [
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,0],
            [0,1,0,0,1,0,0,0,1,0,1,0,0,0,1,0,0,1,0],
            [0,3,0,0,1,0,0,0,1,0,1,0,0,0,1,0,0,3,0],
            [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
            [0,1,0,0,1,0,1,0,0,0,0,0,1,0,1,0,0,1,0],
            [0,1,1,1,1,0,1,1,1,0,1,1,1,0,1,1,1,1,0],
            [0,0,0,0,1,0,0,0,2,0,2,0,0,0,1,0,0,0,0],
            [0,0,0,0,1,0,2,2,2,2,2,2,2,0,1,0,0,0,0],
            [0,0,0,0,1,0,2,0,0,2,0,0,2,0,1,0,0,0,0],
            [2,2,2,2,1,2,2,0,2,2,2,0,2,2,1,2,2,2,2],
            [0,0,0,0,1,0,2,0,0,0,0,0,2,0,1,0,0,0,0],
            [0,0,0,0,1,0,2,2,2,2,2,2,2,0,1,0,0,0,0],
            [0,0,0,0,1,0,2,0,0,0,0,0,2,0,1,0,0,0,0],
            [0,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,0],
            [0,1,0,0,1,0,0,0,1,0,1,0,0,0,1,0,0,1,0],
            [0,3,1,0,1,1,1,1,1,1,1,1,1,1,1,0,1,3,0],
            [0,0,1,0,1,0,1,0,0,0,0,0,1,0,1,0,1,0,0],
            [0,1,1,1,1,0,1,1,1,0,1,1,1,0,1,1,1,1,0],
            [0,1,0,0,0,0,0,0,1,0,1,0,0,0,0,0,0,1,0],
            [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        ];

        // Oblicz rozmiar canvas (MUSI być po zdefiniowaniu maze)
        this.calculateCanvasSize();

        // Policz kropki
        this.countDots();

        // Power mode
        this.powerMode = false;
        this.powerModeTimer = 0;
        this.powerModeDuration = 5000; // 5 sekund

        // Kolory
        this.wallColor = '#0000FF';
        this.dotColor = '#FFB852';
        this.powerPelletColor = '#FFFFFF';
        this.pacmanColor = '#FFFF00';
        this.bgColor = '#000000';

        this.setupControls();
        this.setupTouchControls();
    }

    calculateCanvasSize() {
        const availableHeight = window.innerHeight * 0.84 - 4;
        const availableWidth = Math.min(window.innerHeight * 0.84 - 4, window.innerWidth - 142);

        const maxSize = Math.min(availableWidth, availableHeight);
        const blockSize = Math.floor(maxSize / (this.gridSize + 3)); // +3 dla marginesów

        this.blockSize = Math.min(blockSize, 25);
        this.canvas.width = (this.gridSize) * this.blockSize;
        this.canvas.height = (this.maze.length) * this.blockSize;
    }

    countDots() {
        this.totalDots = 0;
        for (let row = 0; row < this.maze.length; row++) {
            for (let col = 0; col < this.maze[row].length; col++) {
                if (this.maze[row][col] === 1 || this.maze[row][col] === 3) {
                    this.totalDots++;
                }
            }
        }
    }

    setupControls() {
        document.addEventListener('keydown', (e) => {
            if (!this.gameRunning || this.gameOver || this.gameWon) return;

            switch(e.key) {
                case 'ArrowLeft':
                    this.pacman.nextDirection = { x: -1, y: 0 };
                    e.preventDefault();
                    break;
                case 'ArrowRight':
                    this.pacman.nextDirection = { x: 1, y: 0 };
                    e.preventDefault();
                    break;
                case 'ArrowUp':
                    this.pacman.nextDirection = { x: 0, y: -1 };
                    e.preventDefault();
                    break;
                case 'ArrowDown':
                    this.pacman.nextDirection = { x: 0, y: 1 };
                    e.preventDefault();
                    break;
            }
        });
    }

    setupTouchControls() {
        const leftBtn = document.getElementById('pacman-left-btn');
        const rightBtn = document.getElementById('pacman-right-btn');
        const upBtn = document.getElementById('pacman-up-btn');
        const downBtn = document.getElementById('pacman-down-btn');

        if (leftBtn) {
            leftBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver && !this.gameWon) {
                    this.pacman.nextDirection = { x: -1, y: 0 };
                }
            });
            leftBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver && !this.gameWon) {
                    this.pacman.nextDirection = { x: -1, y: 0 };
                }
            });
        }

        if (rightBtn) {
            rightBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver && !this.gameWon) {
                    this.pacman.nextDirection = { x: 1, y: 0 };
                }
            });
            rightBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver && !this.gameWon) {
                    this.pacman.nextDirection = { x: 1, y: 0 };
                }
            });
        }

        if (upBtn) {
            upBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver && !this.gameWon) {
                    this.pacman.nextDirection = { x: 0, y: -1 };
                }
            });
            upBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver && !this.gameWon) {
                    this.pacman.nextDirection = { x: 0, y: -1 };
                }
            });
        }

        if (downBtn) {
            downBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver && !this.gameWon) {
                    this.pacman.nextDirection = { x: 0, y: 1 };
                }
            });
            downBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver && !this.gameWon) {
                    this.pacman.nextDirection = { x: 0, y: 1 };
                }
            });
        }
    }

    start() {
        this.gameRunning = true;
        this.gameOver = false;
        this.gameWon = false;
        this.score = 0;
        this.dotsEaten = 0;
        this.powerMode = false;

        // Reset PacMan
        this.pacman.x = 9;
        this.pacman.y = 15;
        this.pacman.direction = { x: 0, y: 0 };
        this.pacman.nextDirection = { x: 0, y: 0 };

        // Reset duchów
        this.ghosts = [
            { x: 8, y: 7, color: '#FF0000', direction: { x: 1, y: 0 }, name: 'Blinky' },
            { x: 9, y: 7, color: '#FFB8FF', direction: { x: -1, y: 0 }, name: 'Pinky' },
            { x: 10, y: 7, color: '#00FFFF', direction: { x: 1, y: 0 }, name: 'Inky' },
            { x: 11, y: 7, color: '#FFB852', direction: { x: -1, y: 0 }, name: 'Clyde' }
        ];

        // Reset labiryntu
        this.maze = [
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,0],
            [0,1,0,0,1,0,0,0,1,0,1,0,0,0,1,0,0,1,0],
            [0,3,0,0,1,0,0,0,1,0,1,0,0,0,1,0,0,3,0],
            [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
            [0,1,0,0,1,0,1,0,0,0,0,0,1,0,1,0,0,1,0],
            [0,1,1,1,1,0,1,1,1,0,1,1,1,0,1,1,1,1,0],
            [0,0,0,0,1,0,0,0,2,0,2,0,0,0,1,0,0,0,0],
            [0,0,0,0,1,0,2,2,2,2,2,2,2,0,1,0,0,0,0],
            [0,0,0,0,1,0,2,0,0,2,0,0,2,0,1,0,0,0,0],
            [2,2,2,2,1,2,2,0,2,2,2,0,2,2,1,2,2,2,2],
            [0,0,0,0,1,0,2,0,0,0,0,0,2,0,1,0,0,0,0],
            [0,0,0,0,1,0,2,2,2,2,2,2,2,0,1,0,0,0,0],
            [0,0,0,0,1,0,2,0,0,0,0,0,2,0,1,0,0,0,0],
            [0,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,0],
            [0,1,0,0,1,0,0,0,1,0,1,0,0,0,1,0,0,1,0],
            [0,3,1,0,1,1,1,1,1,1,1,1,1,1,1,0,1,3,0],
            [0,0,1,0,1,0,1,0,0,0,0,0,1,0,1,0,1,0,0],
            [0,1,1,1,1,0,1,1,1,0,1,1,1,0,1,1,1,1,0],
            [0,1,0,0,0,0,0,0,1,0,1,0,0,0,0,0,0,1,0],
            [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        ];

        this.countDots();
        this.lastMove = Date.now();
        this.lastGhostMove = Date.now();
        this.gameLoop();
    }

    canMove(x, y) {
        if (y < 0 || y >= this.maze.length || x < 0 || x >= this.maze[0].length) {
            return false;
        }
        return this.maze[y][x] !== 0;
    }

    updatePacMan() {
        // Sprawdź czy można zmienić kierunek
        const nextX = this.pacman.x + this.pacman.nextDirection.x;
        const nextY = this.pacman.y + this.pacman.nextDirection.y;

        if (this.canMove(nextX, nextY)) {
            this.pacman.direction = { ...this.pacman.nextDirection };
        }

        // Porusz PacMana
        const newX = this.pacman.x + this.pacman.direction.x;
        const newY = this.pacman.y + this.pacman.direction.y;

        if (this.canMove(newX, newY)) {
            this.pacman.x = newX;
            this.pacman.y = newY;

            // Zjedzenie kropki
            if (this.maze[newY][newX] === 1) {
                this.maze[newY][newX] = 2;
                this.score += 10;
                this.dotsEaten++;
            }

            // Zjedzenie power pelleta
            if (this.maze[newY][newX] === 3) {
                this.maze[newY][newX] = 2;
                this.score += 50;
                this.dotsEaten++;
                this.activatePowerMode();
            }

            // Sprawdź czy wygrano
            if (this.dotsEaten >= this.totalDots) {
                this.gameWon = true;
                this.gameRunning = false;
                this.submitScore();
            }
        }

        // Animacja ust
        this.pacman.mouthOpen = !this.pacman.mouthOpen;
    }

    activatePowerMode() {
        this.powerMode = true;
        this.powerModeTimer = Date.now();
    }

    updateGhosts() {
        for (let ghost of this.ghosts) {
            // Losowy ruch ducha
            const possibleDirections = [
                { x: 1, y: 0 },
                { x: -1, y: 0 },
                { x: 0, y: 1 },
                { x: 0, y: -1 }
            ];

            // Filtruj kierunki - tylko te, w które można się poruszyć
            const validDirections = possibleDirections.filter(dir => {
                const newX = ghost.x + dir.x;
                const newY = ghost.y + dir.y;
                return this.canMove(newX, newY);
            });

            // Wybierz losowy kierunek z dostępnych
            if (validDirections.length > 0) {
                const randomDir = validDirections[Math.floor(Math.random() * validDirections.length)];
                ghost.direction = randomDir;
            }

            // Porusz ducha
            const newX = ghost.x + ghost.direction.x;
            const newY = ghost.y + ghost.direction.y;

            if (this.canMove(newX, newY)) {
                ghost.x = newX;
                ghost.y = newY;
            }
        }
    }

    checkCollisions() {
        for (let ghost of this.ghosts) {
            if (ghost.x === this.pacman.x && ghost.y === this.pacman.y) {
                if (this.powerMode) {
                    // Zjedz ducha - bonus punktów
                    this.score += 200;
                    // Reset pozycji ducha
                    ghost.x = 9;
                    ghost.y = 7;
                } else {
                    // Game over
                    this.gameOver = true;
                    this.gameRunning = false;
                    this.submitScore();
                }
            }
        }
    }

    update(timestamp) {
        if (!this.gameRunning || this.gameOver || this.gameWon) return;

        // Update power mode
        if (this.powerMode && (Date.now() - this.powerModeTimer > this.powerModeDuration)) {
            this.powerMode = false;
        }

        // Update PacMan
        if (timestamp - this.lastMove > this.speed) {
            this.updatePacMan();
            this.lastMove = timestamp;
        }

        // Update ghosts
        if (timestamp - this.lastGhostMove > this.ghostSpeed) {
            this.updateGhosts();
            this.checkCollisions();
            this.lastGhostMove = timestamp;
        }
    }

    draw() {
        // Wyczyść canvas
        this.ctx.fillStyle = this.bgColor;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Rysuj labirynt
        for (let row = 0; row < this.maze.length; row++) {
            for (let col = 0; col < this.maze[row].length; col++) {
                const x = col * this.blockSize;
                const y = row * this.blockSize;

                if (this.maze[row][col] === 0) {
                    // Ściana
                    this.ctx.fillStyle = this.wallColor;
                    this.ctx.fillRect(x, y, this.blockSize, this.blockSize);
                } else if (this.maze[row][col] === 1) {
                    // Kropka
                    this.ctx.fillStyle = this.dotColor;
                    this.ctx.beginPath();
                    this.ctx.arc(x + this.blockSize / 2, y + this.blockSize / 2, 3, 0, Math.PI * 2);
                    this.ctx.fill();
                } else if (this.maze[row][col] === 3) {
                    // Power pellet
                    this.ctx.fillStyle = this.powerPelletColor;
                    this.ctx.beginPath();
                    this.ctx.arc(x + this.blockSize / 2, y + this.blockSize / 2, 6, 0, Math.PI * 2);
                    this.ctx.fill();
                }
            }
        }

        // Rysuj duchy
        for (let ghost of this.ghosts) {
            const x = ghost.x * this.blockSize;
            const y = ghost.y * this.blockSize;

            if (this.powerMode) {
                this.ctx.fillStyle = '#0000FF';
            } else {
                this.ctx.fillStyle = ghost.color;
            }

            // Ciało ducha
            this.ctx.beginPath();
            this.ctx.arc(x + this.blockSize / 2, y + this.blockSize / 2, this.blockSize / 2.5, Math.PI, 0);
            this.ctx.lineTo(x + this.blockSize * 0.8, y + this.blockSize);
            this.ctx.lineTo(x + this.blockSize * 0.7, y + this.blockSize * 0.85);
            this.ctx.lineTo(x + this.blockSize * 0.6, y + this.blockSize);
            this.ctx.lineTo(x + this.blockSize * 0.5, y + this.blockSize * 0.85);
            this.ctx.lineTo(x + this.blockSize * 0.4, y + this.blockSize);
            this.ctx.lineTo(x + this.blockSize * 0.3, y + this.blockSize * 0.85);
            this.ctx.lineTo(x + this.blockSize * 0.2, y + this.blockSize);
            this.ctx.closePath();
            this.ctx.fill();

            // Oczy ducha
            if (!this.powerMode) {
                this.ctx.fillStyle = '#FFFFFF';
                this.ctx.fillRect(x + this.blockSize * 0.3, y + this.blockSize * 0.35, this.blockSize * 0.15, this.blockSize * 0.2);
                this.ctx.fillRect(x + this.blockSize * 0.55, y + this.blockSize * 0.35, this.blockSize * 0.15, this.blockSize * 0.2);

                this.ctx.fillStyle = '#0000FF';
                this.ctx.fillRect(x + this.blockSize * 0.35, y + this.blockSize * 0.4, this.blockSize * 0.08, this.blockSize * 0.12);
                this.ctx.fillRect(x + this.blockSize * 0.6, y + this.blockSize * 0.4, this.blockSize * 0.08, this.blockSize * 0.12);
            }
        }

        // Rysuj PacMana
        const pacX = this.pacman.x * this.blockSize;
        const pacY = this.pacman.y * this.blockSize;

        this.ctx.fillStyle = this.pacmanColor;
        this.ctx.beginPath();

        // Oblicz kąt ust w zależności od kierunku
        let startAngle = 0.2;
        let endAngle = Math.PI * 2 - 0.2;

        if (this.pacman.direction.x === 1) {
            startAngle = 0.2;
            endAngle = Math.PI * 2 - 0.2;
        } else if (this.pacman.direction.x === -1) {
            startAngle = Math.PI + 0.2;
            endAngle = Math.PI - 0.2;
        } else if (this.pacman.direction.y === -1) {
            startAngle = Math.PI * 1.5 + 0.2;
            endAngle = Math.PI * 1.5 - 0.2;
        } else if (this.pacman.direction.y === 1) {
            startAngle = Math.PI * 0.5 + 0.2;
            endAngle = Math.PI * 0.5 - 0.2;
        }

        if (this.pacman.mouthOpen) {
            this.ctx.arc(pacX + this.blockSize / 2, pacY + this.blockSize / 2, this.blockSize / 2.5, startAngle, endAngle);
            this.ctx.lineTo(pacX + this.blockSize / 2, pacY + this.blockSize / 2);
        } else {
            this.ctx.arc(pacX + this.blockSize / 2, pacY + this.blockSize / 2, this.blockSize / 2.5, 0, Math.PI * 2);
        }
        this.ctx.fill();

        // Wyświetl wynik
        this.ctx.fillStyle = '#FFFFFF';
        this.ctx.font = '16px Arial';
        this.ctx.fillText(`Wynik: ${this.score}`, 10, 20);
        this.ctx.fillText(`Kropki: ${this.dotsEaten}/${this.totalDots}`, 10, 40);

        if (this.powerMode) {
            this.ctx.fillStyle = '#00FF00';
            this.ctx.fillText('POWER MODE!', this.canvas.width - 120, 20);
        }

        // Game over / Win screen
        if (this.gameOver) {
            this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.fillStyle = '#FF0000';
            this.ctx.font = '30px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.fillText('GAME OVER!', this.canvas.width / 2, this.canvas.height / 2);
            this.ctx.fillStyle = '#FFFFFF';
            this.ctx.font = '20px Arial';
            this.ctx.fillText(`Twój wynik: ${this.score}`, this.canvas.width / 2, this.canvas.height / 2 + 40);
        }

        if (this.gameWon) {
            this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.fillStyle = '#00FF00';
            this.ctx.font = '30px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.fillText('WYGRAŁEŚ!', this.canvas.width / 2, this.canvas.height / 2);
            this.ctx.fillStyle = '#FFFFFF';
            this.ctx.font = '20px Arial';
            this.ctx.fillText(`Twój wynik: ${this.score}`, this.canvas.width / 2, this.canvas.height / 2 + 40);
        }
    }

    gameLoop(timestamp = 0) {
        if (!this.gameRunning && !this.gameOver && !this.gameWon) return;

        this.update(timestamp);
        this.draw();

        if (this.gameRunning) {
            requestAnimationFrame((ts) => this.gameLoop(ts));
        }
    }

    async submitScore() {
        try {
            const response = await fetch('/api/player/minigame/complete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    player_id: this.playerId,
                    event_id: this.eventId,
                    minigame_type: 'pacman',
                    score: this.score
                })
            });

            if (response.ok) {
                console.log('Wynik zapisany!');
            }
        } catch (error) {
            console.error('Błąd podczas zapisywania wyniku:', error);
        }
    }

    destroy() {
        this.gameRunning = false;
    }
}
