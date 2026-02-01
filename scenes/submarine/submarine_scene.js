import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { TextGeometry } from 'three/addons/geometries/TextGeometry.js';
import { FontLoader } from 'three/addons/loaders/FontLoader.js';

export class SubmarineScene {
    constructor(container, onButtonClick) {
        this.container = container;
        this.onButtonClick = onButtonClick || (() => {});
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.radiationLevel = 0; // Radiation percentage (0-100)
        this.timeRemaining = 480; // 8 minutes in seconds
        this.hullPressure = 2400; // Depth in feet
        this.systemsRepaired = 0; // Systems repaired counter (0-4)
        this.phase = 1; // Current phase (1-4)
        this.radiationText = null;
        this.timeText = null;
        this.pressureText = null;
        this.systemsText = null;
        this.phaseText = null;
        this.warningLights = [];
        this.interactiveObjects = [];

        // Framerate limiting for better input responsiveness
        this.targetFPS = 50; // Limit to 50 FPS to give CPU time for input
        this.frameInterval = 1000 / this.targetFPS;
        this.lastFrameTime = 0;
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.hoveredObject = null;
        this.mouseNeedsUpdate = false; // Track if mouse moved for raycast optimization

        // Audio system
        this.audioContext = null;
        this.sounds = {};
        this.alarmInterval = null;  // For looping alarm
        this.alarmActive = false;   // Track if alarm is currently active
        this.initAudio();

        // Emergency lighting
        this.emergencyLight = null;
        this.emergencyLightOn = false;

        // Performance tracking
        this.frameCount = 0; // For throttling expensive operations

        // Button debouncing
        this.lastButtonClick = 0;
        this.buttonDebounceMs = 500; // Prevent clicking same button within 500ms

        this.init();
        this.animate();
        this.setupInteraction();
    }

    initAudio() {
        // Create audio context (lazy init on first user interaction)
        this.audioContext = null;  // Will be created on first click

        // Preload default click sound (using Web Audio API with generated tone)
        // This creates a simple click/beep sound without needing external files
        this.sounds.click = () => this.playClickSound();
    }

    playClickSound() {
        // Create audio context on first interaction (required by browsers)
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }

        const ctx = this.audioContext;
        const currentTime = ctx.currentTime;

        // Create oscillator for beep
        const oscillator = ctx.createOscillator();
        const gainNode = ctx.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);

        // Button click sound: short beep
        oscillator.frequency.value = 800;  // 800 Hz tone
        oscillator.type = 'sine';

        // Quick fade out for click effect
        gainNode.gain.setValueAtTime(0.3, currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, currentTime + 0.1);

        // Play for 100ms
        oscillator.start(currentTime);
        oscillator.stop(currentTime + 0.1);
    }

    playSoundEffect(soundName) {
        // Future: load and play sound files from scene.art_assets.audio.sfx_library
        // For now, use generated sounds
        if (this.sounds[soundName]) {
            this.sounds[soundName]();
        }
    }

    playAlarmSound() {
        // Create audio context on first interaction (required by browsers)
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }

        const ctx = this.audioContext;
        const currentTime = ctx.currentTime;

        // Create oscillators for alarm sound (two-tone siren)
        const osc1 = ctx.createOscillator();
        const osc2 = ctx.createOscillator();
        const gainNode = ctx.createGain();

        osc1.connect(gainNode);
        osc2.connect(gainNode);
        gainNode.connect(ctx.destination);

        // Two-tone alarm: alternating high/low
        osc1.frequency.setValueAtTime(800, currentTime);
        osc1.frequency.setValueAtTime(600, currentTime + 0.25);
        osc1.frequency.setValueAtTime(800, currentTime + 0.5);
        osc1.frequency.setValueAtTime(600, currentTime + 0.75);
        osc1.type = 'square';

        // Second oscillator for richer sound
        osc2.frequency.setValueAtTime(400, currentTime);
        osc2.frequency.setValueAtTime(300, currentTime + 0.25);
        osc2.frequency.setValueAtTime(400, currentTime + 0.5);
        osc2.frequency.setValueAtTime(300, currentTime + 0.75);
        osc2.type = 'sawtooth';

        // Volume envelope (75% quieter than original)
        gainNode.gain.setValueAtTime(0.0375, currentTime);
        gainNode.gain.setValueAtTime(0.0375, currentTime + 0.9);
        gainNode.gain.exponentialRampToValueAtTime(0.01, currentTime + 1.0);

        // Play for 1 second
        osc1.start(currentTime);
        osc2.start(currentTime);
        osc1.stop(currentTime + 1.0);
        osc2.stop(currentTime + 1.0);
    }

    startAlarm() {
        if (this.alarmActive) return;

        this.alarmActive = true;
        console.log('[ALARM] Emergency alarm activated - radiation critical!');

        // Alarm sound disabled per user request
        // this.playAlarmSound();

        // Loop alarm every 1.5 seconds
        // this.alarmInterval = setInterval(() => {
        //     if (this.alarmActive) {
        //         this.playAlarmSound();
        //     }
        // }, 1500);
    }

    stopAlarm() {
        if (!this.alarmActive) return;

        this.alarmActive = false;
        console.log('[ALARM] Emergency alarm deactivated');

        if (this.alarmInterval) {
            clearInterval(this.alarmInterval);
            this.alarmInterval = null;
        }
    }

    init() {
        // Scene with submarine interior atmosphere
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a1520);
        this.scene.fog = new THREE.Fog(0x0a1520, 5, 15);

        // Camera - first person perspective, centered and looking at control panel
        this.camera = new THREE.PerspectiveCamera(
            75,
            window.innerWidth / window.innerHeight,
            0.1,
            1000
        );
        // Start centered in the cabin, looking forward at control panel (slightly closer)
        this.camera.position.set(0, 1.6, 0.2);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({
            antialias: false,  // Disable expensive antialiasing for better performance
            powerPreference: "high-performance",  // Request high-performance GPU
            stencil: false,  // Disable stencil buffer (not needed)
            depth: true  // Keep depth buffer for proper z-sorting
        });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); // Cap at 2x for performance
        this.renderer.shadowMap.enabled = false; // Disable shadows for performance
        this.container.appendChild(this.renderer.domElement);

        // Controls - mouse look within ~100 degree range, centered on control panel
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.08;

        // Disable zoom and pan - only rotation
        this.controls.enableZoom = false;
        this.controls.enablePan = false;

        // Set rotation limits for ~100 degree field of view
        // Horizontal rotation: ~50 degrees left and right from center
        this.controls.minAzimuthAngle = -Math.PI / 3.6;  // ~50 degrees left
        this.controls.maxAzimuthAngle = Math.PI / 3.6;   // ~50 degrees right

        // Vertical rotation: ~50 degrees up and down from center
        this.controls.minPolarAngle = Math.PI / 2 - Math.PI / 3.6;  // ~50 degrees up
        this.controls.maxPolarAngle = Math.PI / 2 + Math.PI / 3.6;  // ~50 degrees down

        // Set target to control panel - centered view
        this.controls.target.set(0, 1.6, -2.2);

        // Mouse sensitivity
        this.controls.rotateSpeed = 0.5;

        // Create submarine interior
        this.createSubmarineInterior();
        this.createPorthole();
        this.createSmallPorthole();  // Small porthole near control panel
        this.createGauges();  // Radiation gauge and time remaining display
        this.createControlPanel();
        this.createIntercom();
        this.setupLights();

        // Handle window resize
        window.addEventListener('resize', () => this.onWindowResize());
    }

    createSubmarineInterior() {
        // Cylindrical walls
        const wallGeometry = new THREE.CylinderGeometry(3, 3, 4, 16, 1, true);
        const wallMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a3a4a,
            roughness: 0.9,
            metalness: 0.7,
            side: THREE.BackSide,
        });
        const walls = new THREE.Mesh(wallGeometry, wallMaterial);
        walls.position.y = 2;
        this.scene.add(walls);

        // Floor
        const floorGeometry = new THREE.CylinderGeometry(3, 3, 0.2, 16);
        const floorMaterial = new THREE.MeshStandardMaterial({
            color: 0x1a2a3a,
            roughness: 0.95,
            metalness: 0.5,
        });
        const floor = new THREE.Mesh(floorGeometry, floorMaterial);
        floor.position.y = 0;
        this.scene.add(floor);

        // Ceiling
        const ceiling = new THREE.Mesh(floorGeometry, floorMaterial);
        ceiling.position.y = 4;
        this.scene.add(ceiling);

        // Pipes along walls
        for (let i = 0; i < 8; i++) {
            const angle = (i / 8) * Math.PI * 2;
            const pipeGeometry = new THREE.CylinderGeometry(0.05, 0.05, 3.5, 8);
            const pipeMaterial = new THREE.MeshStandardMaterial({
                color: 0x4a5a6a,
                roughness: 0.7,
                metalness: 0.8,
            });
            const pipe = new THREE.Mesh(pipeGeometry, pipeMaterial);
            pipe.position.x = Math.cos(angle) * 2.8;
            pipe.position.z = Math.sin(angle) * 2.8;
            pipe.position.y = 2;
            this.scene.add(pipe);
        }

        // Rivets on walls
        for (let i = 0; i < 24; i++) {
            const angle = (i / 24) * Math.PI * 2;
            const rivetGeometry = new THREE.SphereGeometry(0.03, 8, 8);
            const rivetMaterial = new THREE.MeshStandardMaterial({
                color: 0x3a4a5a,
                roughness: 0.6,
                metalness: 0.9,
            });
            const rivet = new THREE.Mesh(rivetGeometry, rivetMaterial);
            rivet.position.x = Math.cos(angle) * 2.95;
            rivet.position.z = Math.sin(angle) * 2.95;
            rivet.position.y = 1 + Math.random() * 2;
            this.scene.add(rivet);
        }
    }

    createPorthole() {
        // Porthole frame
        const frameGeometry = new THREE.TorusGeometry(0.4, 0.08, 16, 32);
        const frameMaterial = new THREE.MeshStandardMaterial({
            color: 0x6a7a8a,
            roughness: 0.3,
            metalness: 0.9,
        });
        const frame = new THREE.Mesh(frameGeometry, frameMaterial);
        frame.position.set(-2, 1.8, 1);
        frame.rotation.y = Math.PI / 2;
        this.scene.add(frame);

        // Glass with underwater view
        const glassGeometry = new THREE.CircleGeometry(0.4, 32);
        const glassMaterial = new THREE.MeshPhysicalMaterial({
            color: 0x1a3a5a,
            transparent: true,
            opacity: 0.7,
            roughness: 0.1,
            metalness: 0.1,
            transmission: 0.9,
        });
        const glass = new THREE.Mesh(glassGeometry, glassMaterial);
        glass.position.set(-2.95, 1.8, 1);
        glass.rotation.y = Math.PI / 2;
        this.scene.add(glass);

        // Underwater effect - particles visible through porthole
        const particlesGeometry = new THREE.BufferGeometry();
        const particlesCount = 50; // Reduced from 200 for performance
        const positions = new Float32Array(particlesCount * 3);

        for (let i = 0; i < particlesCount * 3; i += 3) {
            positions[i] = -3 - Math.random() * 2;
            positions[i + 1] = Math.random() * 4;
            positions[i + 2] = 1 + (Math.random() - 0.5) * 2;
        }

        particlesGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const particlesMaterial = new THREE.PointsMaterial({
            color: 0x4a7a9a,
            size: 0.02,
            transparent: true,
            opacity: 0.6,
        });

        this.underwaterParticles = new THREE.Points(particlesGeometry, particlesMaterial);
        this.scene.add(this.underwaterParticles);
    }

    createSmallPorthole() {
        // Small porthole near control panel - player can see blue water and bubbles
        const size = 0.25;  // Smaller than main porthole

        // Porthole frame
        const frameGeometry = new THREE.TorusGeometry(size, 0.05, 12, 24);
        const frameMaterial = new THREE.MeshStandardMaterial({
            color: 0x6a7a8a,
            roughness: 0.3,
            metalness: 0.9,
        });
        const frame = new THREE.Mesh(frameGeometry, frameMaterial);
        frame.position.set(-1.8, 1.8, -2.6);  // Left side, away from control panel
        frame.rotation.y = 0;
        this.scene.add(frame);

        // Glass with deep blue underwater view
        const glassGeometry = new THREE.CircleGeometry(size, 24);
        const glassMaterial = new THREE.MeshPhysicalMaterial({
            color: 0x1a4a7a,  // Deeper blue
            transparent: true,
            opacity: 0.8,
            roughness: 0.1,
            metalness: 0.1,
            transmission: 0.85,
        });
        const glass = new THREE.Mesh(glassGeometry, glassMaterial);
        glass.position.set(-1.8, 1.8, -2.65);
        this.scene.add(glass);

        // Bubbles visible through small porthole
        const bubbleGeometry = new THREE.BufferGeometry();
        const bubbleCount = 20; // Reduced from 50 for performance
        const bubblePositions = new Float32Array(bubbleCount * 3);

        for (let i = 0; i < bubbleCount * 3; i += 3) {
            bubblePositions[i] = -1.8 + (Math.random() - 0.5) * 0.8;     // Near porthole (left side)
            bubblePositions[i + 1] = 1 + Math.random() * 3;               // Rising up
            bubblePositions[i + 2] = -2.7 - Math.random() * 1;            // Outside window
        }

        bubbleGeometry.setAttribute('position', new THREE.BufferAttribute(bubblePositions, 3));

        const bubbleMaterial = new THREE.PointsMaterial({
            color: 0x7aaadd,
            size: 0.03,
            transparent: true,
            opacity: 0.7,
        });

        this.smallPortholeParticles = new THREE.Points(bubbleGeometry, bubbleMaterial);
        this.scene.add(this.smallPortholeParticles);
    }

    createGauges() {
        // === RADIATION GAUGE (LEFT) ===
        // Panel background
        const radPanelGeometry = new THREE.BoxGeometry(0.7, 0.5, 0.1);
        const radPanelMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a2a2a,
            roughness: 0.7,
            metalness: 0.3,
        });
        const radPanel = new THREE.Mesh(radPanelGeometry, radPanelMaterial);
        radPanel.position.set(-0.6, 2.5, -2.8);
        this.scene.add(radPanel);

        // Display screen
        const radDisplayGeometry = new THREE.PlaneGeometry(0.55, 0.3);
        const radDisplayMaterial = new THREE.MeshBasicMaterial({
            color: 0x0a0a0a,
        });
        const radDisplay = new THREE.Mesh(radDisplayGeometry, radDisplayMaterial);
        radDisplay.position.set(-0.6, 2.5, -2.75);
        this.scene.add(radDisplay);

        // Radiation text (will be updated in animate)
        const radCanvas = document.createElement('canvas');
        radCanvas.width = 256;
        radCanvas.height = 128;
        const radContext = radCanvas.getContext('2d');
        radContext.fillStyle = '#ff3333';
        radContext.font = 'bold 48px monospace';
        radContext.textAlign = 'center';
        radContext.textBaseline = 'middle';
        radContext.fillText('0%', 128, 64);

        const radTexture = new THREE.CanvasTexture(radCanvas);
        const radTextMaterial = new THREE.MeshBasicMaterial({
            map: radTexture,
            transparent: true,
        });
        const radTextMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 0.25), radTextMaterial);
        radTextMesh.position.set(-0.6, 2.5, -2.74);
        this.scene.add(radTextMesh);

        this.radiationText = { canvas: radCanvas, context: radContext, texture: radTexture, mesh: radTextMesh };

        // Radiation label
        const radLabelCanvas = document.createElement('canvas');
        radLabelCanvas.width = 256;
        radLabelCanvas.height = 64;
        const radLabelContext = radLabelCanvas.getContext('2d');
        radLabelContext.fillStyle = '#ffffff';
        radLabelContext.font = 'bold 20px monospace';
        radLabelContext.textAlign = 'center';
        radLabelContext.fillText('RADIATION', 128, 32);

        const radLabelTexture = new THREE.CanvasTexture(radLabelCanvas);
        const radLabelMaterial = new THREE.MeshBasicMaterial({
            map: radLabelTexture,
            transparent: true,
        });
        const radLabelMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 0.1), radLabelMaterial);
        radLabelMesh.position.set(-0.6, 2.75, -2.74);
        this.scene.add(radLabelMesh);

        // === TIME REMAINING GAUGE (RIGHT) ===
        // Panel background
        const timePanelGeometry = new THREE.BoxGeometry(0.7, 0.5, 0.1);
        const timePanelMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a2a2a,
            roughness: 0.7,
            metalness: 0.3,
        });
        const timePanel = new THREE.Mesh(timePanelGeometry, timePanelMaterial);
        timePanel.position.set(0.6, 2.5, -2.8);
        this.scene.add(timePanel);

        // Display screen
        const timeDisplayGeometry = new THREE.PlaneGeometry(0.55, 0.3);
        const timeDisplayMaterial = new THREE.MeshBasicMaterial({
            color: 0x0a0a0a,
        });
        const timeDisplay = new THREE.Mesh(timeDisplayGeometry, timeDisplayMaterial);
        timeDisplay.position.set(0.6, 2.5, -2.75);
        this.scene.add(timeDisplay);

        // Time text (will be updated in animate)
        const timeCanvas = document.createElement('canvas');
        timeCanvas.width = 256;
        timeCanvas.height = 128;
        const timeContext = timeCanvas.getContext('2d');
        timeContext.fillStyle = '#ffaa33';
        timeContext.font = 'bold 48px monospace';
        timeContext.textAlign = 'center';
        timeContext.textBaseline = 'middle';
        timeContext.fillText('08:00', 128, 64);

        const timeTexture = new THREE.CanvasTexture(timeCanvas);
        const timeTextMaterial = new THREE.MeshBasicMaterial({
            map: timeTexture,
            transparent: true,
        });
        const timeTextMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 0.25), timeTextMaterial);
        timeTextMesh.position.set(0.6, 2.5, -2.74);
        this.scene.add(timeTextMesh);

        this.timeText = { canvas: timeCanvas, context: timeContext, texture: timeTexture, mesh: timeTextMesh };

        // Time label
        const timeLabelCanvas = document.createElement('canvas');
        timeLabelCanvas.width = 256;
        timeLabelCanvas.height = 64;
        const timeLabelContext = timeLabelCanvas.getContext('2d');
        timeLabelContext.fillStyle = '#ffffff';
        timeLabelContext.font = 'bold 20px monospace';
        timeLabelContext.textAlign = 'center';
        timeLabelContext.fillText('TIME LEFT', 128, 32);

        const timeLabelTexture = new THREE.CanvasTexture(timeLabelCanvas);
        const timeLabelMaterial = new THREE.MeshBasicMaterial({
            map: timeLabelTexture,
            transparent: true,
        });
        const timeLabelMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 0.1), timeLabelMaterial);
        timeLabelMesh.position.set(0.6, 2.75, -2.74);
        this.scene.add(timeLabelMesh);

        // === PRESSURE GAUGE (CENTER) ===
        // Panel background
        const pressurePanelGeometry = new THREE.BoxGeometry(0.7, 0.5, 0.1);
        const pressurePanelMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a2a2a,
            roughness: 0.7,
            metalness: 0.3,
        });
        const pressurePanel = new THREE.Mesh(pressurePanelGeometry, pressurePanelMaterial);
        pressurePanel.position.set(0.0, 2.0, -2.8);
        this.scene.add(pressurePanel);

        // Display screen
        const pressureDisplayGeometry = new THREE.PlaneGeometry(0.55, 0.3);
        const pressureDisplayMaterial = new THREE.MeshBasicMaterial({
            color: 0x0a0a0a,
        });
        const pressureDisplay = new THREE.Mesh(pressureDisplayGeometry, pressureDisplayMaterial);
        pressureDisplay.position.set(0.0, 2.0, -2.75);
        this.scene.add(pressureDisplay);

        // Pressure text (will be updated in animate)
        const pressureCanvas = document.createElement('canvas');
        pressureCanvas.width = 256;
        pressureCanvas.height = 128;
        const pressureContext = pressureCanvas.getContext('2d');
        pressureContext.fillStyle = '#33ccff';
        pressureContext.font = 'bold 40px monospace';
        pressureContext.textAlign = 'center';
        pressureContext.textBaseline = 'middle';
        pressureContext.fillText('2400ft', 128, 64);

        const pressureTexture = new THREE.CanvasTexture(pressureCanvas);
        const pressureTextMaterial = new THREE.MeshBasicMaterial({
            map: pressureTexture,
            transparent: true,
        });
        const pressureTextMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 0.25), pressureTextMaterial);
        pressureTextMesh.position.set(0.0, 2.0, -2.74);
        this.scene.add(pressureTextMesh);

        this.pressureText = { canvas: pressureCanvas, context: pressureContext, texture: pressureTexture, mesh: pressureTextMesh };

        // Pressure label
        const pressureLabelCanvas = document.createElement('canvas');
        pressureLabelCanvas.width = 256;
        pressureLabelCanvas.height = 64;
        const pressureLabelContext = pressureLabelCanvas.getContext('2d');
        pressureLabelContext.fillStyle = '#ffffff';
        pressureLabelContext.font = 'bold 20px monospace';
        pressureLabelContext.textAlign = 'center';
        pressureLabelContext.fillText('DEPTH', 128, 32);

        const pressureLabelTexture = new THREE.CanvasTexture(pressureLabelCanvas);
        const pressureLabelMaterial = new THREE.MeshBasicMaterial({
            map: pressureLabelTexture,
            transparent: true,
        });
        const pressureLabelMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 0.1), pressureLabelMaterial);
        pressureLabelMesh.position.set(0.0, 2.25, -2.74);
        this.scene.add(pressureLabelMesh);

        // === SYSTEMS REPAIRED COUNTER (BOTTOM LEFT) ===
        // Panel background
        const systemsPanelGeometry = new THREE.BoxGeometry(0.5, 0.35, 0.1);
        const systemsPanelMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a2a2a,
            roughness: 0.7,
            metalness: 0.3,
        });
        const systemsPanel = new THREE.Mesh(systemsPanelGeometry, systemsPanelMaterial);
        systemsPanel.position.set(-0.9, 1.5, -2.8);
        this.scene.add(systemsPanel);

        // Display screen
        const systemsDisplayGeometry = new THREE.PlaneGeometry(0.4, 0.2);
        const systemsDisplayMaterial = new THREE.MeshBasicMaterial({
            color: 0x0a0a0a,
        });
        const systemsDisplay = new THREE.Mesh(systemsDisplayGeometry, systemsDisplayMaterial);
        systemsDisplay.position.set(-0.9, 1.5, -2.75);
        this.scene.add(systemsDisplay);

        // Systems text
        const systemsCanvas = document.createElement('canvas');
        systemsCanvas.width = 256;
        systemsCanvas.height = 128;
        const systemsContext = systemsCanvas.getContext('2d');
        systemsContext.fillStyle = '#33ff99';
        systemsContext.font = 'bold 52px monospace';
        systemsContext.textAlign = 'center';
        systemsContext.textBaseline = 'middle';
        systemsContext.fillText('0/4', 128, 64);

        const systemsTexture = new THREE.CanvasTexture(systemsCanvas);
        const systemsTextMaterial = new THREE.MeshBasicMaterial({
            map: systemsTexture,
            transparent: true,
        });
        const systemsTextMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.35, 0.18), systemsTextMaterial);
        systemsTextMesh.position.set(-0.9, 1.5, -2.74);
        this.scene.add(systemsTextMesh);

        this.systemsText = { canvas: systemsCanvas, context: systemsContext, texture: systemsTexture, mesh: systemsTextMesh };

        // Systems label
        const systemsLabelCanvas = document.createElement('canvas');
        systemsLabelCanvas.width = 256;
        systemsLabelCanvas.height = 64;
        const systemsLabelContext = systemsLabelCanvas.getContext('2d');
        systemsLabelContext.fillStyle = '#ffffff';
        systemsLabelContext.font = 'bold 16px monospace';
        systemsLabelContext.textAlign = 'center';
        systemsLabelContext.fillText('SYSTEMS', 128, 32);

        const systemsLabelTexture = new THREE.CanvasTexture(systemsLabelCanvas);
        const systemsLabelMaterial = new THREE.MeshBasicMaterial({
            map: systemsLabelTexture,
            transparent: true,
        });
        const systemsLabelMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.4, 0.08), systemsLabelMaterial);
        systemsLabelMesh.position.set(-0.9, 1.68, -2.74);
        this.scene.add(systemsLabelMesh);

        // === PHASE INDICATOR (BOTTOM RIGHT) ===
        // Panel background
        const phasePanelGeometry = new THREE.BoxGeometry(0.5, 0.35, 0.1);
        const phasePanelMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a2a2a,
            roughness: 0.7,
            metalness: 0.3,
        });
        const phasePanel = new THREE.Mesh(phasePanelGeometry, phasePanelMaterial);
        phasePanel.position.set(0.9, 1.5, -2.8);
        this.scene.add(phasePanel);

        // Display screen
        const phaseDisplayGeometry = new THREE.PlaneGeometry(0.4, 0.2);
        const phaseDisplayMaterial = new THREE.MeshBasicMaterial({
            color: 0x0a0a0a,
        });
        const phaseDisplay = new THREE.Mesh(phaseDisplayGeometry, phaseDisplayMaterial);
        phaseDisplay.position.set(0.9, 1.5, -2.75);
        this.scene.add(phaseDisplay);

        // Phase text
        const phaseCanvas = document.createElement('canvas');
        phaseCanvas.width = 256;
        phaseCanvas.height = 128;
        const phaseContext = phaseCanvas.getContext('2d');
        phaseContext.fillStyle = '#9999ff';
        phaseContext.font = 'bold 56px monospace';
        phaseContext.textAlign = 'center';
        phaseContext.textBaseline = 'middle';
        phaseContext.fillText('1', 128, 64);

        const phaseTexture = new THREE.CanvasTexture(phaseCanvas);
        const phaseTextMaterial = new THREE.MeshBasicMaterial({
            map: phaseTexture,
            transparent: true,
        });
        const phaseTextMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.35, 0.18), phaseTextMaterial);
        phaseTextMesh.position.set(0.9, 1.5, -2.74);
        this.scene.add(phaseTextMesh);

        this.phaseText = { canvas: phaseCanvas, context: phaseContext, texture: phaseTexture, mesh: phaseTextMesh };

        // Phase label
        const phaseLabelCanvas = document.createElement('canvas');
        phaseLabelCanvas.width = 256;
        phaseLabelCanvas.height = 64;
        const phaseLabelContext = phaseLabelCanvas.getContext('2d');
        phaseLabelContext.fillStyle = '#ffffff';
        phaseLabelContext.font = 'bold 16px monospace';
        phaseLabelContext.textAlign = 'center';
        phaseLabelContext.fillText('PHASE', 128, 32);

        const phaseLabelTexture = new THREE.CanvasTexture(phaseLabelCanvas);
        const phaseLabelMaterial = new THREE.MeshBasicMaterial({
            map: phaseLabelTexture,
            transparent: true,
        });
        const phaseLabelMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.4, 0.08), phaseLabelMaterial);
        phaseLabelMesh.position.set(0.9, 1.68, -2.74);
        this.scene.add(phaseLabelMesh);
    }

    createControlPanel() {
        // Main control panel - CENTERED in view
        const panelGeometry = new THREE.BoxGeometry(1.5, 0.8, 0.15);
        const panelMaterial = new THREE.MeshStandardMaterial({
            color: 0x3a3a3a,
            roughness: 0.6,
            metalness: 0.4,
        });
        const panel = new THREE.Mesh(panelGeometry, panelMaterial);
        panel.position.set(0, 1.3, -2.7);  // Centered at x=0, lowered slightly
        this.scene.add(panel);

        // Create buttons - positions relative to panel center (0, 1.3)
        // Spread out more for better clickability
        const buttonPositions = [
            { x: -0.5, y: 0.25, label: 'O2 VALVE', color: 0xff3333 },
            { x: 0.5, y: 0.25, label: 'VENT', color: 0xffaa33 },
            { x: -0.5, y: -0.15, label: 'BALLAST', color: 0x3399ff },
            { x: 0.5, y: -0.15, label: 'POWER', color: 0x33ff33 },
            { x: 0.0, y: -0.55, label: 'CRANK', color: 0xaaaaaa },  // Gray crank at bottom center, lower
            { x: 0.0, y: 0.6, label: 'FLOOD MED BAY', color: 0xff0000, visibleInPhases: [3, 4] },  // Critical decision, only visible in Phase 3+
        ];

        // Store reference to phase-dependent buttons for visibility toggling
        this.phaseButtons = [];

        buttonPositions.forEach(pos => {
            const buttonGeometry = new THREE.CylinderGeometry(0.12, 0.12, 0.08, 16);  // Larger buttons for easier clicking
            const buttonMaterial = new THREE.MeshStandardMaterial({
                color: pos.color,
                roughness: 0.3,
                metalness: 0.7,
                emissive: pos.color,
                emissiveIntensity: 0.4,
            });
            const button = new THREE.Mesh(buttonGeometry, buttonMaterial);
            button.position.set(pos.x, 1.3 + pos.y, -2.62);  // Centered panel
            button.rotation.x = Math.PI / 2;
            button.userData = {
                type: 'button',
                action: pos.label,
                originalColor: pos.color,
                visibleInPhases: pos.visibleInPhases || null  // null means always visible
            };

            // Button label
            const labelCanvas = document.createElement('canvas');
            labelCanvas.width = 256;
            labelCanvas.height = 64;
            const ctx = labelCanvas.getContext('2d');
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 24px monospace';
            ctx.textAlign = 'center';
            ctx.fillText(pos.label, 128, 40);

            const labelTexture = new THREE.CanvasTexture(labelCanvas);
            const labelMaterial = new THREE.MeshBasicMaterial({
                map: labelTexture,
                transparent: true,
            });
            const label = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 0.12), labelMaterial);
            label.position.set(pos.x, 1.3 + pos.y - 0.18, -2.62);  // Below button

            // Track button and label together
            if (pos.visibleInPhases) {
                // Initially hide phase-dependent buttons
                button.visible = false;
                label.visible = false;
                this.phaseButtons.push({ button, label, phases: pos.visibleInPhases });
            }

            this.scene.add(button);
            this.scene.add(label);
            this.interactiveObjects.push(button);
        });
    }

    createIntercom() {
        // Intercom box
        const intercomGeometry = new THREE.BoxGeometry(0.4, 0.3, 0.1);
        const intercomMaterial = new THREE.MeshStandardMaterial({
            color: 0x4a4a4a,
            roughness: 0.5,
            metalness: 0.6,
        });
        const intercom = new THREE.Mesh(intercomGeometry, intercomMaterial);
        intercom.position.set(-1.5, 2.2, -2.7);
        this.scene.add(intercom);

        // Speaker grille
        const grilleGeometry = new THREE.PlaneGeometry(0.3, 0.2);
        const grilleMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a2a2a,
            roughness: 0.9,
        });
        const grille = new THREE.Mesh(grilleGeometry, grilleMaterial);
        grille.position.set(-1.5, 2.2, -2.65);
        this.scene.add(grille);

        // Intercom label
        const labelCanvas = document.createElement('canvas');
        labelCanvas.width = 128;
        labelCanvas.height = 32;
        const ctx = labelCanvas.getContext('2d');
        ctx.fillStyle = '#00ff00';
        ctx.font = 'bold 16px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('INTERCOM', 64, 20);

        const labelTexture = new THREE.CanvasTexture(labelCanvas);
        const labelMaterial = new THREE.MeshBasicMaterial({
            map: labelTexture,
            transparent: true,
        });
        const label = new THREE.Mesh(new THREE.PlaneGeometry(0.25, 0.06), labelMaterial);
        label.position.set(-1.5, 2.38, -2.65);
        this.scene.add(label);

        // Status light
        const lightGeometry = new THREE.SphereGeometry(0.03, 16, 16);
        const lightMaterial = new THREE.MeshBasicMaterial({
            color: 0x00ff00,
            emissive: 0x00ff00,
        });
        const statusLight = new THREE.Mesh(lightGeometry, lightMaterial);
        statusLight.position.set(-1.3, 2.35, -2.65);
        this.scene.add(statusLight);
        this.warningLights.push(statusLight);
    }

    setupLights() {
        // Ambient light for submarine atmosphere - increased by 30%
        const ambientLight = new THREE.AmbientLight(0x405060, 1.04);
        this.scene.add(ambientLight);

        // Warning lights (red, flickering) - increased by 30%
        for (let i = 0; i < 2; i++) {
            const angle = (i / 2) * Math.PI * 2;
            const warningLight = new THREE.PointLight(0xff3333, 0.78, 6);
            warningLight.position.x = Math.cos(angle) * 2;
            warningLight.position.z = Math.sin(angle) * 2;
            warningLight.position.y = 3.5;
            this.scene.add(warningLight);
            this.warningLights.push(warningLight);
        }

        // Main overhead light (bright, cold white) - increased by 30%
        const mainLight = new THREE.PointLight(0x8ab0c0, 1.95, 15);
        mainLight.position.set(0, 3.5, 0);
        this.scene.add(mainLight);

        // Interior cabin light near control panel - increased by 30%
        const interiorLight = new THREE.PointLight(0xa0b5c0, 1.56, 8);
        interiorLight.position.set(0, 2.2, -1.5); // Near control panel
        this.scene.add(interiorLight);

        // Emergency red light - starts OFF, activated when radiation >= 75%
        this.emergencyLight = new THREE.PointLight(0xff0000, 0, 12);
        this.emergencyLight.position.set(0, 3.2, -1);
        this.scene.add(this.emergencyLight);

        // Emergency light fixture (visible red dome)
        const emergencyDomeGeometry = new THREE.SphereGeometry(0.12, 16, 16, 0, Math.PI * 2, 0, Math.PI / 2);
        this.emergencyDomeMaterial = new THREE.MeshBasicMaterial({
            color: 0x330000,  // Dark red when off
            transparent: true,
            opacity: 0.8,
        });
        const emergencyDome = new THREE.Mesh(emergencyDomeGeometry, this.emergencyDomeMaterial);
        emergencyDome.position.set(0, 3.4, -1);
        emergencyDome.rotation.x = Math.PI;  // Dome facing down
        this.scene.add(emergencyDome);

        // Total lights: 5 (ambient + 2 warning + 1 main + 1 interior + 1 emergency)
    }

    setupInteraction() {
        window.addEventListener('mousemove', (event) => {
            this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
            this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
            this.mouseNeedsUpdate = true; // Flag that mouse moved for raycast optimization
        });

        window.addEventListener('click', () => {
            if (this.hoveredObject) {
                // Debounce button clicks to prevent rapid double-clicks
                const now = Date.now();
                if (now - this.lastButtonClick < this.buttonDebounceMs) {
                    console.log('Button click ignored (debounced)');
                    return;
                }
                this.lastButtonClick = now;

                console.log('Button clicked:', this.hoveredObject.userData.action);

                // Play click sound
                this.playSoundEffect('click');

                // Flash button and notify callback
                this.flashButton(this.hoveredObject);
                this.onButtonClick(this.hoveredObject.userData.action);
            }
        });
    }

    flashButton(button) {
        const originalEmissive = button.material.emissiveIntensity;
        button.material.emissiveIntensity = 1.0;
        setTimeout(() => {
            button.material.emissiveIntensity = originalEmissive;
        }, 200);
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        // Framerate limiting for better input responsiveness
        const currentTime = Date.now();
        const deltaTime = currentTime - this.lastFrameTime;

        if (deltaTime < this.frameInterval) {
            return; // Skip this frame to maintain target FPS
        }

        this.lastFrameTime = currentTime - (deltaTime % this.frameInterval);

        const time = currentTime * 0.001;
        this.frameCount++;

        // NOTE: Radiation and time are now handled server-side
        // The setRadiationLevel() and setTimeRemaining() methods receive updates from the server

        // Update radiation gauge every 10 frames for smoother display
        if (this.radiationText && this.frameCount % 10 === 0) {
            const radPercent = Math.round(this.radiationLevel);
            const display = `${radPercent}%`;

            const { context, texture, canvas } = this.radiationText;
            context.clearRect(0, 0, canvas.width, canvas.height);
            // Color changes based on danger level
            if (radPercent >= 75) {
                context.fillStyle = '#ff0000';  // Bright red at critical levels
            } else if (radPercent >= 50) {
                context.fillStyle = '#ff3333';  // Red-orange at high levels
            } else {
                context.fillStyle = '#ff6633';  // Orange at moderate levels
            }
            context.font = 'bold 48px monospace';
            context.textAlign = 'center';
            context.textBaseline = 'middle';
            context.fillText(display, 128, 64);
            texture.needsUpdate = true;
        }

        // Update time remaining gauge every 10 frames
        if (this.timeText && this.frameCount % 10 === 0) {
            const minutes = Math.floor(this.timeRemaining / 60);
            const seconds = Math.floor(this.timeRemaining % 60);
            const display = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

            const { context, texture, canvas } = this.timeText;
            context.clearRect(0, 0, canvas.width, canvas.height);
            // Color changes based on urgency
            if (this.timeRemaining < 60) {
                context.fillStyle = '#ff0000';  // Red when less than 1 minute
            } else if (this.timeRemaining < 120) {
                context.fillStyle = '#ff6633';  // Orange when less than 2 minutes
            } else {
                context.fillStyle = '#ffaa33';  // Yellow-orange normally
            }
            context.font = 'bold 48px monospace';
            context.textAlign = 'center';
            context.textBaseline = 'middle';
            context.fillText(display, 128, 64);
            texture.needsUpdate = true;
        }

        // Update pressure gauge every 10 frames
        if (this.pressureText && this.frameCount % 10 === 0) {
            const depthFeet = Math.round(this.hullPressure);
            const display = `${depthFeet}ft`;

            const { context, texture, canvas } = this.pressureText;
            context.clearRect(0, 0, canvas.width, canvas.height);
            // Color changes based on depth (deeper = more danger)
            if (depthFeet > 2600) {
                context.fillStyle = '#ff3333';  // Red when very deep
            } else if (depthFeet > 2400) {
                context.fillStyle = '#ffaa33';  // Orange when deep
            } else {
                context.fillStyle = '#33ccff';  // Cyan normally
            }
            context.font = 'bold 40px monospace';
            context.textAlign = 'center';
            context.textBaseline = 'middle';
            context.fillText(display, 128, 64);
            texture.needsUpdate = true;
        }

        // Update systems repaired counter every 10 frames
        if (this.systemsText && this.frameCount % 10 === 0) {
            const systems = Math.round(this.systemsRepaired);
            const display = `${systems}/4`;

            const { context, texture, canvas } = this.systemsText;
            context.clearRect(0, 0, canvas.width, canvas.height);
            // Color changes based on progress
            if (systems >= 3) {
                context.fillStyle = '#33ff99';  // Bright green when 3+ systems repaired
            } else if (systems >= 2) {
                context.fillStyle = '#99ff66';  // Yellow-green at 2 systems
            } else if (systems >= 1) {
                context.fillStyle = '#ffcc33';  // Orange at 1 system
            } else {
                context.fillStyle = '#ff6633';  // Red-orange at 0 systems
            }
            context.font = 'bold 52px monospace';
            context.textAlign = 'center';
            context.textBaseline = 'middle';
            context.fillText(display, 128, 64);
            texture.needsUpdate = true;
        }

        // Update phase indicator every 10 frames
        if (this.phaseText && this.frameCount % 10 === 0) {
            const phaseNum = Math.round(this.phase);
            const display = `${phaseNum}`;

            const { context, texture, canvas } = this.phaseText;
            context.clearRect(0, 0, canvas.width, canvas.height);
            // Color changes based on phase intensity
            if (phaseNum === 4) {
                context.fillStyle = '#ff6699';  // Pink/red for final phase (The Choice)
            } else if (phaseNum === 3) {
                context.fillStyle = '#ff9966';  // Orange for Phase 3 (The Revelation)
            } else if (phaseNum === 2) {
                context.fillStyle = '#99ccff';  // Light blue for Phase 2 (Working Relationship)
            } else {
                context.fillStyle = '#9999ff';  // Purple for Phase 1 (Impact & Connection)
            }
            context.font = 'bold 56px monospace';
            context.textAlign = 'center';
            context.textBaseline = 'middle';
            context.fillText(display, 128, 64);
            texture.needsUpdate = true;
        }

        // Flicker warning lights - throttled to every 3 frames for performance
        if (this.frameCount % 3 === 0) {
            this.warningLights.forEach((light, i) => {
                if (light.isPointLight) {
                    light.intensity = 0.3 + Math.sin(time * 3 + i) * 0.2 + Math.random() * 0.1;
                }
            });
        }

        // Pulse emergency light when active (radiation >= 75%)
        if (this.emergencyLightOn && this.emergencyLight) {
            // Pulsing red light effect - rapid flash
            const pulse = Math.sin(time * 8) * 0.5 + 0.5;  // 0-1 pulsing
            this.emergencyLight.intensity = 1.5 + pulse * 1.5;  // 1.5 to 3.0 intensity

            // Update dome color to glow bright red
            if (this.emergencyDomeMaterial) {
                const brightness = Math.floor(pulse * 255);
                this.emergencyDomeMaterial.color.setRGB(1, brightness / 255 * 0.2, 0);
                this.emergencyDomeMaterial.emissive = this.emergencyDomeMaterial.color;
            }
        }

        // Animate underwater particles - throttled to every 5 frames for performance
        if (this.underwaterParticles && this.frameCount % 5 === 0) {
            const positions = this.underwaterParticles.geometry.attributes.position.array;
            for (let i = 0; i < positions.length; i += 3) {
                positions[i + 1] += Math.sin(time + i) * 0.005; // Increased increment since updating less frequently
            }
            this.underwaterParticles.geometry.attributes.position.needsUpdate = true;
        }

        // Animate bubbles in small porthole - throttled to every 5 frames for performance
        if (this.smallPortholeParticles && this.frameCount % 5 === 0) {
            const positions = this.smallPortholeParticles.geometry.attributes.position.array;
            for (let i = 0; i < positions.length; i += 3) {
                // Bubbles rise slowly
                positions[i + 1] += 0.01; // Increased increment since updating less frequently

                // Reset bubble to bottom when it reaches top
                if (positions[i + 1] > 4) {
                    positions[i + 1] = 1;
                }

                // Slight horizontal wobble
                positions[i] += Math.sin(time * 2 + i) * 0.0025; // Increased increment
            }
            this.smallPortholeParticles.geometry.attributes.position.needsUpdate = true;
        }

        // Check for button hover - only raycast when mouse has moved for performance
        if (this.mouseNeedsUpdate) {
            this.raycaster.setFromCamera(this.mouse, this.camera);
            const intersects = this.raycaster.intersectObjects(this.interactiveObjects);

            // Reset previous hover
            if (this.hoveredObject) {
                this.hoveredObject.material.emissiveIntensity = 0.3;
                document.body.style.cursor = 'default';
            }

            // Set new hover
            if (intersects.length > 0) {
                this.hoveredObject = intersects[0].object;
                this.hoveredObject.material.emissiveIntensity = 0.8;  // Brighter hover
                document.body.style.cursor = 'pointer';
                console.log('[HOVER] Button:', this.hoveredObject.userData.action);  // Debug which button you're hovering
            } else {
                this.hoveredObject = null;
            }

            this.mouseNeedsUpdate = false; // Reset flag
        }

        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    onWindowResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    // Method to update radiation level externally
    setRadiationLevel(percentage) {
        const previousLevel = this.radiationLevel;
        this.radiationLevel = percentage;

        // Trigger emergency mode when radiation reaches critical level (75%+)
        if (percentage >= 75 && previousLevel < 75) {
            this.activateEmergencyMode();
        }

        // Deactivate if radiation drops back below 75 (unlikely but possible)
        if (percentage < 75 && previousLevel >= 75) {
            this.deactivateEmergencyMode();
        }
    }

    // Method to update time remaining externally
    setTimeRemaining(seconds) {
        this.timeRemaining = seconds;
    }

    // Method to update hull pressure/depth externally
    setHullPressure(depth) {
        this.hullPressure = depth;
    }

    // Method to update systems repaired counter externally
    setSystemsRepaired(count) {
        this.systemsRepaired = count;
    }

    // Method to update phase externally
    setPhase(phase) {
        const previousPhase = this.phase;
        this.phase = phase;

        // Update visibility of phase-dependent buttons
        if (previousPhase !== phase) {
            this.phaseButtons.forEach(({ button, label, phases }) => {
                const shouldBeVisible = phases.includes(phase);
                button.visible = shouldBeVisible;
                label.visible = shouldBeVisible;

                if (shouldBeVisible && !phases.includes(previousPhase)) {
                    // Button just became visible - log it
                    console.log(`[PHASE ${phase}] New control available: ${button.userData.action}`);
                }
            });
        }
    }

    activateEmergencyMode() {
        console.log('[EMERGENCY] Radiation critical - activating emergency systems!');

        // Turn on emergency red light
        this.emergencyLightOn = true;
        if (this.emergencyDomeMaterial) {
            this.emergencyDomeMaterial.color.setHex(0xff0000);
        }

        // Start alarm sound
        this.startAlarm();
    }

    deactivateEmergencyMode() {
        console.log('[EMERGENCY] Radiation levels lowered - deactivating emergency systems');

        // Turn off emergency light
        this.emergencyLightOn = false;
        if (this.emergencyLight) {
            this.emergencyLight.intensity = 0;
        }
        if (this.emergencyDomeMaterial) {
            this.emergencyDomeMaterial.color.setHex(0x330000);
        }

        // Stop alarm
        this.stopAlarm();
    }

    // Method to add visual feedback for events
    triggerAlert(type) {
        // Could add screen shake, color flash, etc.
        console.log('Alert triggered:', type);
    }

    /**
     * Clean up all resources. Called when switching scenes.
     */
    dispose() {
        console.log('[SUBMARINE] Disposing scene...');

        // Stop alarm
        this.stopAlarm();

        // Close audio context
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        // Dispose Three.js renderer
        if (this.renderer) {
            this.renderer.dispose();
            if (this.renderer.domElement && this.renderer.domElement.parentNode) {
                this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
            }
        }

        // Dispose geometries and materials
        if (this.scene) {
            this.scene.traverse((object) => {
                if (object.geometry) object.geometry.dispose();
                if (object.material) {
                    if (Array.isArray(object.material)) {
                        object.material.forEach(m => m.dispose());
                    } else {
                        object.material.dispose();
                    }
                }
            });
        }

        // Clear references
        this.interactiveObjects = [];
        this.warningLights = [];
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;

        console.log('[SUBMARINE] Scene disposed');
    }

    /**
     * Alias for dispose()
     */
    destroy() {
        this.dispose();
    }
}
