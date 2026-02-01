import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { WorldLabsImporter } from '/scenes/base/world_labs_importer.js';

export class MerlinsRoomScene {
    constructor(container, onButtonClick = null) {
        this.container = container;
        this.onButtonClick = onButtonClick;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.model = null;
        this.lights = [];
        this.floatingCandles = [];

        // WASD movement state
        this.moveState = { forward: false, backward: false, left: false, right: false, up: false, down: false };
        this.shiftPressed = false;
        this.moveSpeed = 0.15;
        this.mouseSensitivity = 0.002;
        this.euler = new THREE.Euler(0, 0, 0, 'YXZ');
        this.isPointerLocked = false;

        // Camera HUD
        this.hudElement = null;
        this.debugMode = false;  // Debug HUD hidden by default, toggle with SHIFT+D

        this.init();
        this.loadModel();
        this.setupWASDControls();
        this.createHUD();
        this.animate();
    }

    init() {
        // Scene with warm magical atmosphere
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x1a1520);
        // Light fog for depth (can remove if obscuring model)
        // this.scene.fog = new THREE.FogExp2(0x1a1520, 0.01);

        // Camera - positioned to view the workshop
        this.camera = new THREE.PerspectiveCamera(
            60,
            window.innerWidth / window.innerHeight,
            0.1,
            1000
        );
        // Start camera at a good viewing position
        this.camera.position.set(0, 1.5, 4);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            powerPreference: "high-performance"
        });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.5;  // Brighter exposure
        this.renderer.outputColorSpace = THREE.SRGBColorSpace;  // Proper color space
        this.container.appendChild(this.renderer.domElement);

        // Controls - Fixed position, mouse look + zoom only
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.08;
        this.controls.rotateSpeed = 0.4;        // Gentle mouse look
        this.controls.enableZoom = false;       // We handle zoom via FOV
        this.controls.enablePan = false;        // No panning
        this.controls.minDistance = 0.01;       // Lock position (tiny orbit radius)
        this.controls.maxDistance = 0.02;       // Lock position
        this.controls.maxPolarAngle = Math.PI;  // Full vertical look
        this.controls.minPolarAngle = 0;

        // Store fixed camera position (will be set when model loads)
        this.fixedCameraPos = new THREE.Vector3(0, 1.5, 4);

        // Magical lighting
        this.setupLights();

        // Create floating candle particles
        this.createFloatingCandles();

        // Handle window resize
        window.addEventListener('resize', () => this.onWindowResize());
    }

    setupLights() {
        // Strong ambient light to see the model clearly
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
        this.scene.add(ambientLight);

        // Hemisphere light for natural fill (sky/ground colors)
        const hemiLight = new THREE.HemisphereLight(0xffeedd, 0x444422, 1.0);
        this.scene.add(hemiLight);

        // Main directional light (like sunlight through a window)
        const mainLight = new THREE.DirectionalLight(0xffffff, 1.5);
        mainLight.position.set(5, 10, 5);
        mainLight.castShadow = true;
        this.scene.add(mainLight);
        this.lights.push(mainLight);

        // Fill light from opposite side
        const fillLight = new THREE.DirectionalLight(0xffffee, 0.8);
        fillLight.position.set(-5, 5, -5);
        this.scene.add(fillLight);

        // Warm candlelight points for atmosphere
        const candlePositions = [
            { x: -2, y: 2, z: 1, color: 0xff9944, intensity: 2.0 },
            { x: 2, y: 1.5, z: -1, color: 0xffaa55, intensity: 1.5 },
            { x: 0, y: 3, z: 0, color: 0xff8833, intensity: 1.5 },
            { x: -1, y: 1, z: 2, color: 0xffbb66, intensity: 1.2 },
        ];

        candlePositions.forEach(pos => {
            const light = new THREE.PointLight(pos.color, pos.intensity, 12);
            light.position.set(pos.x, pos.y, pos.z);
            this.scene.add(light);
            this.lights.push(light);
        });

        // Magical blue accent light (from potions/crystals)
        const magicLight = new THREE.PointLight(0x4466ff, 1.0, 10);
        magicLight.position.set(1, 0.5, 1);
        this.scene.add(magicLight);
        this.lights.push(magicLight);
    }

    async loadModel() {
        try {
            const result = await WorldLabsImporter.load(
                '/scenes/wizard/merlins_room2.glb',
                this.scene,
                this.camera,
                {
                    targetSize: 15,
                    cameraConfigPath: '/scenes/wizard/camera_config.json',
                    autoPositionCamera: true,
                    enableShadows: true,
                    fixBlackMaterials: true,
                }
            );

            this.model = result.model;

            // Update fixed camera position from loaded config
            this.fixedCameraPos.copy(this.camera.position);

            // Set up orbit controls target
            if (result.cameraConfig.target) {
                this.controls.target.set(
                    result.cameraConfig.target.x,
                    result.cameraConfig.target.y,
                    result.cameraConfig.target.z
                );
            } else if (result.cameraConfig.direction) {
                // Fallback: use direction vector to set target slightly in front of camera
                const dir = new THREE.Vector3(
                    result.cameraConfig.direction.x,
                    result.cameraConfig.direction.y,
                    result.cameraConfig.direction.z
                ).normalize();
                this.controls.target.copy(this.camera.position).add(dir.multiplyScalar(0.01));
            } else {
                // Final fallback: look at model center
                this.controls.target.set(
                    result.bounds.center.x,
                    result.bounds.center.y,
                    result.bounds.center.z
                );
            }

            this.controls.update();

            console.log('[MERLIN_SCENE] Model loaded via WorldLabsImporter');
            console.log('[MERLIN_SCENE] Hold SHIFT+WASD/QE to fly around, mouse to look');
            console.log('[MERLIN_SCENE] Press SHIFT+C to export camera config to console');

        } catch (error) {
            console.error('[MERLIN_SCENE] Error loading model:', error);
            this.createFallbackScene();
        }
    }

    createFallbackScene() {
        // Simple placeholder if model fails to load
        const geometry = new THREE.BoxGeometry(2, 2, 2);
        const material = new THREE.MeshStandardMaterial({
            color: 0x4a2c7a,
            roughness: 0.7
        });
        const cube = new THREE.Mesh(geometry, material);
        cube.position.y = 1;
        this.scene.add(cube);

        // Ground
        const groundGeo = new THREE.PlaneGeometry(10, 10);
        const groundMat = new THREE.MeshStandardMaterial({ color: 0x1a0a2a });
        const ground = new THREE.Mesh(groundGeo, groundMat);
        ground.rotation.x = -Math.PI / 2;
        ground.receiveShadow = true;
        this.scene.add(ground);
    }

    setupWASDControls() {
        // FOV zoom with scroll wheel (since camera is fixed)
        this.renderer.domElement.addEventListener('wheel', (e) => {
            if (this.shiftPressed) return; // Let WASD mode handle it
            e.preventDefault();
            const zoomSpeed = 0.05;
            this.camera.fov += e.deltaY * zoomSpeed;
            this.camera.fov = Math.max(20, Math.min(90, this.camera.fov)); // Clamp FOV
            this.camera.updateProjectionMatrix();
        }, { passive: false });

        // Keyboard controls
        document.addEventListener('keydown', (e) => {
            // SHIFT+C to export camera config
            if (e.shiftKey && e.code === 'KeyC') {
                e.preventDefault();
                this.exportCameraConfig();
                return;
            }

            // Enable free-fly mode with SHIFT
            if (e.key === 'Shift') {
                this.shiftPressed = true;
                this.controls.enabled = false; // Disable orbit controls

                // Relax distance constraints to allow free movement
                this.controls.minDistance = 0;
                this.controls.maxDistance = Infinity;

                console.log('[MERLIN_SCENE] 🎮 Free-fly mode enabled - WASD/QE to move, mouse to look');
                return;
            }

            // Toggle debug HUD with SHIFT+D
            if (e.shiftKey && e.code === 'KeyD') {
                this.debugMode = !this.debugMode;
                this.hudElement.style.display = this.debugMode ? 'block' : 'none';
                console.log('[MERLIN_SCENE] 🐛 Debug mode:', this.debugMode ? 'ON' : 'OFF');
                return;
            }

            // Only handle WASD when SHIFT is held
            if (!this.shiftPressed) return;

            switch (e.code) {
                case 'KeyW': this.moveState.forward = true; break;
                case 'KeyS': this.moveState.backward = true; break;
                case 'KeyA': this.moveState.left = true; break;
                case 'KeyD': this.moveState.right = true; break;
                case 'KeyQ': this.moveState.down = true; break;
                case 'KeyE': this.moveState.up = true; break;
            }
        });

        document.addEventListener('keyup', (e) => {
            if (e.key === 'Shift') {
                this.shiftPressed = false;
                this.controls.enabled = true; // Re-enable orbit controls

                // Restore distance constraints to lock camera in place
                this.controls.minDistance = 0.01;
                this.controls.maxDistance = 0.02;

                // Save current position as the new fixed position
                this.fixedCameraPos.copy(this.camera.position);

                // Update orbit target to current camera position
                const dir = new THREE.Vector3(0, 0, -1).applyQuaternion(this.camera.quaternion);
                this.controls.target.copy(this.camera.position).add(dir.multiplyScalar(0.01));

                // Reset all movement states when releasing shift
                this.moveState = { forward: false, backward: false, left: false, right: false, up: false, down: false };

                console.log('[MERLIN_SCENE] 🔒 Camera locked at position:',
                    this.camera.position.x.toFixed(2),
                    this.camera.position.y.toFixed(2),
                    this.camera.position.z.toFixed(2));
            }
            switch (e.code) {
                case 'KeyW': this.moveState.forward = false; break;
                case 'KeyS': this.moveState.backward = false; break;
                case 'KeyA': this.moveState.left = false; break;
                case 'KeyD': this.moveState.right = false; break;
                case 'KeyQ': this.moveState.down = false; break;
                case 'KeyE': this.moveState.up = false; break;
            }
        });

        // Mouse look when shift is held
        document.addEventListener('mousemove', (e) => {
            if (!this.shiftPressed) return;

            this.euler.setFromQuaternion(this.camera.quaternion);
            this.euler.y -= e.movementX * this.mouseSensitivity;
            this.euler.x -= e.movementY * this.mouseSensitivity;
            this.euler.x = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, this.euler.x));
            this.camera.quaternion.setFromEuler(this.euler);

            // Update orbit controls target based on camera direction
            const direction = new THREE.Vector3(0, 0, -1).applyQuaternion(this.camera.quaternion);
            this.controls.target.copy(this.camera.position).add(direction.multiplyScalar(2));
        });
    }

    createHUD() {
        // Create camera position readout
        this.hudElement = document.createElement('div');
        this.hudElement.id = 'camera-hud';
        this.hudElement.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 20px;
            background: rgba(0, 0, 0, 0.7);
            color: #0f0;
            font-family: monospace;
            font-size: 12px;
            padding: 10px 15px;
            border-radius: 5px;
            z-index: 1000;
            pointer-events: none;
            line-height: 1.6;
            display: none;
        `;
        document.body.appendChild(this.hudElement);
    }

    updateHUD() {
        if (!this.hudElement || !this.camera || !this.debugMode) return;

        const pos = this.camera.position;
        const rot = this.camera.rotation;
        const dir = new THREE.Vector3(0, 0, -1).applyQuaternion(this.camera.quaternion);

        const mode = this.shiftPressed ? '<span style="color:#0f0">🎮 FREE-FLY MODE</span>' : 'Drag: Look | Scroll: Zoom';
        this.hudElement.innerHTML = `
            ${mode}<br>
            <span style="color:#888">SHIFT+WASD/QE to fly | SHIFT+C export | SHIFT+D hide debug</span><br>
            Pos: ${pos.x.toFixed(2)}, ${pos.y.toFixed(2)}, ${pos.z.toFixed(2)} | FOV: ${this.camera.fov.toFixed(0)}°
        `;
    }

    updateMovement() {
        if (!this.shiftPressed) return;

        const forward = new THREE.Vector3();
        const right = new THREE.Vector3();
        const up = new THREE.Vector3(0, 1, 0);

        // Get camera forward direction (full 3D direction including pitch)
        this.camera.getWorldDirection(forward);

        // Get right vector (perpendicular to forward and world up)
        right.crossVectors(forward, up).normalize();

        // Get camera's local up (for strafing vertically relative to view)
        const camUp = new THREE.Vector3();
        camUp.crossVectors(right, forward).normalize();

        // Apply movement - W/S move in look direction
        if (this.moveState.forward) this.camera.position.addScaledVector(forward, this.moveSpeed);
        if (this.moveState.backward) this.camera.position.addScaledVector(forward, -this.moveSpeed);
        if (this.moveState.left) this.camera.position.addScaledVector(right, -this.moveSpeed);
        if (this.moveState.right) this.camera.position.addScaledVector(right, this.moveSpeed);
        if (this.moveState.up) this.camera.position.addScaledVector(up, this.moveSpeed);
        if (this.moveState.down) this.camera.position.addScaledVector(up, -this.moveSpeed);

        // Update orbit controls target
        this.controls.target.copy(this.camera.position).add(forward.multiplyScalar(2));
    }

    createFloatingCandles() {
        // Create magical sparkle texture
        const canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');

        // Create a sparkle/star shape with radial gradient
        const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
        gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
        gradient.addColorStop(0.2, 'rgba(255, 255, 255, 0.8)');
        gradient.addColorStop(0.4, 'rgba(255, 255, 255, 0.4)');
        gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 64, 64);

        // Add star points
        ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        ctx.beginPath();
        for (let i = 0; i < 4; i++) {
            const angle = (i * Math.PI) / 2;
            const x1 = 32 + Math.cos(angle) * 28;
            const y1 = 32 + Math.sin(angle) * 28;
            const x2 = 32 + Math.cos(angle) * 4;
            const y2 = 32 + Math.sin(angle) * 4;
            ctx.moveTo(x2, y2);
            ctx.lineTo(x1, y1);
        }
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
        ctx.lineWidth = 2;
        ctx.stroke();

        const texture = new THREE.CanvasTexture(canvas);

        // Create magical floating sparkle particles
        const particleCount = 50;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const colors = new Float32Array(particleCount * 3);
        const sizes = new Float32Array(particleCount);
        const phases = new Float32Array(particleCount);

        // Magical color palette: purple, blue, gold, white
        const colorPalette = [
            new THREE.Color(0x9966ff), // Purple
            new THREE.Color(0x6699ff), // Blue
            new THREE.Color(0xffaa44), // Gold
            new THREE.Color(0xffffff), // White
            new THREE.Color(0xff66ff), // Magenta
            new THREE.Color(0x66ffff), // Cyan
        ];

        for (let i = 0; i < particleCount; i++) {
            // Random position in room
            positions[i * 3] = (Math.random() - 0.5) * 10;
            positions[i * 3 + 1] = Math.random() * 5 + 0.5;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 10;

            // Random color from palette
            const color = colorPalette[Math.floor(Math.random() * colorPalette.length)];
            colors[i * 3] = color.r;
            colors[i * 3 + 1] = color.g;
            colors[i * 3 + 2] = color.b;

            // Varying sizes for depth
            sizes[i] = Math.random() * 0.3 + 0.15;

            // Random phase for twinkling animation
            phases[i] = Math.random() * Math.PI * 2;
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
        geometry.setAttribute('phase', new THREE.BufferAttribute(phases, 1));

        const material = new THREE.PointsMaterial({
            size: 0.25,
            map: texture,
            transparent: true,
            opacity: 0.9,
            vertexColors: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
            sizeAttenuation: true
        });

        this.floatingCandles = new THREE.Points(geometry, material);
        this.scene.add(this.floatingCandles);

        // Store for animation
        this.particlePhases = phases;
        this.particleBaseSizes = new Float32Array(sizes); // Store base sizes for twinkling
        console.log('[MERLIN_SCENE] ✨ Created', particleCount, 'magical sparkle particles');
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        const time = Date.now() * 0.001;

        // Keep camera at fixed position unless in WASD debug mode
        if (!this.shiftPressed && this.fixedCameraPos) {
            this.camera.position.copy(this.fixedCameraPos);
            // Keep orbit target at camera pos for in-place rotation
            const dir = new THREE.Vector3(0, 0, -1).applyQuaternion(this.camera.quaternion);
            this.controls.target.copy(this.camera.position).add(dir.multiplyScalar(0.01));
        }

        // WASD movement (only when SHIFT held)
        this.updateMovement();

        // Update camera HUD
        this.updateHUD();

        // Flicker candle lights
        this.lights.forEach((light, i) => {
            if (light.color.getHex() !== 0x4466ff) { // Don't flicker magic light
                light.intensity = light.userData.baseIntensity || light.intensity;
                light.intensity += Math.sin(time * 3 + i) * 0.2;
                light.intensity += Math.random() * 0.1 - 0.05;
            }
        });

        // Animate magical sparkle particles
        if (this.floatingCandles && this.particlePhases && this.particleBaseSizes) {
            const positions = this.floatingCandles.geometry.attributes.position.array;
            const sizes = this.floatingCandles.geometry.attributes.size.array;

            for (let i = 0; i < this.particlePhases.length; i++) {
                // Gentle floating motion
                positions[i * 3 + 1] += Math.sin(time * 0.5 + this.particlePhases[i]) * 0.002;

                // Gentle horizontal drift
                positions[i * 3] += Math.cos(time * 0.3 + this.particlePhases[i]) * 0.001;
                positions[i * 3 + 2] += Math.sin(time * 0.3 + this.particlePhases[i]) * 0.001;

                // Twinkling effect (size variation based on stored base size)
                const baseSize = this.particleBaseSizes[i];
                const twinkle = Math.abs(Math.sin(time * 2 + this.particlePhases[i]));
                sizes[i] = baseSize * (0.5 + twinkle * 0.5);

                // Wrap around bounds
                if (positions[i * 3 + 1] > 6) positions[i * 3 + 1] = 0.5;
                if (positions[i * 3 + 1] < 0.5) positions[i * 3 + 1] = 6;
            }

            this.floatingCandles.geometry.attributes.position.needsUpdate = true;
            this.floatingCandles.geometry.attributes.size.needsUpdate = true;

            // Slowly rotate entire particle system for magical effect
            this.floatingCandles.rotation.y += 0.0002;
        }

        // Store base intensities on first frame
        if (!this.lights[0]?.userData.baseIntensity) {
            this.lights.forEach(light => {
                light.userData.baseIntensity = light.intensity;
            });
        }

        // Animate floating candles
        if (this.floatingCandles) {
            const positions = this.floatingCandles.geometry.attributes.position.array;
            for (let i = 0; i < positions.length; i += 3) {
                positions[i + 1] += Math.sin(time + i) * 0.002;
            }
            this.floatingCandles.geometry.attributes.position.needsUpdate = true;
            this.floatingCandles.rotation.y += 0.0005;
        }

        // Pulse magic light
        const magicLight = this.lights.find(l => l.color.getHex() === 0x4466ff);
        if (magicLight) {
            magicLight.intensity = 0.5 + Math.sin(time * 2) * 0.2;
        }

        // Only update orbit controls when NOT in free-fly mode
        if (!this.shiftPressed) {
            this.controls.update();
        }

        this.renderer.render(this.scene, this.camera);
    }

    exportCameraConfig() {
        const dir = new THREE.Vector3();
        this.camera.getWorldDirection(dir);

        const config = {
            position: {
                x: parseFloat(this.camera.position.x.toFixed(2)),
                y: parseFloat(this.camera.position.y.toFixed(2)),
                z: parseFloat(this.camera.position.z.toFixed(2)),
            },
            target: {
                x: parseFloat(this.controls.target.x.toFixed(2)),
                y: parseFloat(this.controls.target.y.toFixed(2)),
                z: parseFloat(this.controls.target.z.toFixed(2)),
            },
            direction: {
                x: parseFloat(dir.x.toFixed(2)),
                y: parseFloat(dir.y.toFixed(2)),
                z: parseFloat(dir.z.toFixed(2)),
            },
            fov: this.camera.fov,
            description: "Camera position exported via SHIFT+C"
        };

        console.log('='.repeat(70));
        console.log('📷 CAMERA CONFIG - Copy this to scenes/wizard/camera_config.json:');
        console.log('='.repeat(70));
        console.log(JSON.stringify(config, null, 2));
        console.log('='.repeat(70));

        return config;
    }

    onWindowResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    dispose() {
        // Clean up resources
        if (this.model) {
            this.scene.remove(this.model);
        }
        if (this.hudElement) {
            this.hudElement.remove();
        }
        this.renderer.dispose();
    }
}
