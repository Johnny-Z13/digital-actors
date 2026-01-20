import { CharacterScene } from './scene.js';
import { SubmarineScene } from './submarine_scene.js';

class ChatApp {
    constructor() {
        this.ws = null;
        this.scene = null;
        this.sceneType = 'character'; // 'character' or 'submarine'
        this.currentCharacter = 'eliza';
        this.currentScene = 'introduction';
        this.isConnected = false;

        // Message queue for delivering one message at a time
        this.messageQueue = [];
        this.isProcessingQueue = false;
        this.currentTypingMessage = null;

        // Waiting indicator state
        this.waitingDots = 0;
        this.waitingInterval = null;
        this.maxWaitingDots = 5;

        // Audio playback for TTS
        this.audioEnabled = true;
        this.audioQueue = [];
        this.currentAudio = null;
        this.audioVolume = 0.8;

        // Dialogue lock - ensures only one dialogue at a time
        this.dialogueLocked = false;
        this.pendingResponses = [];

        this.init();
    }

    init() {
        // Initialize Three.js scene
        const sceneContainer = document.getElementById('scene-container');
        this.createScene(sceneContainer, this.currentScene);

        // Setup event listeners
        this.setupEventListeners();

        // Connect to WebSocket
        this.connectWebSocket();

        // Hide loading screen after scene loads
        setTimeout(() => {
            document.getElementById('loading-screen').classList.add('hidden');
        }, 1000);
    }

    createScene(container, sceneId) {
        // Clear existing scene
        if (this.scene && this.scene.renderer) {
            container.removeChild(this.scene.renderer.domElement);
        }

        // Create appropriate scene based on scene ID
        if (sceneId === 'submarine') {
            this.sceneType = 'submarine';
            this.scene = new SubmarineScene(container, (action) => this.handleButtonClick(action));
        } else {
            this.sceneType = 'character';
            this.scene = new CharacterScene(container);
        }
    }

    handleButtonClick(action) {
        // Handle submarine button clicks
        console.log('Button clicked:', action);
        // Don't add system message - let the NPC respond instead
        // This prevents overlapping messages

        // Send button action to server
        if (this.isConnected) {
            this.ws.send(JSON.stringify({
                type: 'button_action',
                action: action
            }));
        }
    }

    setupEventListeners() {
        // Send button
        const sendButton = document.getElementById('send-button');
        sendButton.addEventListener('click', () => this.sendMessage());

        // Enter key in input
        const chatInput = document.getElementById('chat-input');
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Config toggle
        const configToggle = document.getElementById('config-toggle');
        const configPanel = document.getElementById('config-panel');
        configToggle.addEventListener('click', () => {
            configPanel.classList.toggle('collapsed');
        });

        // Setup chat window drag and resize
        this.setupChatDragResize();

        // Character selection
        const characterSelect = document.getElementById('character-select');
        characterSelect.addEventListener('change', (e) => {
            this.changeCharacter(e.target.value);
        });

        // Scene selection
        const sceneSelect = document.getElementById('scene-select');
        sceneSelect.addEventListener('change', (e) => {
            const newScene = e.target.value;
            if (newScene !== this.currentScene) {
                this.currentScene = newScene;

                // Recreate the 3D scene if switching to/from submarine
                const needsSceneRecreate = (newScene === 'submarine' || this.currentScene === 'submarine');
                if (needsSceneRecreate) {
                    const sceneContainer = document.getElementById('scene-container');
                    this.createScene(sceneContainer, newScene);
                }
            }
        });

        // Restart button
        const restartButton = document.getElementById('restart-button');
        restartButton.addEventListener('click', () => this.restartConversation());
    }

    setupChatDragResize() {
        const chatContainer = document.getElementById('chat-container');
        const dragHandle = document.getElementById('chat-header');
        const resizeHandle = document.getElementById('chat-resize-handle');
        const minimizeBtn = document.getElementById('chat-minimize');

        // Dragging state
        let isDragging = false;
        let dragStartX, dragStartY;
        let initialLeft, initialTop;

        // Convert from bottom/right positioning to top/left on first drag
        const convertToTopLeft = () => {
            if (chatContainer.style.top === '') {
                const rect = chatContainer.getBoundingClientRect();
                chatContainer.style.top = rect.top + 'px';
                chatContainer.style.left = rect.left + 'px';
                chatContainer.style.bottom = 'auto';
                chatContainer.style.right = 'auto';
            }
        };

        // Drag start
        dragHandle.addEventListener('mousedown', (e) => {
            if (e.target === minimizeBtn) return; // Don't drag when clicking minimize
            isDragging = true;
            convertToTopLeft();
            dragStartX = e.clientX;
            dragStartY = e.clientY;
            initialLeft = chatContainer.offsetLeft;
            initialTop = chatContainer.offsetTop;
            chatContainer.style.transition = 'none';
            e.preventDefault();
        });

        // Drag move
        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const dx = e.clientX - dragStartX;
            const dy = e.clientY - dragStartY;
            let newLeft = initialLeft + dx;
            let newTop = initialTop + dy;

            // Constrain to viewport
            newLeft = Math.max(0, Math.min(newLeft, window.innerWidth - chatContainer.offsetWidth));
            newTop = Math.max(0, Math.min(newTop, window.innerHeight - chatContainer.offsetHeight));

            chatContainer.style.left = newLeft + 'px';
            chatContainer.style.top = newTop + 'px';
        });

        // Drag end
        document.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                chatContainer.style.transition = '';
            }
        });

        // Resizing state
        let isResizing = false;
        let resizeStartX, resizeStartY;
        let initialWidth, initialHeight;

        // Resize start
        resizeHandle.addEventListener('mousedown', (e) => {
            isResizing = true;
            convertToTopLeft();
            resizeStartX = e.clientX;
            resizeStartY = e.clientY;
            initialWidth = chatContainer.offsetWidth;
            initialHeight = chatContainer.offsetHeight;
            initialLeft = chatContainer.offsetLeft;
            initialTop = chatContainer.offsetTop;
            chatContainer.style.transition = 'none';
            e.preventDefault();
        });

        // Resize move (bottom-left corner resize)
        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            const dx = resizeStartX - e.clientX; // Inverted for left-side resize
            const dy = e.clientY - resizeStartY;

            let newWidth = Math.max(280, initialWidth + dx);
            let newHeight = Math.max(200, initialHeight + dy);

            // Constrain to viewport
            newWidth = Math.min(newWidth, initialLeft + initialWidth);
            newHeight = Math.min(newHeight, window.innerHeight - initialTop);

            // Adjust left position as width changes (resize from left)
            const newLeft = initialLeft + initialWidth - newWidth;

            chatContainer.style.width = newWidth + 'px';
            chatContainer.style.height = newHeight + 'px';
            chatContainer.style.left = newLeft + 'px';
        });

        // Resize end
        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                chatContainer.style.transition = '';
            }
        });

        // Minimize/restore toggle
        minimizeBtn.addEventListener('click', () => {
            chatContainer.classList.toggle('minimized');
            minimizeBtn.textContent = chatContainer.classList.contains('minimized') ? '+' : '−';
        });
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.addSystemMessage('Connecting to server...');

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            this.isConnected = true;
            this.updateConnectionStatus(true);
            this.addSystemMessage('Connected! Say hello to start the conversation.');

            // Send initial configuration
            this.sendConfig();
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleServerMessage(data);
            } catch (error) {
                console.error('Error parsing server message:', error);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.addSystemMessage('Connection error. Please refresh the page.');
        };

        this.ws.onclose = () => {
            this.isConnected = false;
            this.updateConnectionStatus(false);
            this.addSystemMessage('Disconnected from server.');

            // Attempt to reconnect after 3 seconds
            setTimeout(() => {
                if (!this.isConnected) {
                    this.addSystemMessage('Attempting to reconnect...');
                    this.connectWebSocket();
                }
            }, 3000);
        };
    }

    sendConfig() {
        if (!this.isConnected) return;

        this.ws.send(JSON.stringify({
            type: 'config',
            character: this.currentCharacter,
            scene: this.currentScene
        }));
    }

    sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();

        if (!message || !this.isConnected) return;

        // Add user message to chat
        this.addMessage('You', message, 'user');

        // Send to server
        this.ws.send(JSON.stringify({
            type: 'message',
            content: message
        }));

        // Clear input
        input.value = '';

        // Show typing indicator
        this.showTypingIndicator();
    }

    handleServerMessage(data) {
        switch (data.type) {
            case 'character_response':
                this.hideTypingIndicator();
                // Queue the response to ensure one at a time
                this.queueCharacterResponse(data);
                break;

            case 'scene_change':
                this.currentScene = data.scene;
                document.getElementById('current-scene').textContent = data.scene_name || data.scene;
                this.addSystemMessage(`Scene changed: ${data.scene_name || data.scene}`);
                break;

            case 'state_change':
                console.log('State changed:', data.changes);
                break;

            case 'state_update':
                // Server-side state update (e.g., oxygen countdown)
                if (data.state && this.sceneType === 'submarine' && this.scene) {
                    // Sync oxygen level with server
                    if (data.state.oxygen !== undefined) {
                        this.scene.setOxygenLevel(data.state.oxygen);
                    }
                }
                break;

            case 'error':
                this.hideTypingIndicator();
                this.addSystemMessage(`Error: ${data.message}`);
                break;

            case 'opening_speech':
                // Character's opening lines - queue them to display one at a time
                this.queueOpeningLines(data.lines, data.character_name || 'Character');
                break;

            case 'game_over':
                // Game over screen
                this.showGameOverScreen(data.outcome);
                break;

            case 'system_event':
                // World Director spawned an event
                this.addSystemMessage(data.content);
                break;

            default:
                console.log('Unknown message type:', data.type);
        }
    }

    showGameOverScreen(outcome) {
        // Add CSS animations if not already present
        if (!document.getElementById('game-over-styles')) {
            const style = document.createElement('style');
            style.id = 'game-over-styles';
            style.textContent = `
                @keyframes gameOverFadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes gameOverTitleReveal {
                    0% { opacity: 0; transform: scale(0.8); letter-spacing: 0.5em; }
                    100% { opacity: 1; transform: scale(1); letter-spacing: 0.3em; }
                }
                @keyframes gameOverTextReveal {
                    0% { opacity: 0; transform: translateY(30px); }
                    100% { opacity: 1; transform: translateY(0); }
                }
                @keyframes gameOverButtonReveal {
                    0% { opacity: 0; }
                    100% { opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }

        // Create game over overlay
        const overlay = document.createElement('div');
        overlay.id = 'game-over-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(180deg, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.98) 100%);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 10000;
            animation: gameOverFadeIn 1s ease-out;
        `;

        // Container for centered content
        const container = document.createElement('div');
        container.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            max-width: 800px;
            padding: 2rem;
        `;

        // Title - "THE END"
        const title = document.createElement('div');
        const isSuccess = outcome.type === 'success';
        title.style.cssText = `
            font-size: 5rem;
            font-weight: 300;
            margin-bottom: 3rem;
            color: ${isSuccess ? '#4ade80' : '#ef4444'};
            text-transform: uppercase;
            letter-spacing: 0.3em;
            text-shadow: 0 0 40px ${isSuccess ? 'rgba(74, 222, 128, 0.5)' : 'rgba(239, 68, 68, 0.5)'};
            animation: gameOverTitleReveal 1.5s ease-out;
            font-family: 'Georgia', 'Times New Roman', serif;
        `;
        title.textContent = 'The End';

        // Character's final message (the dramatic line)
        const finalMessage = document.createElement('div');
        finalMessage.style.cssText = `
            font-size: 1.4rem;
            max-width: 700px;
            text-align: center;
            line-height: 2;
            color: #ffffff;
            padding: 0 2rem;
            margin-bottom: 2rem;
            font-style: italic;
            animation: gameOverTextReveal 1s ease-out 0.5s both;
            font-family: 'Georgia', 'Times New Roman', serif;
        `;
        finalMessage.textContent = `"${outcome.message}"`;

        // Summary description
        const description = document.createElement('div');
        description.style.cssText = `
            font-size: 1.1rem;
            max-width: 600px;
            text-align: center;
            line-height: 1.8;
            color: #a0a0a0;
            padding: 1.5rem 2rem;
            margin-bottom: 3rem;
            border-top: 1px solid rgba(255,255,255,0.1);
            border-bottom: 1px solid rgba(255,255,255,0.1);
            animation: gameOverTextReveal 1s ease-out 1s both;
        `;
        description.textContent = outcome.description || (isSuccess ? 'You survived.' : 'You did not survive.');

        // Restart button
        const restartButton = document.createElement('button');
        restartButton.textContent = isSuccess ? 'Play Again' : 'Try Again';
        restartButton.style.cssText = `
            padding: 1rem 3rem;
            font-size: 1.1rem;
            background: transparent;
            color: ${isSuccess ? '#4ade80' : '#ef4444'};
            border: 2px solid ${isSuccess ? '#4ade80' : '#ef4444'};
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            animation: gameOverButtonReveal 1s ease-out 1.5s both;
        `;
        restartButton.onmouseover = () => {
            restartButton.style.background = isSuccess ? '#4ade80' : '#ef4444';
            restartButton.style.color = '#000';
            restartButton.style.transform = 'scale(1.05)';
        };
        restartButton.onmouseout = () => {
            restartButton.style.background = 'transparent';
            restartButton.style.color = isSuccess ? '#4ade80' : '#ef4444';
            restartButton.style.transform = 'scale(1)';
        };
        restartButton.onclick = () => {
            overlay.style.animation = 'gameOverFadeIn 0.5s ease-out reverse';
            setTimeout(() => {
                document.body.removeChild(overlay);
                this.restart();
            }, 400);
        };

        container.appendChild(title);
        container.appendChild(finalMessage);
        container.appendChild(description);
        container.appendChild(restartButton);
        overlay.appendChild(container);
        document.body.appendChild(overlay);
    }

    restart() {
        // Stop any playing audio
        this.stopAudio();

        // Send restart message to server
        if (this.isConnected) {
            this.ws.send(JSON.stringify({
                type: 'restart',
                character: this.currentCharacter,
                scene: this.currentScene
            }));
        }

        // Clear chat messages
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = '';
    }

    // ==================== Character Response Queue ====================

    /**
     * Queue a character response to ensure only one plays at a time
     */
    queueCharacterResponse(data) {
        this.pendingResponses.push(data);
        console.log('[Queue] Added response, queue length:', this.pendingResponses.length, 'locked:', this.dialogueLocked);
        this.processNextResponse();
    }

    /**
     * Process the next queued response if not locked
     */
    processNextResponse() {
        if (this.dialogueLocked || this.pendingResponses.length === 0) {
            return;
        }

        this.dialogueLocked = true;
        const data = this.pendingResponses.shift();
        console.log('[Queue] Processing response, remaining:', this.pendingResponses.length);

        const characterName = data.character_name || 'Character';
        const content = data.content;

        // Add the message with typing effect
        this.addCharacterMessageWithAudio(characterName, content, data.audio, data.audio_format || 'mp3');
    }

    /**
     * Add a character message with synchronized audio
     * Waits for both typing and audio to complete before unlocking
     */
    addCharacterMessageWithAudio(sender, content, audioBase64, audioFormat) {
        const messagesContainer = document.getElementById('chat-messages');

        // Stop any waiting indicator
        this.stopWaitingIndicator();

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message character';

        const senderDiv = document.createElement('div');
        senderDiv.className = 'message-sender';
        senderDiv.textContent = sender;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        messageDiv.appendChild(senderDiv);
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Track completion of both typing and audio
        let typingDone = false;
        let audioDone = !audioBase64 || !this.audioEnabled; // If no audio, mark as done

        const checkComplete = () => {
            if (typingDone && audioDone) {
                console.log('[Queue] Response complete, unlocking');
                this.dialogueLocked = false;
                // Process next response after a small delay
                setTimeout(() => this.processNextResponse(), 100);
            }
        };

        // Start typing
        this.typeMessage(contentDiv, content, 30, () => {
            typingDone = true;
            checkComplete();
        });

        // Start audio if available
        if (audioBase64 && this.audioEnabled) {
            console.log('[TTS] Playing audio for response');
            this.playAudioWithCallback(audioBase64, audioFormat, () => {
                audioDone = true;
                checkComplete();
            });
        }
    }

    // ==================== Audio Playback (TTS) ====================

    /**
     * Play audio from base64-encoded data
     * @param {string} audioBase64 - Base64 encoded audio data
     * @param {string} format - Audio format (default: 'mp3')
     */
    playAudio(audioBase64, format = 'mp3') {
        console.log('[TTS] playAudio called, enabled:', this.audioEnabled, 'data length:', audioBase64?.length);

        if (!this.audioEnabled || !audioBase64) {
            console.log('[TTS] Skipping - disabled or no data');
            return;
        }

        try {
            // Stop any currently playing audio
            this.stopAudio();

            // Create audio from base64
            const audioBlob = this.base64ToBlob(audioBase64, `audio/${format}`);
            const audioUrl = URL.createObjectURL(audioBlob);
            console.log('[TTS] Created audio blob, size:', audioBlob.size, 'URL:', audioUrl);

            this.currentAudio = new Audio(audioUrl);
            this.currentAudio.volume = this.audioVolume;

            // Clean up object URL when done
            this.currentAudio.onended = () => {
                console.log('[TTS] Audio playback ended');
                URL.revokeObjectURL(audioUrl);
                this.currentAudio = null;
            };

            this.currentAudio.onerror = (e) => {
                console.error('[TTS] Audio playback error:', e, this.currentAudio?.error);
                URL.revokeObjectURL(audioUrl);
                this.currentAudio = null;
            };

            // Play the audio
            console.log('[TTS] Attempting to play...');
            this.currentAudio.play().then(() => {
                console.log('[TTS] Playback started successfully!');
            }).catch(e => {
                console.warn('[TTS] Audio autoplay blocked:', e);
                // Autoplay was blocked - this is common on first interaction
                // The audio will play once user interacts with the page
            });

        } catch (error) {
            console.error('[TTS] Error playing audio:', error);
        }
    }

    /**
     * Stop currently playing audio
     */
    stopAudio() {
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio.currentTime = 0;
            this.currentAudio = null;
        }
        this.audioCallback = null;
    }

    /**
     * Play audio with a callback when finished
     * @param {string} audioBase64 - Base64 encoded audio data
     * @param {string} format - Audio format (default: 'mp3')
     * @param {function} onComplete - Callback when audio finishes
     */
    playAudioWithCallback(audioBase64, format = 'mp3', onComplete = null) {
        console.log('[TTS] playAudioWithCallback called');

        if (!this.audioEnabled || !audioBase64) {
            if (onComplete) onComplete();
            return;
        }

        try {
            // Stop any currently playing audio
            this.stopAudio();

            // Store callback
            this.audioCallback = onComplete;

            // Create audio from base64
            const audioBlob = this.base64ToBlob(audioBase64, `audio/${format}`);
            const audioUrl = URL.createObjectURL(audioBlob);

            this.currentAudio = new Audio(audioUrl);
            this.currentAudio.volume = this.audioVolume;

            // Clean up and call callback when done
            this.currentAudio.onended = () => {
                console.log('[TTS] Audio playback ended');
                URL.revokeObjectURL(audioUrl);
                this.currentAudio = null;
                if (this.audioCallback) {
                    const cb = this.audioCallback;
                    this.audioCallback = null;
                    cb();
                }
            };

            this.currentAudio.onerror = (e) => {
                console.error('[TTS] Audio playback error:', e);
                URL.revokeObjectURL(audioUrl);
                this.currentAudio = null;
                if (this.audioCallback) {
                    const cb = this.audioCallback;
                    this.audioCallback = null;
                    cb();
                }
            };

            // Play the audio
            this.currentAudio.play().then(() => {
                console.log('[TTS] Playback started');
            }).catch(e => {
                console.warn('[TTS] Audio autoplay blocked:', e);
                // If autoplay blocked, call callback so queue continues
                if (this.audioCallback) {
                    const cb = this.audioCallback;
                    this.audioCallback = null;
                    cb();
                }
            });

        } catch (error) {
            console.error('[TTS] Error playing audio:', error);
            if (onComplete) onComplete();
        }
    }

    /**
     * Convert base64 string to Blob
     * @param {string} base64 - Base64 encoded data
     * @param {string} mimeType - MIME type of the data
     * @returns {Blob}
     */
    base64ToBlob(base64, mimeType) {
        const byteCharacters = atob(base64);
        const byteNumbers = new Array(byteCharacters.length);

        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }

        const byteArray = new Uint8Array(byteNumbers);
        return new Blob([byteArray], { type: mimeType });
    }

    /**
     * Set audio volume (0.0 to 1.0)
     * @param {number} volume
     */
    setAudioVolume(volume) {
        this.audioVolume = Math.max(0, Math.min(1, volume));
        if (this.currentAudio) {
            this.currentAudio.volume = this.audioVolume;
        }
    }

    /**
     * Toggle audio on/off
     */
    toggleAudio() {
        this.audioEnabled = !this.audioEnabled;
        if (!this.audioEnabled) {
            this.stopAudio();
        }
        console.log('Audio', this.audioEnabled ? 'enabled' : 'disabled');
        return this.audioEnabled;
    }

    // ==================== End Audio Playback ====================

    addMessage(sender, content, type, useTypingEffect = true) {
        const messagesContainer = document.getElementById('chat-messages');

        // Stop any waiting indicator when a message arrives
        this.stopWaitingIndicator();

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        const senderDiv = document.createElement('div');
        senderDiv.className = 'message-sender';
        senderDiv.textContent = sender;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        messageDiv.appendChild(senderDiv);
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Apply typing effect for character messages
        if (type === 'character' && useTypingEffect) {
            this.typeMessage(contentDiv, content, 30, null);
        } else {
            // Parse voice annotations for non-typing messages too
            contentDiv.innerHTML = this.parseVoiceAnnotations(content);
        }
    }

    typeMessage(element, text, speed = 30, onComplete = null) {
        let index = 0;
        element.innerHTML = '';

        const messagesContainer = document.getElementById('chat-messages');
        let lastScrollTime = 0;

        // Parse text for voice annotations like [static], [voice cracks], etc.
        const parsedHTML = this.parseVoiceAnnotations(text);

        // For typing effect, we need to handle HTML content
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = parsedHTML;
        const plainText = tempDiv.textContent;

        // Store the final HTML to set when complete
        const finalHTML = parsedHTML;

        const typeInterval = setInterval(() => {
            if (index < plainText.length) {
                // Batch multiple characters for better performance
                const charsToAdd = Math.min(2, plainText.length - index);
                // During typing, show plain text (annotations will be styled at end)
                element.textContent = plainText.substring(0, index + charsToAdd);
                index += charsToAdd;

                // Throttle scroll updates to every 60ms (max ~16 times per second)
                const now = Date.now();
                if (now - lastScrollTime > 60) {
                    requestAnimationFrame(() => {
                        messagesContainer.scrollTop = messagesContainer.scrollHeight;
                    });
                    lastScrollTime = now;
                }
            } else {
                clearInterval(typeInterval);
                // Apply final styled HTML with annotations
                element.innerHTML = finalHTML;
                // Final scroll to ensure we're at bottom
                requestAnimationFrame(() => {
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                });
                // Callback when typing is complete
                if (onComplete) {
                    onComplete();
                }
            }
        }, speed);

        return typeInterval;
    }

    /**
     * Parse voice annotations like [static], [voice cracks], [breathing heavily]
     * and wrap them in styled spans for visual distinction.
     * Also adds data attributes for ElevenLabs TTS integration.
     */
    parseVoiceAnnotations(text) {
        // Match annotations in square brackets like [static], [voice cracks], etc.
        const annotationRegex = /\[([^\]]+)\]/g;

        return text.replace(annotationRegex, (match, content) => {
            // Map common annotations to ElevenLabs/SSML effects
            const lowerContent = content.toLowerCase();
            let elevenLabsEffect = 'none';

            if (lowerContent.includes('static') || lowerContent.includes('crackle')) {
                elevenLabsEffect = 'radio_static';
            } else if (lowerContent.includes('breathing') || lowerContent.includes('breath')) {
                elevenLabsEffect = 'breathing';
            } else if (lowerContent.includes('voice') && (lowerContent.includes('crack') || lowerContent.includes('break'))) {
                elevenLabsEffect = 'voice_crack';
            } else if (lowerContent.includes('whisper')) {
                elevenLabsEffect = 'whisper';
            } else if (lowerContent.includes('shout') || lowerContent.includes('yell')) {
                elevenLabsEffect = 'shout';
            } else if (lowerContent.includes('panic') || lowerContent.includes('fear')) {
                elevenLabsEffect = 'panic';
            } else if (lowerContent.includes('sigh')) {
                elevenLabsEffect = 'sigh';
            } else if (lowerContent.includes('pause') || lowerContent.includes('silence')) {
                elevenLabsEffect = 'pause';
            } else if (lowerContent.includes('alarm') || lowerContent.includes('warning')) {
                elevenLabsEffect = 'sfx_alarm';
            } else if (lowerContent.includes('signal') || lowerContent.includes('lost')) {
                elevenLabsEffect = 'signal_lost';
            }

            // Return styled span with ElevenLabs data attribute
            return `<span class="voice-annotation" data-elevenlabs-effect="${elevenLabsEffect}">${match}</span>`;
        });
    }

    /**
     * Queue opening lines to display one at a time
     */
    queueOpeningLines(lines, characterName) {
        // Add all lines to the queue (including audio if available)
        lines.forEach((line, index) => {
            this.messageQueue.push({
                sender: characterName,
                content: line.text,
                type: 'character',
                delay: index === 0 ? 0 : (line.delay * 1000),
                audio: line.audio || null,
                audio_format: line.audio_format || 'mp3'
            });
        });

        // Start processing the queue
        this.processMessageQueue();
    }

    /**
     * Process the message queue one at a time
     * Waits for audio to finish before showing next message
     */
    processMessageQueue() {
        if (this.isProcessingQueue || this.messageQueue.length === 0) {
            return;
        }

        this.isProcessingQueue = true;
        const message = this.messageQueue.shift();

        // Wait for the specified delay before showing the message
        setTimeout(() => {
            // Play audio if available, and wait for it to finish
            if (message.audio && this.audioEnabled) {
                this.playAudioWithCallback(message.audio, message.audio_format || 'mp3', () => {
                    // Audio finished - now we can process next message
                    this.isProcessingQueue = false;
                    if (this.messageQueue.length > 0) {
                        this.processMessageQueue();
                    }
                });
            }

            // Show the text message
            this.addMessageQueued(message.sender, message.content, message.type, () => {
                // Text typing finished
                // If no audio, proceed to next message now
                if (!message.audio || !this.audioEnabled) {
                    this.isProcessingQueue = false;
                    if (this.messageQueue.length > 0) {
                        this.processMessageQueue();
                    }
                }
                // If audio is playing, the audio callback will trigger next message
            });
        }, message.delay || 0);
    }

    /**
     * Add a message with a callback when typing is complete
     */
    addMessageQueued(sender, content, type, onComplete) {
        const messagesContainer = document.getElementById('chat-messages');

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        const senderDiv = document.createElement('div');
        senderDiv.className = 'message-sender';
        senderDiv.textContent = sender;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        messageDiv.appendChild(senderDiv);
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Apply typing effect with callback
        if (type === 'character') {
            this.typeMessage(contentDiv, content, 30, onComplete);
        } else {
            contentDiv.innerHTML = this.parseVoiceAnnotations(content);
            if (onComplete) onComplete();
        }
    }

    /**
     * Show waiting indicator with animated dots (. . . . .)
     * When 5 dots are reached, triggers story continuation
     */
    startWaitingIndicator() {
        if (this.waitingInterval) {
            return; // Already showing
        }

        this.waitingDots = 0;
        const messagesContainer = document.getElementById('chat-messages');

        // Create waiting indicator element
        const waitingDiv = document.createElement('div');
        waitingDiv.className = 'message character waiting-indicator';
        waitingDiv.id = 'waiting-indicator';

        const senderDiv = document.createElement('div');
        senderDiv.className = 'message-sender';
        senderDiv.textContent = 'Waiting';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content waiting-dots';
        contentDiv.textContent = '.';

        waitingDiv.appendChild(senderDiv);
        waitingDiv.appendChild(contentDiv);
        messagesContainer.appendChild(waitingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Animate dots every 800ms
        this.waitingInterval = setInterval(() => {
            this.waitingDots++;
            const dotsText = '. '.repeat(Math.min(this.waitingDots, this.maxWaitingDots)).trim();
            contentDiv.textContent = dotsText;
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            // When we reach 5 dots, signal to move story on
            if (this.waitingDots >= this.maxWaitingDots) {
                this.stopWaitingIndicator();
                this.onWaitingComplete();
            }
        }, 800);
    }

    /**
     * Stop and remove the waiting indicator
     */
    stopWaitingIndicator() {
        if (this.waitingInterval) {
            clearInterval(this.waitingInterval);
            this.waitingInterval = null;
        }
        this.waitingDots = 0;

        const indicator = document.getElementById('waiting-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    /**
     * Called when waiting completes (5 dots reached)
     * Sends a signal to move the story forward
     */
    onWaitingComplete() {
        console.log('Waiting complete - moving story forward');

        // Send a "waiting_complete" message to the server
        // This tells the World Director to move the story on
        if (this.isConnected) {
            this.ws.send(JSON.stringify({
                type: 'waiting_complete',
                reason: 'Player waited for NPC response'
            }));
        }
    }

    addSystemMessage(content) {
        this.addMessage('System', content, 'system');
    }

    showTypingIndicator() {
        // Use the new waiting indicator with animated dots
        this.startWaitingIndicator();
    }

    hideTypingIndicator() {
        // Stop the waiting indicator
        this.stopWaitingIndicator();

        // Also remove old-style indicator if present
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connection-status');
        if (connected) {
            statusElement.textContent = 'Connected';
            statusElement.className = 'connected';
        } else {
            statusElement.textContent = 'Disconnected';
            statusElement.className = 'disconnected';
        }
    }

    changeCharacter(characterId) {
        this.currentCharacter = characterId;

        // Update UI
        const characterNames = {
            'eliza': 'Eliza',
            'wizard': 'Merlin',
            'detective': 'Detective Stone',
            'engineer': 'Casey Reeves',
            'custom': 'Custom Character'
        };

        const characterDescriptions = {
            'eliza': 'AI Caretaker',
            'wizard': 'Wise Wizard',
            'detective': 'Hard-boiled Detective',
            'engineer': 'Sub Engineer',
            'custom': 'Custom Character'
        };

        const characterColors = {
            'eliza': 0x4fc3f7,
            'wizard': 0x9c27b0,
            'detective': 0x795548,
            'engineer': 0xff6b35,
            'custom': 0x4caf50
        };

        document.getElementById('character-name').textContent = characterNames[characterId];
        document.getElementById('character-description').textContent = characterDescriptions[characterId];

        // Update 3D character appearance (only for character scenes)
        if (this.sceneType === 'character' && this.scene.updateCharacter) {
            this.scene.updateCharacter({ color: characterColors[characterId] });
        }

        // Send config to server
        this.sendConfig();

        this.addSystemMessage(`Switched to ${characterNames[characterId]}`);
    }

    restartConversation() {
        // Stop any playing audio
        this.stopAudio();

        // Clear chat
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = '';

        // Recreate the scene if submarine
        if (this.currentScene === 'submarine') {
            const sceneContainer = document.getElementById('scene-container');
            this.createScene(sceneContainer, this.currentScene);
        }

        // Send restart message to server
        if (this.isConnected) {
            this.ws.send(JSON.stringify({
                type: 'restart',
                character: this.currentCharacter,
                scene: this.currentScene
            }));
        }

        this.addSystemMessage('Conversation restarted. The character is ready to talk!');
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});
