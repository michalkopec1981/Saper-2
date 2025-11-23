    const eventId = {{ event_id }};
    let stream = null;
    let currentPlayerId = null;
    let currentPlayerName = null;

    // Check if player is already logged in
    window.addEventListener('DOMContentLoaded', function() {
        const storedPlayerId = localStorage.getItem(`saperPlayerId_${eventId}`);
        const storedPlayerName = localStorage.getItem(`saperPlayerName_${eventId}`);

        if (storedPlayerId && storedPlayerName) {
            // Player already logged in, go directly to camera
            currentPlayerId = storedPlayerId;
            currentPlayerName = storedPlayerName;
            showCamera();
        } else {
            // Show registration form
            document.getElementById('registration-card').classList.remove('hidden');
        }
    });

    // Handle registration
    document.getElementById('start-btn').addEventListener('click', async function() {
        const name = document.getElementById('player-name').value.trim();

        if (!name) {
            showError('Proszę podać imię');
            return;
        }

        // Register player
        try {
            const response = await fetch('/api/player/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name,
                    event_id: eventId
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Błąd rejestracji');
            }

            // Save player info
            currentPlayerId = data.id;
            currentPlayerName = name;
            localStorage.setItem(`saperPlayerId_${eventId}`, currentPlayerId);
            localStorage.setItem(`saperPlayerName_${eventId}`, name);

            // Show camera
            document.getElementById('registration-card').classList.add('hidden');
            showCamera();

        } catch (error) {
            showError(error.message);
        }
    });

    function showError(message) {
        const errorMsg = document.getElementById('error-msg');
        errorMsg.textContent = message;
        errorMsg.classList.remove('hidden');
        setTimeout(() => {
            errorMsg.classList.add('hidden');
        }, 3000);
    }

    async function showCamera() {
        document.getElementById('camera-card').classList.remove('hidden');

        // Start camera
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'user' },
                audio: false
            });
            document.getElementById('camera').srcObject = stream;
        } catch (error) {
            showError('Nie można uruchomić kamery: ' + error.message);
        }
    }

    // Capture photo
    document.getElementById('capture-btn').addEventListener('click', function() {
        console.log('📸 Capture button clicked');
        const video = document.getElementById('camera');
        const canvas = document.getElementById('canvas');
        const context = canvas.getContext('2d');

        // Set canvas dimensions to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        console.log('📐 Canvas dimensions:', { width: canvas.width, height: canvas.height });

        // Draw video frame to canvas
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Get image data
        const imageData = canvas.toDataURL('image/jpeg', 0.8);

        console.log('🖼️ Image captured, size:', imageData.length, 'bytes');

        // Show preview
        document.getElementById('preview-image').src = imageData;
        document.getElementById('camera').classList.add('hidden');
        document.getElementById('capture-btn').classList.add('hidden');
        document.getElementById('preview-container').classList.remove('hidden');

        console.log('👁️ Preview shown');
    });

    // Retake photo
    document.getElementById('retake-btn').addEventListener('click', function() {
        console.log('🔄 Retake button clicked');
        document.getElementById('preview-container').classList.add('hidden');
        document.getElementById('camera').classList.remove('hidden');
        document.getElementById('capture-btn').classList.remove('hidden');
    });

    // Upload photo
    document.getElementById('upload-btn').addEventListener('click', async function() {
        console.log('🚀 Upload button clicked');
        const canvas = document.getElementById('canvas');

        if (!currentPlayerId) {
            console.error('❌ No player ID');
            showError('Błąd: brak ID gracza');
            return;
        }

        console.log('📤 Starting upload...', {
            playerId: currentPlayerId,
            eventId: eventId,
            canvasWidth: canvas.width,
            canvasHeight: canvas.height
        });

        document.getElementById('preview-container').classList.add('hidden');
        document.getElementById('upload-loading').classList.remove('hidden');

        try {
            // Convert canvas to blob
            console.log('🎨 Converting canvas to blob...');
            const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8));

            if (!blob) {
                throw new Error('Nie udało się utworzyć zdjęcia');
            }

            console.log('✅ Blob created:', {
                size: blob.size,
                type: blob.type
            });

            // Create form data
            const formData = new FormData();
            formData.append('photo', blob, 'selfie.jpg');
            formData.append('player_id', currentPlayerId);
            formData.append('event_id', eventId);

            console.log('📦 FormData prepared, sending request...');

            // Upload photo
            const response = await fetch('/api/player/upload_photo', {
                method: 'POST',
                body: formData
            });

            console.log('📡 Response received:', {
                status: response.status,
                ok: response.ok
            });

            const data = await response.json();
            console.log('📄 Response data:', data);

            if (!response.ok) {
                throw new Error(data.error || 'Błąd uploadu');
            }

            // Stop camera
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
                console.log('📹 Camera stopped');
            }

            // Show success
            document.getElementById('camera-card').classList.add('hidden');
            document.getElementById('success-card').classList.remove('hidden');
            document.getElementById('points-message').textContent =
                `Zdobyłeś ${data.points} punktów!`;

            console.log('🎉 Upload successful!');

        } catch (error) {
            console.error('❌ Upload error:', error);
            document.getElementById('upload-loading').classList.add('hidden');
            document.getElementById('preview-container').classList.remove('hidden');
            showError('Błąd: ' + error.message);
        }
    });

    // View gallery button
    document.getElementById('view-gallery-btn').addEventListener('click', function() {
        console.log('📷 View gallery button clicked');
        document.getElementById('success-card').classList.add('hidden');
        document.getElementById('gallery-card').classList.remove('hidden');
        loadPlayerGallery();
    });

    // Load photo gallery for player
    let playerVotedPhotos = [];
    let maxLikes = 10;

    async function loadPlayerGallery() {
        console.log('📸 Loading player gallery...');
        try {
            // Get max likes setting
            const settingsResponse = await fetch(`/api/host/photo/settings/${eventId}`);
            if (settingsResponse.ok) {
                const settings = await settingsResponse.json();
                maxLikes = settings.max_likes || 10;
            }

            // Get photos
            const response = await fetch(`/api/photos/${eventId}`);
            const photos = await response.json();

            console.log(`📷 Loaded ${photos.length} photos`);

            const gallery = document.getElementById('player-photo-gallery');
            const noPhotosMsg = document.getElementById('no-player-photos-message');

            if (photos.length === 0) {
                gallery.innerHTML = '';
                noPhotosMsg.style.display = 'block';
                return;
            }

            noPhotosMsg.style.display = 'none';

            // Get player's votes
            const votesResponse = await fetch(`/api/player/${currentPlayerId}/votes`);
            if (votesResponse.ok) {
                playerVotedPhotos = await votesResponse.json();
            }

            const remainingLikes = maxLikes - playerVotedPhotos.length;
            document.getElementById('remaining-likes').textContent = remainingLikes;

            gallery.innerHTML = photos.map(photo => {
                const hasVoted = playerVotedPhotos.includes(photo.id);
                const isOwnPhoto = photo.player_name === currentPlayerName;
                const canVote = !isOwnPhoto && !hasVoted && remainingLikes > 0;

                return `
                    <div class="photo-item">
                        <img src="${photo.image_url}" alt="Photo by ${photo.player_name}">
                        <div class="photo-info">
                            <div class="photo-player-name">${photo.player_name}</div>
                            <button
                                class="like-btn ${hasVoted ? 'liked' : ''}"
                                onclick="handleLike(${photo.id}, this)"
                                ${!canVote ? 'disabled' : ''}
                            >
                                ${hasVoted ? '✓ Polubione' : '❤️ Polub'}
                            </button>
                            <div class="votes-count">❤️ ${photo.votes} polubień</div>
                            ${isOwnPhoto ? '<div class="text-muted mt-2"><small>Twoje zdjęcie</small></div>' : ''}
                        </div>
                    </div>
                `;
            }).join('');

            console.log('✅ Gallery loaded');

        } catch (error) {
            console.error('❌ Error loading gallery:', error);
            showError('Błąd ładowania galerii: ' + error.message);
        }
    }

    // Handle like/unlike
    window.handleLike = async function(photoId, button) {
        console.log(`❤️ Liking photo ${photoId}...`);

        try {
            const response = await fetch(`/api/photo/${photoId}/vote`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    player_id: currentPlayerId
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Błąd głosowania');
            }

            console.log('✅ Vote registered:', data);

            // Reload gallery to update votes
            await loadPlayerGallery();

        } catch (error) {
            console.error('❌ Like error:', error);
            showError('Błąd: ' + error.message);
        }
    };
