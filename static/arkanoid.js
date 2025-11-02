class ArkanoidGame {
    constructor(canvasId, playerId, eventId, currentScore = 0) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.playerId = playerId;
        this.eventId = eventId;
        
        // Wymiary - dostosowane do ekranu mobilnego
        this.calculateCanvasSize();
        
        // Ustaw początkowy wynik z serwera
        this.score = currentScore;
        
        // Stan gry
        this.gameOver = false;
        this.gameRunning = false;
        this.lives = 3;
        
        // Paletka
        this.paddleWidth = 80;
        this.paddleHeight = 12;
        this.paddleX = (this.canvas.width - this.paddleWidth) / 2;
        this.paddleSpeed = 8;
        this.paddleMoving = 0; // -1 = lewo, 0 = stop, 1 = prawo
        
        // Piłka
        this.ballRadius = 6;
        this.ballX = this.canvas.width / 2;
        this.ballY = this.canvas.height - 40;
        this.ballSpeedX = 3;
        this.ballSpeedY = -3;
        this.ballSpeed = 3;
        
        // Cegły
        this.brickRows = 7;  // Zwiększono z 5 do 7 rzędów (więcej na wyższej planszy)
        this.brickCols = 8;
        this.brickWidth = 0;
        this.brickHeight = 20;
        this.brickPadding = 4;
        this.brickOffsetTop = 40;
        this.brickOffsetLeft = 0;
        this.bricks = [];
        
        // Kolory cegieł (od najtrudniejszych do najłatwiejszych) - teraz 7 kolorów
        this.brickColors = [
            { color: '#FF0D72', points: 7 },  // Czerwony - 7 pkt
            { color: '#FF8E0D', points: 6 },  // Pomarańczowy - 6 pkt
            { color: '#FFE138', points: 5 },  // Żółty - 5 pkt
            { color: '#0DFF72', points: 4 },  // Zielony - 4 pkt
            { color: '#0DC2FF', points: 3 },  // Niebieski - 3 pkt
            { color: '#3877FF', points: 2 },  // Granatowy - 2 pkt
            { color: '#F538FF', points: 1 }   // Fioletowy - 1 pkt
        ];
        
        this.initBricks();
        this.setupControls();
        this.setupTouchControls();
    }
    
    calculateCanvasSize() {
        // Oblicz rozmiar canvas bazując na dostępnej przestrzeni
        const availableHeight = window.innerHeight * 0.84 - 4;
        const availableWidth = Math.min(window.innerHeight * 0.84 - 4, window.innerWidth - 142);
        
        // Ustaw wymiary canvas - proporcje ~3:5.5 (szerokość:wysokość) - wyższa plansza
        const targetRatio = 0.545; // 3/5.5 ≈ 0.545
        const maxWidth = Math.min(availableWidth, 350);
        const maxHeight = Math.min(availableHeight, 640);
        
        if (maxWidth / maxHeight < targetRatio) {
            this.canvas.width = maxWidth;
            this.canvas.height = maxWidth / targetRatio;
        } else {
            this.canvas.height = maxHeight;
            this.canvas.width = maxHeight * targetRatio;
        }
    }
    
    initBricks() {
        this.bricks = [];
        this.brickWidth = (this.canvas.width - (this.brickCols + 1) * this.brickPadding) / this.brickCols;
        this.brickOffsetLeft = this.brickPadding;
        
        for (let row = 0; row < this.brickRows; row++) {
            this.bricks[row] = [];
            for (let col = 0; col < this.brickCols; col++) {
                const colorData = this.brickColors[row % this.brickColors.length];
                this.bricks[row][col] = {
                    x: 0,
                    y: 0,
                    status: 1,
                    color: colorData.color,
                    points: colorData.points
                };
            }
        }
    }
    
    setupControls() {
        // Sterowanie klawiaturą (dla komputerów)
        document.addEventListener('keydown', (e) => {
            if (!this.gameRunning || this.gameOver) return;
            
            switch(e.key) {
                case 'ArrowLeft':
                    this.paddleMoving = -1;
                    e.preventDefault();
                    break;
                case 'ArrowRight':
                    this.paddleMoving = 1;
                    e.preventDefault();
                    break;
            }
        });
        
        document.addEventListener('keyup', (e) => {
            if (!this.gameRunning || this.gameOver) return;
            
            if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                this.paddleMoving = 0;
                e.preventDefault();
            }
        });
    }
    
    setupTouchControls() {
        // Przyciski dotykowe dla urządzeń mobilnych
        const leftBtn = document.getElementById('arkanoid-left-btn');
        const rightBtn = document.getElementById('arkanoid-right-btn');
        
        if (leftBtn) {
            // Touch events
            leftBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver) this.paddleMoving = -1;
            });
            leftBtn.addEventListener('touchend', (e) => {
                e.preventDefault();
                this.paddleMoving = 0;
            });
            leftBtn.addEventListener('touchcancel', (e) => {
                e.preventDefault();
                this.paddleMoving = 0;
            });
            
            // Mouse events (dla desktopów)
            leftBtn.addEventListener('mousedown', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver) this.paddleMoving = -1;
            });
            leftBtn.addEventListener('mouseup', (e) => {
                e.preventDefault();
                this.paddleMoving = 0;
            });
            leftBtn.addEventListener('mouseleave', (e) => {
                this.paddleMoving = 0;
            });
        }
        
        if (rightBtn) {
            // Touch events
            rightBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver) this.paddleMoving = 1;
            });
            rightBtn.addEventListener('touchend', (e) => {
                e.preventDefault();
                this.paddleMoving = 0;
            });
            rightBtn.addEventListener('touchcancel', (e) => {
                e.preventDefault();
                this.paddleMoving = 0;
            });
            
            // Mouse events (dla desktopów)
            rightBtn.addEventListener('mousedown', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver) this.paddleMoving = 1;
            });
            rightBtn.addEventListener('mouseup', (e) => {
                e.preventDefault();
                this.paddleMoving = 0;
            });
            rightBtn.addEventListener('mouseleave', (e) => {
                this.paddleMoving = 0;
            });
        }
    }
    
    start() {
        this.initBricks();
        this.lives = 3;
        this.gameOver = false;
        this.gameRunning = true;
        this.paddleX = (this.canvas.width - this.paddleWidth) / 2;
        this.resetBall();
        this.updateScore();
        this.updateLives();
        this.gameLoop();
    }
    
    resetBall() {
        this.ballX = this.canvas.width / 2;
        this.ballY = this.canvas.height - 40;
        this.ballSpeedX = (Math.random() > 0.5 ? 1 : -1) * this.ballSpeed;
        this.ballSpeedY = -this.ballSpeed;
    }
    
    gameLoop() {
        if (!this.gameRunning || this.gameOver) return;
        
        this.update();
        this.draw();
        requestAnimationFrame(() => this.gameLoop());
    }
    
    update() {
        // Ruch paletki
        if (this.paddleMoving !== 0) {
            this.paddleX += this.paddleMoving * this.paddleSpeed;
            
            // Granice paletki
            if (this.paddleX < 0) this.paddleX = 0;
            if (this.paddleX + this.paddleWidth > this.canvas.width) {
                this.paddleX = this.canvas.width - this.paddleWidth;
            }
        }
        
        // Ruch piłki
        this.ballX += this.ballSpeedX;
        this.ballY += this.ballSpeedY;
        
        // Odbicie od ścian
        if (this.ballX + this.ballRadius > this.canvas.width || this.ballX - this.ballRadius < 0) {
            this.ballSpeedX = -this.ballSpeedX;
        }
        
        if (this.ballY - this.ballRadius < 0) {
            this.ballSpeedY = -this.ballSpeedY;
        }
        
        // Odbicie od paletki
        if (this.ballY + this.ballRadius > this.canvas.height - this.paddleHeight) {
            if (this.ballX > this.paddleX && this.ballX < this.paddleX + this.paddleWidth) {
                // Oblicz kąt odbicia na podstawie miejsca uderzenia
                const hitPos = (this.ballX - this.paddleX) / this.paddleWidth;
                const angle = (hitPos - 0.5) * Math.PI * 0.6; // Max 54 stopni
                
                const speed = Math.sqrt(this.ballSpeedX * this.ballSpeedX + this.ballSpeedY * this.ballSpeedY);
                this.ballSpeedX = speed * Math.sin(angle);
                this.ballSpeedY = -speed * Math.cos(angle);
            }
        }
        
        // Piłka spadła poniżej paletki
        if (this.ballY - this.ballRadius > this.canvas.height) {
            this.lives--;
            this.updateLives();
            
            if (this.lives <= 0) {
                this.endGame();
            } else {
                this.resetBall();
            }
        }
        
        // Kolizje z cegłami
        for (let row = 0; row < this.brickRows; row++) {
            for (let col = 0; col < this.brickCols; col++) {
                const brick = this.bricks[row][col];
                if (brick.status === 0) continue;
                
                const brickX = this.brickOffsetLeft + col * (this.brickWidth + this.brickPadding);
                const brickY = this.brickOffsetTop + row * (this.brickHeight + this.brickPadding);
                
                brick.x = brickX;
                brick.y = brickY;
                
                // Prosta detekcja kolizji
                if (this.ballX > brickX && this.ballX < brickX + this.brickWidth &&
                    this.ballY > brickY && this.ballY < brickY + this.brickHeight) {
                    
                    this.ballSpeedY = -this.ballSpeedY;
                    brick.status = 0;
                    this.score += brick.points;
                    this.updateScore();
                    
                    // Sprawdź czy osiągnięto cel (20 punktów)
                    if (this.score >= 20) {
                        this.winGame();
                    }
                    
                    // Sprawdź czy wszystkie cegły zostały zniszczone
                    if (this.checkAllBricksDestroyed()) {
                        this.winGame();
                    }
                }
            }
        }
    }
    
    checkAllBricksDestroyed() {
        for (let row = 0; row < this.brickRows; row++) {
            for (let col = 0; col < this.brickCols; col++) {
                if (this.bricks[row][col].status === 1) {
                    return false;
                }
            }
        }
        return true;
    }
    
    draw() {
        // Wyczyść canvas
        this.ctx.fillStyle = '#1a1a2e';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Rysuj cegły
        for (let row = 0; row < this.brickRows; row++) {
            for (let col = 0; col < this.brickCols; col++) {
                const brick = this.bricks[row][col];
                if (brick.status === 0) continue;
                
                this.ctx.fillStyle = brick.color;
                this.ctx.fillRect(brick.x, brick.y, this.brickWidth, this.brickHeight);
                
                // Efekt 3D
                this.ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
                this.ctx.fillRect(brick.x, brick.y, this.brickWidth, 3);
            }
        }
        
        // Rysuj paletkę
        this.ctx.fillStyle = '#3877FF';
        this.ctx.fillRect(this.paddleX, this.canvas.height - this.paddleHeight, this.paddleWidth, this.paddleHeight);
        
        // Efekt 3D na paletce
        this.ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
        this.ctx.fillRect(this.paddleX, this.canvas.height - this.paddleHeight, this.paddleWidth, 3);
        
        // Rysuj piłkę
        this.ctx.beginPath();
        this.ctx.arc(this.ballX, this.ballY, this.ballRadius, 0, Math.PI * 2);
        this.ctx.fillStyle = '#FFE138';
        this.ctx.fill();
        this.ctx.closePath();
        
        // Dodaj połysk do piłki
        this.ctx.beginPath();
        this.ctx.arc(this.ballX - 2, this.ballY - 2, this.ballRadius / 2, 0, Math.PI * 2);
        this.ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
        this.ctx.fill();
        this.ctx.closePath();
    }
    
    updateScore() {
        const scoreEl = document.getElementById('arkanoid-score');
        if (scoreEl) {
            scoreEl.textContent = this.score;
        }
    }
    
    updateLives() {
        const livesEl = document.getElementById('arkanoid-lives');
        if (livesEl) {
            livesEl.textContent = '❤️'.repeat(this.lives);
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
                    game_type: 'arkanoid',
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
                    document.getElementById('arkanoid-game-view').style.display = 'none';
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
            document.getElementById('arkanoid-start-btn').style.display = 'inline-block';
            document.getElementById('arkanoid-start-btn').textContent = 'Spróbuj ponownie';
        }, 1000);
    }
}

// Eksportuj klasę (jeśli używasz modułów)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ArkanoidGame;
}
