# Scene Development Guide

This directory contains all scene definitions, assets, and logic organized in a scene-centric folder structure.

## Folder Structure

```
/scenes/
  /base/
    base.py                      # BaseScene Python class
    base_scene.js                # BaseScene JavaScript interface
    handler_base.py              # SceneHandler base class
    world_labs_importer.js       # World Labs GLB import utility

  /[scene_name]/
    [scene_name].py              # Scene definition (controls, facts, hooks)
    [scene_name]_handler.py      # Scene handler (button logic) - optional
    [scene_name]_scene.js        # Frontend Three.js scene
    [scene_name]_model.glb       # World Labs 3D environment
    camera_config.json           # Camera positioning preset
    art_prompt.md                # World Labs generation prompt
```

## Importing World Labs Environments

### 1. Generate 3D Environment

1. Go to [World Labs Marble](https://marble.worldlabs.ai/)
2. Create your environment with a detailed prompt
3. Export as GLB format
4. Document your generation prompt for future reference

### 2. Add to Project

```bash
# Create scene folder (if new scene)
mkdir -p scenes/my_scene

# Add GLB file
cp ~/Downloads/my_environment.glb scenes/my_scene/my_environment.glb

# Create art prompt documentation
cat > scenes/my_scene/art_prompt.md << 'EOF'
# World Labs Generation Prompt

**Prompt:** Victorian detective office with mahogany desk, leather chair,
gaslight fixtures, evidence board with photos and string connections,
vintage telephone, filing cabinets, London cityscape through window.

**Date:** 2026-01-31
**Model Version:** World Labs Marble v1
**Export Format:** GLB
**Notes:** Emphasized dark wood tones and atmospheric lighting
EOF
```

### 3. Load in Scene JavaScript

```javascript
import { WorldLabsImporter } from '/scenes/base/world_labs_importer.js';

export class MyScene {
    constructor(container) {
        this.container = container;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.model = null;

        this.init();
        this.loadEnvironment();
        this.animate();
    }

    init() {
        // Create Three.js scene, camera, renderer
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        // ... setup code ...
    }

    async loadEnvironment() {
        try {
            const result = await WorldLabsImporter.load(
                '/scenes/my_scene/my_environment.glb',
                this.scene,
                this.camera,
                {
                    targetSize: 15,              // Scale model to 15 units wide
                    cameraConfigPath: '/scenes/my_scene/camera_config.json',
                    autoPositionCamera: true,    // Auto-calculate if no config
                    enableShadows: true,
                    fixBlackMaterials: true,     // Brighten pure black materials
                }
            );

            this.model = result.model;

            // Setup orbit controls target
            if (result.cameraConfig.target) {
                this.controls.target.set(
                    result.cameraConfig.target.x,
                    result.cameraConfig.target.y,
                    result.cameraConfig.target.z
                );
            } else {
                // Fallback: look at model center
                this.controls.target.copy(result.bounds.center);
            }

            this.controls.update();

            // Setup SHIFT+C shortcut to export camera position
            WorldLabsImporter.setupExportShortcut(this.camera, this.controls);

            console.log('[MY_SCENE] Model loaded successfully');
            console.log('[MY_SCENE] Press SHIFT+C to export camera config');

        } catch (error) {
            console.error('[MY_SCENE] Error loading model:', error);
            this.createFallbackScene();
        }
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }
}
```

### 4. Find Optimal Camera Position

The WorldLabsImporter provides two methods for camera positioning:

#### Method A: Auto-Positioning (Quick Start)

1. **Don't create a camera_config.json file** - let the importer auto-calculate
2. Run the scene - camera will position based on model bounding box heuristics
3. The auto-position algorithm places the camera to show ~70% of model height with a slight offset for depth perception
4. If satisfied, you're done! If not, proceed to Method B for fine-tuning

#### Method B: Manual Positioning (Fine Control)

1. **Enable WASD debug mode** (if not already in your scene):
   - Hold SHIFT and use WASD keys to fly around
   - Q/E for up/down movement
   - Mouse drag to look around
   - Scroll to adjust FOV

2. **Find the perfect view**:
   - Fly around the environment with SHIFT+WASD
   - Position the camera where you want the player to start
   - Aim the camera at the focal point of your scene

3. **Export camera config**:
   - Press **SHIFT+C** while at your desired position
   - Camera config JSON will be printed to browser console
   - Copy the JSON output

4. **Save camera config**:
   ```bash
   # Paste the console output into camera_config.json
   cat > scenes/my_scene/camera_config.json << 'EOF'
   {
     "position": { "x": 1.13, "y": 2.92, "z": 1.58 },
     "target": { "x": 0.47, "y": 2.98, "z": 0.83 },
     "fov": 60,
     "description": "Optimal view of detective's desk with evidence visible"
   }
   EOF
   ```

5. **Test saved config**:
   - Reload the scene
   - Camera should now use your saved position
   - SHIFT+C still works to export new positions

### 5. Camera Config Format

```json
{
  "position": {
    "x": 1.13,
    "y": 2.92,
    "z": 1.58
  },
  "target": {
    "x": 0.47,
    "y": 2.98,
    "z": 0.83
  },
  "direction": {
    "x": -0.66,
    "y": 0.06,
    "z": -0.75
  },
  "fov": 60,
  "description": "Optimal view of workbench with spell components visible"
}
```

**Fields:**
- `position` (required): Camera position in world space
- `target` (optional): Point the camera looks at (for orbit controls)
- `direction` (optional): Direction vector (alternative to target)
- `fov` (optional): Field of view in degrees (default: 60)
- `description` (optional): Human-readable notes about this camera position

## WorldLabsImporter API Reference

### `WorldLabsImporter.load(modelPath, scene, camera, options)`

Loads a World Labs GLB model with automatic setup.

**Parameters:**
- `modelPath` (string): Path to GLB file (e.g., "/scenes/wizard/merlins_workshop.glb")
- `scene` (THREE.Scene): Three.js scene to add model to
- `camera` (THREE.Camera): Camera to position
- `options` (object): Configuration options

**Options:**
```javascript
{
    targetSize: 15,              // Scale model to this many units (default: 15)
    cameraConfigPath: null,      // Path to camera_config.json (optional)
    autoPositionCamera: true,    // Auto-calculate camera position (default: true)
    groundAtZero: true,          // Place model bottom at y=0 (default: true)
    centerHorizontally: true,    // Center model at x=0, z=0 (default: true)
    fixBlackMaterials: true,     // Brighten pure black materials (default: true)
    enableShadows: true,         // Enable shadow casting/receiving (default: true)
}
```

**Returns:** Promise resolving to:
```javascript
{
    model: THREE.Group,          // The loaded 3D model
    cameraConfig: object,        // Camera configuration used
    bounds: {                    // Model bounding box info
        box: THREE.Box3,
        size: THREE.Vector3,
        center: THREE.Vector3
    },
    scale: number               // Scale factor applied to model
}
```

### `WorldLabsImporter.setupExportShortcut(camera, controls)`

Sets up SHIFT+C keyboard shortcut to export camera config.

**Parameters:**
- `camera` (THREE.Camera): Camera to export
- `controls` (OrbitControls): Orbit controls (for target position)

**Returns:** Cleanup function to remove event listener

### `WorldLabsImporter.exportCameraConfig(camera, controls)`

Manually export current camera position (same as SHIFT+C).

**Parameters:**
- `camera` (THREE.Camera): Camera to export
- `controls` (OrbitControls): Orbit controls (for target position)

**Returns:** Camera config object (also logged to console)

## Scene Development Workflow

### Creating a New Scene

1. **Create scene folder:**
   ```bash
   mkdir -p scenes/my_scene
   ```

2. **Create Python scene definition** (`scenes/my_scene/my_scene.py`):
   ```python
   from scenes.base.base import Scene, SceneControl, StateVariable
   from scene_hooks import create_standard_hooks

   class MyScene(Scene):
       def __init__(self):
           facts = [
               "Fact 1 about the scene...",
               "Fact 2 about the scene...",
           ]

           hooks = create_standard_hooks(
               slip_detection=True,
               emotional_tracking=True,
               custom_hooks=[...]
           )

           controls = [
               SceneControl(id="action_1", label="DO THING", npc_aware=True),
           ]

           super().__init__(
               id="my_scene",
               name="My Scene",
               description="Scene description for LLM...",
               facts=facts,
               hooks=hooks,
               controls=controls,
           )
   ```

3. **Register scene** (`scenes/__init__.py`):
   ```python
   from scenes.my_scene.my_scene import MyScene

   SCENES = {
       'my_scene': MyScene(),
       # ... other scenes ...
   }
   ```

4. **Create JavaScript scene** (`scenes/my_scene/my_scene_scene.js`):
   - Use WorldLabsImporter for 3D environments
   - Implement BaseScene interface (init, dispose, updateState, setPhase)

5. **Add to frontend** (`web/js/app.js`):
   ```javascript
   import { MyScene } from '/scenes/my_scene/my_scene_scene.js';
   ```

6. **Configure scene mapping** (`config/scene_mappings.json`):
   ```json
   {
     "scenes": {
       "my_scene": {
         "character": "character_id",
         "characterName": "Character Name",
         "displayName": "Scene Display Name"
       }
     }
   }
   ```

### Updating Existing Scenes

To migrate an existing scene to use WorldLabsImporter:

1. **Move files to scene folder:**
   ```bash
   cp scenes/old_scene.py scenes/old_scene/old_scene.py
   cp web/js/old_scene.js scenes/old_scene/old_scene_scene.js
   cp art/old_model.glb scenes/old_scene/old_model.glb
   ```

2. **Update scene JavaScript:**
   - Replace GLTFLoader code with WorldLabsImporter.load()
   - Extract hardcoded camera positions to camera_config.json
   - Update import paths to use absolute paths (/scenes/...)

3. **Update imports:**
   - Update `scenes/__init__.py` to import from new location
   - Update `web/js/app.js` to import from new location

4. **Test:**
   - Verify model loads
   - Verify camera positions correctly
   - Test SHIFT+C export functionality

## Best Practices

### World Labs Generation

- **Be specific with prompts:** Include lighting, materials, style, time of day
- **Document your prompt:** Save to art_prompt.md for reproducibility
- **Iterate on exports:** Try different prompts if first result isn't ideal
- **Consider scale:** Mention size/scope in prompt (e.g., "small room", "large cathedral")

### Camera Positioning

- **Start with auto-positioning:** Let the algorithm give you a starting point
- **Use WASD for fine-tuning:** Manual positioning gives precise control
- **Test different angles:** Export multiple configs and compare
- **Consider player perspective:** Position camera for optimal gameplay/narrative view
- **Document positions:** Use the "description" field to note what's visible

### Performance

- **Target size matters:** 15 units is a good default, adjust for scene complexity
- **Enable shadows selectively:** Disable if FPS drops below 50
- **Monitor GLB file size:** Keep under 150MB for reasonable load times
- **Test on target hardware:** Desktop GPUs can handle more than integrated graphics

### Code Organization

- **Keep scenes self-contained:** All assets in scene folder
- **Reuse base utilities:** WorldLabsImporter, base scene classes
- **Document custom behavior:** Add comments for scene-specific logic
- **Use handlers for complex logic:** Keep scene definitions declarative

## Troubleshooting

### Model doesn't load
- Check GLB file path is correct
- Verify static file route serves /scenes/ directory
- Check browser console for 404 errors
- Confirm GLB file isn't corrupted (try re-exporting from World Labs)

### Camera position is wrong
- Delete camera_config.json to test auto-positioning
- Use SHIFT+C to export current position
- Check camera_config.json is valid JSON
- Verify cameraConfigPath points to correct file

### Black materials / poor lighting
- Enable `fixBlackMaterials: true` in WorldLabsImporter options
- Add scene lights (ambient, point, directional)
- Check World Labs export settings
- Adjust renderer tone mapping and exposure

### Performance issues
- Reduce `targetSize` to scale model smaller
- Disable shadows with `enableShadows: false`
- Lower renderer pixel ratio
- Simplify World Labs model (fewer polygons, smaller textures)

### SHIFT+C doesn't work
- Check WorldLabsImporter.setupExportShortcut() is called
- Verify browser console isn't filtering logs
- Try manual export: `WorldLabsImporter.exportCameraConfig(camera, controls)`
- Check keyboard focus is on renderer canvas

## Examples

### Merlin's Workshop (Reference Implementation)

See `scenes/wizard/` for a complete example:
- `merlins_room_scene.js`: Uses WorldLabsImporter with saved config
- `camera_config.json`: Carefully positioned camera for workbench view
- `merlins_workshop.glb`: 136MB World Labs export
- `art_prompt.md`: Original generation prompt

### Creating a Detective Office

```javascript
// scenes/detective/detective_scene.js
import { WorldLabsImporter } from '/scenes/base/world_labs_importer.js';

export class DetectiveScene {
    async loadEnvironment() {
        const result = await WorldLabsImporter.load(
            '/scenes/detective/office_environment.glb',
            this.scene,
            this.camera,
            {
                targetSize: 12,  // Smaller room
                cameraConfigPath: '/scenes/detective/camera_config.json',
            }
        );

        this.model = result.model;

        // Load additional props (phone, magnifying glass, etc.)
        await this.loadInteractiveProps();
    }
}
```

## Additional Resources

- [World Labs Documentation](https://worldlabs.ai/docs)
- [Three.js Documentation](https://threejs.org/docs/)
- [GLTFLoader Guide](https://threejs.org/docs/#examples/en/loaders/GLTFLoader)
- [CLAUDE.md](../CLAUDE.md): Full project architecture guide
