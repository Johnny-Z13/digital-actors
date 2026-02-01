import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

/**
 * WorldLabsImporter - Standardized utility for importing World Labs GLB environments
 *
 * Features:
 * - Automatic model scaling and centering
 * - Smart camera positioning based on bounding box heuristics
 * - Load/save camera presets from camera_config.json
 * - Material fixes (brighten pure black materials)
 * - Developer workflow: SHIFT+C to export camera positions
 */
export class WorldLabsImporter {
    /**
     * Load and position World Labs GLB model with automatic camera setup
     * @param {string} modelPath - Path to GLB file (e.g., "/scenes/wizard/merlins_workshop.glb")
     * @param {THREE.Scene} scene - Three.js scene to add model to
     * @param {THREE.Camera} camera - Camera to position
     * @param {Object} options - Import options
     * @returns {Promise<Object>} - { model, cameraConfig, bounds, scale }
     */
    static async load(modelPath, scene, camera, options = {}) {
        const defaults = {
            targetSize: 15,           // Scale model to this many units (width)
            cameraConfigPath: null,   // Optional: path to camera_config.json
            autoPositionCamera: true, // Auto-calculate camera position from bounds
            groundAtZero: true,       // Place model bottom at y=0
            centerHorizontally: true, // Center model at x=0, z=0
            fixBlackMaterials: true,  // Brighten pure black materials
            enableShadows: true,      // Enable shadow casting/receiving
        };

        const opts = { ...defaults, ...options };
        const loader = new GLTFLoader();

        console.log('[WorldLabsImporter] Loading:', modelPath);

        return new Promise((resolve, reject) => {
            loader.load(
                modelPath,
                async (gltf) => {
                    const model = gltf.scene;

                    // Calculate original bounding box
                    const box = new THREE.Box3().setFromObject(model);
                    const size = box.getSize(new THREE.Vector3());
                    const center = box.getCenter(new THREE.Vector3());

                    console.log('[WorldLabsImporter] Original size:', size, 'center:', center);

                    // 1. Auto-scale to target size
                    const maxDim = Math.max(size.x, size.y, size.z);
                    const scale = opts.targetSize / maxDim;
                    model.scale.setScalar(scale);

                    // Recalculate after scaling
                    box.setFromObject(model);
                    box.getCenter(center);
                    box.getSize(size);

                    // 2. Auto-position model
                    if (opts.centerHorizontally) {
                        model.position.x = -center.x;
                        model.position.z = -center.z;
                    }
                    if (opts.groundAtZero) {
                        model.position.y = -box.min.y; // Bottom at y=0
                    }

                    // 3. Process materials and shadows
                    model.traverse((child) => {
                        if (child.isMesh) {
                            if (opts.enableShadows) {
                                child.castShadow = true;
                                child.receiveShadow = true;
                            }

                            if (opts.fixBlackMaterials && child.material) {
                                const materials = Array.isArray(child.material)
                                    ? child.material
                                    : [child.material];
                                materials.forEach(mat => {
                                    if (mat.color && mat.color.getHex() === 0x000000) {
                                        mat.color.setHex(0x888888); // Brighten pure black
                                    }
                                    mat.needsUpdate = true;
                                });
                            }
                        }
                    });

                    scene.add(model);

                    // 4. Camera positioning
                    let cameraConfig = null;

                    // Try to load saved camera config first
                    if (opts.cameraConfigPath) {
                        try {
                            const response = await fetch(opts.cameraConfigPath);
                            if (response.ok) {
                                cameraConfig = await response.json();
                                console.log('[WorldLabsImporter] Loaded camera config:', cameraConfig);
                            }
                        } catch (err) {
                            console.warn('[WorldLabsImporter] No camera config found, using auto-positioning');
                        }
                    }

                    // If no config, calculate automatic camera position
                    if (!cameraConfig && opts.autoPositionCamera) {
                        cameraConfig = this.calculateCameraPosition(box, size, center);
                        console.log('[WorldLabsImporter] Auto-calculated camera position:', cameraConfig);
                    }

                    // Apply camera config
                    if (cameraConfig && camera) {
                        camera.position.set(
                            cameraConfig.position.x,
                            cameraConfig.position.y,
                            cameraConfig.position.z
                        );
                    }

                    resolve({
                        model,
                        cameraConfig,
                        bounds: { box, size, center },
                        scale
                    });
                },
                (progress) => {
                    const percent = (progress.loaded / progress.total * 100).toFixed(1);
                    console.log('[WorldLabsImporter] Progress:', percent + '%');
                },
                (error) => {
                    console.error('[WorldLabsImporter] Load error:', error);
                    reject(error);
                }
            );
        });
    }

    /**
     * Calculate optimal camera position from model bounding box
     * Uses heuristics to find a good viewing angle
     */
    static calculateCameraPosition(box, size, center) {
        // Strategy: Position camera to see ~70% of model height, offset from center

        const diagonal = Math.sqrt(size.x * size.x + size.z * size.z);

        // Calculate camera distance to fit model in view (FOV ~60 degrees)
        const fov = 60;
        const fovRad = (fov * Math.PI) / 180;
        const maxDim = Math.max(size.x, size.y, size.z);
        const distance = (maxDim / 2) / Math.tan(fovRad / 2) * 1.2; // 20% margin

        // Position camera at:
        // - 30% of model height above center (look slightly down)
        // - 0.7 * distance back in Z (front-ish view)
        // - Slight X offset for depth perception
        const cameraPos = {
            x: diagonal * 0.15,  // Slight right offset
            y: center.y + size.y * 0.3,  // 30% above center
            z: center.z + distance * 0.7,  // Front view
        };

        // Target center of model (slightly lower than geometric center)
        const targetPos = {
            x: center.x,
            y: center.y - size.y * 0.1,  // Look 10% below center
            z: center.z,
        };

        // Calculate direction vector (for orbit controls)
        const dir = new THREE.Vector3(
            targetPos.x - cameraPos.x,
            targetPos.y - cameraPos.y,
            targetPos.z - cameraPos.z
        ).normalize();

        return {
            position: cameraPos,
            target: targetPos,
            direction: { x: dir.x, y: dir.y, z: dir.z },
            fov: 60,
        };
    }

    /**
     * Save current camera position to config file (for dev/debugging)
     * Call this from browser console after finding good camera position
     * @param {THREE.Camera} camera - Camera to export
     * @param {Object} controls - OrbitControls or similar with target property
     * @returns {Object} Camera config object (copy to camera_config.json)
     */
    static exportCameraConfig(camera, controls) {
        const config = {
            position: {
                x: parseFloat(camera.position.x.toFixed(2)),
                y: parseFloat(camera.position.y.toFixed(2)),
                z: parseFloat(camera.position.z.toFixed(2)),
            },
            target: controls && controls.target ? {
                x: parseFloat(controls.target.x.toFixed(2)),
                y: parseFloat(controls.target.y.toFixed(2)),
                z: parseFloat(controls.target.z.toFixed(2)),
            } : null,
            fov: camera.fov,
            description: "Camera position exported via SHIFT+C"
        };

        console.log('='.repeat(60));
        console.log('Camera config (copy to camera_config.json):');
        console.log('='.repeat(60));
        console.log(JSON.stringify(config, null, 2));
        console.log('='.repeat(60));

        return config;
    }

    /**
     * Setup keyboard shortcut for exporting camera config
     * @param {THREE.Camera} camera - Camera to export
     * @param {Object} controls - OrbitControls or similar
     */
    static setupExportShortcut(camera, controls) {
        const handleKeyPress = (e) => {
            if (e.key === 'C' && e.shiftKey) {
                this.exportCameraConfig(camera, controls);
            }
        };

        window.addEventListener('keydown', handleKeyPress);
        console.log('[WorldLabsImporter] Press SHIFT+C to export camera config');

        // Return cleanup function
        return () => window.removeEventListener('keydown', handleKeyPress);
    }
}
