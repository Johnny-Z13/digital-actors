/**
 * Foxhole Scene - The Prospero Bridge
 *
 * 3D environment for the Foxhole crisis scenario featuring the antiquated
 * Nautilus-inspired bridge of the deep-sea research vessel Prospero.
 *
 * Environment: 360° panoramic image
 */

import * as THREE from 'three';

export class FoxholeScene {
    constructor(container, onButtonClick) {
        this.container = container;
        this.onButtonClick = onButtonClick;

        // Three.js core objects
        this.scene = null;
        this.camera = null;
        this.renderer = null;

        // Scene objects
        this.panoramaSphere = null;
        this.lights = [];

        // State tracking
        this.currentPhase = 1;
        this.state = {
            powerLevel: 0,
            trajectoryStability: 0,
            oxygen: 100,
            phase: 1
        };

        // Animation
        this.animationFrameId = null;

        this.init();
    }

    async init() {
        // Create scene
        this.scene = new THREE.Scene();

        // Create camera
        this.camera = new THREE.PerspectiveCamera(
            75,
            this.container.clientWidth / this.container.clientHeight,
            0.1,
            1000
        );
        this.camera.position.set(0, 0, 0.1); // Slightly offset to avoid gimbal lock

        // Create renderer
        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: false
        });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.container.appendChild(this.renderer.domElement);

        // Load panoramic image as environment
        this.loadPanorama();

        // Add atmospheric lighting effects
        this.setupLighting();

        // Setup window resize handler
        this.onWindowResize = this.onWindowResize.bind(this);
        window.addEventListener('resize', this.onWindowResize);

        // Enable mouse drag to look around
        this.setupMouseControls();

        // Start animation loop
        this.animate();
    }

    loadPanorama() {
        // Create sphere geometry for panorama
        const geometry = new THREE.SphereGeometry(500, 60, 40);

        // Load texture
        const textureLoader = new THREE.TextureLoader();
        textureLoader.load(
            '/scenes/foxhole/foxhole_panorama.png',
            (texture) => {
                // Create material with texture - BackSide renders inside of sphere
                const material = new THREE.MeshBasicMaterial({
                    map: texture,
                    side: THREE.BackSide
                });

                // Create mesh
                this.panoramaSphere = new THREE.Mesh(geometry, material);
                this.scene.add(this.panoramaSphere);

                console.log('[Foxhole] Panorama loaded successfully');
            },
            undefined,
            (error) => {
                console.error('[Foxhole] Error loading panorama:', error);
                // Create fallback dark environment
                const material = new THREE.MeshBasicMaterial({
                    color: 0x1a2f4f,
                    side: THREE.BackSide
                });
                this.panoramaSphere = new THREE.Mesh(geometry, material);
                this.scene.add(this.panoramaSphere);
            }
        );
    }

    setupLighting() {
        // Ambient light to slightly brighten the panorama
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
        this.scene.add(ambientLight);
        this.lights.push(ambientLight);
    }

    setupMouseControls() {
        // Simple mouse drag to look around
        let isMouseDown = false;
        let previousMouseX = 0;
        let previousMouseY = 0;
        let cameraRotationX = 0;
        let cameraRotationY = 0;

        this.container.addEventListener('mousedown', (event) => {
            isMouseDown = true;
            previousMouseX = event.clientX;
            previousMouseY = event.clientY;
        });

        this.container.addEventListener('mouseup', () => {
            isMouseDown = false;
        });

        this.container.addEventListener('mousemove', (event) => {
            if (!isMouseDown) return;

            const deltaX = event.clientX - previousMouseX;
            const deltaY = event.clientY - previousMouseY;

            cameraRotationY -= deltaX * 0.003;
            cameraRotationX -= deltaY * 0.003;

            // Limit vertical rotation
            cameraRotationX = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, cameraRotationX));

            this.camera.rotation.order = 'YXZ';
            this.camera.rotation.x = cameraRotationX;
            this.camera.rotation.y = cameraRotationY;

            previousMouseX = event.clientX;
            previousMouseY = event.clientY;
        });

        // Touch controls for mobile
        let touchStartX = 0;
        let touchStartY = 0;

        this.container.addEventListener('touchstart', (event) => {
            if (event.touches.length === 1) {
                touchStartX = event.touches[0].clientX;
                touchStartY = event.touches[0].clientY;
            }
        });

        this.container.addEventListener('touchmove', (event) => {
            if (event.touches.length === 1) {
                const deltaX = event.touches[0].clientX - touchStartX;
                const deltaY = event.touches[0].clientY - touchStartY;

                cameraRotationY -= deltaX * 0.003;
                cameraRotationX -= deltaY * 0.003;

                cameraRotationX = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, cameraRotationX));

                this.camera.rotation.order = 'YXZ';
                this.camera.rotation.x = cameraRotationX;
                this.camera.rotation.y = cameraRotationY;

                touchStartX = event.touches[0].clientX;
                touchStartY = event.touches[0].clientY;
            }
        });
    }

    animate() {
        this.animationFrameId = requestAnimationFrame(this.animate.bind(this));

        this.renderer.render(this.scene, this.camera);
    }

    /**
     * Update scene state from server
     */
    updateState(state) {
        this.state = { ...this.state, ...state };

        // Update visual feedback based on state
        if (state.powerLevel !== undefined) {
            this.updatePowerLevel(state.powerLevel);
        }

        if (state.oxygen !== undefined) {
            this.updateOxygenLevel(state.oxygen);
        }

        if (state.phase !== undefined && state.phase !== this.currentPhase) {
            this.setPhase(state.phase);
        }
    }

    /**
     * Update power level visual feedback
     */
    updatePowerLevel(powerLevel) {
        // Adjust ambient light based on power level
        if (this.lights[0]) {
            this.lights[0].intensity = 0.2 + (powerLevel / 100) * 0.5;
        }
    }

    /**
     * Update oxygen level visual feedback
     */
    updateOxygenLevel(oxygen) {
        // Darken scene as oxygen depletes
        if (this.lights[0] && oxygen < 50) {
            const oxygenFactor = oxygen / 50;
            this.lights[0].intensity = 0.2 * oxygenFactor;
        }
    }

    /**
     * Handle phase transitions
     */
    setPhase(phase) {
        console.log(`[Foxhole] Phase transition: ${this.currentPhase} → ${phase}`);
        this.currentPhase = phase;

        // Phase-specific visual changes
        switch (phase) {
            case 1:
                // Power out, very dim
                if (this.lights[0]) this.lights[0].intensity = 0.2;
                break;
            case 2:
                // Power restored, lights brighten
                if (this.lights[0]) this.lights[0].intensity = 0.5;
                break;
            case 3:
            case 4:
                // Crisis deepens
                if (this.lights[0]) this.lights[0].intensity = 0.4;
                break;
            case 5:
                // Grief spiral - darker, more oppressive
                if (this.lights[0]) this.lights[0].intensity = 0.3;
                break;
            case 6:
                // Resolution - clarity returns
                if (this.lights[0]) this.lights[0].intensity = 0.5;
                break;
        }
    }

    /**
     * Handle window resize
     */
    onWindowResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();

        this.renderer.setSize(width, height);
    }

    /**
     * Clean up scene resources
     */
    dispose() {
        // Cancel animation
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
        }

        // Remove event listeners
        window.removeEventListener('resize', this.onWindowResize);

        // Dispose Three.js resources
        this.scene.traverse((object) => {
            if (object.geometry) {
                object.geometry.dispose();
            }
            if (object.material) {
                if (Array.isArray(object.material)) {
                    object.material.forEach(material => {
                        if (material.map) material.map.dispose();
                        material.dispose();
                    });
                } else {
                    if (object.material.map) object.material.map.dispose();
                    object.material.dispose();
                }
            }
        });

        this.renderer.dispose();
        this.renderer.domElement.remove();

        console.log('[Foxhole] Scene disposed');
    }
}

export default FoxholeScene;
