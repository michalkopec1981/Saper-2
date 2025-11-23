/**
 * Socket.IO Manager
 * Centralized Socket.IO connection management
 */

const SocketManager = {
    socket: null,
    eventId: null,
    
    init(eventId, options = {}) {
        this.eventId = eventId;
        
        // Connect to Socket.IO server
        this.socket = io.connect(window.location.origin, {
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: 5,
            ...options
        });

        this.setupDefaultHandlers();
        return this.socket;
    },

    setupDefaultHandlers() {
        this.socket.on('connect', () => {
            console.log('✅ Socket.IO connected');
            this.joinRoom();
        });

        this.socket.on('disconnect', () => {
            console.log('❌ Socket.IO disconnected');
        });

        this.socket.on('connect_error', (error) => {
            console.error('Socket.IO connection error:', error);
        });

        this.socket.on('reconnect', (attemptNumber) => {
            console.log(`🔄 Socket.IO reconnected after ${attemptNumber} attempts`);
            this.joinRoom();
        });
    },

    joinRoom() {
        if (this.eventId) {
            const room = `event_${this.eventId}`;
            this.socket.emit('join', { room });
            console.log(`📍 Joined room: ${room}`);
        }
    },

    emit(event, data) {
        if (this.socket) {
            this.socket.emit(event, data);
        } else {
            console.error('Socket not initialized. Call SocketManager.init() first.');
        }
    },

    on(event, callback) {
        if (this.socket) {
            this.socket.on(event, callback);
        } else {
            console.error('Socket not initialized. Call SocketManager.init() first.');
        }
    },

    off(event, callback) {
        if (this.socket) {
            this.socket.off(event, callback);
        }
    },

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
    }
};

// Export for use in other modules
window.SocketManager = SocketManager;
