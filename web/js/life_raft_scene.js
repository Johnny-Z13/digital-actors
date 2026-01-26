import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export class LifeRaftScene {
    constructor(container, onButtonClick) {
        this.container = container;
        this.onButtonClick = onButtonClick || (() => {});
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;

        // State variables matching scene definition
        this.playerOxygen = 30;
        this.captainOxygen = 60;
        this.hullIntegrity = 80;
        this.phase = 1;

        // Text displays
        this.playerO2Text = null;
        this.captainO2Text = null;
        this.hullText = null;
        this.phaseText = null;

        // Interactive elements
        this.warningLights = [];
        this.interactiveObjects = [];
        this.phaseButtons = [];

        // Framerate limiting
        this.targetFPS = 50;
        this.frameInterval = 1000 / this.targetFPS;
        this.lastFrameTime = 0;
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.hoveredObject = null;
        this.mouseNeedsUpdate = false;

        // Audio system
        this.audioContext = null;
        this.sounds = {};
        this.initAudio();

        // Emergency lighting
        this.emergencyLight = null;
        this.emergencyLightOn = false;

        // Performance tracking
        this.frameCount = 0;

        // Button debouncing
        this.lastButtonClick = 0;
        this.buttonDebounceMs = 500;

        this.init();
        this.animate();
        this.setupInteraction();
    }

    initAudio() {
        this.audioContext = null;
        this.sounds.click = () => this.playClickSound();
    }

    playClickSound() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }

        const ctx = this.audioContext;
        const currentTime = ctx.currentTime;

        const oscillator = ctx.createOscillator();
        const gainNode = ctx.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);

        oscillator.frequency.value = 600;
        oscillator.type = 'sine';

        gainNode.gain.setValueAtTime(0.25, currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, currentTime + 0.1);

        oscillator.start(currentTime);
        oscillator.stop(currentTime + 0.1);
    }

    playHullGroan() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }

        const ctx = this.audioContext;
        const currentTime = ctx.currentTime;

        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.frequency.setValueAtTime(80, currentTime);
        osc.frequency.linearRampToValueAtTime(40, currentTime + 1.5);
        osc.type = 'sawtooth';

        gain.gain.setValueAtTime(0.15, currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, currentTime + 1.5);

        osc.start(currentTime);
        osc.stop(currentTime + 1.5);
    }

    init() {
        // Scene with cramped escape pod atmosphere
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a1015);
        this.scene.fog = new THREE.Fog(0x0a1015, 3, 10);

        // Camera - first person, cramped space
        this.camera = new THREE.PerspectiveCamera(
            70,
            window.innerWidth / window.innerHeight,
            0.1,
            1000
        );
        this.camera.position.set(0, 1.4, 0.3);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({
            antialias: false,
            powerPreference: "high-performance",
            stencil: false,
            depth: true
        });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.shadowMap.enabled = false;
        this.container.appendChild(this.renderer.domElement);

        // Controls - limited rotation for cramped space
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.08;
        this.controls.enableZoom = false;
        this.controls.enablePan = false;
        this.controls.minAzimuthAngle = -Math.PI / 4;
        this.controls.maxAzimuthAngle = Math.PI / 4;
        this.controls.minPolarAngle = Math.PI / 2 - Math.PI / 4;
        this.controls.maxPolarAngle = Math.PI / 2 + Math.PI / 4;
        this.controls.target.set(0, 1.4, -1.5);
        this.controls.rotateSpeed = 0.4;

        // Build the scene
        this.createPodInterior();
        this.createPorthole();
        this.createGauges();
        this.createControlPanel();
        this.setupLights();

        window.addEventListener('resize', () => this.onWindowResize());
    }

    createPodInterior() {
        // Curved cylindrical walls - smaller, more cramped
        const wallGeometry = new THREE.CylinderGeometry(2, 2, 3, 12, 1, true);
        const wallMaterial = new THREE.MeshStandardMaterial({
            color: 0x1a2530,
            roughness: 0.9,
            metalness: 0.6,
            side: THREE.BackSide,
        });
        const walls = new THREE.Mesh(wallGeometry, wallMaterial);
        walls.position.y = 1.5;
        this.scene.add(walls);

        // Floor
        const floorGeometry = new THREE.CylinderGeometry(2, 2, 0.15, 12);
        const floorMaterial = new THREE.MeshStandardMaterial({
            color: 0x151f28,
            roughness: 0.95,
            metalness: 0.4,
        });
        const floor = new THREE.Mesh(floorGeometry, floorMaterial);
        floor.position.y = 0;
        this.scene.add(floor);

        // Ceiling
        const ceiling = new THREE.Mesh(floorGeometry, floorMaterial);
        ceiling.position.y = 3;
        this.scene.add(ceiling);

        // Rivets and pipes for industrial feel
        for (let i = 0; i < 6; i++) {
            const angle = (i / 6) * Math.PI * 2;
            const pipeGeometry = new THREE.CylinderGeometry(0.04, 0.04, 2.8, 6);
            const pipeMaterial = new THREE.MeshStandardMaterial({
                color: 0x3a4550,
                roughness: 0.7,
                metalness: 0.8,
            });
            const pipe = new THREE.Mesh(pipeGeometry, pipeMaterial);
            pipe.position.x = Math.cos(angle) * 1.9;
            pipe.position.z = Math.sin(angle) * 1.9;
            pipe.position.y = 1.5;
            this.scene.add(pipe);
        }

        // Add condensation/water drip effect (visual particles)
        const dripGeometry = new THREE.BufferGeometry();
        const dripCount = 15;
        const dripPositions = new Float32Array(dripCount * 3);

        for (let i = 0; i < dripCount * 3; i += 3) {
            dripPositions[i] = (Math.random() - 0.5) * 3;
            dripPositions[i + 1] = Math.random() * 2.5 + 0.5;
            dripPositions[i + 2] = (Math.random() - 0.5) * 3;
        }

        dripGeometry.setAttribute('position', new THREE.BufferAttribute(dripPositions, 3));

        const dripMaterial = new THREE.PointsMaterial({
            color: 0x4488aa,
            size: 0.02,
            transparent: true,
            opacity: 0.4,
        });

        this.waterDrips = new THREE.Points(dripGeometry, dripMaterial);
        this.scene.add(this.waterDrips);
    }

    createPorthole() {
        // Small porthole showing dark water
        const size = 0.2;

        const frameGeometry = new THREE.TorusGeometry(size, 0.04, 10, 20);
        const frameMaterial = new THREE.MeshStandardMaterial({
            color: 0x5a6a7a,
            roughness: 0.4,
            metalness: 0.8,
        });
        const frame = new THREE.Mesh(frameGeometry, frameMaterial);
        frame.position.set(-1.4, 1.5, -1.2);
        frame.rotation.y = Math.PI / 4;
        this.scene.add(frame);

        // Dark blue glass
        const glassGeometry = new THREE.CircleGeometry(size, 20);
        const glassMaterial = new THREE.MeshPhysicalMaterial({
            color: 0x0a2040,
            transparent: true,
            opacity: 0.85,
            roughness: 0.1,
            metalness: 0.1,
            transmission: 0.7,
        });
        const glass = new THREE.Mesh(glassGeometry, glassMaterial);
        glass.position.set(-1.38, 1.5, -1.18);
        glass.rotation.y = Math.PI / 4;
        this.scene.add(glass);

        // Bubbles outside
        const bubbleGeometry = new THREE.BufferGeometry();
        const bubbleCount = 12;
        const bubblePositions = new Float32Array(bubbleCount * 3);

        for (let i = 0; i < bubbleCount * 3; i += 3) {
            bubblePositions[i] = -1.5 + (Math.random() - 0.5) * 0.5;
            bubblePositions[i + 1] = 1 + Math.random() * 2;
            bubblePositions[i + 2] = -1.3 - Math.random() * 0.5;
        }

        bubbleGeometry.setAttribute('position', new THREE.BufferAttribute(bubblePositions, 3));

        const bubbleMaterial = new THREE.PointsMaterial({
            color: 0x5588bb,
            size: 0.025,
            transparent: true,
            opacity: 0.6,
        });

        this.bubbles = new THREE.Points(bubbleGeometry, bubbleMaterial);
        this.scene.add(this.bubbles);
    }

    createGauges() {
        // === PLAYER O2 GAUGE (LEFT - GREEN) ===
        const playerPanelGeometry = new THREE.BoxGeometry(0.5, 0.4, 0.08);
        const playerPanelMaterial = new THREE.MeshStandardMaterial({
            color: 0x1a2a1a,
            roughness: 0.7,
            metalness: 0.3,
        });
        const playerPanel = new THREE.Mesh(playerPanelGeometry, playerPanelMaterial);
        playerPanel.position.set(-0.5, 2.1, -1.8);
        this.scene.add(playerPanel);

        const playerDisplayGeometry = new THREE.PlaneGeometry(0.4, 0.25);
        const playerDisplayMaterial = new THREE.MeshBasicMaterial({ color: 0x0a0a0a });
        const playerDisplay = new THREE.Mesh(playerDisplayGeometry, playerDisplayMaterial);
        playerDisplay.position.set(-0.5, 2.1, -1.76);
        this.scene.add(playerDisplay);

        // Player O2 text
        const playerCanvas = document.createElement('canvas');
        playerCanvas.width = 256;
        playerCanvas.height = 128;
        const playerContext = playerCanvas.getContext('2d');
        playerContext.fillStyle = '#33ff66';
        playerContext.font = 'bold 44px monospace';
        playerContext.textAlign = 'center';
        playerContext.textBaseline = 'middle';
        playerContext.fillText('30%', 128, 64);

        const playerTexture = new THREE.CanvasTexture(playerCanvas);
        const playerTextMaterial = new THREE.MeshBasicMaterial({ map: playerTexture, transparent: true });
        const playerTextMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.38, 0.2), playerTextMaterial);
        playerTextMesh.position.set(-0.5, 2.1, -1.75);
        this.scene.add(playerTextMesh);

        this.playerO2Text = { canvas: playerCanvas, context: playerContext, texture: playerTexture, mesh: playerTextMesh };

        // Player O2 label
        this.createLabel('YOUR O2', -0.5, 2.32, -1.75, '#33ff66');

        // === CAPTAIN O2 GAUGE (RIGHT - RED) ===
        const captainPanelGeometry = new THREE.BoxGeometry(0.5, 0.4, 0.08);
        const captainPanelMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a1a1a,
            roughness: 0.7,
            metalness: 0.3,
        });
        const captainPanel = new THREE.Mesh(captainPanelGeometry, captainPanelMaterial);
        captainPanel.position.set(0.5, 2.1, -1.8);
        this.scene.add(captainPanel);

        const captainDisplayGeometry = new THREE.PlaneGeometry(0.4, 0.25);
        const captainDisplayMaterial = new THREE.MeshBasicMaterial({ color: 0x0a0a0a });
        const captainDisplay = new THREE.Mesh(captainDisplayGeometry, captainDisplayMaterial);
        captainDisplay.position.set(0.5, 2.1, -1.76);
        this.scene.add(captainDisplay);

        // Captain O2 text
        const captainCanvas = document.createElement('canvas');
        captainCanvas.width = 256;
        captainCanvas.height = 128;
        const captainContext = captainCanvas.getContext('2d');
        captainContext.fillStyle = '#ff6633';
        captainContext.font = 'bold 44px monospace';
        captainContext.textAlign = 'center';
        captainContext.textBaseline = 'middle';
        captainContext.fillText('60%', 128, 64);

        const captainTexture = new THREE.CanvasTexture(captainCanvas);
        const captainTextMaterial = new THREE.MeshBasicMaterial({ map: captainTexture, transparent: true });
        const captainTextMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.38, 0.2), captainTextMaterial);
        captainTextMesh.position.set(0.5, 2.1, -1.75);
        this.scene.add(captainTextMesh);

        this.captainO2Text = { canvas: captainCanvas, context: captainContext, texture: captainTexture, mesh: captainTextMesh };

        // Captain O2 label
        this.createLabel('CAPTAIN O2', 0.5, 2.32, -1.75, '#ff6633');

        // === HULL INTEGRITY GAUGE (CENTER) ===
        const hullPanelGeometry = new THREE.BoxGeometry(0.6, 0.35, 0.08);
        const hullPanelMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a2a2a,
            roughness: 0.7,
            metalness: 0.3,
        });
        const hullPanel = new THREE.Mesh(hullPanelGeometry, hullPanelMaterial);
        hullPanel.position.set(0, 1.7, -1.8);
        this.scene.add(hullPanel);

        const hullDisplayGeometry = new THREE.PlaneGeometry(0.5, 0.22);
        const hullDisplayMaterial = new THREE.MeshBasicMaterial({ color: 0x0a0a0a });
        const hullDisplay = new THREE.Mesh(hullDisplayGeometry, hullDisplayMaterial);
        hullDisplay.position.set(0, 1.7, -1.76);
        this.scene.add(hullDisplay);

        // Hull text
        const hullCanvas = document.createElement('canvas');
        hullCanvas.width = 256;
        hullCanvas.height = 128;
        const hullContext = hullCanvas.getContext('2d');
        hullContext.fillStyle = '#ffaa33';
        hullContext.font = 'bold 40px monospace';
        hullContext.textAlign = 'center';
        hullContext.textBaseline = 'middle';
        hullContext.fillText('80%', 128, 64);

        const hullTexture = new THREE.CanvasTexture(hullCanvas);
        const hullTextMaterial = new THREE.MeshBasicMaterial({ map: hullTexture, transparent: true });
        const hullTextMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.45, 0.18), hullTextMaterial);
        hullTextMesh.position.set(0, 1.7, -1.75);
        this.scene.add(hullTextMesh);

        this.hullText = { canvas: hullCanvas, context: hullContext, texture: hullTexture, mesh: hullTextMesh };

        // Hull label
        this.createLabel('HULL', 0, 1.88, -1.75, '#ffaa33');

        // === PHASE INDICATOR (BOTTOM RIGHT) ===
        const phasePanelGeometry = new THREE.BoxGeometry(0.35, 0.25, 0.08);
        const phasePanelMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a2a2a,
            roughness: 0.7,
            metalness: 0.3,
        });
        const phasePanel = new THREE.Mesh(phasePanelGeometry, phasePanelMaterial);
        phasePanel.position.set(0.7, 1.35, -1.8);
        this.scene.add(phasePanel);

        const phaseDisplayGeometry = new THREE.PlaneGeometry(0.28, 0.15);
        const phaseDisplayMaterial = new THREE.MeshBasicMaterial({ color: 0x0a0a0a });
        const phaseDisplay = new THREE.Mesh(phaseDisplayGeometry, phaseDisplayMaterial);
        phaseDisplay.position.set(0.7, 1.35, -1.76);
        this.scene.add(phaseDisplay);

        // Phase text
        const phaseCanvas = document.createElement('canvas');
        phaseCanvas.width = 128;
        phaseCanvas.height = 64;
        const phaseContext = phaseCanvas.getContext('2d');
        phaseContext.fillStyle = '#9999ff';
        phaseContext.font = 'bold 40px monospace';
        phaseContext.textAlign = 'center';
        phaseContext.textBaseline = 'middle';
        phaseContext.fillText('1', 64, 32);

        const phaseTexture = new THREE.CanvasTexture(phaseCanvas);
        const phaseTextMaterial = new THREE.MeshBasicMaterial({ map: phaseTexture, transparent: true });
        const phaseTextMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.25, 0.12), phaseTextMaterial);
        phaseTextMesh.position.set(0.7, 1.35, -1.75);
        this.scene.add(phaseTextMesh);

        this.phaseText = { canvas: phaseCanvas, context: phaseContext, texture: phaseTexture, mesh: phaseTextMesh };

        // Phase label
        this.createLabel('PHASE', 0.7, 1.48, -1.75, '#9999ff', 14);
    }

    createLabel(text, x, y, z, color, fontSize = 18) {
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 48;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = color;
        ctx.font = `bold ${fontSize}px monospace`;
        ctx.textAlign = 'center';
        ctx.fillText(text, 128, 30);

        const texture = new THREE.CanvasTexture(canvas);
        const material = new THREE.MeshBasicMaterial({ map: texture, transparent: true });
        const mesh = new THREE.Mesh(new THREE.PlaneGeometry(0.4, 0.08), material);
        mesh.position.set(x, y, z);
        this.scene.add(mesh);
    }

    createControlPanel() {
        // Main control panel
        const panelGeometry = new THREE.BoxGeometry(1.2, 0.6, 0.12);
        const panelMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a3040,
            roughness: 0.6,
            metalness: 0.4,
        });
        const panel = new THREE.Mesh(panelGeometry, panelMaterial);
        panel.position.set(0, 1.1, -1.7);
        this.scene.add(panel);

        // Button definitions
        const buttonPositions = [
            { x: -0.35, y: 0.15, label: 'O2 VALVE', color: 0x33ff33 },
            { x: 0.35, y: 0.15, label: 'COMMS', color: 0x3399ff },
            { x: -0.35, y: -0.1, label: 'PREP POD', color: 0xffaa33, visibleInPhases: [4, 5] },
            { x: 0.35, y: -0.1, label: 'DETACH', color: 0xff3333, visibleInPhases: [4, 5] },
            { x: 0.0, y: -0.35, label: 'RISKY SAVE', color: 0xff00ff, visibleInPhases: [5] },
        ];

        buttonPositions.forEach(pos => {
            const buttonGeometry = new THREE.CylinderGeometry(0.08, 0.08, 0.06, 12);
            const buttonMaterial = new THREE.MeshStandardMaterial({
                color: pos.color,
                roughness: 0.3,
                metalness: 0.7,
                emissive: pos.color,
                emissiveIntensity: 0.3,
            });
            const button = new THREE.Mesh(buttonGeometry, buttonMaterial);
            button.position.set(pos.x, 1.1 + pos.y, -1.64);
            button.rotation.x = Math.PI / 2;
            button.userData = {
                type: 'button',
                action: pos.label,
                originalColor: pos.color,
                visibleInPhases: pos.visibleInPhases || null
            };

            // Button label
            const labelCanvas = document.createElement('canvas');
            labelCanvas.width = 256;
            labelCanvas.height = 48;
            const ctx = labelCanvas.getContext('2d');
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 20px monospace';
            ctx.textAlign = 'center';
            ctx.fillText(pos.label, 128, 32);

            const labelTexture = new THREE.CanvasTexture(labelCanvas);
            const labelMaterial = new THREE.MeshBasicMaterial({ map: labelTexture, transparent: true });
            const label = new THREE.Mesh(new THREE.PlaneGeometry(0.35, 0.08), labelMaterial);
            label.position.set(pos.x, 1.1 + pos.y - 0.12, -1.64);

            if (pos.visibleInPhases) {
                button.visible = false;
                label.visible = false;
                this.phaseButtons.push({ button, label, phases: pos.visibleInPhases });
            }

            this.scene.add(button);
            this.scene.add(label);
            this.interactiveObjects.push(button);
        });
    }

    setupLights() {
        // Ambient - dimmer for cramped atmosphere
        const ambientLight = new THREE.AmbientLight(0x304050, 0.6);
        this.scene.add(ambientLight);

        // Warning lights (amber)
        for (let i = 0; i < 2; i++) {
            const angle = (i / 2) * Math.PI * 2 + Math.PI / 4;
            const warningLight = new THREE.PointLight(0xff6633, 0.5, 4);
            warningLight.position.x = Math.cos(angle) * 1.5;
            warningLight.position.z = Math.sin(angle) * 1.5;
            warningLight.position.y = 2.5;
            this.scene.add(warningLight);
            this.warningLights.push(warningLight);
        }

        // Main overhead light
        const mainLight = new THREE.PointLight(0x7090a0, 1.2, 8);
        mainLight.position.set(0, 2.8, 0);
        this.scene.add(mainLight);

        // Emergency red light (activates when hull < 30%)
        this.emergencyLight = new THREE.PointLight(0xff0000, 0, 6);
        this.emergencyLight.position.set(0, 2.5, -0.5);
        this.scene.add(this.emergencyLight);
    }

    setupInteraction() {
        window.addEventListener('mousemove', (event) => {
            this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
            this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
            this.mouseNeedsUpdate = true;
        });

        window.addEventListener('click', () => {
            if (this.hoveredObject) {
                const now = Date.now();
                if (now - this.lastButtonClick < this.buttonDebounceMs) {
                    return;
                }
                this.lastButtonClick = now;

                console.log('Button clicked:', this.hoveredObject.userData.action);
                this.playClickSound();
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

        const currentTime = Date.now();
        const deltaTime = currentTime - this.lastFrameTime;

        if (deltaTime < this.frameInterval) {
            return;
        }

        this.lastFrameTime = currentTime - (deltaTime % this.frameInterval);
        const time = currentTime * 0.001;
        this.frameCount++;

        // Update player O2 gauge
        if (this.playerO2Text && this.frameCount % 10 === 0) {
            const percent = Math.round(this.playerOxygen);
            const { context, texture, canvas } = this.playerO2Text;
            context.clearRect(0, 0, canvas.width, canvas.height);

            if (percent < 20) {
                context.fillStyle = '#ff3333';
            } else if (percent < 40) {
                context.fillStyle = '#ffaa33';
            } else {
                context.fillStyle = '#33ff66';
            }

            context.font = 'bold 44px monospace';
            context.textAlign = 'center';
            context.textBaseline = 'middle';
            context.fillText(`${percent}%`, 128, 64);
            texture.needsUpdate = true;
        }

        // Update captain O2 gauge
        if (this.captainO2Text && this.frameCount % 10 === 0) {
            const percent = Math.round(this.captainOxygen);
            const { context, texture, canvas } = this.captainO2Text;
            context.clearRect(0, 0, canvas.width, canvas.height);

            if (percent < 20) {
                context.fillStyle = '#ff0000';
            } else if (percent < 40) {
                context.fillStyle = '#ff6633';
            } else {
                context.fillStyle = '#ff9966';
            }

            context.font = 'bold 44px monospace';
            context.textAlign = 'center';
            context.textBaseline = 'middle';
            context.fillText(`${percent}%`, 128, 64);
            texture.needsUpdate = true;
        }

        // Update hull integrity gauge
        if (this.hullText && this.frameCount % 10 === 0) {
            const percent = Math.round(this.hullIntegrity);
            const { context, texture, canvas } = this.hullText;
            context.clearRect(0, 0, canvas.width, canvas.height);

            if (percent < 30) {
                context.fillStyle = '#ff3333';
            } else if (percent < 50) {
                context.fillStyle = '#ff6633';
            } else {
                context.fillStyle = '#ffaa33';
            }

            context.font = 'bold 40px monospace';
            context.textAlign = 'center';
            context.textBaseline = 'middle';
            context.fillText(`${percent}%`, 128, 64);
            texture.needsUpdate = true;

            // Activate emergency mode when hull is critical
            if (percent < 30 && !this.emergencyLightOn) {
                this.activateEmergencyMode();
            } else if (percent >= 30 && this.emergencyLightOn) {
                this.deactivateEmergencyMode();
            }
        }

        // Update phase indicator
        if (this.phaseText && this.frameCount % 10 === 0) {
            const phaseNum = Math.round(this.phase);
            const { context, texture, canvas } = this.phaseText;
            context.clearRect(0, 0, canvas.width, canvas.height);

            if (phaseNum === 5) {
                context.fillStyle = '#ff6699';
            } else if (phaseNum === 4) {
                context.fillStyle = '#ff9966';
            } else if (phaseNum === 3) {
                context.fillStyle = '#ffcc66';
            } else {
                context.fillStyle = '#9999ff';
            }

            context.font = 'bold 40px monospace';
            context.textAlign = 'center';
            context.textBaseline = 'middle';
            context.fillText(`${phaseNum}`, 64, 32);
            texture.needsUpdate = true;
        }

        // Flicker warning lights
        if (this.frameCount % 3 === 0) {
            this.warningLights.forEach((light, i) => {
                light.intensity = 0.3 + Math.sin(time * 2 + i) * 0.15 + Math.random() * 0.05;
            });
        }

        // Pulse emergency light
        if (this.emergencyLightOn && this.emergencyLight) {
            const pulse = Math.sin(time * 6) * 0.5 + 0.5;
            this.emergencyLight.intensity = 1.0 + pulse * 1.5;
        }

        // Animate water drips
        if (this.waterDrips && this.frameCount % 5 === 0) {
            const positions = this.waterDrips.geometry.attributes.position.array;
            for (let i = 0; i < positions.length; i += 3) {
                positions[i + 1] -= 0.015;
                if (positions[i + 1] < 0.2) {
                    positions[i + 1] = 2.8;
                }
            }
            this.waterDrips.geometry.attributes.position.needsUpdate = true;
        }

        // Animate bubbles
        if (this.bubbles && this.frameCount % 5 === 0) {
            const positions = this.bubbles.geometry.attributes.position.array;
            for (let i = 0; i < positions.length; i += 3) {
                positions[i + 1] += 0.01;
                if (positions[i + 1] > 3) {
                    positions[i + 1] = 1;
                }
                positions[i] += Math.sin(time * 2 + i) * 0.002;
            }
            this.bubbles.geometry.attributes.position.needsUpdate = true;
        }

        // Occasional hull groan
        if (this.frameCount % 300 === 0 && this.hullIntegrity < 50) {
            this.playHullGroan();
        }

        // Button hover detection
        if (this.mouseNeedsUpdate) {
            this.raycaster.setFromCamera(this.mouse, this.camera);
            const intersects = this.raycaster.intersectObjects(this.interactiveObjects);

            if (this.hoveredObject) {
                this.hoveredObject.material.emissiveIntensity = 0.3;
                document.body.style.cursor = 'default';
            }

            if (intersects.length > 0) {
                this.hoveredObject = intersects[0].object;
                this.hoveredObject.material.emissiveIntensity = 0.8;
                document.body.style.cursor = 'pointer';
            } else {
                this.hoveredObject = null;
            }

            this.mouseNeedsUpdate = false;
        }

        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    onWindowResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    // External state update methods
    setPlayerOxygen(percentage) {
        this.playerOxygen = percentage;
    }

    setCaptainOxygen(percentage) {
        this.captainOxygen = percentage;
    }

    setHullIntegrity(percentage) {
        this.hullIntegrity = percentage;
    }

    setPhase(phase) {
        const previousPhase = this.phase;
        this.phase = phase;

        if (previousPhase !== phase) {
            this.phaseButtons.forEach(({ button, label, phases }) => {
                const shouldBeVisible = phases.includes(phase);
                button.visible = shouldBeVisible;
                label.visible = shouldBeVisible;

                if (shouldBeVisible && !phases.includes(previousPhase)) {
                    console.log(`[PHASE ${phase}] New control available: ${button.userData.action}`);
                }
            });
        }
    }

    activateEmergencyMode() {
        console.log('[EMERGENCY] Hull critical - activating emergency systems!');
        this.emergencyLightOn = true;
    }

    deactivateEmergencyMode() {
        console.log('[EMERGENCY] Hull stabilized - deactivating emergency systems');
        this.emergencyLightOn = false;
        if (this.emergencyLight) {
            this.emergencyLight.intensity = 0;
        }
    }

    triggerAlert(type) {
        console.log('Alert triggered:', type);
    }

    /**
     * Clean up all resources. Called when switching scenes.
     */
    dispose() {
        console.log('[LIFE_RAFT] Disposing scene...');

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
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;

        console.log('[LIFE_RAFT] Scene disposed');
    }

    /**
     * Alias for dispose()
     */
    destroy() {
        this.dispose();
    }
}
