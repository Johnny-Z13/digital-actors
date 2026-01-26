/**
 * BaseScene - Abstract base class for all 3D scene implementations.
 *
 * This defines the interface contract that all scenes must implement.
 * Provides common functionality and ensures consistent behavior.
 *
 * GLOBAL vs SCENE-SPECIFIC:
 * - BaseScene defines the GLOBAL interface (lifecycle, state updates)
 * - Subclasses implement SCENE-SPECIFIC visuals and interactions
 */

import * as THREE from 'three';

export class BaseScene {
    /**
     * Create a new scene.
     * @param {HTMLElement} container - DOM element to render into
     * @param {Function} onButtonClick - Callback for button/control interactions
     * @param {Object} sceneConfig - Optional scene configuration from server
     */
    constructor(container, onButtonClick = () => {}, sceneConfig = null) {
        if (new.target === BaseScene) {
            throw new Error('BaseScene is abstract and cannot be instantiated directly');
        }

        this.container = container;
        this.onButtonClick = onButtonClick;
        this.sceneConfig = sceneConfig;

        // Three.js core objects - initialized by subclasses
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;

        // Animation state
        this.clock = new THREE.Clock();
        this.isDisposed = false;
        this.animationFrameId = null;

        // Interaction state
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.interactiveObjects = [];
        this.hoveredObject = null;

        // Bound event handlers (for cleanup)
        this._boundOnResize = this.onWindowResize.bind(this);
        this._boundOnMouseMove = this._onMouseMove.bind(this);
        this._boundOnClick = this._onClick.bind(this);
    }

    // =========================================================================
    // LIFECYCLE METHODS - Must be called by subclasses
    // =========================================================================

    /**
     * Initialize the scene. Call this at the end of subclass constructor.
     * Sets up renderer, event listeners, and starts animation loop.
     */
    init() {
        // Validate subclass setup
        if (!this.scene || !this.camera || !this.renderer) {
            throw new Error('Subclass must create scene, camera, and renderer before calling init()');
        }

        // Add renderer to container
        this.container.appendChild(this.renderer.domElement);

        // Setup event listeners
        window.addEventListener('resize', this._boundOnResize);
        window.addEventListener('mousemove', this._boundOnMouseMove);
        window.addEventListener('click', this._boundOnClick);

        // Start animation loop
        this.animate();

        console.log(`[${this.constructor.name}] Initialized`);
    }

    /**
     * Clean up all resources. MUST be called when switching scenes.
     * Subclasses should override and call super.dispose().
     */
    dispose() {
        console.log(`[${this.constructor.name}] Disposing...`);

        this.isDisposed = true;

        // Stop animation loop
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }

        // Remove event listeners
        window.removeEventListener('resize', this._boundOnResize);
        window.removeEventListener('mousemove', this._boundOnMouseMove);
        window.removeEventListener('click', this._boundOnClick);

        // Dispose Three.js objects
        if (this.renderer) {
            this.renderer.dispose();
            if (this.renderer.domElement && this.renderer.domElement.parentNode) {
                this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
            }
        }

        // Dispose geometries and materials in scene
        if (this.scene) {
            this.scene.traverse((object) => {
                if (object.geometry) {
                    object.geometry.dispose();
                }
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

        console.log(`[${this.constructor.name}] Disposed`);
    }

    /**
     * Alias for dispose() - some code uses destroy()
     */
    destroy() {
        this.dispose();
    }

    // =========================================================================
    // ANIMATION LOOP - Override render() for custom per-frame logic
    // =========================================================================

    /**
     * Main animation loop. Calls render() each frame.
     */
    animate() {
        if (this.isDisposed) return;

        this.animationFrameId = requestAnimationFrame(() => this.animate());

        // Update controls if present
        if (this.controls && this.controls.update) {
            this.controls.update();
        }

        // Call subclass render logic
        this.render();

        // Render the scene
        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }
    }

    /**
     * Per-frame render logic. Override in subclasses for animations.
     * Called every frame before Three.js render.
     */
    render() {
        // Subclasses override this for custom animations
    }

    // =========================================================================
    // STATE INTERFACE - Called by app.js to update scene state
    // =========================================================================

    /**
     * Update scene state from server.
     * Routes to specific setter methods based on state keys.
     * @param {Object} updates - Key-value pairs of state updates
     */
    updateState(updates) {
        if (!updates) return;

        Object.entries(updates).forEach(([key, value]) => {
            // Try to call a specific setter (e.g., setOxygen, setRadiation)
            const setterName = `set${this._capitalize(key)}`;
            if (typeof this[setterName] === 'function') {
                this[setterName](value);
            }
        });
    }

    /**
     * Set the current game phase. Override for phase-based visuals.
     * @param {number} phase - Phase number
     */
    setPhase(phase) {
        // Subclasses override for phase-specific UI changes
    }

    // Convenience state setters - subclasses override as needed
    setOxygenLevel(level) {}
    setRadiationLevel(level) {}
    setTimeRemaining(time) {}
    setHullPressure(pressure) {}
    setTrustLevel(level) {}
    setSystemsRepaired(count) {}

    // =========================================================================
    // EVENT HANDLERS - Common interaction handling
    // =========================================================================

    /**
     * Handle window resize. Override for custom behavior.
     */
    onWindowResize() {
        if (!this.camera || !this.renderer) return;

        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    /**
     * Internal mouse move handler.
     */
    _onMouseMove(event) {
        this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

        // Subclasses can override onMouseMove for hover effects
        this.onMouseMove(event);
    }

    /**
     * Handle mouse move. Override for hover effects.
     */
    onMouseMove(event) {
        // Subclasses implement hover logic
    }

    /**
     * Internal click handler.
     */
    _onClick(event) {
        if (!this.camera || this.interactiveObjects.length === 0) return;

        this.raycaster.setFromCamera(this.mouse, this.camera);
        const intersects = this.raycaster.intersectObjects(this.interactiveObjects, true);

        if (intersects.length > 0) {
            const object = intersects[0].object;
            this.onClick(object, event);
        }
    }

    /**
     * Handle click on interactive object. Override for custom click handling.
     * @param {THREE.Object3D} object - The clicked object
     * @param {MouseEvent} event - The click event
     */
    onClick(object, event) {
        // Check for userData action
        if (object.userData && object.userData.action) {
            this.onButtonClick(object.userData.action);
        }
    }

    // =========================================================================
    // UTILITY METHODS
    // =========================================================================

    /**
     * Capitalize first letter of a string.
     */
    _capitalize(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    /**
     * Create a standard perspective camera.
     */
    createDefaultCamera(fov = 55, near = 0.1, far = 1000) {
        return new THREE.PerspectiveCamera(
            fov,
            window.innerWidth / window.innerHeight,
            near,
            far
        );
    }

    /**
     * Create a standard WebGL renderer.
     */
    createDefaultRenderer(options = {}) {
        const renderer = new THREE.WebGLRenderer({
            antialias: true,
            powerPreference: "high-performance",
            ...options
        });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        return renderer;
    }

    /**
     * Register an object as interactive (clickable).
     */
    addInteractiveObject(object) {
        if (!this.interactiveObjects.includes(object)) {
            this.interactiveObjects.push(object);
        }
    }

    /**
     * Unregister an interactive object.
     */
    removeInteractiveObject(object) {
        const index = this.interactiveObjects.indexOf(object);
        if (index > -1) {
            this.interactiveObjects.splice(index, 1);
        }
    }
}
