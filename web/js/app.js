import { CharacterScene } from './scene.js';

class ChatApp {
    constructor() {
        this.ws = null;
        this.scene = null;
        this.currentCharacter = 'eliza';
        this.currentScene = 'introduction';
        this.isConnected = false;

        this.init();
    }

    init() {
        // Initialize Three.js scene
        const sceneContainer = document.getElementById('scene-container');
        this.scene = new CharacterScene(sceneContainer);

        // Setup event listeners
        this.setupEventListeners();

        // Connect to WebSocket
        this.connectWebSocket();

        // Hide loading screen after scene loads
        setTimeout(() => {
            document.getElementById('loading-screen').classList.add('hidden');
        }, 1000);
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
            this.currentScene = e.target.value;
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

            default:
                console.log('Unknown message type:', data.type);
        }
    }

    addMessage(sender, content, type) {
        const messagesContainer = document.getElementById('chat-messages');

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        const senderDiv = document.createElement('div');
        senderDiv.className = 'message-sender';
        senderDiv.textContent = sender;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;

        messageDiv.appendChild(senderDiv);
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
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
            'custom': 'Custom Character'
        };

        const characterDescriptions = {
            'eliza': 'AI Caretaker',
            'wizard': 'Wise Wizard',
            'detective': 'Hard-boiled Detective',
            'custom': 'Custom Character'
        };

        const characterColors = {
            'eliza': 0x4fc3f7,
            'wizard': 0x9c27b0,
            'detective': 0x795548,
            'custom': 0x4caf50
        };

        document.getElementById('character-name').textContent = characterNames[characterId];
        document.getElementById('character-description').textContent = characterDescriptions[characterId];

        // Update 3D character appearance
        this.scene.updateCharacter({ color: characterColors[characterId] });

        // Send config to server
        this.sendConfig();

        this.addSystemMessage(`Switched to ${characterNames[characterId]}`);
    }

    restartConversation() {
        // Clear chat
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = '';

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
