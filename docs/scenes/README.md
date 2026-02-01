# Scene Descriptions Directory

This directory contains comprehensive documentation for all Digital Actors scenes, organized into two complementary file types:

1. **Scene Descriptions** (`*.md`) - Complete narrative, gameplay, and design documentation
2. **3D Art Prompts** (`*_3d-art-prompt.md`) - Production-ready prompts for World Labs 3D generation

---

## File Structure

### Scene Descriptions (Narrative & Design)
Comprehensive documentation including narrative design, gameplay mechanics, state variables, endings, and RAG facts. Used for dialogue generation, game design, and development.

- **[Pressure Point](pressure_point.md)** - Submarine survival with moral dilemma
- **[Life Raft](life_raft.md)** - Escape pod survival with sacrifice choice
- **[Iconic Detectives](iconic_detectives.md)** - 1987 NYC murder mystery phone call
- **[Crown Court](crown_court.md)** - Courtroom defense trial
- **[Merlin's Workshop](merlins_workshop.md)** - Medieval wizard's enchanted workshop
- **[Welcome](welcome.md)** - Platform introduction with Clippy
- **[Conversation](conversation.md)** - Free-form dialogue
- **[Introduction](introduction.md)** - First meeting with character

### 3D Art Generation Prompts (World Labs Ready)
Standalone prompts optimized for 3D world generation. Copy-paste ready for World Labs or other 3D generation tools. Each includes detailed environment specs, lighting, camera positioning, and style references.

- **[Merlin's Workshop](merlins_workshop_3d-art-prompt.md)** (9.3KB) - Medieval wizard workshop with floating candles
- **[Pressure Point](pressure_point_3d-art-prompt.md)** (11KB) - Damaged submarine interior, emergency state
- **[Iconic Detectives](iconic_detectives_3d-art-prompt.md)** (11KB) - 1987 NYC detective office with string board
- **[Life Raft](life_raft_3d-art-prompt.md)** (11KB) - Cramped escape pod with dual oxygen gauges
- **[Crown Court](crown_court_3d-art-prompt.md)** (11KB) - British Crown Court courtroom
- **[Welcome](welcome_3d-art-prompt.md)** (7.4KB) - Clean UI space with Clippy character

---

## How to Use These Files

### For 3D Artists & World Generation
1. Open the `*_3d-art-prompt.md` file for your scene
2. Use the structured sections for detailed generation specs
3. Use the **"Copy-Paste Prompt Summary"** section at the bottom for quick generation
4. Reference the style examples and color palettes
5. Paste directly into World Labs or your 3D generation tool

### For Game Designers
Reference the scene description `*.md` files for:
- Gameplay mechanics and control interactions
- State variable tracking and progression
- Win/loss conditions and multiple endings
- Phase structures and milestone systems

### For Writers & Dialogue Designers
Use the scene description `*.md` files for:
- Character voices and emotional beats
- RAG facts (character knowledge base)
- Opening speeches and narrative structure
- Success/failure message templates

### For Developers
Both file types provide:
- Scene IDs and technical identifiers
- State variable definitions
- Control mappings and button specifications
- Integration notes and implementation details

---

## 3D Art Prompt Structure

Each `*_3d-art-prompt.md` file includes:

### 1. Scene Overview
One-sentence summary of the environment

### 2. Environment Description
Detailed paragraph describing the space, atmosphere, and purpose

### 3. Key Environmental Elements
Bulleted breakdown of all props, architecture, and details:
- Architecture & structure
- Hero props (control panels, desks, key objects)
- Critical interactive elements
- Environmental damage/details
- Atmospheric elements

### 4. Atmosphere & Mood
Emotional tone, feel, and design intent

### 5. Lighting Specifications
- Primary lighting sources
- Secondary/accent lighting
- Color temperature values
- Shadow and contrast guidelines
- VFX lighting (sparks, glows, etc.)

### 6. Camera Specifications
- Position coordinates (when applicable)
- Viewing angles and FOV
- Movement constraints
- Framing goals

### 7. Technical Details
- Scale and proportions (measurements)
- Material properties (textures, finishes)
- Particle and VFX requirements
- Animation suggestions

### 8. Color Palette
- Primary colors (hex codes)
- Accent colors
- Surface tones
- Lighting colors

### 9. Style References
- Visual style examples (films, games, art)
- Cinematic references
- Period authenticity notes
- Artistic direction

### 10. Production Notes
- Optimization priorities
- What to avoid (anti-patterns)
- Sound design integration cues

### 11. Copy-Paste Prompt Summary
**Condensed version** - Single paragraph with all critical details, ready to paste into World Labs for quick generation.

---

## Scene Categories

**Survival:** High-stakes scenarios with life-or-death choices
- Pressure Point (Submarine), Life Raft (Escape Pod)

**Mystery:** Investigation, evidence gathering, contradiction detection
- Iconic Detectives (Detective Office)

**Drama:** Emotional tension, moral dilemmas
- Crown Court (Courtroom), Life Raft (Sacrifice)

**Fantasy:** Magical, exploratory, world-building
- Merlin's Workshop (Wizard Tower)

**Tutorial:** Platform introduction, low-stakes exploration
- Welcome (Clippy Interface)

---

## Creating New Scene Documentation

### When Adding a New Scene:

#### 1. Create Scene Description (`scene_name.md`)
Follow the template structure:
- Overview (metadata)
- Visual description
- World Labs prompt (embedded)
- Gameplay mechanics
- Narrative details
- Endings
- Design pillars

#### 2. Create 3D Art Prompt (`scene_name_3d-art-prompt.md`)
Use the dedicated template:
- Scene overview
- Environment description
- Key elements (detailed bullets)
- Atmosphere & mood
- Lighting specifications
- Camera specifications
- Technical details
- Color palette (hex codes)
- Style references
- Production notes
- **Copy-paste summary** (condensed prompt at bottom)

### Tips for Writing 3D Prompts
- **Be specific:** Include measurements, hex codes, exact positions
- **Reference real examples:** Films, games, locations
- **Provide alternatives:** "Option A or Option B" gives flexibility
- **Include a condensed version:** Copy-paste summary at bottom for quick use
- **Use hex codes:** #4466ff, not "blue"
- **Specify materials:** "Matte gunmetal gray" not "gray metal"
- **Give context:** "Worn 1960s desk" not "old desk"

---

## Dual-File Philosophy

### Why Separate Files?

**Scene Descriptions** are for:
- Game designers planning mechanics
- Writers crafting dialogue
- Developers implementing systems
- RAG/AI context for character dialogue generation

**3D Art Prompts** are for:
- Artists generating 3D environments
- World Labs or similar AI generation tools
- Art direction and style guides
- Production pipelines (can be automated later)

By separating concerns, each file serves its audience without clutter. 3D artists don't need gameplay mechanics, and game designers don't need lighting hex codes.

---

## Future Automation

These 3D art prompt files are designed to support future automation:
- Batch generation via World Labs API (when available)
- CI/CD pipeline integration for art asset generation
- Version control for iterative 3D scene refinement
- A/B testing different prompt variations

For now, they serve as copy-paste templates for manual generation.

---

## Maintenance

Update these files when:
- Scene designs change significantly
- New 3D models are created or revised
- Gameplay mechanics are updated
- Narrative beats shift
- Visual style evolves
- New technical specifications are added

Keep both file types synchronized - if the submarine gets a new control panel in gameplay, update both the scene description AND the 3D art prompt.

---

## Quick Reference

| Scene | Scene Description | 3D Art Prompt |
|-------|------------------|---------------|
| Merlin's Workshop | [merlins_workshop.md](merlins_workshop.md) | [merlins_workshop_3d-art-prompt.md](merlins_workshop_3d-art-prompt.md) |
| Pressure Point | [pressure_point.md](pressure_point.md) | [pressure_point_3d-art-prompt.md](pressure_point_3d-art-prompt.md) |
| Iconic Detectives | [iconic_detectives.md](iconic_detectives.md) | [iconic_detectives_3d-art-prompt.md](iconic_detectives_3d-art-prompt.md) |
| Life Raft | [life_raft.md](life_raft.md) | [life_raft_3d-art-prompt.md](life_raft_3d-art-prompt.md) |
| Crown Court | [crown_court.md](crown_court.md) | [crown_court_3d-art-prompt.md](crown_court_3d-art-prompt.md) |
| Welcome | [welcome.md](welcome.md) | [welcome_3d-art-prompt.md](welcome_3d-art-prompt.md) |
| Conversation | [conversation.md](conversation.md) | N/A (sphere scene) |
| Introduction | [introduction.md](introduction.md) | N/A (sphere scene) |
