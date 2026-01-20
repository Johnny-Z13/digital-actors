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
        this.addSystemMessage(`[Control] ${action} activated`);

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
                this.addMessage(
                    data.character_name || 'Character',
                    data.content,
                    'character'
                );
                break;

            case 'scene_change':
                this.currentScene = data.scene;
                document.getElementById('current-scene').textContent = data.scene_name || data.scene;
                this.addSystemMessage(`Scene changed: ${data.scene_name || data.scene}`);
                break;

            case 'state_change':
                console.log('State changed:', data.changes);
                break;

            case 'error':
                this.hideTypingIndicator();
                this.addSystemMessage(`Error: ${data.message}`);
                break;

            case 'opening_speech':
                // Character's opening lines
                data.lines.forEach((line, index) => {
                    setTimeout(() => {
                        this.addMessage(
                            data.character_name || 'Character',
                            line.text,
                            'character'
                        );
                    }, line.delay * 1000 + index * 100);
                });
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
        // Create game over overlay
        const overlay = document.createElement('div');
        overlay.id = 'game-over-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.95);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 10000;
            animation: fadeIn 0.5s;
        `;

        // Title
        const title = document.createElement('div');
        title.style.cssText = `
            font-size: 4rem;
            font-weight: bold;
            margin-bottom: 2rem;
            color: ${outcome.type === 'success' ? '#4ade80' : '#ef4444'};
            text-shadow: 0 0 20px currentColor;
        `;
        title.textContent = 'THE END';

        // Outcome description
        const description = document.createElement('div');
        description.style.cssText = `
            font-size: 1.5rem;
            max-width: 600px;
            text-align: center;
            line-height: 1.8;
            color: #e0e0e0;
            padding: 0 2rem;
            margin-bottom: 3rem;
        `;
        description.textContent = outcome.description || outcome.message;

        // Restart button
        const restartButton = document.createElement('button');
        restartButton.textContent = 'Try Again';
        restartButton.style.cssText = `
            padding: 1rem 2rem;
            font-size: 1.2rem;
            background: ${outcome.type === 'success' ? '#4ade80' : '#ef4444'};
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.2s;
        `;
        restartButton.onmouseover = () => restartButton.style.transform = 'scale(1.1)';
        restartButton.onmouseout = () => restartButton.style.transform = 'scale(1)';
        restartButton.onclick = () => {
            document.body.removeChild(overlay);
            this.restart();
        };

        // Add CSS animation
        if (!document.getElementById('game-over-styles')) {
            const style = document.createElement('style');
            style.id = 'game-over-styles';
            style.textContent = `
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }

        overlay.appendChild(title);
        overlay.appendChild(description);
        overlay.appendChild(restartButton);
        document.body.appendChild(overlay);
    }

    restart() {
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

    addMessage(sender, content, type, useTypingEffect = true) {
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

        // Apply typing effect for character messages
        if (type === 'character' && useTypingEffect) {
            this.typeMessage(contentDiv, content);
        } else {
            contentDiv.textContent = content;
        }
    }

    typeMessage(element, text, speed = 30) {
        let index = 0;
        element.textContent = '';

        const messagesContainer = document.getElementById('chat-messages');
        let lastScrollTime = 0;

        const typeInterval = setInterval(() => {
            if (index < text.length) {
                // Batch multiple characters for better performance
                const charsToAdd = Math.min(2, text.length - index);
                element.textContent += text.substring(index, index + charsToAdd);
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
                // Final scroll to ensure we're at bottom
                requestAnimationFrame(() => {
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                });
            }
        }, speed);
    }

    addSystemMessage(content) {
        this.addMessage('System', content, 'system');
    }

    showTypingIndicator() {
        const messagesContainer = document.getElementById('chat-messages');

        const typingDiv = document.createElement('div');
        typingDiv.className = 'message character';
        typingDiv.id = 'typing-indicator';

        const senderDiv = document.createElement('div');
        senderDiv.className = 'message-sender';
        senderDiv.textContent = 'Character';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator';
        indicator.innerHTML = '<span></span><span></span><span></span>';

        contentDiv.appendChild(indicator);
        typingDiv.appendChild(senderDiv);
        typingDiv.appendChild(contentDiv);
        messagesContainer.appendChild(typingDiv);

        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    hideTypingIndicator() {
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
