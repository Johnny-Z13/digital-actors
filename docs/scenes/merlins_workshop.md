# Merlin's Workshop Scene Description

**Scene ID:** `merlins_room` (quest.py)
**Character:** Merlin (Wizard)
**Category:** Fantasy
**Display Name:** Merlin's Workshop
**3D Model:** `/art/merlins_workshop.glb`

---

## Overview

An enchanted alchemy workshop where the ancient wizard Merlin resides. A cluttered but cozy medieval space filled with bubbling potions, ancient tomes, glowing crystals, and mysterious artifacts spanning centuries of accumulated magical knowledge.

---

## World Labs Generation Prompt

### Scene Description

A medieval wizard's enchanted alchemy workshop carved from weathered stone, cluttered with centuries of accumulated magical artifacts and arcane knowledge. The cramped but cozy space emanates mystical warmth and ancient wisdom.

### Key Environmental Elements

**Architecture & Walls:**
- Rough-hewn stone walls with a warm, aged patina showing centuries of use
- Arched doorways and gothic architectural details
- Weathered medieval stonework with moss or magical runes in crevices
- Ceiling height approximately 12-15 feet with exposed wooden beams

**Shelving & Storage:**
- Floor-to-ceiling wooden shelves lining all walls, warped and dark with age
- Shelves packed with glass jars containing glowing liquids, dried herbs, mysterious powders, and preserved specimens
- Labels written in flowing calligraphy on yellowed parchment
- Some jars emit soft internal light (amber, green, blue)

**Central Features:**
- Large cast-iron cauldron (3-4 feet diameter) in the corner, actively bubbling with luminescent green or purple liquid
- Steam rising from cauldron creating atmospheric haze
- Wooden worktable cluttered with brass instruments, mortars and pestles, open grimoires, and crystal spheres
- Ancient leather-bound tomes stacked haphazardly, some floating mid-air defying gravity

**Magical Lighting:**
- 20-30 floating candles hovering at various heights (key feature - primary light source)
- Candles emit warm orange-yellow light (color temperature ~2000K)
- Candles gently bob and drift in slow, lazy patterns
- Flickering candlelight creates dancing shadows across all surfaces
- Magical blue accent light emanating from crystals, potions, or a glowing artifact on the worktable (cool blue #4466ff)

**Additional Details:**
- Glowing crystals scattered throughout - amethyst, quartz, and unnatural luminescent varieties
- Brass/copper alchemical equipment: retorts, alembics, distillation apparatus
- Scrolls partially unrolled showing star charts, magical circles, or ancient scripts
- A gnarled wooden staff leaning in corner with glowing crystal pommel
- Dried herbs and roots hanging from ceiling beams
- Mysterious artifacts: astrolabes, orreries, enchanted mirrors
- Dusty particles visible in light beams creating volumetric lighting effect
- Overall color palette: deep purples, warm ambers, mystical blues, aged browns

**Atmosphere & Mood:**
- Mystical yet welcoming, not ominous
- Cluttered organized chaos - everything has purpose but placement is eccentric
- Warm and lived-in despite magical elements
- Sense of accumulated wisdom and ancient knowledge
- Intimate scale - feels like a personal study rather than grand tower

### Technical Specifications

**Camera Position:**
- Position primary viewing angle at coordinates (1.13, 2.92, 1.58) relative to scene center
- Looking slightly down and toward the main workshop area to showcase the worktable, cauldron, and floating candles

**Lighting Configuration:**
- Background ambient color: Deep midnight purple (#1a1520)
- Primary lighting: Warm candlelight (orange-yellow, ~2000K)
- Accent lighting: Cool blue magical glow (#4466ff)
- Ensure volumetric effects for cauldron steam and atmospheric dust
- Floating candles should appear to defy gravity with gentle drift animation potential

**Style Reference:** Medieval fantasy wizard's tower interior meets alchemist's laboratory. Think *Harry Potter's* Dumbledore's office meets classic D&D wizard workshop. Mystical, warm, cluttered with magical purpose. Not modern or clean - embrace the weathered, ancient quality.

---

## Narrative Details

**Opening Speech:**
- "Ah, a visitor! Come in, come in..."
- "Mind the cauldron - it bites."
- "Now then, what brings you to my humble workshop?"

**Character:** Merlin speaks mystically yet approachably, occasionally using riddles and metaphors. He has witnessed centuries of history and enjoys teaching through stories.

**Interaction Style:** Free-form conversation about magic, wisdom, philosophy, and ancient knowledge. No time pressure, purely exploratory dialogue.

---

## Implementation Details

**Scene Type:** Custom 3D scene with GLB model
**JavaScript Handler:** `merlins_room_scene.js`
**Controls:** WASD movement (SHIFT mode), mouse look, FOV zoom
**Audio:** Background ambience, SFX library for magical sounds
**Voice Effect:** None (natural voice)

**Lighting System (Three.js):**
- Strong ambient light (0.8 intensity)
- Hemisphere light (sky/ground fill)
- Main directional light (1.5 intensity, shadows enabled)
- Fill light from opposite side (0.8 intensity)
- 4 warm point lights (candlelight positions, flickering animation)
- 1 magical blue point light (1.0 intensity, pulsing animation)

**Particle System:**
- 30 floating candle particles
- Warm orange color (#ffaa44)
- Additive blending for glow effect
- Vertical floating animation

---

## Design Goals

1. **Mystical Atmosphere:** Balance magic and warmth - fantastical but inviting
2. **Visual Density:** Rich detail without overwhelming - cluttered with purpose
3. **Lighting Drama:** Candlelight flicker and magical glow as primary sources
4. **Scale Intimacy:** Personal workshop feel, not grand wizard tower
5. **Ancient Wisdom:** Visual storytelling of accumulated knowledge over centuries
