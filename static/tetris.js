class TetrisGame {
    constructor(canvasId, playerId, eventId, currentScore = 0) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.playerId = playerId;
        this.eventId = eventId;
        
        // Wymiary - dostosowane do ekranu mobilnego
        this.cols = 10;
        this.rows = 20;
        this.calculateCanvasSize();
        
        // Ustaw początkowy wynik z serwera
        this.score = currentScore;
        
        // Stan gry
        this.board = this.createEmptyBoard();
        this.gameOver = false;
        this.gameRunning = false;
        this.dropInterval = 1000; // ms
        this.lastDrop = 0;
        
        // Aktualny klocek
        this.currentPiece = null;
        this.currentX = 0;
        this.currentY = 0;
        
        // Kolory klocków
        this.colors = [
            null,
            '#FF0D72', // I
            '#0DC2FF', // J
            '#0DFF72', // L
            '#F538FF', // O
            '#FF8E0D', // S
            '#FFE138', // T
            '#3877FF'  // Z
        ];
        
        // Kształty klocków (tetromino)
        this.pieces = {
            'I': [[1,1,1,1]],
            'O': [[2,2],[2,2]],
            'T': [[0,3,0],[3,3,3]],
            'S': [[0,4,4],[4,4,0]],
            'Z': [[5,5,0],[0,5,5]],
            'J': [[6,0,0],[6,6,6]],
            'L': [[0,0,7],[7,7,7]]
        };
        
        this.setupControls();
        this.setupTouchControls();
    }
    
    calculateCanvasSize() {
        // Oblicz rozmiar canvas bazując na dostępnej przestrzeni
        // 65% wysokości viewportu minus nagłówek (około 120px)
        const availableHeight = window.innerHeight * 0.65 - 120;
        const availableWidth = Math.min(window.innerWidth - 40, 400);
        
        // Oblicz blockSize tak, aby plansza zmieściła się w dostępnej przestrzeni
        const blockSizeByHeight = Math.floor(availableHeight / this.rows);
        const blockSizeByWidth = Math.floor(availableWidth / this.cols);
        
        this.blockSize = Math.min(blockSizeByHeight, blockSizeByWidth, 30);
        
        // Ustaw wymiary canvas
        this.canvas.width = this.cols * this.blockSize;
        this.canvas.height = this.rows * this.blockSize;
    }
    
    createEmptyBoard() {
        return Array.from({ length: this.rows }, () => Array(this.cols).fill(0));
    }
    
    setupControls() {
        // Sterowanie klawiaturą (dla komputerów)
        document.addEventListener('keydown', (e) => {
            if (!this.gameRunning || this.gameOver) return;
            
            switch(e.key) {
                case 'ArrowLeft':
                    this.movePiece(-1, 0);
                    e.preventDefault();
                    break;
                case 'ArrowRight':
                    this.movePiece(1, 0);
                    e.preventDefault();
                    break;
                case 'ArrowDown':
                    this.movePiece(0, 1);
                    e.preventDefault();
                    break;
                case ' ':
                    this.rotatePiece();
                    e.preventDefault();
                    break;
            }
        });
    }
    
    setupTouchControls() {
        // Przyciski dotykowe dla urządzeń mobilnych
        const leftBtn = document.getElementById('tetris-left-btn');
        const rightBtn = document.getElementById('tetris-right-btn');
        const rotateBtn = document.getElementById('tetris-rotate-btn');
        const downBtn = document.getElementById('tetris-down-btn');
        
        if (leftBtn) {
            leftBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver) this.movePiece(-1, 0);
            });
            leftBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver) this.movePiece(-1, 0);
            });
        }
        
        if (rightBtn) {
            rightBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver) this.movePiece(1, 0);
            });
            rightBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver) this.movePiece(1, 0);
            });
        }
        
        if (rotateBtn) {
            rotateBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver) this.rotatePiece();
            });
            rotateBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver) this.rotatePiece();
            });
        }
        
        if (downBtn) {
            downBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver) this.movePiece(0, 1);
            });
            downBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (this.gameRunning && !this.gameOver) this.movePiece(0, 1);
            });
        }
    }
    
    start() {
        this.board = this.createEmptyBoard();
        // Nie resetujemy score - kontynuujemy od obecnego wyniku
        this.gameOver = false;
        this.gameRunning = true;
        this.spawnPiece();
        this.updateScore();
        this.gameLoop();
    }
    
    gameLoop(timestamp = 0) {
        if (!this.gameRunning || this.gameOver) return;
        
        // Auto-drop co dropInterval ms
        if (timestamp - this.lastDrop > this.dropInterval) {
            this.movePiece(0, 1);
            this.lastDrop = timestamp;
        }
        
        this.draw();
        requestAnimationFrame((ts) => this.gameLoop(ts));
    }
    
    spawnPiece() {
        const pieceTypes = Object.keys(this.pieces);
        const randomType = pieceTypes[Math.floor(Math.random() * pieceTypes.length)];
        this.currentPiece = this.pieces[randomType];
        this.currentX = Math.floor(this.cols / 2) - Math.floor(this.currentPiece[0].length / 2);
        this.currentY = 0;
        
        if (this.checkCollision(this.currentPiece, this.currentX, this.currentY)) {
            this.endGame();
        }
    }
    
    movePiece(dx, dy) {
        const newX = this.currentX + dx;
        const newY = this.currentY + dy;
        
        if (!this.checkCollision(this.currentPiece, newX, newY)) {
            this.currentX = newX;
            this.currentY = newY;
        } else if (dy > 0) {
            // Klocek "wylądował"
            this.mergePiece();
            this.clearLines();
            this.spawnPiece();
        }
    }
    
    rotatePiece() {
        const rotated = this.currentPiece[0].map((_, i) =>
            this.currentPiece.map(row => row[i]).reverse()
        );
        
        if (!this.checkCollision(rotated, this.currentX, this.currentY)) {
            this.currentPiece = rotated;
        }
    }
    
    checkCollision(piece, offsetX, offsetY) {
        for (let y = 0; y < piece.length; y++) {
            for (let x = 0; x < piece[y].length; x++) {
                if (piece[y][x] !== 0) {
                    const newX = offsetX + x;
                    const newY = offsetY + y;
                    
                    // Sprawdź granice
                    if (newX < 0 || newX >= this.cols || newY >= this.rows) {
                        return true;
                    }
                    
                    // Sprawdź kolizję z planszą
                    if (newY >= 0 && this.board[newY][newX] !== 0) {
                        return true;
                    }
                }
            }
        }
        return false;
    }
    
    mergePiece() {
        for (let y = 0; y < this.currentPiece.length; y++) {
            for (let x = 0; x < this.currentPiece[y].length; x++) {
                if (this.currentPiece[y][x] !== 0) {
                    const boardY = this.currentY + y;
                    const boardX = this.currentX + x;
                    if (boardY >= 0) {
                        this.board[boardY][boardX] = this.currentPiece[y][x];
                    }
                }
            }
        }
    }
    
    clearLines() {
        let linesCleared = 0;
        
        for (let y = this.rows - 1; y >= 0; y--) {
            if (this.board[y].every(cell => cell !== 0)) {
                this.board.splice(y, 1);
                this.board.unshift(Array(this.cols).fill(0));
                linesCleared++;
                y++; // Sprawdź tę samą linię ponownie
            }
        }
        
        if (linesCleared > 0) {
            // Punktacja: 1 linia = 1 pkt, 2 linie = 3 pkt, 3 linie = 6 pkt, 4 linie = 10 pkt
            const points = [0, 1, 3, 6, 10][linesCleared] || linesCleared;
            this.score += points;
            this.updateScore();
            
            // Sprawdź czy osiągnięto cel (20 punktów)
            if (this.score >= 20) {
                this.winGame();
            }
        }
    }
    
    updateScore() {
        const scoreEl = document.getElementById('tetris-score');
        if (scoreEl) {
            scoreEl.textContent = this.score;
        }
    }
    
    draw() {
        // Wyczyść canvas
        this.ctx.fillStyle = '#000';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Rysuj planszę
        for (let y = 0; y < this.rows; y++) {
            for (let x = 0; x < this.cols; x++) {
                if (this.board[y][x] !== 0) {
                    this.drawBlock(x, y, this.colors[this.board[y][x]]);
                }
            }
        }
        
        // Rysuj aktualny klocek
        if (this.currentPiece) {
            for (let y = 0; y < this.currentPiece.length; y++) {
                for (let x = 0; x < this.currentPiece[y].length; x++) {
                    if (this.currentPiece[y][x] !== 0) {
                        this.drawBlock(
                            this.currentX + x,
                            this.currentY + y,
                            this.colors[this.currentPiece[y][x]]
                        );
                    }
                }
            }
        }
        
        // Rysuj siatkę
        this.ctx.strokeStyle = '#222';
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
    }
    
    drawBlock(x, y, color) {
        this.ctx.fillStyle = color;
        this.ctx.fillRect(
            x * this.blockSize + 1,
            y * this.blockSize + 1,
            this.blockSize - 2,
            this.blockSize - 2
        );
        
        // Dodaj efekt 3D
        this.ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        this.ctx.fillRect(
            x * this.blockSize + 1,
            y * this.blockSize + 1,
            this.blockSize - 2,
            3
        );
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
                    game_type: 'tetris',
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
                    document.getElementById('tetris-game-view').style.display = 'none';
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
            document.getElementById('tetris-start-btn').style.display = 'inline-block';
            document.getElementById('tetris-start-btn').textContent = 'Spróbuj ponownie';
        }, 1000);
    }
}

// Eksportuj klasę (jeśli używasz modułów)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TetrisGame;
}
