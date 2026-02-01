import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export class WelcomeScene {
    constructor(container, onButtonClick) {
        this.container = container;
        this.onButtonClick = onButtonClick || (() => {});
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;

        // Clippy the paper clip
        this.clippy = null;
        this.leftEye = null;
        this.rightEye = null;
        this.leftPupil = null;
        this.rightPupil = null;

        // Animation state
        this.time = 0;
        this.blinkTimer = 0;
        this.isBlinking = false;
        this.lookTarget = new THREE.Vector3(0, 0, 1);

        // Framerate limiting
        this.targetFPS = 60;
        this.frameInterval = 1000 / this.targetFPS;
        this.lastFrameTime = 0;

        // UI overlay element
        this.welcomeOverlay = null;

        this.init();
        this.createWelcomeUI();
        this.animate();
        this.setupInteraction();
    }

    init() {
        // Scene with retro Windows 95 background (for Clippy!)
        this.scene = new THREE.Scene();

        // Load Windows 95 desktop background texture with proper aspect handling
        const textureLoader = new THREE.TextureLoader();

        console.log('[WelcomeScene] Attempting to load background from: /art/win95DeskTop.jpg');

        textureLoader.load(
            '/art/win95DeskTop.jpg',
            (texture) => {
                // Success - calculate aspect ratio and create proper background
                console.log('[WelcomeScene] Background texture loaded successfully!');
                const img = texture.image;
                const imgAspect = img.width / img.height;
                const windowAspect = window.innerWidth / window.innerHeight;

                console.log('[WelcomeScene] Image dimensions:', img.width, 'x', img.height, 'Aspect:', imgAspect);

                // Adjust texture repeat/offset to fill screen while maintaining aspect
                if (windowAspect > imgAspect) {
                    // Window is wider - fit to width
                    texture.repeat.y = imgAspect / windowAspect;
                    texture.offset.y = (1 - texture.repeat.y) / 2;
                } else {
                    // Window is taller - fit to height
                    texture.repeat.x = windowAspect / imgAspect;
                    texture.offset.x = (1 - texture.repeat.x) / 2;
                }

                this.scene.background = texture;
                console.log('[WelcomeScene] ✓ Win95 background applied to scene');
            },
            (progress) => {
                // Progress callback
                if (progress.lengthComputable) {
                    const percentComplete = (progress.loaded / progress.total) * 100;
                    console.log('[WelcomeScene] Loading background:', percentComplete.toFixed(0) + '%');
                }
            },
            (error) => {
                // Fallback to solid color if image fails to load
                console.error('[WelcomeScene] ❌ Failed to load Win95 background:', error);
                console.error('[WelcomeScene] Error type:', error.type);
                console.error('[WelcomeScene] Error target:', error.target);
                console.error('[WelcomeScene] Error message:', error.message || 'No message');
                this.scene.background = new THREE.Color(0x1a1a2e);
            }
        );

        // Camera
        this.camera = new THREE.PerspectiveCamera(
            60,
            window.innerWidth / window.innerHeight,
            0.1,
            1000
        );
        this.camera.position.set(0, 0.5, 3.5);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            powerPreference: "high-performance"
        });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.container.appendChild(this.renderer.domElement);

        // Controls
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.enableZoom = true;
        this.controls.minDistance = 2;
        this.controls.maxDistance = 6;
        this.controls.target.set(0, 0.3, 0);

        // Build scene
        this.createClippy();
        this.setupLights();

        window.addEventListener('resize', () => this.onWindowResize());
    }

    createClippy() {
        // Create the paper clip body using a curved tube
        const clipGroup = new THREE.Group();

        // Paper clip wire material - shiny silver
        const wireMaterial = new THREE.MeshStandardMaterial({
            color: 0xC0C0C0,
            roughness: 0.3,
            metalness: 0.9,
        });

        // Create paper clip shape using curves
        const wireRadius = 0.08;

        // Outer loop (bottom)
        const outerCurve = new THREE.CatmullRomCurve3([
            new THREE.Vector3(-0.4, -1.2, 0),
            new THREE.Vector3(-0.5, -0.8, 0),
            new THREE.Vector3(-0.5, 0.3, 0),
            new THREE.Vector3(-0.4, 0.7, 0),
            new THREE.Vector3(0, 0.9, 0),
            new THREE.Vector3(0.4, 0.7, 0),
            new THREE.Vector3(0.5, 0.3, 0),
            new THREE.Vector3(0.5, -0.5, 0),
            new THREE.Vector3(0.4, -0.8, 0),
            new THREE.Vector3(0.1, -0.9, 0),
        ]);

        const outerGeometry = new THREE.TubeGeometry(outerCurve, 50, wireRadius, 12, false);
        const outerWire = new THREE.Mesh(outerGeometry, wireMaterial);
        clipGroup.add(outerWire);

        // Inner loop (creates the paper clip shape)
        const innerCurve = new THREE.CatmullRomCurve3([
            new THREE.Vector3(0.1, -0.9, 0),
            new THREE.Vector3(-0.2, -0.7, 0),
            new THREE.Vector3(-0.3, -0.3, 0),
            new THREE.Vector3(-0.3, 0.4, 0),
            new THREE.Vector3(-0.2, 0.6, 0),
            new THREE.Vector3(0, 0.7, 0),
            new THREE.Vector3(0.2, 0.6, 0),
            new THREE.Vector3(0.3, 0.3, 0),
            new THREE.Vector3(0.3, -0.2, 0),
        ]);

        const innerGeometry = new THREE.TubeGeometry(innerCurve, 40, wireRadius, 12, false);
        const innerWire = new THREE.Mesh(innerGeometry, wireMaterial);
        clipGroup.add(innerWire);

        // Add googly eyes
        this.createGooglyEyes(clipGroup);

        // Position and add to scene
        clipGroup.position.set(0, 0.3, 0);
        clipGroup.scale.set(1.3, 1.3, 1.3);
        this.clippy = clipGroup;
        this.scene.add(clipGroup);
    }

    createGooglyEyes(parent) {
        // Eye socket material (white)
        const eyeWhiteMaterial = new THREE.MeshStandardMaterial({
            color: 0xFFFFFF,
            roughness: 0.3,
            metalness: 0.0,
        });

        // Pupil material (black)
        const pupilMaterial = new THREE.MeshStandardMaterial({
            color: 0x000000,
            roughness: 0.5,
            metalness: 0.0,
        });

        // Eye size
        const eyeRadius = 0.18;
        const pupilRadius = 0.08;

        // Left eye
        const leftEyeGeometry = new THREE.SphereGeometry(eyeRadius, 24, 24);
        this.leftEye = new THREE.Mesh(leftEyeGeometry, eyeWhiteMaterial);
        this.leftEye.position.set(-0.18, 0.35, 0.15);
        parent.add(this.leftEye);

        // Left pupil
        const leftPupilGeometry = new THREE.SphereGeometry(pupilRadius, 16, 16);
        this.leftPupil = new THREE.Mesh(leftPupilGeometry, pupilMaterial);
        this.leftPupil.position.set(0, 0, eyeRadius - 0.02);
        this.leftEye.add(this.leftPupil);

        // Right eye
        const rightEyeGeometry = new THREE.SphereGeometry(eyeRadius, 24, 24);
        this.rightEye = new THREE.Mesh(rightEyeGeometry, eyeWhiteMaterial);
        this.rightEye.position.set(0.18, 0.35, 0.15);
        parent.add(this.rightEye);

        // Right pupil
        const rightPupilGeometry = new THREE.SphereGeometry(pupilRadius, 16, 16);
        this.rightPupil = new THREE.Mesh(rightPupilGeometry, pupilMaterial);
        this.rightPupil.position.set(0, 0, eyeRadius - 0.02);
        this.rightEye.add(this.rightPupil);
    }

    createWelcomeUI() {
        // Create screen-space UI overlay for welcome text
        this.welcomeOverlay = document.createElement('div');
        this.welcomeOverlay.id = 'welcome-overlay';
        this.welcomeOverlay.style.cssText = `
            position: fixed;
            top: 120px;
            left: 20px;
            max-width: 320px;
            padding: 20px;
            background: rgba(26, 26, 46, 0.85);
            border: 1px solid rgba(76, 175, 80, 0.4);
            border-radius: 8px;
            z-index: 100;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            pointer-events: none;
        `;

        this.welcomeOverlay.innerHTML = `
            <h3 style="
                color: #4CAF50;
                font-size: 16px;
                font-weight: 600;
                margin: 0 0 12px 0;
                text-align: left;
            ">Welcome to Digital Actors</h3>
            <p style="
                color: #CCCCCC;
                font-size: 13px;
                line-height: 1.6;
                margin: 0 0 10px 0;
                text-align: left;
            ">A playground to play, configure and create AI NPCs (APCs). Create Scenarios and interactive stories.</p>
            <p style="
                color: #999999;
                font-size: 12px;
                line-height: 1.5;
                margin: 0;
                text-align: left;
            ">Speak with Clippy here to find out more, or dive into the menus. Have fun! :)</p>
        `;

        document.body.appendChild(this.welcomeOverlay);
    }

    setupLights() {
        // Ambient light
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);

        // Main light
        const mainLight = new THREE.DirectionalLight(0xffffff, 1.0);
        mainLight.position.set(2, 3, 4);
        this.scene.add(mainLight);

        // Fill light
        const fillLight = new THREE.DirectionalLight(0x4CAF50, 0.3);
        fillLight.position.set(-2, 1, 2);
        this.scene.add(fillLight);

        // Rim light for Clippy
        const rimLight = new THREE.PointLight(0xFFFFFF, 0.5, 5);
        rimLight.position.set(0, 1, -1);
        this.scene.add(rimLight);
    }

    setupInteraction() {
        window.addEventListener('mousemove', (event) => {
            // Update look target for Clippy's eyes
            const mouseX = (event.clientX / window.innerWidth) * 2 - 1;
            const mouseY = -(event.clientY / window.innerHeight) * 2 + 1;
            this.lookTarget.set(mouseX * 2, mouseY * 2 + 0.3, 1);
        });
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        const currentTime = Date.now();
        const deltaTime = currentTime - this.lastFrameTime;

        if (deltaTime < this.frameInterval) {
            return;
        }

        this.lastFrameTime = currentTime - (deltaTime % this.frameInterval);
        this.time += deltaTime * 0.001;

        // Animate Clippy
        if (this.clippy) {
            // Gentle bobbing
            this.clippy.position.y = 0.3 + Math.sin(this.time * 2) * 0.05;

            // Slight rotation
            this.clippy.rotation.z = Math.sin(this.time * 1.5) * 0.05;
        }

        // Animate eyes following mouse
        this.animateEyes();

        // Handle blinking
        this.handleBlinking();

        if (this.controls) {
            this.controls.update();
        }
        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }
    }

    animateEyes() {
        if (!this.leftPupil || !this.rightPupil) return;

        // Calculate direction to look target
        const maxOffset = 0.06;

        // Left eye
        const leftDir = this.lookTarget.clone().sub(this.leftEye.getWorldPosition(new THREE.Vector3()));
        leftDir.normalize();
        this.leftPupil.position.x = THREE.MathUtils.clamp(leftDir.x * maxOffset, -maxOffset, maxOffset);
        this.leftPupil.position.y = THREE.MathUtils.clamp(leftDir.y * maxOffset, -maxOffset, maxOffset);

        // Right eye
        const rightDir = this.lookTarget.clone().sub(this.rightEye.getWorldPosition(new THREE.Vector3()));
        rightDir.normalize();
        this.rightPupil.position.x = THREE.MathUtils.clamp(rightDir.x * maxOffset, -maxOffset, maxOffset);
        this.rightPupil.position.y = THREE.MathUtils.clamp(rightDir.y * maxOffset, -maxOffset, maxOffset);
    }

    handleBlinking() {
        this.blinkTimer += 16;

        // Random blink every 2-5 seconds
        if (!this.isBlinking && this.blinkTimer > 2000 + Math.random() * 3000) {
            this.isBlinking = true;
            this.blinkTimer = 0;

            // Close eyes
            if (this.leftEye) this.leftEye.scale.y = 0.1;
            if (this.rightEye) this.rightEye.scale.y = 0.1;

            // Open after 150ms
            setTimeout(() => {
                if (this.leftEye) this.leftEye.scale.y = 1;
                if (this.rightEye) this.rightEye.scale.y = 1;
                this.isBlinking = false;
            }, 150);
        }
    }

    onWindowResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    /**
     * Clean up all resources. Called when switching scenes.
     */
    dispose() {
        console.log('[WELCOME] Disposing scene...');

        // Remove overlay
        if (this.welcomeOverlay && this.welcomeOverlay.parentNode) {
            this.welcomeOverlay.parentNode.removeChild(this.welcomeOverlay);
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
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;

        console.log('[WELCOME] Scene disposed');
    }

    /**
     * Alias for dispose()
     */
    destroy() {
        this.dispose();
    }

    // Public methods for state updates
    setTopicsExplored(count) {
        console.log('Topics explored:', count);
    }
}
