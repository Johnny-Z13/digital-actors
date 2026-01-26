import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

/**
 * DetectiveScene - 1980s NYC Private Eye Office
 *
 * A moody, atmospheric detective agency office with:
 * - Wooden desk with phone, papers, ashtray
 * - Large window with venetian blinds casting shadows
 * - NYC cityscape visible through window
 * - Filing cabinet, coat rack, bookshelf
 * - Noir lighting with dramatic shadows
 */
export class DetectiveScene {
    constructor(container, onButtonClick) {
        this.container = container;
        this.onButtonClick = onButtonClick || (() => {});
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.interactiveObjects = [];
        this.hoveredObject = null;
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.mouseNeedsUpdate = false;

        // Animation
        this.clock = new THREE.Clock();
        this.blindsLight = null;
        this.neonSign = null;
        this.raindrops = null;

        // Phone state
        this.phone = null;
        this.phoneRinging = false;
        this.phoneAnswered = false;
        this.ringInterval = null;
        this.audioContext = null;

        // Evidence board state
        this.evidencePins = [];
        this.hoveredPin = null;
        this.selectedPin = null;
        this.evidenceBoard = null;  // Reference to clickable board
        this.isPinFocusing = false; // Camera focus animation in progress

        // Camera view states
        this.currentView = 'desk';  // 'desk' or 'board'
        this.isTransitioning = false;
        this.cameraViews = {
            desk: {
                position: new THREE.Vector3(0, 2.0, 0.5),
                target: new THREE.Vector3(0, 0.75, -0.5),
                fov: 55
            },
            board: {
                position: new THREE.Vector3(0, 1.6, -0.3),
                target: new THREE.Vector3(0, 1.5, -1.2),
                fov: 50
            }
        };

        // Back button element
        this.backButton = null;

        // Tooltip for board hint
        this.boardTooltip = null;
        this.lastMouseEvent = null;

        // Performance
        this.targetFPS = 50;
        this.frameInterval = 1000 / this.targetFPS;
        this.lastFrameTime = 0;
        this.frameCount = 0;

        this.init();
        this.animate();
        this.setupInteraction();

        // Start phone ringing after scene loads
        setTimeout(() => this.startPhoneRinging(), 2000);
    }

    init() {
        // Scene with moody atmosphere
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a0a12);
        this.scene.fog = new THREE.Fog(0x0a0a12, 8, 20);

        // Camera - seated in front of the desk, looking down at it
        this.camera = new THREE.PerspectiveCamera(
            55,
            window.innerWidth / window.innerHeight,
            0.1,
            1000
        );
        // Position camera for desk view (can see both desk and board)
        this.camera.position.copy(this.cameraViews.desk.position);

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
        this.renderer.toneMappingExposure = 1.2;
        this.container.appendChild(this.renderer.domElement);

        // Set camera to look at desk initially
        this.camera.lookAt(this.cameraViews.desk.target);

        // Controls - limited movement, focused on desk area
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.08;
        this.controls.enableZoom = false;
        this.controls.enablePan = false;
        this.controls.minAzimuthAngle = -Math.PI / 3;
        this.controls.maxAzimuthAngle = Math.PI / 3;
        this.controls.minPolarAngle = Math.PI / 4;
        this.controls.maxPolarAngle = Math.PI / 2.2;
        // Look at the desk surface
        this.controls.target.copy(this.cameraViews.desk.target);
        this.controls.rotateSpeed = 0.4;
        this.controls.update();

        // Build the office
        this.createRoom();
        this.createWindow();
        this.createDesk();
        this.createFurniture();
        this.createEvidenceBoard();
        this.createAtmosphere();
        this.setupLights();
        this.loadPhoneModel();
        this.createBackButton();

        // Handle resize
        window.addEventListener('resize', () => this.onWindowResize());
    }

    createBackButton() {
        // Create back button for returning from board view
        this.backButton = document.createElement('button');
        this.backButton.innerHTML = '← Back to Desk';
        this.backButton.style.cssText = `
            position: fixed;
            top: 20px;
            left: 20px;
            padding: 12px 20px;
            font-size: 14px;
            font-weight: bold;
            background: rgba(0, 0, 0, 0.8);
            color: #ccc;
            border: 2px solid #555;
            border-radius: 6px;
            cursor: pointer;
            z-index: 1000;
            display: none;
            transition: all 0.2s ease;
            font-family: 'Courier New', monospace;
        `;
        this.backButton.onmouseover = () => {
            this.backButton.style.background = '#333';
            this.backButton.style.borderColor = '#888';
            this.backButton.style.color = '#fff';
        };
        this.backButton.onmouseout = () => {
            this.backButton.style.background = 'rgba(0, 0, 0, 0.8)';
            this.backButton.style.borderColor = '#555';
            this.backButton.style.color = '#ccc';
        };
        this.backButton.onclick = () => this.switchToView('desk');
        document.body.appendChild(this.backButton);

        // Create tooltip for board hover hint
        this.boardTooltip = document.createElement('div');
        this.boardTooltip.innerHTML = 'Click to examine evidence';
        this.boardTooltip.style.cssText = `
            position: fixed;
            padding: 8px 14px;
            font-size: 12px;
            background: rgba(0, 0, 0, 0.85);
            color: #ffd700;
            border: 1px solid #ffd700;
            border-radius: 4px;
            pointer-events: none;
            z-index: 1000;
            display: none;
            font-family: 'Courier New', monospace;
            white-space: nowrap;
        `;
        document.body.appendChild(this.boardTooltip);
    }

    switchToView(viewName) {
        if (this.isTransitioning || this.currentView === viewName) return;

        const targetView = this.cameraViews[viewName];
        if (!targetView) return;

        this.isTransitioning = true;
        this.currentView = viewName;

        console.log('[DETECTIVE] Switching to view:', viewName);

        // Animate camera transition
        const startPos = this.camera.position.clone();
        const startTarget = this.controls.target.clone();
        const duration = 800;
        const startTime = Date.now();

        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // Smooth easing
            const eased = 1 - Math.pow(1 - progress, 3);

            // Interpolate position
            this.camera.position.lerpVectors(startPos, targetView.position, eased);
            this.controls.target.lerpVectors(startTarget, targetView.target, eased);
            this.controls.update();

            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                this.isTransitioning = false;
                this.updateControlsForView(viewName);
                this.updateUIForView(viewName);
            }
        };

        animate();
    }

    updateControlsForView(viewName) {
        if (viewName === 'desk') {
            // Desk view - limited orbit around desk
            this.controls.minAzimuthAngle = -Math.PI / 3;
            this.controls.maxAzimuthAngle = Math.PI / 3;
            this.controls.minPolarAngle = Math.PI / 4;
            this.controls.maxPolarAngle = Math.PI / 2.2;
            this.controls.rotateSpeed = 0.4;
        } else if (viewName === 'board') {
            // Board view - more freedom to look around the board
            this.controls.minAzimuthAngle = -Math.PI / 4;
            this.controls.maxAzimuthAngle = Math.PI / 4;
            this.controls.minPolarAngle = Math.PI / 3;
            this.controls.maxPolarAngle = Math.PI / 1.8;
            this.controls.rotateSpeed = 0.3;
        }
        this.controls.update();
    }

    updateUIForView(viewName) {
        if (viewName === 'board') {
            this.backButton.style.display = 'block';
        } else {
            this.backButton.style.display = 'none';
        }
    }

    createRoom() {
        // Floor - worn wooden floorboards
        const floorGeometry = new THREE.PlaneGeometry(6, 5);
        const floorMaterial = new THREE.MeshStandardMaterial({
            color: 0x4a3520,
            roughness: 0.9,
            metalness: 0.1,
        });
        const floor = new THREE.Mesh(floorGeometry, floorMaterial);
        floor.rotation.x = -Math.PI / 2;
        floor.position.set(0, 0, -1);
        floor.receiveShadow = true;
        this.scene.add(floor);

        // Walls - darker wood paneling
        const wallMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a2018,
            roughness: 0.85,
            metalness: 0.05,
        });

        // Back wall (behind desk) - closer
        const backWall = new THREE.Mesh(
            new THREE.PlaneGeometry(6, 3),
            wallMaterial
        );
        backWall.position.set(0, 1.5, -2);
        backWall.receiveShadow = true;
        this.scene.add(backWall);

        // Left wall
        const leftWall = new THREE.Mesh(
            new THREE.PlaneGeometry(5, 3),
            wallMaterial
        );
        leftWall.position.set(-3, 1.5, -1);
        leftWall.rotation.y = Math.PI / 2;
        leftWall.receiveShadow = true;
        this.scene.add(leftWall);

        // Right wall (with window) - just partial walls around window
        const rightWallLower = new THREE.Mesh(
            new THREE.PlaneGeometry(5, 0.8),
            wallMaterial
        );
        rightWallLower.position.set(2.5, 0.4, -1);
        rightWallLower.rotation.y = -Math.PI / 2;
        this.scene.add(rightWallLower);

        const rightWallUpper = new THREE.Mesh(
            new THREE.PlaneGeometry(5, 0.6),
            wallMaterial
        );
        rightWallUpper.position.set(2.5, 2.7, -1);
        rightWallUpper.rotation.y = -Math.PI / 2;
        this.scene.add(rightWallUpper);

        // Ceiling
        const ceilingMaterial = new THREE.MeshStandardMaterial({
            color: 0x1a1510,
            roughness: 0.95,
        });
        const ceiling = new THREE.Mesh(
            new THREE.PlaneGeometry(6, 5),
            ceilingMaterial
        );
        ceiling.position.set(0, 3, -1);
        ceiling.rotation.x = Math.PI / 2;
        this.scene.add(ceiling);

        // Baseboard trim on back wall
        const baseboardMaterial = new THREE.MeshStandardMaterial({
            color: 0x1a1208,
            roughness: 0.7,
        });
        const baseboardBack = new THREE.Mesh(
            new THREE.BoxGeometry(6, 0.12, 0.04),
            baseboardMaterial
        );
        baseboardBack.position.set(0, 0.06, -1.97);
        this.scene.add(baseboardBack);
    }

    createWindow() {
        // Window frame - on the right side, visible from desk
        const frameMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a2018,
            roughness: 0.6,
            metalness: 0.2,
        });

        // Window opening (right wall, closer to camera)
        const windowWidth = 1.8;
        const windowHeight = 1.4;
        const windowY = 1.5;
        const windowZ = -0.3;
        const windowX = 2.5;

        // Frame pieces
        const frameThickness = 0.06;

        // Top frame
        const topFrame = new THREE.Mesh(
            new THREE.BoxGeometry(windowWidth + 0.15, frameThickness, 0.08),
            frameMaterial
        );
        topFrame.position.set(windowX, windowY + windowHeight / 2 + frameThickness / 2, windowZ);
        topFrame.rotation.y = -Math.PI / 2;
        this.scene.add(topFrame);

        // Bottom frame (sill)
        const sillMaterial = new THREE.MeshStandardMaterial({
            color: 0x3d2817,
            roughness: 0.5,
        });
        const sill = new THREE.Mesh(
            new THREE.BoxGeometry(windowWidth + 0.2, 0.05, 0.15),
            sillMaterial
        );
        sill.position.set(windowX - 0.03, windowY - windowHeight / 2, windowZ);
        sill.rotation.y = -Math.PI / 2;
        this.scene.add(sill);

        // Glass with city reflection
        const glassMaterial = new THREE.MeshPhysicalMaterial({
            color: 0x1a2a4a,
            transparent: true,
            opacity: 0.4,
            roughness: 0.05,
            metalness: 0.1,
            transmission: 0.5,
        });
        const glass = new THREE.Mesh(
            new THREE.PlaneGeometry(windowWidth, windowHeight),
            glassMaterial
        );
        glass.position.set(windowX + 0.02, windowY, windowZ);
        glass.rotation.y = -Math.PI / 2;
        this.scene.add(glass);

        // NYC cityscape outside (simple silhouette)
        this.createCityscape(windowZ, windowY, windowX);

        // Venetian blinds
        this.createVenetianBlinds(windowWidth, windowHeight, windowY, windowZ, windowX);
    }

    createCityscape(windowZ, windowY, windowX) {
        // Building silhouettes outside window
        const buildingMaterial = new THREE.MeshBasicMaterial({
            color: 0x080812,
        });

        const buildings = [
            { width: 0.4, height: 1.5, offset: -0.6, depth: 1 },
            { width: 0.3, height: 2.0, offset: -0.2, depth: 1.5 },
            { width: 0.5, height: 1.2, offset: 0.3, depth: 0.8 },
            { width: 0.35, height: 1.8, offset: 0.7, depth: 1.2 },
        ];

        buildings.forEach(b => {
            const building = new THREE.Mesh(
                new THREE.BoxGeometry(0.3, b.height, b.width),
                buildingMaterial
            );
            building.position.set(windowX + b.depth, windowY - 0.2 + b.height / 2, windowZ + b.offset);
            this.scene.add(building);

            // Random lit windows on buildings
            const windowMat = new THREE.MeshBasicMaterial({
                color: 0xffdd88,
                transparent: true,
                opacity: 0.9,
            });
            for (let i = 0; i < 5; i++) {
                if (Math.random() > 0.4) {
                    const win = new THREE.Mesh(
                        new THREE.PlaneGeometry(0.03, 0.05),
                        windowMat
                    );
                    win.position.set(
                        windowX + b.depth - 0.16,
                        windowY - 0.1 + Math.random() * (b.height - 0.3),
                        windowZ + b.offset + (Math.random() - 0.5) * (b.width * 0.5)
                    );
                    win.rotation.y = -Math.PI / 2;
                    this.scene.add(win);
                }
            }
        });

        // Neon sign across the street (flickering)
        const neonGeometry = new THREE.PlaneGeometry(0.5, 0.12);
        const neonMaterial = new THREE.MeshBasicMaterial({
            color: 0xff3366,
            transparent: true,
            opacity: 0.9,
        });
        this.neonSign = new THREE.Mesh(neonGeometry, neonMaterial);
        this.neonSign.position.set(windowX + 1.2, windowY + 0.3, windowZ);
        this.neonSign.rotation.y = -Math.PI / 2;
        this.scene.add(this.neonSign);
    }

    createVenetianBlinds(width, height, y, z, x) {
        // Venetian blind slats
        const slatCount = 10;
        const slatHeight = height / slatCount;
        const slatMaterial = new THREE.MeshStandardMaterial({
            color: 0xd4c4a8,
            roughness: 0.6,
            metalness: 0.1,
            side: THREE.DoubleSide,
        });

        for (let i = 0; i < slatCount; i++) {
            const slat = new THREE.Mesh(
                new THREE.BoxGeometry(width - 0.08, 0.015, 0.06),
                slatMaterial
            );
            slat.position.set(x - 0.02, y - height / 2 + slatHeight * (i + 0.5), z);
            slat.rotation.y = -Math.PI / 2;
            // Angle slats slightly open
            slat.rotation.z = 0.25;
            slat.castShadow = true;
            this.scene.add(slat);
        }
    }

    createDesk() {
        // Large wooden desk - positioned closer to camera
        const deskMaterial = new THREE.MeshStandardMaterial({
            color: 0x5a4530,
            roughness: 0.7,
            metalness: 0.1,
        });

        // Desktop - closer to camera at z=-0.5
        const desktop = new THREE.Mesh(
            new THREE.BoxGeometry(1.8, 0.08, 0.9),
            deskMaterial
        );
        desktop.position.set(0, 0.75, -0.5);
        desktop.castShadow = true;
        desktop.receiveShadow = true;
        this.scene.add(desktop);

        // Desk legs
        const legMaterial = new THREE.MeshStandardMaterial({
            color: 0x3a2815,
            roughness: 0.8,
        });
        const legPositions = [
            [-0.8, 0.375, -0.1],
            [0.8, 0.375, -0.1],
            [-0.8, 0.375, -0.9],
            [0.8, 0.375, -0.9],
        ];
        legPositions.forEach(pos => {
            const leg = new THREE.Mesh(
                new THREE.BoxGeometry(0.08, 0.75, 0.08),
                legMaterial
            );
            leg.position.set(...pos);
            leg.castShadow = true;
            this.scene.add(leg);
        });

        // Desk front panel (modesty panel)
        const frontPanel = new THREE.Mesh(
            new THREE.BoxGeometry(1.6, 0.6, 0.04),
            deskMaterial
        );
        frontPanel.position.set(0, 0.45, -0.05);
        this.scene.add(frontPanel);

        // Desk drawer fronts (on the side facing camera-right)
        const drawerMaterial = new THREE.MeshStandardMaterial({
            color: 0x4d3820,
            roughness: 0.6,
        });

        // Right side drawers
        for (let i = 0; i < 3; i++) {
            const drawer = new THREE.Mesh(
                new THREE.BoxGeometry(0.35, 0.16, 0.02),
                drawerMaterial
            );
            drawer.position.set(0.65, 0.60 - i * 0.18, -0.04);
            this.scene.add(drawer);

            // Drawer handle
            const handle = new THREE.Mesh(
                new THREE.BoxGeometry(0.08, 0.015, 0.02),
                new THREE.MeshStandardMaterial({ color: 0xaa8855, metalness: 0.8, roughness: 0.3 })
            );
            handle.position.set(0.65, 0.60 - i * 0.18, -0.02);
            this.scene.add(handle);
        }

        // Desk items
        this.createDeskItems();
    }

    createDeskItems() {
        // Desk lamp (left side of desk)
        const lampBaseMaterial = new THREE.MeshStandardMaterial({
            color: 0x228b22,
            roughness: 0.3,
            metalness: 0.7,
        });

        const lampBase = new THREE.Mesh(
            new THREE.CylinderGeometry(0.06, 0.08, 0.03, 16),
            lampBaseMaterial
        );
        lampBase.position.set(-0.6, 0.81, -0.7);
        this.scene.add(lampBase);

        const lampNeck = new THREE.Mesh(
            new THREE.CylinderGeometry(0.012, 0.012, 0.3, 8),
            new THREE.MeshStandardMaterial({ color: 0xb8860b, metalness: 0.9, roughness: 0.2 })
        );
        lampNeck.position.set(-0.6, 0.96, -0.7);
        this.scene.add(lampNeck);

        const lampShade = new THREE.Mesh(
            new THREE.ConeGeometry(0.12, 0.1, 16, 1, true),
            new THREE.MeshStandardMaterial({
                color: 0x228b22,
                roughness: 0.4,
                side: THREE.DoubleSide,
                emissive: 0x112211,
                emissiveIntensity: 0.3,
            })
        );
        lampShade.position.set(-0.6, 1.13, -0.7);
        lampShade.rotation.x = Math.PI;
        this.scene.add(lampShade);

        // Papers scattered on desk
        const paperMaterial = new THREE.MeshStandardMaterial({
            color: 0xf5f0e0,
            roughness: 0.95,
        });

        for (let i = 0; i < 5; i++) {
            const paper = new THREE.Mesh(
                new THREE.BoxGeometry(0.12, 0.002, 0.16),
                paperMaterial
            );
            paper.position.set(
                -0.2 + Math.random() * 0.3,
                0.79 + i * 0.002,
                -0.5 + Math.random() * 0.2
            );
            paper.rotation.y = (Math.random() - 0.5) * 0.4;
            this.scene.add(paper);
        }

        // Ashtray (front right of desk)
        const ashtrayMaterial = new THREE.MeshStandardMaterial({
            color: 0x3a3a3a,
            roughness: 0.3,
            metalness: 0.4,
        });
        const ashtray = new THREE.Mesh(
            new THREE.CylinderGeometry(0.05, 0.06, 0.02, 16),
            ashtrayMaterial
        );
        ashtray.position.set(0.5, 0.8, -0.2);
        this.scene.add(ashtray);

        // Coffee mug (near center)
        const mugMaterial = new THREE.MeshStandardMaterial({
            color: 0xf5f5dc,
            roughness: 0.6,
        });
        const mug = new THREE.Mesh(
            new THREE.CylinderGeometry(0.03, 0.025, 0.08, 12),
            mugMaterial
        );
        mug.position.set(0.2, 0.83, -0.35);
        this.scene.add(mug);

        // Mug handle
        const handleGeom = new THREE.TorusGeometry(0.02, 0.005, 8, 12, Math.PI);
        const mugHandle = new THREE.Mesh(handleGeom, mugMaterial);
        mugHandle.position.set(0.23, 0.83, -0.35);
        mugHandle.rotation.y = Math.PI / 2;
        this.scene.add(mugHandle);

        // Pencil holder (left side)
        const holderMaterial = new THREE.MeshStandardMaterial({
            color: 0x1a1a1a,
            roughness: 0.5,
            metalness: 0.3,
        });
        const holder = new THREE.Mesh(
            new THREE.CylinderGeometry(0.035, 0.035, 0.08, 8),
            holderMaterial
        );
        holder.position.set(-0.35, 0.83, -0.3);
        this.scene.add(holder);

        // Pencils in holder
        for (let i = 0; i < 4; i++) {
            const pencil = new THREE.Mesh(
                new THREE.CylinderGeometry(0.004, 0.004, 0.12, 6),
                new THREE.MeshStandardMaterial({ color: 0xffd700 })
            );
            pencil.position.set(
                -0.35 + (Math.random() - 0.5) * 0.025,
                0.9,
                -0.3 + (Math.random() - 0.5) * 0.025
            );
            pencil.rotation.x = (Math.random() - 0.5) * 0.15;
            pencil.rotation.z = (Math.random() - 0.5) * 0.15;
            this.scene.add(pencil);
        }

        // Small notepad
        const notepadMaterial = new THREE.MeshStandardMaterial({
            color: 0xfffacd,
            roughness: 0.9,
        });
        const notepad = new THREE.Mesh(
            new THREE.BoxGeometry(0.1, 0.015, 0.14),
            notepadMaterial
        );
        notepad.position.set(0.0, 0.79, -0.25);
        notepad.rotation.y = 0.1;
        this.scene.add(notepad);
    }

    loadPhoneModel() {
        const loader = new GLTFLoader();

        loader.load(
            '/art/Phone_01.glb',
            (gltf) => {
                this.phone = gltf.scene;
                this.phone.scale.set(1.2, 1.2, 1.2);
                // Position on desk, right side, slightly back
                this.phone.position.set(0.55, 0.79, -0.65);
                this.phone.rotation.x = -Math.PI / 2;  // Lie flat on desk
                this.phone.rotation.y = 0.3;
                this.phone.userData = { type: 'phone', action: 'ANSWER_PHONE' };

                // Make all meshes in phone interactive
                this.phone.traverse((child) => {
                    if (child.isMesh) {
                        child.castShadow = true;
                        child.receiveShadow = true;
                        child.userData = { type: 'phone', action: 'ANSWER_PHONE' };
                        this.interactiveObjects.push(child);
                    }
                });

                this.scene.add(this.phone);
                console.log('[DETECTIVE] Phone model loaded and interactive');
            },
            (progress) => {
                console.log('[DETECTIVE] Loading phone:', (progress.loaded / progress.total * 100).toFixed(0) + '%');
            },
            (error) => {
                console.warn('[DETECTIVE] Could not load phone model:', error);
                // Create fallback phone
                this.createFallbackPhone();
            }
        );
    }

    createFallbackPhone() {
        // Simple 1980s rotary phone if model fails to load
        const phoneMaterial = new THREE.MeshStandardMaterial({
            color: 0x1a1a1a,
            roughness: 0.4,
            metalness: 0.3,
        });

        // Phone base - position on desk, right side
        const base = new THREE.Mesh(
            new THREE.BoxGeometry(0.16, 0.04, 0.1),
            phoneMaterial
        );
        base.position.set(0.55, 0.81, -0.65);
        base.userData = { type: 'phone', action: 'ANSWER_PHONE' };
        this.interactiveObjects.push(base);
        this.scene.add(base);

        // Rotary dial
        const dial = new THREE.Mesh(
            new THREE.CylinderGeometry(0.04, 0.04, 0.01, 16),
            new THREE.MeshStandardMaterial({ color: 0x2a2a2a, metalness: 0.5 })
        );
        dial.position.set(0.55, 0.84, -0.65);
        dial.userData = { type: 'phone', action: 'ANSWER_PHONE' };
        this.interactiveObjects.push(dial);
        this.scene.add(dial);

        // Handset cradle
        const cradle = new THREE.Mesh(
            new THREE.BoxGeometry(0.14, 0.02, 0.03),
            phoneMaterial
        );
        cradle.position.set(0.55, 0.85, -0.65);
        this.scene.add(cradle);

        // Handset
        const handset = new THREE.Mesh(
            new THREE.CapsuleGeometry(0.015, 0.12, 4, 8),
            phoneMaterial
        );
        handset.position.set(0.55, 0.87, -0.65);
        handset.rotation.z = Math.PI / 2;
        handset.userData = { type: 'phone', action: 'ANSWER_PHONE' };
        this.interactiveObjects.push(handset);
        this.scene.add(handset);

        this.phone = base; // Reference for animations
        console.log('[DETECTIVE] Fallback phone created');
    }

    createFurniture() {
        // Chair material
        const chairMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a1a0a,
            roughness: 0.7,
        });

        // Detective's office chair (behind desk)
        const seat = new THREE.Mesh(
            new THREE.BoxGeometry(0.45, 0.06, 0.4),
            chairMaterial
        );
        seat.position.set(0, 0.5, -1.3);
        this.scene.add(seat);

        const chairBack = new THREE.Mesh(
            new THREE.BoxGeometry(0.45, 0.5, 0.06),
            chairMaterial
        );
        chairBack.position.set(0, 0.8, -1.5);
        this.scene.add(chairBack);

        // Filing cabinet (against left wall, visible)
        const cabinetMaterial = new THREE.MeshStandardMaterial({
            color: 0x4a4a4a,
            roughness: 0.5,
            metalness: 0.6,
        });

        const cabinet = new THREE.Mesh(
            new THREE.BoxGeometry(0.45, 1.1, 0.5),
            cabinetMaterial
        );
        cabinet.position.set(-2.2, 0.55, -1.2);
        cabinet.castShadow = true;
        this.scene.add(cabinet);

        // Cabinet drawers facing forward
        for (let i = 0; i < 3; i++) {
            const drawerFront = new THREE.Mesh(
                new THREE.BoxGeometry(0.42, 0.32, 0.02),
                new THREE.MeshStandardMaterial({ color: 0x3a3a3a, metalness: 0.7 })
            );
            drawerFront.position.set(-2.2, 0.22 + i * 0.36, -0.94);
            this.scene.add(drawerFront);

            // Drawer handle
            const handle = new THREE.Mesh(
                new THREE.BoxGeometry(0.08, 0.015, 0.02),
                new THREE.MeshStandardMaterial({ color: 0x888888, metalness: 0.9 })
            );
            handle.position.set(-2.2, 0.22 + i * 0.36, -0.92);
            this.scene.add(handle);
        }

        // Small bookshelf on back wall (behind desk)
        const shelfMaterial = new THREE.MeshStandardMaterial({
            color: 0x3d2817,
            roughness: 0.7,
        });

        // Shelf bracket/back
        const shelfBack = new THREE.Mesh(
            new THREE.BoxGeometry(1.0, 0.8, 0.04),
            shelfMaterial
        );
        shelfBack.position.set(-1.5, 1.6, -1.95);
        this.scene.add(shelfBack);

        // Shelf
        const shelf = new THREE.Mesh(
            new THREE.BoxGeometry(1.0, 0.025, 0.2),
            shelfMaterial
        );
        shelf.position.set(-1.5, 1.4, -1.85);
        this.scene.add(shelf);

        // Books on shelf
        const bookColors = [0x8b0000, 0x006400, 0x00008b, 0x4a3520, 0x8b4513, 0x2f4f4f];
        for (let i = 0; i < 6; i++) {
            const book = new THREE.Mesh(
                new THREE.BoxGeometry(0.025 + Math.random() * 0.015, 0.15 + Math.random() * 0.08, 0.12),
                new THREE.MeshStandardMaterial({
                    color: bookColors[Math.floor(Math.random() * bookColors.length)],
                    roughness: 0.8
                })
            );
            book.position.set(-1.9 + i * 0.14, 1.5, -1.82);
            book.rotation.y = (Math.random() - 0.5) * 0.08;
            this.scene.add(book);
        }

        // Coat rack in corner (left back)
        const rackMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a1a08,
            roughness: 0.6,
        });

        const rackBase = new THREE.Mesh(
            new THREE.CylinderGeometry(0.15, 0.18, 0.03, 16),
            rackMaterial
        );
        rackBase.position.set(-2.5, 0.015, -1.7);
        this.scene.add(rackBase);

        const rackPole = new THREE.Mesh(
            new THREE.CylinderGeometry(0.025, 0.03, 1.6, 8),
            rackMaterial
        );
        rackPole.position.set(-2.5, 0.83, -1.7);
        this.scene.add(rackPole);

        // Fedora on rack
        const hatMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a2a2a,
            roughness: 0.7,
        });
        const hatBrim = new THREE.Mesh(
            new THREE.CylinderGeometry(0.1, 0.1, 0.015, 16),
            hatMaterial
        );
        hatBrim.position.set(-2.45, 1.55, -1.65);
        hatBrim.rotation.z = 0.15;
        this.scene.add(hatBrim);

        const hatTop = new THREE.Mesh(
            new THREE.CylinderGeometry(0.055, 0.07, 0.08, 16),
            hatMaterial
        );
        hatTop.position.set(-2.45, 1.59, -1.65);
        hatTop.rotation.z = 0.15;
        this.scene.add(hatTop);
    }

    createEvidenceBoard() {
        // Cork board - moved closer and centered behind desk for better visibility
        const boardWidth = 1.6;
        const boardHeight = 1.0;
        const boardX = 0;      // Centered
        const boardY = 1.5;    // Slightly lower
        const boardZ = -1.3;   // Much closer to desk

        // Store board dimensions for other methods
        this.boardDimensions = { width: boardWidth, height: boardHeight, x: boardX, y: boardY, z: boardZ };

        // Cork board backing - make it clickable to zoom in
        const corkMaterial = new THREE.MeshStandardMaterial({
            color: 0xb5885a,  // Cork tan color
            roughness: 0.95,
            metalness: 0.0,
        });

        const corkBoard = new THREE.Mesh(
            new THREE.BoxGeometry(boardWidth, boardHeight, 0.03),
            corkMaterial
        );
        corkBoard.position.set(boardX, boardY, boardZ);
        corkBoard.receiveShadow = true;
        corkBoard.userData = {
            type: 'evidence_board',
            action: 'VIEW_BOARD'
        };
        this.interactiveObjects.push(corkBoard);
        this.evidenceBoard = corkBoard;
        this.scene.add(corkBoard);

        // Wood frame around the board
        const frameMaterial = new THREE.MeshStandardMaterial({
            color: 0x3d2817,
            roughness: 0.6,
            metalness: 0.1,
        });

        const frameThickness = 0.04;
        // Top frame
        const topFrame = new THREE.Mesh(
            new THREE.BoxGeometry(boardWidth + frameThickness * 2, frameThickness, 0.05),
            frameMaterial
        );
        topFrame.position.set(boardX, boardY + boardHeight / 2 + frameThickness / 2, boardZ + 0.01);
        this.scene.add(topFrame);

        // Bottom frame
        const bottomFrame = new THREE.Mesh(
            new THREE.BoxGeometry(boardWidth + frameThickness * 2, frameThickness, 0.05),
            frameMaterial
        );
        bottomFrame.position.set(boardX, boardY - boardHeight / 2 - frameThickness / 2, boardZ + 0.01);
        this.scene.add(bottomFrame);

        // Left frame
        const leftFrame = new THREE.Mesh(
            new THREE.BoxGeometry(frameThickness, boardHeight, 0.05),
            frameMaterial
        );
        leftFrame.position.set(boardX - boardWidth / 2 - frameThickness / 2, boardY, boardZ + 0.01);
        this.scene.add(leftFrame);

        // Right frame
        const rightFrame = new THREE.Mesh(
            new THREE.BoxGeometry(frameThickness, boardHeight, 0.05),
            frameMaterial
        );
        rightFrame.position.set(boardX + boardWidth / 2 + frameThickness / 2, boardY, boardZ + 0.01);
        this.scene.add(rightFrame);

        // === VICTIM HEADER - Central anchor at top ===
        this.createVictimHeader(boardX, boardY + 0.38, boardZ + 0.02);

        // Evidence pin definitions with enhanced labels - adjusted layout
        const pinData = [
            { id: 'pin_map', label: 'LOCATIONS', subtext: 'MARLOW / RIVERWALK / GLASSWORKS', x: -0.55, y: 0.15, color: 0xff0000 },
            { id: 'pin_door', label: 'LOCK SCRATCHES', subtext: 'FRONT DOOR - KEY COPY?', x: -0.15, y: 0.18, color: 0xff4444 },
            { id: 'pin_study', label: 'SAFE MISSING', subtext: 'STUDY - WALL SAFE REMOVED', x: 0.25, y: 0.12, color: 0xff4444 },
            { id: 'pin_receipt', label: 'KEY BLANK', subtext: 'KESTREL PAWN - 2 DAYS PRIOR', x: 0.55, y: 0.18, color: 0xffff00 },
            { id: 'pin_cctv', label: 'SUSPECT?', subtext: 'HOODED FIGURE - REFLECTIVE SLEEVE', x: -0.5, y: -0.12, color: 0x00ff00 },
            { id: 'pin_note', label: 'GLASSWORKS', subtext: '"DON\'T OPEN IT..."', x: -0.55, y: -0.32, color: 0x00ffff },
            { id: 'pin_calllog', label: 'PHONE LOG', subtext: '3 CALLS - UNKNOWN NUMBER', x: 0.55, y: -0.08, color: 0xff00ff },
        ];

        // Create pins and evidence cards
        pinData.forEach((pin, index) => {
            this.createEvidencePin(
                pin.id,
                pin.label,
                boardX + pin.x,
                boardY + pin.y,
                boardZ + 0.02,
                pin.color,
                index,
                pin.subtext
            );
        });

        // === STICKY NOTE ANNOTATIONS ===
        this.createStickyNote('INSIDE JOB?', boardX + 0.35, boardY + 0.0, boardZ + 0.025, -0.08);
        this.createStickyNote('THEY MADE A COPY', boardX + 0.15, boardY - 0.15, boardZ + 0.025, 0.05, true); // highlighted
        this.createStickyNote('7:12 PM - LAST CALL', boardX + 0.55, boardY - 0.25, boardZ + 0.025, -0.03);
        this.createStickyNote('WHO IS SHE?', boardX - 0.2, boardY - 0.38, boardZ + 0.025, 0.1);

        // Suspect placeholder with question mark
        this.createSuspectPlaceholder(boardX + 0.0, boardY - 0.28, boardZ + 0.02);

        // === TIMELINE STRIP along bottom ===
        this.createTimelineStrip(boardX, boardY - 0.46, boardZ + 0.025);

        // === REVISED STRING CONNECTIONS - More logical investigation threads ===
        // Find pin indices for connections
        const mapPin = pinData[0];      // LOCATIONS
        const doorPin = pinData[1];     // LOCK SCRATCHES
        const studyPin = pinData[2];    // SAFE MISSING
        const receiptPin = pinData[3];  // KEY BLANK
        const cctvPin = pinData[4];     // SUSPECT?
        const notePin = pinData[5];     // GLASSWORKS
        const callPin = pinData[6];     // PHONE LOG

        // Victim to locations (where he was killed)
        this.createStringConnection({ x: 0, y: 0.32 }, mapPin, boardY, boardZ, boardX);

        // Locations to Glassworks note (what happened there?)
        this.createStringConnection(mapPin, notePin, boardY, boardZ, boardX);

        // Door scratches to Key blank (they made a copy!)
        this.createStringConnection(doorPin, receiptPin, boardY, boardZ, boardX);

        // CCTV to Locations (riverwalk connection)
        this.createStringConnection(cctvPin, mapPin, boardY, boardZ, boardX);

        // Phone log to victim area (last contact before death)
        this.createStringConnection(callPin, { x: 0.1, y: 0.32 }, boardY, boardZ, boardX);

        // Safe missing to Key blank (what did the key open?)
        this.createStringConnection(studyPin, receiptPin, boardY, boardZ, boardX);

        console.log('[DETECTIVE] Evidence board created with', this.evidencePins.length, 'pins');
    }

    /**
     * Create a canvas texture with styled text for evidence labels
     */
    createTextTexture(text, options = {}) {
        const {
            fontSize = 24,
            fontFamily = 'Courier New, monospace',
            textColor = '#222222',
            bgColor = null,
            width = 256,
            height = 64,
            bold = false,
            italic = false,
            align = 'center'
        } = options;

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');

        // Background
        if (bgColor) {
            ctx.fillStyle = bgColor;
            ctx.fillRect(0, 0, width, height);
        } else {
            ctx.clearRect(0, 0, width, height);
        }

        // Text styling
        let fontStyle = '';
        if (italic) fontStyle += 'italic ';
        if (bold) fontStyle += 'bold ';
        ctx.font = `${fontStyle}${fontSize}px ${fontFamily}`;
        ctx.fillStyle = textColor;
        ctx.textAlign = align;
        ctx.textBaseline = 'middle';

        // Draw text
        const x = align === 'center' ? width / 2 : (align === 'left' ? 10 : width - 10);
        ctx.fillText(text, x, height / 2);

        const texture = new THREE.CanvasTexture(canvas);
        texture.needsUpdate = true;
        return texture;
    }

    /**
     * Create multi-line text texture
     */
    createMultiLineTexture(lines, options = {}) {
        const {
            fontSize = 20,
            lineHeight = 1.3,
            fontFamily = 'Courier New, monospace',
            textColor = '#222222',
            bgColor = null,
            width = 256,
            bold = false
        } = options;

        const height = Math.ceil(lines.length * fontSize * lineHeight + 20);
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');

        // Background
        if (bgColor) {
            ctx.fillStyle = bgColor;
            ctx.fillRect(0, 0, width, height);
        }

        // Text
        ctx.font = `${bold ? 'bold ' : ''}${fontSize}px ${fontFamily}`;
        ctx.fillStyle = textColor;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';

        lines.forEach((line, i) => {
            ctx.fillText(line, width / 2, 10 + i * fontSize * lineHeight);
        });

        const texture = new THREE.CanvasTexture(canvas);
        texture.needsUpdate = true;
        return { texture, height };
    }

    /**
     * Create victim header card at top center of board
     */
    createVictimHeader(x, y, z) {
        // Dark photo-style card
        const cardWidth = 0.28;
        const cardHeight = 0.12;

        // Photo backing (dark)
        const photoMaterial = new THREE.MeshStandardMaterial({
            color: 0x1a1a1a,
            roughness: 0.8,
        });
        const photoBacking = new THREE.Mesh(
            new THREE.BoxGeometry(cardWidth, cardHeight, 0.003),
            photoMaterial
        );
        photoBacking.position.set(x, y, z);
        this.scene.add(photoBacking);

        // Victim silhouette area (slightly lighter)
        const silhouetteMaterial = new THREE.MeshStandardMaterial({
            color: 0x2a2a2a,
            roughness: 0.9,
        });
        const silhouette = new THREE.Mesh(
            new THREE.BoxGeometry(cardWidth * 0.35, cardHeight * 0.7, 0.001),
            silhouetteMaterial
        );
        silhouette.position.set(x - cardWidth * 0.25, y, z + 0.003);
        this.scene.add(silhouette);

        // Name label texture
        const nameTexture = this.createMultiLineTexture(
            ['DR. ELIAS CROWE', 'MARLOW ST - DOA 11/14/87'],
            { fontSize: 18, textColor: '#cccccc', bgColor: '#1a1a1a', width: 200, bold: true }
        );

        const nameLabelMaterial = new THREE.MeshBasicMaterial({
            map: nameTexture.texture,
            transparent: true,
        });
        const nameLabel = new THREE.Mesh(
            new THREE.PlaneGeometry(cardWidth * 0.6, cardHeight * 0.8),
            nameLabelMaterial
        );
        nameLabel.position.set(x + cardWidth * 0.15, y, z + 0.004);
        this.scene.add(nameLabel);

        // Red pin for victim card
        const pinMaterial = new THREE.MeshStandardMaterial({
            color: 0xff0000,
            roughness: 0.3,
            metalness: 0.6,
            emissive: 0xff0000,
            emissiveIntensity: 0.3,
        });
        const pin = new THREE.Mesh(
            new THREE.SphereGeometry(0.02, 12, 12),
            pinMaterial
        );
        pin.position.set(x, y + cardHeight / 2 + 0.015, z + 0.01);
        this.scene.add(pin);
    }

    /**
     * Create sticky note annotation card
     */
    createStickyNote(text, x, y, z, rotation = 0, highlighted = false) {
        const noteWidth = 0.1;
        const noteHeight = 0.06;

        // Yellow sticky note background
        const noteColor = highlighted ? 0xffcc00 : 0xfffacd;
        const noteMaterial = new THREE.MeshStandardMaterial({
            color: noteColor,
            roughness: 0.95,
            metalness: 0.0,
        });

        const note = new THREE.Mesh(
            new THREE.BoxGeometry(noteWidth, noteHeight, 0.002),
            noteMaterial
        );
        note.position.set(x, y, z);
        note.rotation.z = rotation;
        this.scene.add(note);

        // Handwritten text texture
        const textTexture = this.createTextTexture(text, {
            fontSize: highlighted ? 16 : 14,
            textColor: '#333333',
            fontFamily: 'Georgia, serif',
            italic: true,
            bold: highlighted,
            width: 180,
            height: 50
        });

        const textMaterial = new THREE.MeshBasicMaterial({
            map: textTexture,
            transparent: true,
        });
        const textMesh = new THREE.Mesh(
            new THREE.PlaneGeometry(noteWidth * 0.95, noteHeight * 0.8),
            textMaterial
        );
        textMesh.position.set(x, y, z + 0.003);
        textMesh.rotation.z = rotation;
        this.scene.add(textMesh);
    }

    /**
     * Create suspect placeholder with question mark
     */
    createSuspectPlaceholder(x, y, z) {
        const cardWidth = 0.1;
        const cardHeight = 0.12;

        // Dark card with dashed outline effect
        const cardMaterial = new THREE.MeshStandardMaterial({
            color: 0x333333,
            roughness: 0.9,
            transparent: true,
            opacity: 0.7,
        });
        const card = new THREE.Mesh(
            new THREE.BoxGeometry(cardWidth, cardHeight, 0.002),
            cardMaterial
        );
        card.position.set(x, y, z);
        this.scene.add(card);

        // Question mark texture
        const qTexture = this.createTextTexture('?', {
            fontSize: 48,
            textColor: '#ff4444',
            bold: true,
            width: 64,
            height: 64
        });

        const qMaterial = new THREE.MeshBasicMaterial({
            map: qTexture,
            transparent: true,
        });
        const qMesh = new THREE.Mesh(
            new THREE.PlaneGeometry(cardWidth * 0.6, cardHeight * 0.5),
            qMaterial
        );
        qMesh.position.set(x, y + 0.01, z + 0.003);
        this.scene.add(qMesh);

        // "HOLLIS ROOK?" label below
        const labelTexture = this.createTextTexture('HOLLIS ROOK?', {
            fontSize: 12,
            textColor: '#999999',
            italic: true,
            width: 128,
            height: 24
        });

        const labelMaterial = new THREE.MeshBasicMaterial({
            map: labelTexture,
            transparent: true,
        });
        const labelMesh = new THREE.Mesh(
            new THREE.PlaneGeometry(cardWidth * 1.2, cardHeight * 0.25),
            labelMaterial
        );
        labelMesh.position.set(x, y - cardHeight / 2 - 0.02, z + 0.003);
        this.scene.add(labelMesh);

        // Yellow pin
        const pinMaterial = new THREE.MeshStandardMaterial({
            color: 0xffff00,
            roughness: 0.3,
            metalness: 0.6,
            emissive: 0xffff00,
            emissiveIntensity: 0.2,
        });
        const pin = new THREE.Mesh(
            new THREE.SphereGeometry(0.015, 12, 12),
            pinMaterial
        );
        pin.position.set(x, y + cardHeight / 2 + 0.01, z + 0.01);
        this.scene.add(pin);
    }

    /**
     * Create timeline strip along bottom of board
     */
    createTimelineStrip(x, y, z) {
        const stripWidth = 1.4;
        const stripHeight = 0.05;

        // Timeline background strip
        const stripMaterial = new THREE.MeshStandardMaterial({
            color: 0xf0e8d8,
            roughness: 0.95,
        });
        const strip = new THREE.Mesh(
            new THREE.BoxGeometry(stripWidth, stripHeight, 0.002),
            stripMaterial
        );
        strip.position.set(x, y, z);
        this.scene.add(strip);

        // Timeline events
        const events = [
            { text: '11/12 KEY BLANK', offset: -0.5 },
            { text: '7:12PM LAST CALL', offset: 0 },
            { text: '~9PM BODY FOUND', offset: 0.5 }
        ];

        events.forEach(event => {
            // Event marker (small circle)
            const markerMaterial = new THREE.MeshStandardMaterial({
                color: 0xcc0000,
                roughness: 0.3,
            });
            const marker = new THREE.Mesh(
                new THREE.CircleGeometry(0.012, 12),
                markerMaterial
            );
            marker.position.set(x + event.offset, y, z + 0.003);
            this.scene.add(marker);

            // Event text
            const textTexture = this.createTextTexture(event.text, {
                fontSize: 11,
                textColor: '#444444',
                width: 140,
                height: 24
            });

            const textMaterial = new THREE.MeshBasicMaterial({
                map: textTexture,
                transparent: true,
            });
            const textMesh = new THREE.Mesh(
                new THREE.PlaneGeometry(0.12, 0.025),
                textMaterial
            );
            textMesh.position.set(x + event.offset, y + stripHeight / 2 + 0.018, z + 0.003);
            this.scene.add(textMesh);
        });

        // Connecting line through timeline
        const lineMaterial = new THREE.LineBasicMaterial({ color: 0x666666 });
        const linePoints = [
            new THREE.Vector3(x - stripWidth / 2 + 0.05, y, z + 0.004),
            new THREE.Vector3(x + stripWidth / 2 - 0.05, y, z + 0.004)
        ];
        const lineGeometry = new THREE.BufferGeometry().setFromPoints(linePoints);
        const timelineLine = new THREE.Line(lineGeometry, lineMaterial);
        this.scene.add(timelineLine);
    }

    createEvidencePin(id, label, x, y, z, color, index, subtext = '') {
        // Pin head (sphere)
        const pinHeadMaterial = new THREE.MeshStandardMaterial({
            color: color,
            roughness: 0.3,
            metalness: 0.6,
            emissive: color,
            emissiveIntensity: 0.2,
        });

        const pinHead = new THREE.Mesh(
            new THREE.SphereGeometry(0.025, 16, 16),
            pinHeadMaterial
        );
        pinHead.position.set(x, y, z + 0.02);
        pinHead.userData = {
            type: 'evidence_pin',
            pinId: id,
            label: label,
            action: `PIN_${id.toUpperCase()}`
        };
        this.interactiveObjects.push(pinHead);
        this.evidencePins.push(pinHead);
        this.scene.add(pinHead);

        // Pin needle
        const needleMaterial = new THREE.MeshStandardMaterial({
            color: 0xcccccc,
            metalness: 0.9,
            roughness: 0.2,
        });
        const needle = new THREE.Mesh(
            new THREE.CylinderGeometry(0.003, 0.003, 0.03, 8),
            needleMaterial
        );
        needle.position.set(x, y, z + 0.005);
        needle.rotation.x = Math.PI / 2;
        this.scene.add(needle);

        // Evidence card/photo under the pin with label and subtext
        this.createEvidenceCard(id, label, x, y - 0.06, z + 0.015, index, subtext);
    }

    createEvidenceCard(id, label, x, y, z, index, subtext = '') {
        // Different card styles based on evidence type - larger cards for better label visibility
        const cardConfigs = {
            'pin_map': { width: 0.2, height: 0.14, color: 0xf5f0e0, type: 'map' },
            'pin_door': { width: 0.14, height: 0.11, color: 0xdddddd, type: 'photo' },
            'pin_study': { width: 0.14, height: 0.11, color: 0xdddddd, type: 'photo' },
            'pin_receipt': { width: 0.1, height: 0.14, color: 0xffffd0, type: 'receipt' },
            'pin_cctv': { width: 0.14, height: 0.1, color: 0x222222, type: 'screen' },
            'pin_note': { width: 0.12, height: 0.08, color: 0xf5f0e0, type: 'note' },
            'pin_calllog': { width: 0.1, height: 0.12, color: 0xf5f0e0, type: 'paper' },
        };

        const config = cardConfigs[id] || { width: 0.12, height: 0.1, color: 0xf5f0e0 };

        const cardMaterial = new THREE.MeshStandardMaterial({
            color: config.color,
            roughness: 0.9,
            metalness: 0.0,
        });

        const card = new THREE.Mesh(
            new THREE.BoxGeometry(config.width, config.height, 0.002),
            cardMaterial
        );

        // Slight random rotation for natural look
        const tilt = (Math.random() - 0.5) * 0.08;
        card.position.set(x, y, z);
        card.rotation.z = tilt;
        card.receiveShadow = true;
        this.scene.add(card);

        // Add visual details based on type
        if (config.type === 'photo') {
            // Dark rectangle for photo content (upper portion)
            const photoContent = new THREE.Mesh(
                new THREE.BoxGeometry(config.width * 0.85, config.height * 0.5, 0.001),
                new THREE.MeshStandardMaterial({ color: 0x333333, roughness: 0.8 })
            );
            photoContent.position.set(x, y + config.height * 0.15, z + 0.002);
            photoContent.rotation.z = tilt;
            this.scene.add(photoContent);
        } else if (config.type === 'screen') {
            // Greenish tint for CCTV (upper portion)
            const screenGlow = new THREE.Mesh(
                new THREE.BoxGeometry(config.width * 0.85, config.height * 0.5, 0.001),
                new THREE.MeshStandardMaterial({
                    color: 0x003300,
                    emissive: 0x002200,
                    emissiveIntensity: 0.3,
                    roughness: 0.5
                })
            );
            screenGlow.position.set(x, y + config.height * 0.15, z + 0.002);
            screenGlow.rotation.z = tilt;
            this.scene.add(screenGlow);
        } else if (config.type === 'map') {
            // Add some "lines" to suggest a map (upper area)
            for (let i = 0; i < 3; i++) {
                const line = new THREE.Mesh(
                    new THREE.BoxGeometry(config.width * 0.5, 0.003, 0.001),
                    new THREE.MeshStandardMaterial({ color: 0x666666 })
                );
                line.position.set(x + (Math.random() - 0.5) * 0.03, y + 0.02 + i * 0.025, z + 0.002);
                line.rotation.z = tilt + (Math.random() - 0.5) * 0.15;
                this.scene.add(line);
            }
            // Red circles for locations
            const circlePositions = [
                { cx: -0.03, cy: 0.04 },
                { cx: 0.02, cy: 0.02 },
                { cx: 0.04, cy: 0.05 },
            ];
            circlePositions.forEach(pos => {
                const circle = new THREE.Mesh(
                    new THREE.RingGeometry(0.006, 0.008, 16),
                    new THREE.MeshBasicMaterial({ color: 0xff0000, side: THREE.DoubleSide })
                );
                circle.position.set(x + pos.cx, y + pos.cy, z + 0.003);
                circle.rotation.z = tilt;
                this.scene.add(circle);
            });
        }

        // === TEXT LABEL BELOW VISUAL CONTENT ===
        // Label header (bold)
        const labelTextColor = config.type === 'screen' ? '#00ff00' : '#222222';
        const labelBgColor = config.type === 'screen' ? '#111111' : null;

        const labelTexture = this.createTextTexture(label, {
            fontSize: 14,
            textColor: labelTextColor,
            bgColor: labelBgColor,
            bold: true,
            width: 160,
            height: 28
        });

        const labelMaterial = new THREE.MeshBasicMaterial({
            map: labelTexture,
            transparent: true,
        });
        const labelMesh = new THREE.Mesh(
            new THREE.PlaneGeometry(config.width * 0.9, config.height * 0.22),
            labelMaterial
        );
        labelMesh.position.set(x, y - config.height * 0.2, z + 0.003);
        labelMesh.rotation.z = tilt;
        this.scene.add(labelMesh);

        // Subtext (smaller, italic)
        if (subtext) {
            const subtextTexture = this.createTextTexture(subtext, {
                fontSize: 10,
                textColor: config.type === 'screen' ? '#88ff88' : '#555555',
                italic: true,
                width: 200,
                height: 24
            });

            const subtextMaterial = new THREE.MeshBasicMaterial({
                map: subtextTexture,
                transparent: true,
            });
            const subtextMesh = new THREE.Mesh(
                new THREE.PlaneGeometry(config.width * 0.95, config.height * 0.18),
                subtextMaterial
            );
            subtextMesh.position.set(x, y - config.height * 0.38, z + 0.003);
            subtextMesh.rotation.z = tilt;
            this.scene.add(subtextMesh);
        }
    }

    createStringConnection(pin1Data, pin2Data, boardY, boardZ, boardX) {
        // Red string connecting evidence pins
        const stringMaterial = new THREE.LineBasicMaterial({
            color: 0xcc0000,
            linewidth: 2,
        });

        const points = [
            new THREE.Vector3(boardX + pin1Data.x, boardY + pin1Data.y, boardZ + 0.025),
            new THREE.Vector3(boardX + pin2Data.x, boardY + pin2Data.y, boardZ + 0.025),
        ];

        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const string = new THREE.Line(geometry, stringMaterial);
        this.scene.add(string);
    }

    createAtmosphere() {
        // Rain on window (particle system) - near the window on the right
        const rainGeometry = new THREE.BufferGeometry();
        const rainCount = 60;
        const rainPositions = new Float32Array(rainCount * 3);

        for (let i = 0; i < rainCount * 3; i += 3) {
            rainPositions[i] = 2.6 + Math.random() * 0.3;  // Just outside window
            rainPositions[i + 1] = 0.8 + Math.random() * 1.8;  // Window height range
            rainPositions[i + 2] = -1.2 + Math.random() * 1.8;  // Window width range
        }

        rainGeometry.setAttribute('position', new THREE.BufferAttribute(rainPositions, 3));

        const rainMaterial = new THREE.PointsMaterial({
            color: 0x8899aa,
            size: 0.015,
            transparent: true,
            opacity: 0.5,
        });

        this.raindrops = new THREE.Points(rainGeometry, rainMaterial);
        this.scene.add(this.raindrops);

        // Dust particles floating in the desk lamp light
        const dustGeometry = new THREE.BufferGeometry();
        const dustCount = 40;
        const dustPositions = new Float32Array(dustCount * 3);

        for (let i = 0; i < dustCount * 3; i += 3) {
            dustPositions[i] = -0.8 + Math.random() * 1.2;  // Around desk area
            dustPositions[i + 1] = 0.8 + Math.random() * 0.8;  // Above desk
            dustPositions[i + 2] = -0.8 + Math.random() * 0.6;  // Desk depth
        }

        dustGeometry.setAttribute('position', new THREE.BufferAttribute(dustPositions, 3));

        const dustMaterial = new THREE.PointsMaterial({
            color: 0xffffee,
            size: 0.012,
            transparent: true,
            opacity: 0.4,
        });

        this.dustParticles = new THREE.Points(dustGeometry, dustMaterial);
        this.scene.add(this.dustParticles);
    }

    setupLights() {
        // Ambient - moderate for visibility
        const ambient = new THREE.AmbientLight(0x404050, 0.6);
        this.scene.add(ambient);

        // Desk lamp light (warm pool of light on desk surface)
        const deskLight = new THREE.SpotLight(0xffdd88, 3, 2.5, Math.PI / 3, 0.4);
        deskLight.position.set(-0.6, 1.15, -0.7);
        deskLight.target.position.set(0, 0.75, -0.5);
        deskLight.castShadow = true;
        deskLight.shadow.mapSize.width = 512;
        deskLight.shadow.mapSize.height = 512;
        this.scene.add(deskLight);
        this.scene.add(deskLight.target);

        // Secondary fill light from above
        const fillLight = new THREE.PointLight(0xffeedd, 0.8, 5);
        fillLight.position.set(0, 2.5, 0);
        this.scene.add(fillLight);

        // Window light (cold, from city outside)
        this.blindsLight = new THREE.DirectionalLight(0x6688aa, 1.0);
        this.blindsLight.position.set(4, 2.5, -0.5);
        this.blindsLight.target.position.set(0, 0.75, -0.5);
        this.blindsLight.castShadow = true;
        this.blindsLight.shadow.mapSize.width = 1024;
        this.blindsLight.shadow.mapSize.height = 1024;
        this.blindsLight.shadow.camera.near = 1;
        this.blindsLight.shadow.camera.far = 8;
        this.blindsLight.shadow.camera.left = -2;
        this.blindsLight.shadow.camera.right = 2;
        this.blindsLight.shadow.camera.top = 2;
        this.blindsLight.shadow.camera.bottom = -1;
        this.scene.add(this.blindsLight);
        this.scene.add(this.blindsLight.target);

        // Neon glow from outside (pink/red tint)
        const neonLight = new THREE.PointLight(0xff3366, 0.4, 6);
        neonLight.position.set(3, 2, -1);
        this.scene.add(neonLight);

        // Phone area light - warm accent to illuminate the phone on right side of desk
        const phoneLight = new THREE.SpotLight(0xffeedd, 1.5, 2, Math.PI / 5, 0.5);
        phoneLight.position.set(0.8, 1.5, -0.4);
        phoneLight.target.position.set(0.55, 0.79, -0.65);
        phoneLight.castShadow = true;
        phoneLight.shadow.mapSize.width = 256;
        phoneLight.shadow.mapSize.height = 256;
        this.scene.add(phoneLight);
        this.scene.add(phoneLight.target);
    }

    setupInteraction() {
        window.addEventListener('mousemove', (event) => {
            this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
            this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
            this.mouseNeedsUpdate = true;
            this.lastMouseEvent = event;  // Store for tooltip positioning
        });

        window.addEventListener('click', () => {
            if (this.isTransitioning) return;  // Ignore clicks during camera transition

            if (this.hoveredObject && this.hoveredObject.userData.action) {
                const action = this.hoveredObject.userData.action;
                console.log('Object clicked:', action);

                // Handle phone answering
                if (action === 'ANSWER_PHONE' && this.phoneRinging && !this.phoneAnswered) {
                    this.answerPhone();
                } else if (action === 'VIEW_BOARD' && this.currentView === 'desk') {
                    // Click on evidence board - zoom to board view
                    this.switchToView('board');
                } else if (this.hoveredObject.userData.type === 'evidence_pin') {
                    // Handle evidence pin click (works in both views, but better in board view)
                    this.handlePinClick(this.hoveredObject);
                } else if (this.hoveredObject.userData.action) {
                    this.onButtonClick(action);
                }
            }
        });
    }

    handlePinClick(pinMesh) {
        const pinId = pinMesh.userData.pinId;
        const label = pinMesh.userData.label;

        console.log('[DETECTIVE] Evidence pin clicked:', pinId, label);

        // Prevent clicks during camera animation
        if (this.isPinFocusing) return;

        // Visual feedback - make pin glow brighter
        if (this.selectedPin && this.selectedPin !== pinMesh) {
            // Reset previous selection
            this.selectedPin.material.emissiveIntensity = 0.2;
        }

        this.selectedPin = pinMesh;
        pinMesh.material.emissiveIntensity = 0.8;

        // Camera focus animation - zoom 15% towards pin, hold 2s, reset
        this.focusOnPin(pinMesh.position.clone());

        // Notify the app of pin selection
        this.onButtonClick(pinId);
    }

    /**
     * Animate camera to focus on a pin position, hold, then reset
     */
    focusOnPin(pinPosition) {
        if (this.isPinFocusing) return;
        this.isPinFocusing = true;

        // Store original camera state
        const originalPos = this.camera.position.clone();
        const originalTarget = this.controls.target.clone();

        // Calculate 15% closer position towards the pin
        const zoomFactor = 0.15;
        const targetPos = new THREE.Vector3().lerpVectors(originalPos, pinPosition, zoomFactor);
        const targetLook = new THREE.Vector3().lerpVectors(originalTarget, pinPosition, zoomFactor * 0.5);

        const zoomInDuration = 300;  // ms
        const holdDuration = 2000;   // ms
        const zoomOutDuration = 400; // ms (slightly slower for soft reset)

        // Phase 1: Zoom in
        this.animateCameraTo(targetPos, targetLook, zoomInDuration, () => {
            // Phase 2: Hold for 2 seconds, then zoom out
            setTimeout(() => {
                // Phase 3: Soft reset back to original
                this.animateCameraTo(originalPos, originalTarget, zoomOutDuration, () => {
                    this.isPinFocusing = false;
                }, 'easeOut');
            }, holdDuration);
        }, 'easeOut');
    }

    /**
     * Animate camera position and target smoothly
     */
    animateCameraTo(targetPos, targetLook, duration, onComplete, easing = 'easeInOut') {
        const startPos = this.camera.position.clone();
        const startTarget = this.controls.target.clone();
        const startTime = Date.now();

        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);

            // Apply easing
            let eased;
            if (easing === 'easeOut') {
                eased = 1 - Math.pow(1 - progress, 3);
            } else if (easing === 'easeIn') {
                eased = Math.pow(progress, 3);
            } else {
                // easeInOut
                eased = progress < 0.5
                    ? 4 * progress * progress * progress
                    : 1 - Math.pow(-2 * progress + 2, 3) / 2;
            }

            // Interpolate position and target
            this.camera.position.lerpVectors(startPos, targetPos, eased);
            this.controls.target.lerpVectors(startTarget, targetLook, eased);
            this.controls.update();

            if (progress < 1) {
                requestAnimationFrame(animate);
            } else if (onComplete) {
                onComplete();
            }
        };

        animate();
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        const currentTime = Date.now();
        const deltaTime = currentTime - this.lastFrameTime;

        if (deltaTime < this.frameInterval) {
            return;
        }

        this.lastFrameTime = currentTime - (deltaTime % this.frameInterval);

        const time = this.clock.getElapsedTime();
        this.frameCount++;

        // Animate rain
        if (this.raindrops && this.frameCount % 2 === 0) {
            const positions = this.raindrops.geometry.attributes.position.array;
            for (let i = 0; i < positions.length; i += 3) {
                positions[i + 1] -= 0.04;
                if (positions[i + 1] < 0.8) {
                    positions[i + 1] = 2.6;
                }
            }
            this.raindrops.geometry.attributes.position.needsUpdate = true;
        }

        // Animate dust floating
        if (this.dustParticles && this.frameCount % 3 === 0) {
            const positions = this.dustParticles.geometry.attributes.position.array;
            for (let i = 0; i < positions.length; i += 3) {
                positions[i] += Math.sin(time + i) * 0.001;
                positions[i + 1] += Math.cos(time * 0.5 + i) * 0.0005;
                positions[i + 2] += Math.sin(time * 0.7 + i) * 0.001;
            }
            this.dustParticles.geometry.attributes.position.needsUpdate = true;
        }

        // Flicker neon sign
        if (this.neonSign && this.frameCount % 10 === 0) {
            const flicker = Math.random() > 0.95 ? 0.3 : 0.9;
            this.neonSign.material.opacity = flicker;
        }

        // Subtle light variation (passing cars, etc.)
        if (this.blindsLight) {
            this.blindsLight.intensity = 0.7 + Math.sin(time * 0.5) * 0.1;
        }

        // Phone shake animation when ringing
        if (this.phone && this.phoneRinging && !this.phoneAnswered) {
            const shake = Math.sin(time * 30) * 0.003;
            this.phone.position.x = 0.55 + shake;
            this.phone.rotation.z = shake * 2;
        } else if (this.phone && this.phoneAnswered) {
            // Reset phone position after answered
            this.phone.position.x = 0.55;
            this.phone.rotation.z = 0;
        }

        // Raycast for interaction
        if (this.mouseNeedsUpdate && this.interactiveObjects.length > 0) {
            this.raycaster.setFromCamera(this.mouse, this.camera);
            const intersects = this.raycaster.intersectObjects(this.interactiveObjects);

            // Reset previous hover
            if (this.hoveredObject) {
                document.body.style.cursor = 'default';
                // Reset pin hover effect
                if (this.hoveredObject.userData.type === 'evidence_pin' && this.hoveredObject !== this.selectedPin) {
                    this.hoveredObject.material.emissiveIntensity = 0.2;
                }
            }

            if (intersects.length > 0) {
                this.hoveredObject = intersects[0].object;
                document.body.style.cursor = 'pointer';

                // Pin hover effect - brighten
                if (this.hoveredObject.userData.type === 'evidence_pin') {
                    this.hoveredObject.material.emissiveIntensity = 0.5;
                }

                // Board hover effect - show it's clickable in desk view
                if (this.hoveredObject.userData.type === 'evidence_board' && this.currentView === 'desk') {
                    this.hoveredObject.material.emissive = new THREE.Color(0x332200);
                    this.hoveredObject.material.emissiveIntensity = 0.3;
                    // Show tooltip
                    if (this.boardTooltip && this.lastMouseEvent) {
                        this.boardTooltip.style.display = 'block';
                        this.boardTooltip.style.left = this.lastMouseEvent.clientX + 15 + 'px';
                        this.boardTooltip.style.top = this.lastMouseEvent.clientY - 10 + 'px';
                    }
                } else {
                    // Hide tooltip when not hovering board
                    if (this.boardTooltip) {
                        this.boardTooltip.style.display = 'none';
                    }
                }
            } else {
                this.hoveredObject = null;
                // Hide tooltip
                if (this.boardTooltip) {
                    this.boardTooltip.style.display = 'none';
                }
            }

            // Reset board hover effect
            if (this.evidenceBoard && (!this.hoveredObject || this.hoveredObject.userData.type !== 'evidence_board')) {
                this.evidenceBoard.material.emissive = new THREE.Color(0x000000);
                this.evidenceBoard.material.emissiveIntensity = 0;
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

    // Phone ringing system
    startPhoneRinging() {
        if (this.phoneAnswered) return;

        this.phoneRinging = true;
        console.log('[DETECTIVE] Phone is ringing...');

        // Play ring sound immediately, then every 3 seconds
        this.playRingSound();
        this.ringInterval = setInterval(() => {
            if (this.phoneRinging && !this.phoneAnswered) {
                this.playRingSound();
            }
        }, 3000);
    }

    stopPhoneRinging() {
        this.phoneRinging = false;
        if (this.ringInterval) {
            clearInterval(this.ringInterval);
            this.ringInterval = null;
        }
        console.log('[DETECTIVE] Phone stopped ringing');
    }

    answerPhone() {
        if (this.phoneAnswered) return;

        this.phoneAnswered = true;
        this.stopPhoneRinging();
        console.log('[DETECTIVE] Phone answered!');

        // Notify app.js that phone was answered
        this.onButtonClick('ANSWER_PHONE');
    }

    playRingSound() {
        // Create audio context lazily
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }

        const ctx = this.audioContext;
        const now = ctx.currentTime;

        // Classic 1980s phone ring - two-tone pattern
        // Ring pattern: brring-brring (2 bursts)
        for (let burst = 0; burst < 2; burst++) {
            const burstStart = now + burst * 0.4;

            // High frequency tone
            const osc1 = ctx.createOscillator();
            const gain1 = ctx.createGain();
            osc1.connect(gain1);
            gain1.connect(ctx.destination);
            osc1.frequency.value = 440; // A4
            osc1.type = 'sine';
            gain1.gain.setValueAtTime(0.15, burstStart);
            gain1.gain.exponentialRampToValueAtTime(0.01, burstStart + 0.3);
            osc1.start(burstStart);
            osc1.stop(burstStart + 0.3);

            // Low frequency modulation
            const osc2 = ctx.createOscillator();
            const gain2 = ctx.createGain();
            osc2.connect(gain2);
            gain2.connect(ctx.destination);
            osc2.frequency.value = 480; // Slightly higher for bell sound
            osc2.type = 'sine';
            gain2.gain.setValueAtTime(0.12, burstStart);
            gain2.gain.exponentialRampToValueAtTime(0.01, burstStart + 0.3);
            osc2.start(burstStart);
            osc2.stop(burstStart + 0.3);

            // Add some "bell" harmonics
            const osc3 = ctx.createOscillator();
            const gain3 = ctx.createGain();
            osc3.connect(gain3);
            gain3.connect(ctx.destination);
            osc3.frequency.value = 880; // Octave up
            osc3.type = 'sine';
            gain3.gain.setValueAtTime(0.05, burstStart);
            gain3.gain.exponentialRampToValueAtTime(0.01, burstStart + 0.2);
            osc3.start(burstStart);
            osc3.stop(burstStart + 0.2);
        }
    }

    // Stub methods for compatibility with app.js state updates
    setRadiationLevel(level) {}
    setTimeRemaining(time) {}
    setHullPressure(pressure) {}
    setSystemsRepaired(count) {}
    setPhase(phase) {}

    /**
     * Clean up all resources. Called when switching scenes.
     */
    dispose() {
        console.log('[DETECTIVE] Disposing scene...');

        // Stop phone ringing
        this.stopPhoneRinging();

        // Close audio context
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        // Remove UI elements
        if (this.backButton && this.backButton.parentNode) {
            this.backButton.parentNode.removeChild(this.backButton);
        }
        if (this.boardTooltip && this.boardTooltip.parentNode) {
            this.boardTooltip.parentNode.removeChild(this.boardTooltip);
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
        this.evidencePins = [];
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;

        console.log('[DETECTIVE] Scene disposed');
    }

    /**
     * Alias for dispose() - compatibility with app.js
     */
    destroy() {
        this.dispose();
    }
}
