# Foxhole Scene - 3D Environment Art Prompt

**Scene:** Foxhole - The Prospero Bridge
**File:** scenes/foxhole/foxhole_panorama.png (360° panoramic image)
**Style:** Antiquated submarine interior, Nautilus-inspired, steampunk-meets-naval

---

## Overview

The bridge of the Prospero, a deep-sea research vessel with a Victorian-era aesthetic meets modern submarine functionality. This is a working military-grade submarine but with an antiquated, almost Jules Verne quality - like the Nautilus from 20,000 Leagues Under the Sea.

**Mood:** Emergency crisis. Dim emergency lighting. Claustrophobic but functional. Water dripping. Sparks flying. A place built for competence now failing under extraordinary circumstances.

---

## Core Design Elements

### The Bridge Layout
- **Compact circular/oval space** - approximately 12-15 feet diameter
- **High ceiling** with exposed pipes, valves, pressure gauges
- **Central helm station** - ship's wheel or modern helm controls
- **Surrounding control panels** - arranged in arc around perimeter
- **Floor** - metal grating with water pooling beneath
- **One exit** - stairwell/hatch leading down (shows water/flooding below)

### Aesthetic: Mechanical & Analogue
- **Physical switches and levers** - no touchscreens, everything is tactile
- **Brass and copper accents** on steel/iron base
- **Pressure gauges** - circular dials with brass bezels, red zones marked
- **Valves and pipes** - visible throughout, some dripping/leaking
- **Riveted hull plates** - visible construction, industrial strength
- **Manual overrides** - pull-handles, emergency releases
- **Nautical instrumentation** - depth gauge, compass, inclinometer
- **Cable runs** - exposed electrical/communications cables

### Emergency Lighting
- **Primary:** Dim red/orange emergency lights
- **Secondary:** Flickering overhead incandescent bulbs
- **Warning lights:** Red alarm lights rotating slowly
- **Panel illumination:** Backlit gauges and switches (some flickering)
- **Overall tone:** Very dim, dramatic shadows, pools of light

### Crisis Details (Scene Setting)
- **Water effects:**
  - Puddles on floor grating
  - Water dripping from ceiling pipes
  - Slow leak from one bulkhead
  - Mist/condensation in air
- **Damage:**
  - Sparking electrical panel (intermittent)
  - Cracked gauge glass on one instrument
  - Hanging cable (disconnected)
  - Slight list/tilt to entire space (5-10 degrees)
- **Active systems:**
  - Steam venting from relief valve
  - Spinning pressure gauges showing critical levels
  - Blinking warning indicators

---

## Specific Control Panels

### Main Helm Station (Center)
- Large ship's wheel OR modern submarine helm controls
- Central position, slightly elevated
- Trajectory/depth controls visible
- Compass and horizon indicator
- Throttle levers

### Power Control Panel (Side)
- Large breaker switches (up/down toggles)
- Battery level indicators
- Generator status lights (currently red/dark)
- Emergency power controls
- **Key element:** One large lever marked "BACKUP POWER"

### Crew Status Board (Side)
- Names and positions listed
- Duty roster
- Location tracking board
- **Key element:** Machinery bay entry log display screen (analogue readout)

### Flooding Control Panel (Side)
- Valve controls for compartments
- Drainage pump switches
- Compartment isolation indicators
- **Key element:** Large red button/lever - "MACHINERY BAY FLOOD CONTROL" with warning labels

### Communications Station (Side)
- Radio equipment
- Headset hanging
- Frequency dials
- Microphone
- Status: Active, patched through to James Kovich's vessel

---

## Atmosphere & Mood

**Color Palette:**
- **Dominant:** Dark steel grey, gunmetal
- **Accents:** Brass, copper, tarnished gold
- **Emergency:** Red and orange (lights, warnings)
- **Depth:** Deep blue-black through portholes
- **Sparks:** Bright white/blue electrical arcs

**Lighting:**
- Chiaroscuro - dramatic light and shadow
- Key lights from emergency panels
- Rim lighting from overhead emergency strips
- Practical lights: illuminated gauges, warning lights
- Overall: Moody, tense, barely enough light to work

**Sound Design (for reference, not in model):**
- Distant alarm klaxon
- Metal creaking under pressure
- Water dripping
- Steam hissing
- Electrical buzzing/sparking
- Radio static

---

## Camera Angles & Composition

**Default View (camera_config.json):**
- Position: Standing at entrance, looking toward helm
- Height: 1.6m (eye level)
- Shows: Helm in center, control panels flanking, ceiling detail
- Framing: Wide enough to see scope but intimate/claustrophobic

**Key Visual Lines:**
- Pipes leading eye upward to ceiling
- Panels creating circular flow around space
- Depth created by layers of detail front-to-back
- Central helm as focal point

---

## Technical Specifications

**Model Requirements:**
- **Scale:** Realistic human scale (2m ceiling height)
- **Polycount:** Moderate detail - this is a hero environment
- **Textures:** PBR materials (roughness, metallic, normal maps)
- **Lighting:** Baked ambient occlusion, emissive materials for lit elements
- **Modularity:** Could extract individual panels/elements for interaction

**Materials:**
- Steel (various finishes - brushed, painted, rusted)
- Brass/copper (polished and tarnished)
- Glass (gauges, some cracked)
- Rubber (cable insulation, gaskets)
- Painted metal (chipped, worn)

---

## Reference Inspirations

**Real Submarines:**
- WW2 submarine control rooms (U-boats, US fleet subs)
- Modern submarine conn (for layout efficiency)
- Research submarine pilot spheres (Alvin, Deepsea Challenger)

**Fiction:**
- Nautilus interior (20,000 Leagues Under the Sea)
- Submarine from The Hunt for Red October
- Bioshock underwater aesthetic
- Das Boot submarine interiors
- Crimson Tide submarine sets

**Mood References:**
- Pressure Point scene from Digital Actors (but different vessel)
- Emergency lighting in spacecraft (Apollo 13, Gravity)
- Dieselpunk submarine concepts
- Victorian-era industrial machinery

---

## Storytelling Through Environment

The environment should silently communicate:

1. **This was built for competence** - every control has purpose, everything is labeled
2. **It's failing** - but slowly, giving time to act
3. **Someone should be here** - the crew quarters door is visible (sealed), implying others nearby but unreachable
4. **Isolation** - this is a small space in a vast dark ocean
5. **Age and history** - this vessel has been through much, patina of use
6. **Beauty in function** - the aesthetic comes from nautical engineering, not decoration

---

## Player Interactions (for context)

The player will:
- Stand at stations and "press" buttons
- Read gauges and logs
- Look around to understand their situation
- Experience the space transform as power is restored (lights brighten)
- Witness visual feedback from their actions (gauges changing, lights activating)

The environment is a character in the story - it tells the player about:
- James's world (he knows spaces like this intimately)
- The crisis (visible damage, warnings)
- The weight of their actions (the FLOOD MACHINERY BAY control is ominous)

---

## Implementation Notes

**For World Labs Generation:**
- Prompt: "Vintage submarine control room bridge, Nautilus inspired, Victorian steampunk naval aesthetic, emergency red lighting, metal and brass controls, pressure gauges, water damage, dramatic shadows, Jules Verne meets WW2 submarine, claustrophobic but functional"
- Style: Realistic with industrial/nautical character
- Lighting: Dim emergency atmosphere
- Detail level: High on hero elements (controls, helm), moderate elsewhere

**Post-Generation Adjustments:**
- May need to add emissive materials for lit gauges
- Camera positioning per camera_config.json
- Verify scale feels appropriate for player
- Test visibility of key interactive elements

---

## Notes on Divergence from Default Submarine

Foxhole uses the PROSPERO, not the Prospero from Pressure Point scene (James Smith).

**Key Differences:**
- This is James KOVICH's scenario (British, remote guidance)
- MACHINERY BAY instead of med bay
- Player is alone (not coordinating with trapped character on board)
- Bridge-focused (not moving between compartments)
- More antiquated aesthetic (vs modern military submarine)

The Prospero is a research vessel, so it can have character and charm that a military submarine wouldn't - this is the submarine equivalent of an old wooden sailing ship preserved with modern tech.
