import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export class CharacterScene {
    constructor(container) {
        this.container = container;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.character = null;
        this.lights = [];

        this.init();
        this.animate();
    }

    init() {
        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a0a0f);
        this.scene.fog = new THREE.Fog(0x0a0a0f, 10, 50);

        // Camera
        this.camera = new THREE.PerspectiveCamera(
            75,
            window.innerWidth / window.innerHeight,
            0.1,
            1000
        );
        this.camera.position.set(0, 1.6, 3);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.container.appendChild(this.renderer.domElement);

        // Controls
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.minDistance = 2;
        this.controls.maxDistance = 8;
        this.controls.maxPolarAngle = Math.PI / 2;
        this.controls.target.set(0, 1, 0);

        // Lights
        this.setupLights();

        // Ground
        this.createGround();

        // Character
        this.createCharacter();

        // Particles
        this.createParticles();

        // Handle window resize
        window.addEventListener('resize', () => this.onWindowResize());
    }

    setupLights() {
        // Ambient light
        const ambientLight = new THREE.AmbientLight(0x404060, 0.5);
        this.scene.add(ambientLight);

        // Main directional light
        const mainLight = new THREE.DirectionalLight(0xffffff, 1);
        mainLight.position.set(5, 10, 5);
        mainLight.castShadow = true;
        mainLight.shadow.camera.near = 0.1;
        mainLight.shadow.camera.far = 50;
        mainLight.shadow.camera.left = -10;
        mainLight.shadow.camera.right = 10;
        mainLight.shadow.camera.top = 10;
        mainLight.shadow.camera.bottom = -10;
        mainLight.shadow.mapSize.width = 2048;
        mainLight.shadow.mapSize.height = 2048;
        this.scene.add(mainLight);

        // Rim light
        const rimLight = new THREE.DirectionalLight(0x4fc3f7, 0.5);
        rimLight.position.set(-5, 5, -5);
        this.scene.add(rimLight);

        // Point light for character
        const characterLight = new THREE.PointLight(0x4fc3f7, 0.5, 10);
        characterLight.position.set(0, 2, 2);
        this.scene.add(characterLight);
        this.lights.push(characterLight);
    }

    createGround() {
        const groundGeometry = new THREE.CircleGeometry(10, 64);
        const groundMaterial = new THREE.MeshStandardMaterial({
            color: 0x0f0f1a,
            roughness: 0.8,
            metalness: 0.2,
        });
        const ground = new THREE.Mesh(groundGeometry, groundMaterial);
        ground.rotation.x = -Math.PI / 2;
        ground.receiveShadow = true;
        this.scene.add(ground);

        // Grid helper
        const gridHelper = new THREE.GridHelper(20, 20, 0x2a2a3a, 0x1a1a2a);
        gridHelper.position.y = 0.01;
        this.scene.add(gridHelper);
    }

    createCharacter() {
        // Create a simple humanoid character using basic geometries
        const characterGroup = new THREE.Group();

        // Body
        const bodyGeometry = new THREE.CapsuleGeometry(0.3, 0.8, 16, 32);
        const bodyMaterial = new THREE.MeshStandardMaterial({
            color: 0x4fc3f7,
            roughness: 0.5,
            metalness: 0.3,
        });
        const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
        body.position.y = 1.2;
        body.castShadow = true;
        characterGroup.add(body);

        // Head
        const headGeometry = new THREE.SphereGeometry(0.25, 32, 32);
        const headMaterial = new THREE.MeshStandardMaterial({
            color: 0xffd4a3,
            roughness: 0.7,
            metalness: 0.1,
        });
        const head = new THREE.Mesh(headGeometry, headMaterial);
        head.position.y = 2.1;
        head.castShadow = true;
        characterGroup.add(head);

        // Eyes
        const eyeGeometry = new THREE.SphereGeometry(0.05, 16, 16);
        const eyeMaterial = new THREE.MeshStandardMaterial({
            color: 0x4fc3f7,
            emissive: 0x4fc3f7,
            emissiveIntensity: 0.5,
        });

        const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
        leftEye.position.set(-0.1, 2.15, 0.2);
        characterGroup.add(leftEye);

        const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
        rightEye.position.set(0.1, 2.15, 0.2);
        characterGroup.add(rightEye);

        // Glow effect around character
        const glowGeometry = new THREE.SphereGeometry(0.6, 32, 32);
        const glowMaterial = new THREE.MeshBasicMaterial({
            color: 0x4fc3f7,
            transparent: true,
            opacity: 0.1,
        });
        const glow = new THREE.Mesh(glowGeometry, glowMaterial);
        glow.position.y = 1.5;
        glow.scale.set(1.5, 2, 1.5);
        characterGroup.add(glow);

        this.character = characterGroup;
        this.scene.add(characterGroup);
    }

    createParticles() {
        const particlesGeometry = new THREE.BufferGeometry();
        const particlesCount = 200; // Reduced from 1000 for performance
        const positions = new Float32Array(particlesCount * 3);

        for (let i = 0; i < particlesCount * 3; i++) {
            positions[i] = (Math.random() - 0.5) * 20;
        }

        particlesGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const particlesMaterial = new THREE.PointsMaterial({
            color: 0x4fc3f7,
            size: 0.02,
            transparent: true,
            opacity: 0.6,
            blending: THREE.AdditiveBlending,
        });

        this.particles = new THREE.Points(particlesGeometry, particlesMaterial);
        this.scene.add(this.particles);
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        // Animate character (gentle breathing motion)
        if (this.character) {
            const time = Date.now() * 0.001;
            this.character.position.y = Math.sin(time * 0.5) * 0.05;
            this.character.rotation.y = Math.sin(time * 0.3) * 0.1;
        }

        // Animate particles
        if (this.particles) {
            this.particles.rotation.y += 0.0002;
        }

        // Pulse character light
        if (this.lights[0]) {
            const time = Date.now() * 0.001;
            this.lights[0].intensity = 0.5 + Math.sin(time * 2) * 0.2;
        }

        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    onWindowResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    // Method to change character appearance
    updateCharacter(config) {
        if (!this.character) return;

        // Update character color based on config
        const body = this.character.children.find(child =>
            child.geometry?.type === 'CapsuleGeometry'
        );
        if (body && config.color) {
            body.material.color.setHex(config.color);
        }

        // Update glow color
        const glow = this.character.children.find(child =>
            child.material?.transparent && child.scale.x > 1
        );
        if (glow && config.color) {
            glow.material.color.setHex(config.color);
        }
    }
}
