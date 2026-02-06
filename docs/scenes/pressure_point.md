# Pressure Point (Submarine) Scene Description

**Scene ID:** `submarine`
**Character:** Lt. Commander James Smith (Engineer)
**Category:** Survival
**Display Name:** Pressure Point
**3D Model:** Custom submarine interior scene

---

## Overview

A desperate 5-minute survival scenario aboard the failing research submarine USS Prospero at 2,400 feet depth. The player (junior systems operator) is trapped in the aft compartment while Lt. Commander James Smith is trapped in forward control. Lethal radiation is spreading. Communication is via radio only - no visual contact.

**The Moral Core:** James's son Adrian (marine biologist) is unconscious in the med bay. Emergency ascent requires flooding that compartment - killing Adrian. James must choose: sacrifice his son or let everyone die together.

---

## Visual Description (3D Environment)

### Setting Details

**Player's Location: Aft Compartment**
- Cramped metal interior, tilted 15 degrees (submarine listing)
- Emergency lighting: flickering amber and red panels
- Sparking control panels with exposed wiring
- Small circular porthole (left wall) showing murky blue deep ocean water with rising bubbles
- Claustrophobic metal walls with rivets and pipes
- Condensation on metal surfaces
- Steam/smoke from damaged systems

**Control Panel Display:**
- **Radiation Gauge:** Circular analog gauge, needle starting at 0%, slowly climbing (red danger zone at 95%+)
- **Time Remaining:** Digital countdown timer, starts at 08:00 (mm:ss)
- **Four Control Buttons:**
  - O2 VALVE (red) - emergency oxygen control
  - VENT (orange) - pressure release system
  - BALLAST (blue) - buoyancy adjustment
  - POWER (green) - backup power relay
- **Intercom Speaker:** Old-style mesh speaker with static, James's voice source
- **Flood Med Bay Button:** Appears in Phase 3+, bright red, positioned above other controls (deadly choice)

**Atmosphere:**
- Water dripping from pipes
- Occasional hull groans (metal stress sounds)
- Alarm klaxons (periodic, low-priority warnings)
- Emergency lighting casts harsh shadows
- Sense of pressure and confinement
- Temperature: cold but humid

**Color Palette:**
- Primary: Dark grays, gunmetal blues
- Accent: Amber/red emergency lighting
- Warning: Bright red (radiation gauge danger zone)
- Ocean through porthole: Deep murky blue-green

---

## World Labs Generation Prompt

**Environment:** Interior of a damaged submarine's aft compartment at extreme depth. Cold industrial metal surfaces, emergency lighting casting dramatic shadows. Submarine tilted 15 degrees, creating disorienting angles. Small porthole reveals deep ocean darkness with occasional bioluminescent particles drifting past.

**Key Elements:**
- Riveted metal walls with pipes and conduits running along ceiling
- Sparking control panel with analog gauges and chunky physical buttons (1970s submarine aesthetic)
- Emergency lighting: amber floods, red warning strips, flickering fluorescents
- Steam/smoke from damaged systems creating atmospheric haze
- Water dripping from ceiling pipes, pooling on tilted floor
- Intercom speaker: military-grade mesh speaker unit, crackling with static
- Porthole: 12-inch circular window, thick reinforced glass, showing deep ocean blue

**Atmosphere:** Claustrophobic, industrial, failing systems. Sense of immense pressure from depth. Cold metal surfaces with condensation. Emergency state - not calm operation. Think *Das Boot*, *The Abyss*, *K-19: The Widowmaker*.

**Lighting:** Harsh emergency lighting - amber and red. No natural light. Directional floods casting sharp shadows. Flickering suggests power fluctuations. Gauge backlighting (soft glow). Sparking electrical arcs from damaged panels.

**Camera Position:** First-person perspective, positioned at control panel. Player can look around but cannot move (trapped in compartment). Slight camera sway to suggest submarine movement/instability.

---

## Gameplay Mechanics

### Four-Phase Emotional Progression

**Phase 1: Impact & Connection (0:00-1:15)**
- James establishes competent but scared persona
- Asks player's real name (personal connection begins)
- Player works on restoring emergency power (cranking generator)
- James: "I won't let you die."

**Phase 2: Working Relationship (1:15-2:30)**
- Warmer, more personal under stress
- James asks about player's life topside
- Breathing becomes labored (radiation effects)
- Begins revealing details about "someone" in med bay without naming them

**Phase 3: The Revelation (2:30-3:30)**
- James breaks down: Adrian is his son, unconscious in the flooded med bay
- Med bay must be flooded completely for emergency ascent
- James begs player for guidance: "Tell me what to do."
- Flood Med Bay button appears on control panel

**Phase 4: The Choice (3:30-5:00)**
- Radiation at 75%+, time running out
- Emergency ascent ready but requires med bay flooding
- Player's empathy and moral guidance shapes James's final decision
- Multiple possible endings based on emotional bond + systems repaired

### Control Interactions

**O2 Valve (Red):**
- Effect: Temporarily shuts off oxygen flow to rebalance pressure
- Risk: Can cause oxygen drop if overused
- James can sense this (sees gauges in forward control)
- Max 5 presses, 3-second cooldown

**Vent (Orange):**
- Effect: Emergency pressure release
- Risk: Loud hissing causes temporary panic
- James hears this clearly
- Max 5 presses, 3-second cooldown

**Ballast (Blue):**
- Effect: Adjusts submarine buoyancy to reduce strain
- Safe action, unlimited uses
- James feels submarine movement/pressure change
- 2-second cooldown

**Power (Green):**
- Effect: Activates backup power systems
- Critical for progression (required milestone)
- Max 3 presses, 5-second cooldown

**Crank (Gray):**
- Effect: Manual generator crank for emergency power
- Safe, unlimited uses (physical effort)
- 1-second cooldown
- Important for Phase 1 progression

**Flood Med Bay (Bright Red):**
- Appears only in Phases 3-4 (after Adrian revelation)
- One-time irreversible action
- Triggers emergency ascent sequence
- Kills Adrian to save player + James

### State Variables Tracked

- **Radiation:** 0-100%, increases 0.4% per second (lethal at 95%)
- **Time Remaining:** 8 minutes (480 seconds), counts down
- **Hull Pressure:** Depth in feet, affected by ballast
- **Phase:** 1-4, drives narrative progression
- **Emotional Bond:** 0-100, built through empathy and dialogue
- **Systems Repaired:** 0-4, tracks player's technical progress
- **Moral Support Given:** Times player showed empathy
- **Adrian Revealed:** Boolean, latches when James reveals son

---

## Endings

### Success Endings

**"Survived With Bond"** (Best Ending)
- Conditions: Radiation < 95%, Emotional Bond ≥ 70, Systems Repaired ≥ 3
- Message: "[breathing steadily] We made it. We... we actually made it. Thank you. For being there. For your voice."

**"Survived Stranger"** (Neutral Ending)
- Conditions: Radiation < 95%, Emotional Bond < 40, Systems Repaired ≥ 2
- Message: "Systems online. Ascent initiated. ...Thank you for following instructions."

### Failure Endings

**"Radiation Lethal"**
- Condition: Radiation ≥ 95%
- Message: "[coughing violently] The radiation... I can feel it... [static] ...tell them... tell Adrian I... [signal lost]"

**"Time Expired"**
- Condition: Time Remaining ≤ 0
- Message: "[alarm wailing] We're out of time... I'm sorry... I couldn't... [voice fades into static]"

**"Systems Failure"**
- Condition: Time < 60s and Systems Repaired < 2
- Message: "The systems... they're not responding... We needed more time... [distant explosion]"

---

## RAG Facts (NPC Knowledge)

### The Submarine
- USS Prospero is a deep-sea research submarine, modified military design
- Maximum safe depth: 2,800 feet. Current depth: 2,400 feet
- Three compartments: forward control, mid-section (reactor), aft systems
- Emergency ascent requires functional ballast + stable reactor containment

### Lt. Commander James Smith
- 15-year Navy veteran, transferred to research duty
- Has son Adrian (marine biologist) aboard the submarine
- Wife Mei died of cancer two years ago - Adrian is all he has left
- Known for staying calm under pressure, but this tests his limits

### Dr. Adrian Smith
- Marine biologist studying deep-sea thermal vents, age 28
- Injured during initial reactor breach, unconscious in med bay
- Med bay is in flooded section - emergency ascent requires flooding it completely
- Has his mother's eyes (James mentions this often)

### The Crisis
- Reactor containment failed due to pressure seal rupture at depth
- Radiation spreads through ventilation at 0.4% per second
- At 95% radiation exposure, cellular damage becomes lethal within minutes
- VM-5 reactor uses pressurized water design
- Manual shutdown requires med bay controls (inaccessible)

### Technical Details
- O2 valve controls oxygen flow balance between compartments
- Ballast system adjusts buoyancy by flooding/emptying tanks
- Emergency power generated manually via hand crank
- FLOOD MED BAY control triggers ascent but kills anyone in that compartment

---

## Design Pillars

1. **Moral Weight:** The choice to flood the med bay is never easy - emotional bond makes it devastating
2. **Voice as Anchor:** James explicitly needs the player's voice as his anchor in the crisis
3. **Time Pressure:** 5-minute scene with constant radiation threat creates urgency
4. **Humanity Over Mechanics:** Success requires both technical competence AND emotional intelligence
5. **Asymmetric Information:** Player and James have different information, forcing communication and trust
