import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

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

        // Store fixed camera position
        this.fixedCameraPos = new THREE.Vector3(1.13, 2.92, 1.58);

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

    loadModel() {
        const loader = new GLTFLoader();
        const modelPath = "/art/merlins_workshop.glb";

        console.log('[MERLIN_SCENE] Loading model:', modelPath);

        loader.load(
            modelPath,
            (gltf) => {
                this.model = gltf.scene;

                // Calculate bounding box to properly position/scale model
                const box = new THREE.Box3().setFromObject(this.model);
                const size = box.getSize(new THREE.Vector3());
                const center = box.getCenter(new THREE.Vector3());

                console.log('[MERLIN_SCENE] Model loaded. Size:', size, 'Center:', center);

                // Scale model to fit nicely in view (target ~15 units wide - 300% larger)
                const maxDim = Math.max(size.x, size.y, size.z);
                const scale = 15 / maxDim;
                this.model.scale.setScalar(scale);

                // Recalculate after scaling
                box.setFromObject(this.model);
                box.getCenter(center);
                box.getSize(size);

                // Center model horizontally and place on ground
                this.model.position.x = -center.x;
                this.model.position.y = -box.min.y; // Place bottom at y=0
                this.model.position.z = -center.z;

                // Process all meshes - fix materials and enable shadows
                this.model.traverse((child) => {
                    if (child.isMesh) {
                        child.castShadow = true;
                        child.receiveShadow = true;

                        // Ensure materials respond to light properly
                        if (child.material) {
                            // Handle array of materials
                            const materials = Array.isArray(child.material) ? child.material : [child.material];
                            materials.forEach(mat => {
                                // Make sure material is not too dark
                                if (mat.color && mat.color.getHex() === 0x000000) {
                                    mat.color.setHex(0x888888);
                                }
                                // Ensure material uses lights
                                mat.needsUpdate = true;

                                // Log material info for debugging
                                console.log('[MERLIN_SCENE] Material:', mat.type, 'color:', mat.color?.getHexString());
                            });
                        }
                    }
                });

                this.scene.add(this.model);

                // Position camera at user-defined sweet spot
                this.camera.position.set(1.13, 2.92, 1.58);
                this.fixedCameraPos.set(1.13, 2.92, 1.58);

                // Set orbit target slightly in front of camera (for in-place rotation)
                const dir = new THREE.Vector3(-0.66, 0.06, -0.75).normalize();
                this.controls.target.copy(this.camera.position).add(dir.multiplyScalar(0.01));
                this.controls.update();

                console.log('[MERLIN_SCENE] Camera fixed - drag to look, scroll to zoom FOV');

                console.log('[MERLIN_SCENE] Model positioned. Camera at:', this.camera.position);
            },
            (progress) => {
                const percent = (progress.loaded / progress.total * 100).toFixed(1);
                console.log('[MERLIN_SCENE] Loading progress:', percent + '%');
            },
            (error) => {
                console.error('[MERLIN_SCENE] Error loading model:', error);
                // Fallback: create a simple placeholder
                this.createFallbackScene();
            }
        );
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
            if (e.key === 'Shift') {
                this.shiftPressed = true;
                this.controls.enabled = false; // Disable orbit controls
            }
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
        `;
        document.body.appendChild(this.hudElement);
    }

    updateHUD() {
        if (!this.hudElement || !this.camera) return;

        const pos = this.camera.position;
        const rot = this.camera.rotation;
        const dir = new THREE.Vector3(0, 0, -1).applyQuaternion(this.camera.quaternion);

        this.hudElement.innerHTML = `
            Drag: Look | Scroll: Zoom (FOV)<br>
            <span style="color:#888">SHIFT+WASD: Debug fly</span><br>
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
        // Create magical floating particle lights
        const particleCount = 30;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);

        for (let i = 0; i < particleCount; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 8;
            positions[i * 3 + 1] = Math.random() * 4 + 0.5;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 8;
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const material = new THREE.PointsMaterial({
            color: 0xffaa44,
            size: 0.15,
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending
        });

        this.floatingCandles = new THREE.Points(geometry, material);
        this.scene.add(this.floatingCandles);
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

        this.controls.update();
        this.renderer.render(this.scene, this.camera);
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
