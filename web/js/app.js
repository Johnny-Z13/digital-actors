import { CharacterScene } from './scene.js';
import { SubmarineScene } from '/scenes/submarine/submarine_scene.js';
import { DetectiveScene } from '/scenes/detective/detective_scene.js';
import { MerlinsRoomScene } from '/scenes/wizard/merlins_room_scene.js';
import { LifeRaftScene } from './life_raft_scene.js';
import { FoxholeScene } from '/scenes/foxhole/foxhole_scene.js';
import { WelcomeScene } from './welcome_scene.js';

class ChatApp {
    constructor() {
        this.ws = null;
        this.scene = null;
        this.sceneType = 'welcome'; // Scene type for 3D environment
        this.currentCharacter = 'clippy';
        this.currentScene = 'welcome';
        this.isConnected = false;
        this.sessionId = null; // Authentication token from server

        // Configuration - loaded from server (single source of truth)
        this.config = null;
        this.sceneCharacterMap = {};
        this.characterSceneMap = {};
        this.customScenes = [];

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

        // Web Audio API for radio effects
        this.audioContext = null;
        this.radioEffectsEnabled = false;
        this.staticNoise = null;

        // Scene voice effect configuration (phone, radio, etc.)
        this.voiceEffect = null;
        this.phoneNoiseSource = null;

        // Dialogue lock - ensures only one dialogue at a time
        this.dialogueLocked = false;
        this.pendingResponses = [];

        // TEXT-FIRST: Track pending responses waiting for audio
        this.pendingAudioResponses = new Map(); // response_id -> {element, characterName, content}

        // Suggested questions state
        this.currentSuggestions = [];
        this.suggestionsEnabled = true; // Toggle for reply suggestions feature

        this.init();
    }

    async init() {
        // Load configuration from server (single source of truth)
        await this.loadConfig();

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

    async loadConfig() {
        /**
         * Load scene configuration from server.
         * This is the single source of truth for scene↔character mappings.
         */
        try {
            const response = await fetch('/api/config');
            if (!response.ok) {
                throw new Error(`Config fetch failed: ${response.status}`);
            }
            this.config = await response.json();

            // Build lookup maps from config
            this.sceneCharacterMap = {};
            this.characterSceneMap = {};
            this.customScenes = [];

            for (const [sceneId, sceneConfig] of Object.entries(this.config.scenes)) {
                // scene -> character
                this.sceneCharacterMap[sceneId] = sceneConfig.character;

                // character -> scene (first occurrence wins for characters in multiple scenes)
                if (!this.characterSceneMap[sceneConfig.character]) {
                    this.characterSceneMap[sceneConfig.character] = sceneId;
                }

                // Track custom scenes
                if (sceneConfig.requiresCustomScene) {
                    this.customScenes.push(sceneId);
                }
            }

            // Add character aliases
            if (this.config.characterAliases) {
                for (const [alias, canonical] of Object.entries(this.config.characterAliases)) {
                    if (this.characterSceneMap[canonical]) {
                        this.characterSceneMap[alias] = this.characterSceneMap[canonical];
                    }
                }
            }

            console.log('[CONFIG] Loaded scene mappings:', {
                scenes: Object.keys(this.sceneCharacterMap),
                characters: Object.keys(this.characterSceneMap),
                customScenes: this.customScenes
            });

        } catch (error) {
            console.error('[CONFIG] Failed to load config, using fallback:', error);
            // Fallback mappings if server unavailable
            this.sceneCharacterMap = {
                'welcome': 'clippy',
                'submarine': 'engineer',
                'iconic_detectives': 'mara_vane',
                'life_raft': 'captain_hale',
                'crown_court': 'judge',
                'quest': 'wizard',
                'introduction': 'eliza',
                'conversation': 'eliza',
            };
            this.characterSceneMap = {
                'clippy': 'welcome',
                'engineer': 'submarine',
                'mara_vane': 'iconic_detectives',
                'captain_hale': 'life_raft',
                'judge': 'crown_court',
                'wizard': 'quest',
                'eliza': 'introduction',
                'detective': 'iconic_detectives',
            };
            this.customScenes = ['welcome', 'submarine', 'iconic_detectives', 'merlins_room', 'life_raft'];
        }
    }

    createScene(container, sceneId) {
        // Clean up existing scene using dispose() (preferred) or destroy() (fallback)
        if (this.scene) {
            if (typeof this.scene.dispose === 'function') {
                this.scene.dispose();
            } else if (typeof this.scene.destroy === 'function') {
                this.scene.destroy();
            }
            // Remove renderer element if dispose didn't (fallback for legacy code)
            if (this.scene.renderer && this.scene.renderer.domElement && this.scene.renderer.domElement.parentNode) {
                this.scene.renderer.domElement.parentNode.removeChild(this.scene.renderer.domElement);
            }
        }

        // Remove any lingering welcome overlay
        const existingOverlay = document.getElementById('welcome-overlay');
        if (existingOverlay) {
            existingOverlay.remove();
        }

        // Create appropriate scene based on scene ID
        if (sceneId === 'welcome') {
            this.sceneType = 'welcome';
            this.scene = new WelcomeScene(container, (action) => this.handleButtonClick(action));
        } else if (sceneId === 'submarine') {
            this.sceneType = 'submarine';
            this.scene = new SubmarineScene(container, (action) => this.handleButtonClick(action));
        } else if (sceneId === 'iconic_detectives') {
            this.sceneType = 'detective';
            this.scene = new DetectiveScene(container, (action) => this.handleButtonClick(action));
        } else if (sceneId === 'merlins_room') {
            this.sceneType = 'merlins_room';
            this.scene = new MerlinsRoomScene(container, (action) => this.handleButtonClick(action));
        } else if (sceneId === 'life_raft') {
            this.sceneType = 'life_raft';
            this.scene = new LifeRaftScene(container, (action) => this.handleButtonClick(action));
        } else if (sceneId === 'foxhole') {
            this.sceneType = 'foxhole';
            this.scene = new FoxholeScene(container, (action) => this.handleButtonClick(action));
        } else {
            this.sceneType = 'character';
            this.scene = new CharacterScene(container);
        }
    }

    handleButtonClick(action) {
        // Handle submarine button clicks or detective scene actions
        console.log('Button clicked:', action);
        // Don't add system message - let the NPC respond instead
        // This prevents overlapping messages

        // Send button action to server
        if (this.isConnected && this.sessionId) {
            // Check if this is an evidence pin click
            if (action.startsWith('pin_')) {
                this.ws.send(JSON.stringify({
                    type: 'pin_referenced',
                    session_id: this.sessionId,
                    pin_id: action
                }));
            } else {
                this.ws.send(JSON.stringify({
                    type: 'button_action',
                    session_id: this.sessionId,
                    action: action
                }));
            }
        }
    }

    setupEventListeners() {
        // Send button
        const sendButton = document.getElementById('send-button');
        sendButton.addEventListener('click', () => this.sendMessage());

        // Enter key in input
        const chatInput = document.getElementById('chat-input');
        // Add pulse animation to input field
        chatInput.classList.add('pulse');
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

        // === SCENARIO SELECTION (scene is master, character follows) ===
        const sceneSelect = document.getElementById('scene-select');
        sceneSelect.addEventListener('change', (e) => {
            const newScene = e.target.value;
            if (newScene !== this.currentScene) {
                const oldScene = this.currentScene;
                this.currentScene = newScene;

                // Update scenario info display (actor + tagline)
                this.updateScenarioInfo(newScene);

                // Set the matching character internally
                if (this.sceneCharacterMap[newScene]) {
                    const matchingChar = this.sceneCharacterMap[newScene];
                    console.log(`[CONFIG] Scene ${newScene} -> Character ${matchingChar}`);
                    this.currentCharacter = matchingChar;
                    this.updateCharacterDisplay(matchingChar);
                }

                // Reset voice effect when changing scenes (will be set by opening_speech)
                this.voiceEffect = null;
                this.stopPhoneNoise();

                // Check if scene needs custom 3D environment (from config)
                const needsSceneRecreate = this.customScenes.includes(newScene) || this.customScenes.includes(oldScene);
                if (needsSceneRecreate) {
                    const sceneContainer = document.getElementById('scene-container');
                    this.createScene(sceneContainer, newScene);
                }
            }
        });

        // TTS mode selection (expressive vs fast)
        const ttsModeSelect = document.getElementById('tts-mode-select');
        if (ttsModeSelect) {
            ttsModeSelect.addEventListener('change', (e) => {
                console.log('[TTS_MODE] Changed to:', e.target.value);
                // Send updated config to server
                this.sendTtsMode(e.target.value);
            });
        }

        // Reply suggestions toggle
        const suggestionsToggle = document.getElementById('suggestions-toggle');
        if (suggestionsToggle) {
            suggestionsToggle.addEventListener('change', (e) => {
                this.suggestionsEnabled = e.target.checked;
                console.log('[SUGGESTIONS] Toggle:', this.suggestionsEnabled ? 'ON' : 'OFF');
                if (!this.suggestionsEnabled) {
                    // Hide but preserve stored suggestions for re-enable
                    this.hideSuggestedQuestions();
                } else if (this.currentSuggestions && this.currentSuggestions.length > 0) {
                    // Re-display stored suggestions when toggled back on
                    this.updateSuggestedQuestions(this.currentSuggestions);
                }
            });
        }

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
        if (!this.isConnected || !this.sessionId) return;

        const ttsModeSelect = document.getElementById('tts-mode-select');
        const ttsMode = ttsModeSelect ? ttsModeSelect.value : 'expressive';

        this.ws.send(JSON.stringify({
            type: 'config',
            session_id: this.sessionId,
            character: this.currentCharacter,
            scene: this.currentScene,
            tts_mode: ttsMode
        }));
    }

    sendTtsMode(mode) {
        if (!this.isConnected || !this.sessionId) return;

        this.ws.send(JSON.stringify({
            type: 'tts_mode',
            session_id: this.sessionId,
            mode: mode
        }));
    }

    sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();

        if (!message || !this.isConnected || !this.sessionId) return;

        // Clear suggestions when sending a message
        this.clearSuggestedQuestions();

        // Add user message to chat
        this.addMessage('You', message, 'user');

        // Send to server
        this.ws.send(JSON.stringify({
            type: 'message',
            session_id: this.sessionId,
            content: message
        }));

        // Clear input
        input.value = '';

        // Show typing indicator
        this.showTypingIndicator();
    }

    handleServerMessage(data) {
        switch (data.type) {
            case 'session_init':
                // Store session ID for authentication
                this.sessionId = data.session_id;
                console.log('[AUTH] Received session token');
                // Acknowledge session initialization
                this.ws.send(JSON.stringify({
                    type: 'session_ack'
                }));
                break;

            case 'character_response':
                // Legacy combined text+audio response (backward compatible)
                this.hideTypingIndicator();
                // Queue the response to ensure one at a time
                this.queueCharacterResponse(data);
                break;

            case 'character_response_text':
                // TEXT-FIRST: Text arrives before audio for perceived low-latency
                this.hideTypingIndicator();
                this.handleTextFirstResponse(data);
                break;

            case 'character_response_audio':
                // TEXT-FIRST: Audio arrives after text - play it
                this.handleTextFirstAudio(data);
                break;

            case 'scene_change':
                this.currentScene = data.scene;
                document.getElementById('current-scene').textContent = data.scene_name || data.scene;
                this.addSystemMessage(`Scene changed: ${data.scene_name || data.scene}`);
                break;

            case 'config_confirmed':
                // Server confirmed configuration (may have auto-selected character for scene)
                if (data.character !== this.currentCharacter) {
                    console.log(`Character auto-selected: ${data.character} (${data.character_name})`);
                    this.currentCharacter = data.character;
                    // Update UI elements
                    const charNameEl = document.getElementById('character-name');
                    if (charNameEl) {
                        charNameEl.textContent = data.character_name;
                    }
                    // Update scenario info display
                    this.updateScenarioInfo(this.currentScene);
                }
                break;

            case 'available_options':
                // Populate character and scene dropdowns dynamically from server
                this.populateMenus(data.characters, data.scenes, data.current_character, data.current_scene);
                break;

            case 'state_change':
                console.log('State changed:', data.changes);
                break;

            case 'state_update':
                // Server-side state update (e.g., radiation levels, time remaining, hull pressure)
                if (data.state && this.sceneType === 'submarine' && this.scene) {
                    // Sync radiation level with server
                    if (data.state.radiation !== undefined) {
                        this.scene.setRadiationLevel(data.state.radiation);
                    }
                    // Sync time remaining with server
                    if (data.state.time_remaining !== undefined) {
                        this.scene.setTimeRemaining(data.state.time_remaining);
                    }
                    // Sync hull pressure/depth with server
                    if (data.state.hull_pressure !== undefined) {
                        this.scene.setHullPressure(data.state.hull_pressure);
                    }
                    // Sync systems repaired counter with server
                    if (data.state.systems_repaired !== undefined) {
                        this.scene.setSystemsRepaired(data.state.systems_repaired);
                    }
                    // Sync phase with server
                    if (data.state.phase !== undefined) {
                        this.scene.setPhase(data.state.phase);
                    }
                }
                // Handle life_raft scene state updates
                if (data.state && this.sceneType === 'life_raft' && this.scene) {
                    if (data.state.player_oxygen !== undefined) {
                        this.scene.setPlayerOxygen(data.state.player_oxygen);
                    }
                    if (data.state.captain_oxygen !== undefined) {
                        this.scene.setCaptainOxygen(data.state.captain_oxygen);
                    }
                    if (data.state.hull_integrity !== undefined) {
                        this.scene.setHullIntegrity(data.state.hull_integrity);
                    }
                    if (data.state.phase !== undefined) {
                        this.scene.setPhase(data.state.phase);
                    }
                }
                // Handle detective scene state updates
                if (data.state && this.sceneType === 'detective') {
                    this.updateDetectiveUI(data.state);
                }
                break;

            case 'error':
                this.hideTypingIndicator();
                this.addSystemMessage(`Error: ${data.message}`);
                break;

            case 'opening_speech':
                // Character's opening lines - queue them to display one at a time
                console.log('[OPENING_SPEECH] Received opening_speech with', data.lines.length, 'lines');
                // Store voice effect configuration from scene
                if (data.voice_effect) {
                    this.voiceEffect = data.voice_effect;
                    console.log('[VOICE_EFFECT] Configured:', this.voiceEffect.id, 'enabled:', this.voiceEffect.enabled);
                } else {
                    this.voiceEffect = null;
                }
                // SYNC FIX: Disable input during opening speech
                if (data.disable_input) {
                    const chatInput = document.getElementById('chat-input');
                    const sendButton = document.getElementById('send-button');
                    chatInput.disabled = true;
                    sendButton.disabled = true;
                    chatInput.placeholder = 'Please wait...';
                    chatInput.classList.remove('pulse');
                    this.clearSuggestedQuestions(); // Hide suggestions during opening
                    console.log('[SYNC] Input disabled during opening speech');
                }
                // If no lines (like Welcome scene), show initial suggestions
                if (data.lines.length === 0 && data.initial_suggestions) {
                    this.updateSuggestedQuestions(data.initial_suggestions);
                }
                this.queueOpeningLines(data.lines, data.character_name || 'Character');
                break;

            case 'enable_input':
                // SYNC FIX: Re-enable input after opening speech
                const chatInput = document.getElementById('chat-input');
                const sendButton = document.getElementById('send-button');
                chatInput.disabled = false;
                sendButton.disabled = false;
                chatInput.placeholder = 'Type your message...';
                chatInput.classList.add('pulse');
                this.hideTypingIndicator();
                console.log('[SYNC] Input enabled after opening speech');
                break;

            case 'npc_thinking':
                // SYNC FIX: Show typing indicator when NPC is thinking
                const thinkingInput = document.getElementById('chat-input');
                thinkingInput.placeholder = 'Please wait...';
                thinkingInput.classList.remove('pulse');
                this.clearSuggestedQuestions(); // Hide suggestions while waiting
                this.showTypingIndicator(data.character_name);
                break;

            case 'game_over':
                // Game over screen
                this.clearSuggestedQuestions();
                this.showGameOverScreen(data.outcome);
                break;

            case 'system_event':
                // World Director spawned an event
                this.addSystemMessage(data.content);
                break;

            case 'system_notification':
                // Button press or action notification
                this.addSystemMessage(data.message);
                break;

            case 'stop_audio':
                // === DEATH/GAME OVER: Stop ALL audio and clear queues ===
                console.log('[STOP_AUDIO] Received stop signal:', data.reason);
                this.stopAllAudioAndQueues();
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

        // Send restart message to server (include TTS mode)
        if (this.isConnected && this.sessionId) {
            const ttsModeSelect = document.getElementById('tts-mode-select');
            const ttsMode = ttsModeSelect ? ttsModeSelect.value : 'expressive';

            this.ws.send(JSON.stringify({
                type: 'restart',
                session_id: this.sessionId,
                character: this.currentCharacter,
                scene: this.currentScene,
                tts_mode: ttsMode
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

    // ==================== TEXT-FIRST Response Handling ====================

    /**
     * Handle text-first response (text arrives before audio)
     * Display text immediately for perceived low-latency
     */
    handleTextFirstResponse(data) {
        const characterName = data.character_name || 'Character';
        const content = data.content;
        const responseId = data.response_id;
        const suggestions = data.suggested_questions || [];

        console.log('[TEXT-FIRST] Displaying text immediately:', content.substring(0, 50) + '...');

        const messagesContainer = document.getElementById('chat-messages');
        this.stopWaitingIndicator();

        // Create message element
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message character';
        messageDiv.dataset.responseId = responseId;

        const senderDiv = document.createElement('div');
        senderDiv.className = 'message-sender';
        senderDiv.textContent = characterName;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        messageDiv.appendChild(senderDiv);
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Track this response for when audio arrives
        this.pendingAudioResponses.set(responseId, {
            element: messageDiv,
            contentDiv: contentDiv,
            characterName: characterName,
            content: content,
            typingComplete: false
        });

        // Start typing effect
        this.typeMessage(contentDiv, content, 30, () => {
            const pending = this.pendingAudioResponses.get(responseId);
            if (pending) {
                pending.typingComplete = true;
                // If audio already arrived, it will play
                // If not, we'll play it when it arrives
            }
        });

        // Update suggested questions (if input is enabled)
        const chatInput = document.getElementById('chat-input');
        if (!chatInput.disabled && suggestions.length > 0) {
            this.updateSuggestedQuestions(suggestions);
        }
    }

    /**
     * Update the suggested questions UI
     * @param {string[]} suggestions - Array of suggestion strings
     */
    updateSuggestedQuestions(suggestions) {
        const container = document.getElementById('suggested-questions');
        if (!container) return;

        // Check if suggestions are enabled (global toggle)
        if (!this.suggestionsEnabled) {
            container.innerHTML = '';
            container.classList.add('hidden');
            return;
        }

        // Clear existing buttons
        container.innerHTML = '';
        this.currentSuggestions = suggestions;

        if (suggestions.length === 0) {
            container.classList.add('hidden');
            return;
        }

        // Create buttons for each suggestion
        suggestions.forEach((suggestion, index) => {
            const btn = document.createElement('button');
            btn.className = 'suggestion-btn';
            btn.textContent = suggestion;
            btn.setAttribute('aria-label', `Suggestion: ${suggestion}`);
            btn.addEventListener('click', () => this.handleSuggestionClick(suggestion));
            container.appendChild(btn);
        });

        container.classList.remove('hidden');
        console.log('[SUGGESTIONS] Displayed', suggestions.length, 'suggestions');
    }

    /**
     * Handle click on a suggestion button
     * @param {string} suggestion - The suggestion text to send
     */
    handleSuggestionClick(suggestion) {
        console.log('[SUGGESTIONS] User clicked:', suggestion);

        // Clear suggestions immediately
        this.clearSuggestedQuestions();

        // Put the suggestion in the input field and send
        const chatInput = document.getElementById('chat-input');
        chatInput.value = suggestion;

        // Send the message
        this.sendMessage();
    }

    /**
     * Clear all suggested questions (clears stored suggestions too)
     */
    clearSuggestedQuestions() {
        const container = document.getElementById('suggested-questions');
        if (container) {
            container.innerHTML = '';
            container.classList.add('hidden');
        }
        this.currentSuggestions = [];
    }

    /**
     * Hide suggested questions without clearing stored state
     * Used when temporarily hiding (e.g., toggle off) but may restore later
     */
    hideSuggestedQuestions() {
        const container = document.getElementById('suggested-questions');
        if (container) {
            container.innerHTML = '';
            container.classList.add('hidden');
        }
        // Note: does NOT clear this.currentSuggestions
    }

    /**
     * Handle audio that arrives after text (text-first pattern)
     */
    handleTextFirstAudio(data) {
        const responseId = data.response_id;
        const audioBase64 = data.audio;
        const audioFormat = data.audio_format || 'mp3';

        console.log('[TEXT-FIRST] Audio received for response:', responseId);

        const pending = this.pendingAudioResponses.get(responseId);
        if (!pending) {
            console.warn('[TEXT-FIRST] No pending response found for audio:', responseId);
            return;
        }

        // Play audio immediately (text is already displaying)
        if (audioBase64 && this.audioEnabled) {
            this.playAudioWithCallback(audioBase64, audioFormat, () => {
                // Audio complete
                console.log('[TEXT-FIRST] Audio playback complete for:', responseId);
            });
        }

        // Clean up after a delay (allow time for typing to complete)
        setTimeout(() => {
            this.pendingAudioResponses.delete(responseId);
        }, 10000); // Clean up after 10 seconds
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
            // Handle both HTMLAudioElement and AudioBufferSourceNode
            if (this.currentAudio.pause) {
                // HTMLAudioElement
                this.currentAudio.pause();
                this.currentAudio.currentTime = 0;
            } else if (this.currentAudio.stop) {
                // AudioBufferSourceNode (Web Audio API)
                try {
                    this.currentAudio.stop();
                } catch (e) {
                    // May already be stopped
                }
            }
            this.currentAudio = null;
        }
        this.audioCallback = null;
    }

    /**
     * DEATH/GAME OVER: Stop ALL audio and clear ALL queues
     * Called when character dies - ensures no more dialogue plays
     */
    stopAllAudioAndQueues() {
        console.log('[DEATH] Stopping all audio and clearing all queues');

        // 1. Stop any currently playing audio
        this.stopAudio();

        // 2. Clear message queue
        this.messageQueue = [];
        this.isProcessingQueue = false;
        this.currentTypingMessage = null;

        // 3. Clear audio queue
        this.audioQueue = [];

        // 4. Clear pending audio responses (TEXT-FIRST system)
        this.pendingAudioResponses.clear();

        // 5. Clear pending responses
        this.pendingResponses = [];
        this.dialogueLocked = false;

        // 6. Hide typing indicator
        this.hideTypingIndicator();

        // 7. Clear waiting indicator
        if (this.waitingInterval) {
            clearInterval(this.waitingInterval);
            this.waitingInterval = null;
        }
        this.waitingDots = 0;

        // 8. Clear suggested questions
        this.clearSuggestedQuestions();

        // 9. Stop any radio static/noise effects
        if (this.staticNoise) {
            try {
                this.staticNoise.stop();
            } catch (e) {}
            this.staticNoise = null;
        }
        if (this.phoneNoiseSource) {
            try {
                this.phoneNoiseSource.stop();
            } catch (e) {}
            this.phoneNoiseSource = null;
        }

        console.log('[DEATH] All audio and queues cleared - silence');
    }

    /**
     * Initialize Web Audio context and radio effects
     */
    initRadioEffects() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            console.log('[RADIO] Web Audio context initialized');
        }

        // Enable radio effects for submarine scene
        if (this.sceneType === 'submarine') {
            this.radioEffectsEnabled = true;
            console.log('[RADIO] Radio effects enabled for submarine scene');
        }
    }

    /**
     * Create radio effect processing chain
     * @param {AudioBufferSourceNode} source - Audio source node
     * @returns {AudioNode} - Final node in the chain to connect to destination
     */
    createRadioEffectChain(source) {
        if (!this.audioContext) return source;

        // Low-pass filter (muffles high frequencies like a radio)
        const lowpass = this.audioContext.createBiquadFilter();
        lowpass.type = 'lowpass';
        lowpass.frequency.value = 3000; // Cut off frequencies above 3kHz
        lowpass.Q.value = 0.7;

        // High-pass filter (removes very low rumble)
        const highpass = this.audioContext.createBiquadFilter();
        highpass.type = 'highpass';
        highpass.frequency.value = 300; // Cut off frequencies below 300Hz
        highpass.Q.value = 0.7;

        // Compressor (adds radio compression effect)
        const compressor = this.audioContext.createDynamicsCompressor();
        compressor.threshold.value = -20;
        compressor.knee.value = 10;
        compressor.ratio.value = 12;
        compressor.attack.value = 0.003;
        compressor.release.value = 0.05;

        // Gain (volume control)
        const gainNode = this.audioContext.createGain();
        gainNode.gain.value = this.audioVolume;

        // Connect the chain: source -> highpass -> lowpass -> compressor -> gain
        source.connect(highpass);
        highpass.connect(lowpass);
        lowpass.connect(compressor);
        compressor.connect(gainNode);

        return gainNode;
    }

    /**
     * Create phone effect processing chain based on scene voice_effect config
     * Simulates 80s landline phone receiver - narrow, midrangey, gritty
     * @param {AudioBufferSourceNode} source - Audio source node
     * @returns {AudioNode} - Final node in the chain to connect to destination
     */
    createPhoneEffectChain(source) {
        if (!this.audioContext || !this.voiceEffect || !this.voiceEffect.enabled) {
            return source;
        }

        const effect = this.voiceEffect;
        console.log('[PHONE_EFFECT] Creating chain with params:', effect);

        // 1. High-pass filter (removes bass - phone can't reproduce low frequencies)
        const highpass = this.audioContext.createBiquadFilter();
        highpass.type = 'highpass';
        highpass.frequency.value = effect.highpass_freq || 400;
        highpass.Q.value = 0.7;

        // 2. Low-pass filter (removes treble - phone bandwidth is narrow)
        const lowpass = this.audioContext.createBiquadFilter();
        lowpass.type = 'lowpass';
        lowpass.frequency.value = effect.lowpass_freq || 2800;
        lowpass.Q.value = 0.7;

        // 3. Mid-boost peaking filter (telephone presence, that "in your ear" quality)
        let midBoost = null;
        if (effect.mid_boost_freq && effect.mid_boost_gain) {
            midBoost = this.audioContext.createBiquadFilter();
            midBoost.type = 'peaking';
            midBoost.frequency.value = effect.mid_boost_freq;
            midBoost.gain.value = effect.mid_boost_gain;
            midBoost.Q.value = effect.mid_boost_q || 1.0;
        }

        // 4. Compressor (tight dynamics like cheap phone circuitry)
        const compressor = this.audioContext.createDynamicsCompressor();
        compressor.threshold.value = effect.compressor_threshold || -20;
        compressor.knee.value = 6;
        compressor.ratio.value = effect.compressor_ratio || 6;
        compressor.attack.value = effect.compressor_attack || 0.002;
        compressor.release.value = effect.compressor_release || 0.2;

        // 5. Waveshaper for distortion (analog grit from cheap speaker)
        let distortion = null;
        if (effect.distortion_amount && effect.distortion_amount > 0) {
            distortion = this.audioContext.createWaveShaper();
            distortion.curve = this.makeDistortionCurve(effect.distortion_amount);
            distortion.oversample = '2x';
        }

        // 6. Output gain
        const gainNode = this.audioContext.createGain();
        gainNode.gain.value = this.audioVolume;

        // Build the chain: source -> highpass -> lowpass -> (midBoost) -> compressor -> (distortion) -> gain
        let currentNode = source;

        currentNode.connect(highpass);
        currentNode = highpass;

        currentNode.connect(lowpass);
        currentNode = lowpass;

        if (midBoost) {
            currentNode.connect(midBoost);
            currentNode = midBoost;
        }

        currentNode.connect(compressor);
        currentNode = compressor;

        if (distortion) {
            currentNode.connect(distortion);
            currentNode = distortion;
        }

        currentNode.connect(gainNode);

        console.log('[PHONE_EFFECT] Chain created: highpass(' + highpass.frequency.value +
                    ') -> lowpass(' + lowpass.frequency.value +
                    ') -> midBoost -> compressor -> distortion -> gain');

        return gainNode;
    }

    /**
     * Create distortion curve for waveshaper (soft clipping)
     * @param {number} amount - Distortion intensity (higher = more distortion)
     * @returns {Float32Array} - Distortion curve
     */
    makeDistortionCurve(amount) {
        const k = typeof amount === 'number' ? amount : 35;
        const n_samples = 44100;
        const curve = new Float32Array(n_samples);
        const deg = Math.PI / 180;

        for (let i = 0; i < n_samples; ++i) {
            const x = (i * 2) / n_samples - 1;
            curve[i] = ((3 + k) * x * 20 * deg) / (Math.PI + k * Math.abs(x));
        }

        return curve;
    }

    /**
     * Start phone line noise bed (optional background hum/static)
     */
    startPhoneNoise() {
        if (!this.voiceEffect || !this.voiceEffect.noise_level || !this.audioContext) return;

        // Create noise buffer (2 seconds, looping)
        const sampleRate = this.audioContext.sampleRate;
        const bufferSize = sampleRate * 2;
        const noiseBuffer = this.audioContext.createBuffer(1, bufferSize, sampleRate);
        const data = noiseBuffer.getChannelData(0);

        // Generate pink-ish noise (filtered white noise)
        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1;
        }

        this.phoneNoiseSource = this.audioContext.createBufferSource();
        this.phoneNoiseSource.buffer = noiseBuffer;
        this.phoneNoiseSource.loop = true;

        // Bandpass filter to make it sound like phone line noise
        const noiseFilter = this.audioContext.createBiquadFilter();
        noiseFilter.type = 'bandpass';
        noiseFilter.frequency.value = 1000;
        noiseFilter.Q.value = 0.5;

        // Very quiet - convert dB to linear gain (-35 dB ≈ 0.018)
        const noiseGain = this.audioContext.createGain();
        noiseGain.gain.value = Math.pow(10, this.voiceEffect.noise_level / 20);

        this.phoneNoiseSource.connect(noiseFilter);
        noiseFilter.connect(noiseGain);
        noiseGain.connect(this.audioContext.destination);

        this.phoneNoiseSource.start();
        console.log('[PHONE_EFFECT] Line noise started at', this.voiceEffect.noise_level, 'dB');
    }

    /**
     * Stop phone line noise
     */
    stopPhoneNoise() {
        if (this.phoneNoiseSource) {
            try {
                this.phoneNoiseSource.stop();
            } catch (e) {
                // May already be stopped
            }
            this.phoneNoiseSource = null;
            console.log('[PHONE_EFFECT] Line noise stopped');
        }
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

            // Determine which effect to use
            const useVoiceEffect = this.voiceEffect && this.voiceEffect.enabled;
            const useRadioEffect = this.sceneType === 'submarine';

            // Use Web Audio API for any scene with audio effects
            if (useVoiceEffect || useRadioEffect) {
                this.initRadioEffects();

                // Start phone line noise if this is first audio with phone effect
                if (useVoiceEffect && this.voiceEffect.noise_level && !this.phoneNoiseSource) {
                    this.startPhoneNoise();
                }

                // Decode audio data
                fetch(audioUrl)
                    .then(response => response.arrayBuffer())
                    .then(arrayBuffer => this.audioContext.decodeAudioData(arrayBuffer))
                    .then(audioBuffer => {
                        // Create source
                        const source = this.audioContext.createBufferSource();
                        source.buffer = audioBuffer;

                        // Apply appropriate effect chain
                        let effectChain;
                        if (useVoiceEffect) {
                            effectChain = this.createPhoneEffectChain(source);
                            console.log('[PHONE_EFFECT] Applying phone effect chain');
                        } else {
                            effectChain = this.createRadioEffectChain(source);
                            console.log('[RADIO] Applying radio effect chain');
                        }
                        effectChain.connect(this.audioContext.destination);

                        // Handle completion
                        source.onended = () => {
                            console.log('[AUDIO_EFFECT] Audio playback ended');
                            URL.revokeObjectURL(audioUrl);
                            this.currentAudio = null;
                            if (this.audioCallback) {
                                const cb = this.audioCallback;
                                this.audioCallback = null;
                                cb();
                            }
                        };

                        // Start playback
                        source.start(0);
                        this.currentAudio = source; // Store reference
                        console.log('[AUDIO_EFFECT] Effect-processed playback started');
                    })
                    .catch(e => {
                        console.error('[AUDIO_EFFECT] Audio processing failed:', e);
                        URL.revokeObjectURL(audioUrl);
                        if (this.audioCallback) {
                            const cb = this.audioCallback;
                            this.audioCallback = null;
                            cb();
                        }
                    });
                return;
            }

            // Standard playback (no effects) for non-submarine scenes
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
     * Escape HTML special characters to prevent XSS attacks.
     * @param {string} unsafe - Raw text that may contain HTML
     * @returns {string} - HTML-safe text
     */
    escapeHTML(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    /**
     * Parse voice annotations like [static], [voice cracks], [breathing heavily]
     * and wrap them in styled spans for visual distinction.
     * Also adds data attributes for ElevenLabs TTS integration.
     *
     * SECURITY: Text is HTML-escaped first to prevent XSS, then annotations are processed.
     */
    parseVoiceAnnotations(text) {
        // SECURITY: Escape HTML first to prevent XSS attacks
        const escapedText = this.escapeHTML(text);

        // Match annotations in square brackets like [static], [voice cracks], etc.
        const annotationRegex = /\[([^\]]+)\]/g;

        return escapedText.replace(annotationRegex, (match, content) => {
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
        console.log('[OPENING_SPEECH] queueOpeningLines called with', lines.length, 'lines. Current queue length:', this.messageQueue.length);

        // Track that this is an opening speech queue
        this.openingSpeechPending = true;
        this.openingSpeechLineCount = lines.length;
        this.openingSpeechLinesProcessed = 0;

        // Add all lines to the queue (including audio if available)
        lines.forEach((line, index) => {
            console.log('[OPENING_SPEECH] Adding line', index + 1, ':', line.text.substring(0, 50) + '...');
            this.messageQueue.push({
                sender: characterName,
                content: line.text,
                type: 'character',
                delay: index === 0 ? 0 : (line.delay * 1000),
                audio: line.audio || null,
                audio_format: line.audio_format || 'mp3',
                isOpeningSpeech: true
            });
        });

        console.log('[OPENING_SPEECH] Queue now has', this.messageQueue.length, 'messages');

        // Start processing the queue
        this.processMessageQueue();
    }

    /**
     * Process the message queue one at a time
     * Waits for audio to finish before showing next message
     */
    processMessageQueue() {
        if (this.isProcessingQueue || this.messageQueue.length === 0) {
            // Check if opening speech just finished
            if (this.messageQueue.length === 0 && this.openingSpeechPending) {
                this.onOpeningSpeechComplete();
            }
            return;
        }

        this.isProcessingQueue = true;
        const message = this.messageQueue.shift();

        // Track opening speech progress
        if (message.isOpeningSpeech) {
            this.openingSpeechLinesProcessed++;
        }

        // Wait for the specified delay before showing the message
        setTimeout(() => {
            // Play audio if available, and wait for it to finish
            if (message.audio && this.audioEnabled) {
                this.playAudioWithCallback(message.audio, message.audio_format || 'mp3', () => {
                    // Audio finished - now we can process next message
                    this.isProcessingQueue = false;
                    if (this.messageQueue.length > 0) {
                        this.processMessageQueue();
                    } else if (this.openingSpeechPending) {
                        this.onOpeningSpeechComplete();
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
                    } else if (this.openingSpeechPending) {
                        this.onOpeningSpeechComplete();
                    }
                }
                // If audio is playing, the audio callback will trigger next message
            });
        }, message.delay || 0);
    }

    /**
     * Called when all opening speech lines have been processed
     * Notifies the server to enable input immediately
     */
    onOpeningSpeechComplete() {
        if (!this.openingSpeechPending) return;

        this.openingSpeechPending = false;
        console.log('[OPENING_SPEECH] All lines processed, notifying server');

        // Immediately enable input on the client side
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-button');
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.placeholder = 'Enter message...';
        chatInput.classList.add('pulse');
        this.hideTypingIndicator();

        // Notify server that opening speech is complete
        if (this.isConnected && this.sessionId) {
            this.ws.send(JSON.stringify({
                type: 'opening_speech_complete',
                session_id: this.sessionId
            }));
        }
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
        if (this.isConnected && this.sessionId) {
            this.ws.send(JSON.stringify({
                type: 'waiting_complete',
                session_id: this.sessionId,
                reason: 'Player waited for NPC response'
            }));
        }
    }

    addSystemMessage(content) {
        this.addMessage('System', content, 'system');
    }

    showTypingIndicator(characterName = null) {
        // Use the new waiting indicator with animated dots
        // If character name provided, use it in the indicator
        this.startWaitingIndicator(characterName);
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

    /**
     * Update character display in the UI without side effects.
     * Called when character changes due to scene selection.
     */
    updateCharacterDisplay(characterId) {
        const characterNames = {
            'clippy': 'Clippy',
            'eliza': 'Eliza',
            'wizard': 'Merlin',
            'detective': 'Detective Stone',
            'engineer': 'Lt. Cmdr. James Smith',
            'judge': 'Judge Harriet Thorne',
            'mara_vane': 'Mara Vane',
            'captain_hale': 'Captain Hale',
            'custom': 'Custom Character'
        };

        const characterDescriptions = {
            'clippy': 'Your Friendly Guide',
            'eliza': 'AI Caretaker',
            'wizard': 'Wise Wizard',
            'detective': 'Hard-boiled Detective',
            'engineer': 'Sub Commander',
            'judge': 'Crown Court Judge',
            'mara_vane': 'Mysterious Caller',
            'captain_hale': 'Life Raft Commander',
            'custom': 'Custom Character'
        };

        const characterColors = {
            'clippy': 0x7B7B7B,
            'eliza': 0x4fc3f7,
            'wizard': 0x9c27b0,
            'detective': 0x795548,
            'engineer': 0xff6b35,
            'judge': 0x8b4513,
            'mara_vane': 0x6b4423,
            'captain_hale': 0x2a5a8a,
            'custom': 0x4caf50
        };

        const name = characterNames[characterId] || characterId;
        const desc = characterDescriptions[characterId] || '';

        document.getElementById('character-name').textContent = name;
        document.getElementById('character-description').textContent = desc;

        // Update 3D character appearance (only for character scenes)
        if (this.sceneType === 'character' && this.scene && this.scene.updateCharacter) {
            this.scene.updateCharacter({ color: characterColors[characterId] });
        }

        return { name, description: desc };
    }

    /**
     * Update the scenario info display (actor name + tagline).
     * Called when scenario selection changes.
     */
    updateScenarioInfo(sceneId) {
        const actorNameEl = document.getElementById('scenario-actor-name');
        const taglineEl = document.getElementById('scenario-tagline');

        if (!actorNameEl || !taglineEl) return;

        // Get scene config from loaded config
        const sceneConfig = this.config?.scenes?.[sceneId];

        if (sceneConfig) {
            actorNameEl.textContent = sceneConfig.characterName || sceneConfig.character || '—';
            taglineEl.textContent = sceneConfig.tagline || 'No description available';
            console.log(`[SCENARIO] Updated info: ${sceneConfig.characterName} - ${sceneConfig.tagline?.substring(0, 50)}...`);
        } else {
            actorNameEl.textContent = '—';
            taglineEl.textContent = 'Select a scenario above';
        }
    }

    changeCharacter(characterId) {
        this.currentCharacter = characterId;

        // Update UI
        const { name } = this.updateCharacterDisplay(characterId);

        // Send config to server
        this.sendConfig();

        this.addSystemMessage(`Switched to ${name}`);
    }

    restartConversation() {
        // Stop any playing audio
        this.stopAudio();

        // Clear chat
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = '';

        // Clear detective dialogue buttons and suggestions
        this.clearDetectiveDialogueButtons();
        this.clearSuggestedQuestions();

        // Reset voice effect for new scene
        this.voiceEffect = null;
        this.stopPhoneNoise();

        // Recreate the scene if it's a custom 3D scene
        const customScenes = ['welcome', 'submarine', 'iconic_detectives', 'merlins_room', 'life_raft'];
        if (customScenes.includes(this.currentScene)) {
            const sceneContainer = document.getElementById('scene-container');
            this.createScene(sceneContainer, this.currentScene);
        }

        // Send restart message to server (include TTS mode)
        if (this.isConnected && this.sessionId) {
            const ttsModeSelect = document.getElementById('tts-mode-select');
            const ttsMode = ttsModeSelect ? ttsModeSelect.value : 'expressive';

            this.ws.send(JSON.stringify({
                type: 'restart',
                session_id: this.sessionId,
                character: this.currentCharacter,
                scene: this.currentScene,
                tts_mode: ttsMode
            }));
        }

        this.addSystemMessage('Conversation restarted. The character is ready to talk!');
    }

    // ==================== Dynamic Menu Population ====================

    /**
     * Populate scenario dropdown from server data.
     * Scenario is the master selection; character follows automatically.
     */
    populateMenus(characters, scenes, currentCharacter, currentScene) {
        console.log('[MENUS] Populating scenario menu with', scenes.length, 'scenarios');

        // Populate scenario (scene) dropdown
        const sceneSelect = document.getElementById('scene-select');
        if (sceneSelect) {
            sceneSelect.innerHTML = '';
            scenes.forEach(scene => {
                const option = document.createElement('option');
                option.value = scene.id;
                option.textContent = scene.name;
                if (scene.id === currentScene) {
                    option.selected = true;
                }
                sceneSelect.appendChild(option);
            });
        }

        // Update current state
        this.currentCharacter = currentCharacter;
        this.currentScene = currentScene;

        // Update scenario info display (actor + tagline)
        this.updateScenarioInfo(currentScene);

        // Update header with current character info
        const selectedChar = characters.find(c => c.id === currentCharacter);
        if (selectedChar) {
            const charNameEl = document.getElementById('character-name');
            const charDescEl = document.getElementById('character-description');
            if (charNameEl) charNameEl.textContent = selectedChar.name;
            if (charDescEl) charDescEl.textContent = selectedChar.description;
        }

        // Update scene display
        const selectedScene = scenes.find(s => s.id === currentScene);
        if (selectedScene) {
            const sceneEl = document.getElementById('current-scene');
            if (sceneEl) sceneEl.textContent = selectedScene.name;
        }

        console.log('[MENUS] Current scenario:', currentScene, '-> Character:', currentCharacter);
    }

    // ==================== Detective Scene UI ====================

    /**
     * Update the detective scene UI based on current state
     */
    updateDetectiveUI(state) {
        const phase = state.phase || 1;
        const trust = state.trust || 50;
        const contradictions = state.contradictions || 0;
        const pathChosen = state.path_chosen || 0;

        console.log('[DETECTIVE] State update - Phase:', phase, 'Trust:', trust, 'Contradictions:', contradictions);

        // Update dialogue buttons based on phase
        this.renderDetectiveDialogueButtons(phase, pathChosen, contradictions);

        // Update any status display if present
        this.updateDetectiveStatus(trust, contradictions, phase);
    }

    /**
     * Render dialogue choice buttons based on current phase
     */
    renderDetectiveDialogueButtons(phase, pathChosen, contradictions) {
        // Get or create the dialogue buttons container
        let buttonContainer = document.getElementById('detective-dialogue-buttons');
        if (!buttonContainer) {
            buttonContainer = document.createElement('div');
            buttonContainer.id = 'detective-dialogue-buttons';
            buttonContainer.style.cssText = `
                position: fixed;
                bottom: 200px;
                left: 20px;
                display: flex;
                flex-direction: column;
                gap: 8px;
                z-index: 1000;
                max-width: 280px;
            `;
            document.body.appendChild(buttonContainer);
        }

        // Clear existing buttons
        buttonContainer.innerHTML = '';

        // Button configurations by phase
        const buttonConfigs = {
            2: [ // Core hooks
                { id: 'hook_identity', label: 'WHO ARE YOU?', color: '#4682b4' },
                { id: 'hook_timeline', label: "WHAT'S WRONG WITH THE TIMING?", color: '#4682b4' },
                { id: 'hook_key', label: 'WHY STEAL A KEY?', color: '#4682b4' },
            ],
            3: [ // Branch choice
                { id: 'follow_key', label: 'FOLLOW THE KEY', color: '#ffd700' },
                { id: 'follow_lie', label: 'FOLLOW THE LIE', color: '#ff6347' },
            ],
            4: [ // Path 1 sub-options
                { id: 'p1_how_know', label: 'HOW DO YOU KNOW SABLE STORAGE?', color: '#228b22' },
                { id: 'p1_whats_inside', label: "WHAT'S IN THE BOX?", color: '#228b22' },
                { id: 'p1_who_knows', label: 'WHO ELSE KNOWS?', color: '#228b22' },
            ],
            5: [ // Path 2 sub-options
                { id: 'p2_who_staged', label: 'WHO STAGED IT?', color: '#800020' },
                { id: 'p2_why_argument', label: 'WHY AN ARGUMENT?', color: '#800020' },
                { id: 'p2_killer_detail', label: 'GIVE ME A KILLER DETAIL', color: '#800020' },
            ],
        };

        // Get buttons for current phase
        const buttons = buttonConfigs[phase] || [];

        // Add challenge button if contradictions >= 1 and in path phases
        if ((phase === 4 || phase === 5) && contradictions >= 1) {
            buttons.push({
                id: 'challenge_mara',
                label: contradictions >= 2 ? 'YOU WERE THERE' : 'CHALLENGE HER',
                color: '#ff0000'
            });
        }

        // Create buttons
        buttons.forEach(config => {
            const button = document.createElement('button');
            button.textContent = config.label;
            button.style.cssText = `
                padding: 10px 16px;
                font-size: 12px;
                font-weight: bold;
                background: rgba(0, 0, 0, 0.8);
                color: ${config.color};
                border: 2px solid ${config.color};
                border-radius: 4px;
                cursor: pointer;
                transition: all 0.2s ease;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                text-align: left;
            `;

            button.onmouseover = () => {
                button.style.background = config.color;
                button.style.color = '#000';
            };
            button.onmouseout = () => {
                button.style.background = 'rgba(0, 0, 0, 0.8)';
                button.style.color = config.color;
            };

            button.onclick = () => {
                this.handleButtonClick(config.id);
            };

            buttonContainer.appendChild(button);
        });

        // Show phase indicator
        if (buttons.length > 0) {
            const phaseLabel = document.createElement('div');
            phaseLabel.style.cssText = `
                font-size: 10px;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 0.1em;
                margin-bottom: 4px;
            `;
            const phaseNames = {
                2: 'Core Questions',
                3: 'Choose Your Path',
                4: 'Follow the Key',
                5: 'Follow the Lie'
            };
            phaseLabel.textContent = phaseNames[phase] || '';
            buttonContainer.insertBefore(phaseLabel, buttonContainer.firstChild);
        }
    }

    /**
     * Update detective status display
     */
    updateDetectiveStatus(trust, contradictions, phase) {
        // Get or create status display
        let statusDisplay = document.getElementById('detective-status');
        if (!statusDisplay) {
            statusDisplay = document.createElement('div');
            statusDisplay.id = 'detective-status';
            statusDisplay.style.cssText = `
                position: fixed;
                top: 20px;
                left: 20px;
                padding: 12px 16px;
                background: rgba(0, 0, 0, 0.8);
                border: 1px solid #333;
                border-radius: 4px;
                font-size: 12px;
                color: #ccc;
                z-index: 1000;
                font-family: monospace;
            `;
            document.body.appendChild(statusDisplay);
        }

        // Trust color based on level
        let trustColor = '#4ade80'; // Green
        if (trust < 40) trustColor = '#ef4444'; // Red
        else if (trust < 60) trustColor = '#fbbf24'; // Yellow

        statusDisplay.innerHTML = `
            <div style="margin-bottom: 6px;">
                <span style="color: #888;">TRUST:</span>
                <span style="color: ${trustColor}; font-weight: bold;">${trust.toFixed(0)}%</span>
            </div>
            <div>
                <span style="color: #888;">CONTRADICTIONS:</span>
                <span style="color: ${contradictions >= 2 ? '#ef4444' : '#ccc'}; font-weight: bold;">${contradictions}</span>
            </div>
        `;
    }

    /**
     * Clear detective dialogue buttons
     */
    clearDetectiveDialogueButtons() {
        const buttonContainer = document.getElementById('detective-dialogue-buttons');
        if (buttonContainer) {
            buttonContainer.remove();
        }
        const statusDisplay = document.getElementById('detective-status');
        if (statusDisplay) {
            statusDisplay.remove();
        }
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});
