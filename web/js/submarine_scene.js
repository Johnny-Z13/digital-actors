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
        this.oxygenLevel = 180; // 3 minutes in seconds
        this.oxygenText = null;
        this.warningLights = [];
        this.interactiveObjects = [];
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.hoveredObject = null;
        this.mouseNeedsUpdate = false; // Track if mouse moved for raycast optimization

        // Audio system
        this.audioContext = null;
        this.sounds = {};
        this.initAudio();

        // Performance tracking
        this.frameCount = 0; // For throttling expensive operations

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
        // Start centered in the cabin, looking forward at control panel
        this.camera.position.set(0, 1.6, 0.5);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
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
        this.createOxygenGauge();
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

    createOxygenGauge() {
        // Gauge panel background
        const panelGeometry = new THREE.BoxGeometry(0.8, 0.5, 0.1);
        const panelMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a2a2a,
            roughness: 0.7,
            metalness: 0.3,
        });
        const panel = new THREE.Mesh(panelGeometry, panelMaterial);
        panel.position.set(0, 2.5, -2.8);
        this.scene.add(panel);

        // Gauge display
        const displayGeometry = new THREE.PlaneGeometry(0.6, 0.3);
        const displayMaterial = new THREE.MeshBasicMaterial({
            color: 0x0a0a0a,
        });
        const display = new THREE.Mesh(displayGeometry, displayMaterial);
        display.position.set(0, 2.5, -2.75);
        this.scene.add(display);

        // Oxygen text (will be updated in animate)
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 128;
        const context = canvas.getContext('2d');
        context.fillStyle = '#ff3333';
        context.font = 'bold 48px monospace';
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        context.fillText('03:00', 128, 64);

        const texture = new THREE.CanvasTexture(canvas);
        const textMaterial = new THREE.MeshBasicMaterial({
            map: texture,
            transparent: true,
        });
        const textMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.55, 0.25), textMaterial);
        textMesh.position.set(0, 2.5, -2.74);
        this.scene.add(textMesh);

        this.oxygenText = { canvas, context, texture, mesh: textMesh };

        // Label
        const labelCanvas = document.createElement('canvas');
        labelCanvas.width = 256;
        labelCanvas.height = 64;
        const labelContext = labelCanvas.getContext('2d');
        labelContext.fillStyle = '#ffffff';
        labelContext.font = 'bold 24px monospace';
        labelContext.textAlign = 'center';
        labelContext.fillText('OXYGEN', 128, 32);

        const labelTexture = new THREE.CanvasTexture(labelCanvas);
        const labelMaterial = new THREE.MeshBasicMaterial({
            map: labelTexture,
            transparent: true,
        });
        const labelMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.4, 0.1), labelMaterial);
        labelMesh.position.set(0, 2.75, -2.74);
        this.scene.add(labelMesh);
    }

    createControlPanel() {
        // Main control panel
        const panelGeometry = new THREE.BoxGeometry(1.5, 0.8, 0.15);
        const panelMaterial = new THREE.MeshStandardMaterial({
            color: 0x3a3a3a,
            roughness: 0.6,
            metalness: 0.4,
        });
        const panel = new THREE.Mesh(panelGeometry, panelMaterial);
        panel.position.set(1.5, 1.5, -2.7);
        this.scene.add(panel);

        // Create buttons
        const buttonPositions = [
            { x: -0.4, y: 0.2, label: 'O2 VALVE', color: 0xff3333 },
            { x: 0.2, y: 0.2, label: 'VENT', color: 0xffaa33 },
            { x: -0.4, y: -0.15, label: 'BALLAST', color: 0x3399ff },
            { x: 0.2, y: -0.15, label: 'POWER', color: 0x33ff33 },
        ];

        buttonPositions.forEach(pos => {
            const buttonGeometry = new THREE.CylinderGeometry(0.08, 0.08, 0.05, 16);
            const buttonMaterial = new THREE.MeshStandardMaterial({
                color: pos.color,
                roughness: 0.3,
                metalness: 0.7,
                emissive: pos.color,
                emissiveIntensity: 0.3,
            });
            const button = new THREE.Mesh(buttonGeometry, buttonMaterial);
            button.position.set(1.5 + pos.x, 1.5 + pos.y, -2.62);
            button.rotation.x = Math.PI / 2;
            button.userData = { type: 'button', action: pos.label, originalColor: pos.color };
            this.scene.add(button);
            this.interactiveObjects.push(button);

            // Button label - 100% larger (doubled)
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
            label.position.set(1.5 + pos.x, 1.5 + pos.y - 0.15, -2.62);
            this.scene.add(label);
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

        // Total lights: 4 (ambient + 2 warning + 1 main + 1 interior)
    }

    setupInteraction() {
        window.addEventListener('mousemove', (event) => {
            this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
            this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
            this.mouseNeedsUpdate = true; // Flag that mouse moved for raycast optimization
        });

        window.addEventListener('click', () => {
            if (this.hoveredObject) {
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

        const time = Date.now() * 0.001;
        this.frameCount++;

        // Update oxygen display
        if (this.oxygenLevel > 0) {
            this.oxygenLevel -= 0.016; // Approximately 1 second per frame
        }

        // Only update oxygen canvas texture every 30 frames (~500ms at 60fps) for performance
        if (this.oxygenText && this.frameCount % 30 === 0) {
            const minutes = Math.floor(this.oxygenLevel / 60);
            const seconds = Math.floor(this.oxygenLevel % 60);
            const display = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

            const { context, texture, canvas } = this.oxygenText;
            context.clearRect(0, 0, canvas.width, canvas.height);
            context.fillStyle = this.oxygenLevel < 60 ? '#ff0000' : '#ff3333';
            context.font = 'bold 48px monospace';
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
                this.hoveredObject.material.emissiveIntensity = 0.6;
                document.body.style.cursor = 'pointer';
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

    // Method to update oxygen level externally
    setOxygenLevel(seconds) {
        this.oxygenLevel = seconds;
    }

    // Method to add visual feedback for events
    triggerAlert(type) {
        // Could add screen shake, color flash, etc.
        console.log('Alert triggered:', type);
    }
}
