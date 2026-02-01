# Life Raft Scene Description

**Scene ID:** `life_raft`
**Character:** Captain Chen Hale
**Category:** Survival
**Display Name:** Life Raft
**Scene Type:** Submarine escape pod survival

---

## Overview

A 5-minute submarine survival experience where the player is trapped in a flooding escape pod compartment. Captain Hale is in forward control. Only one escape pod seat exists. The Captain can transfer his oxygen to keep the player alive, but ultimately must choose between:
1. **Safe Protocol:** Detach pod with player, Captain stays and dies
2. **Risky Maneuver:** 1-in-10 chance both survive (requires high empathy + commitment)

**Core Theme:** Earning survival through conversation and emotional connection, not just button presses.

---

## Visual Description (3D Environment)

### Setting: Escape Pod Compartment (Aft Section)

**Pod Interior:**
- Cramped cylindrical metal pod, curved walls with rivets
- Submarine tilted, creating disorienting angles
- Emergency lighting: amber and red floods, flickering
- Cold industrial surfaces with condensation
- Water seeping in from damaged seals (visible dripping, pooling)
- Metal bulkhead separating player from forward control
- Intercom speaker: military-grade mesh unit (Captain Hale's voice source)

**Control Panel Display:**
- **Two Oxygen Gauges Side-by-Side:**
  - Player gauge (green border): Starts at 30%, decreasing slowly
  - Captain gauge (red border): Starts at 60%, decreasing slower
  - Visual comparison crucial - shows Captain has more O2
- **Hull Integrity Gauge:** 0-100%, starts at 80%, decreases over time
  - Critical warning at <40% (structural collapse imminent)
- **Control Buttons:**
  - O2 VALVE (green) - Accept oxygen transfer from Captain
  - COMMS (blue) - Open communication channel
  - PREP POD (orange) - Prepare escape pod (Phase 4+)
  - DETACH (red) - Trigger safe escape / Captain's sacrifice (Phase 4+)
  - RISKY SAVE (magenta) - Attempt 1-in-10 maneuver (Phase 5 only)

**Porthole:**
- Small circular window showing dark water with occasional bioluminescent particles
- Depth pressure visible (water very dark, no surface light)
- Bubbles rising (suggests air leaks)

**Atmosphere:**
- Claustrophobic, tilted environment
- Water dripping sounds (constant reminder of flooding)
- Hull groans (metal stress, pressure creaking)
- Alarm warnings (low-priority, periodic)
- Captain's breathing audible through intercom (becomes more labored over time)
- Cold temperature (visible breath optional)

**Color Palette:**
- Primary: Gunmetal gray, industrial steel
- Emergency lighting: Amber, red
- Oxygen gauges: Green (player), Red (Captain)
- Hull integrity: Yellow → Orange → Red gradient
- Porthole: Deep navy blue to black

---

## World Labs Generation Prompt

**Environment:** Interior of a submarine escape pod compartment. Cramped cylindrical metal space, tilted at angle due to damaged submarine. Emergency state - water seeping in, systems failing. Player is trapped, cannot leave.

**Key Elements:**
- Riveted metal walls curving to form cylinder (diameter ~6 feet)
- Emergency lighting: amber floods, red warning strips along ceiling
- Control panel with two prominent oxygen gauges (green and red bordered)
- Intercom speaker unit (military-grade, crackling with static)
- Small circular porthole (12 inches diameter, reinforced glass, showing dark ocean)
- Water dripping from ceiling seams, pooling on tilted floor
- Condensation on all metal surfaces
- Bulkhead door (sealed, inaccessible - separation from forward control)
- Pipes and conduits along walls/ceiling
- Emergency equipment: fire extinguisher, first aid kit (strapped to walls)

**Atmosphere:** Claustrophobic survival situation. Sense of time running out. Cold, damp, metal environment. Not calm - stressed, failing systems. Submarine disaster aesthetic - think *K-19: The Widowmaker*, *The Abyss* escape pod scenes, *Das Boot* tension.

**Lighting:**
- Primary: Harsh amber emergency floods (high contrast, dramatic shadows)
- Accent: Red warning strips (constant reminder of danger)
- Gauge backlighting: Green and red glows from oxygen displays
- Porthole: Faint blue ambient from deep ocean (minimal light source)
- Flickering: Occasional power surges cause lighting instability

**Camera Position:** First-person, seated/trapped position facing control panel. Can look around pod interior but cannot move. Slight camera tilt matching submarine's angle. Optional: subtle swaying motion suggesting water movement/pressure.

**Style Reference:** Submarine disaster films. Industrial, military, no comfort. Cold metal, emergency state, flooding threat. Period: modern but not futuristic - analog gauges, physical buttons.

---

## Gameplay Mechanics

### Five-Phase Emotional Progression

**Phase 1: Initial Contact (0:00-0:30)**
- Captain Hale is formal, professional, "corporate" voice
- Asks player's status
- Establishes situation: flooding, oxygen low, hull failing
- **Milestone:** First response from player

**Phase 2: O2 Crisis (0:30-1:30)**
- Player's oxygen drops below 40%
- Captain offers O2 transfer via valve
- Player must accept help (vulnerability/trust moment)
- **Milestone:** O2 valve used at least once

**Phase 3: Bonding (1:30-3:00)**
- Captain becomes more personal under stress
- Asks about player's life, family
- Reveals he has daughter Mei (age 7, lives in San Diego)
- Wife passed during childbirth - Mei is everything to him
- Breathing labored, admits fear
- **Milestone:** Personal information shared

**Phase 4: Decision (3:00-4:00)**
- Hull integrity drops below 40% (critical)
- Captain explains situation: escape pod seats only one
- Presents two options:
  - **Safe Protocol (DETACH):** Pod detaches with player, Captain stays and dies
  - **Risky Maneuver:** Dangerous technique, ~10% success rate, requires perfect timing
- PREP POD and DETACH buttons appear
- **Milestone:** Situation explained, pod prepped

**Phase 5: Finale (4:00-5:00)**
- Player makes final choice
- If high empathy + commitment + presence: Risky maneuver becomes viable
- RISKY SAVE button appears (only if scores are high enough)
- Ending plays out based on choice + emotional scores

### Control Interactions

**O2 Valve (Green):**
- Transfers oxygen from Captain to player
- Captain's O2 decreases faster during transfer
- Costs Captain to save player
- Builds empathy ("He's sacrificing for me")
- Effect: +20 player O2, trust +10, Captain O2 decreases faster

**Comms (Blue):**
- Opens communication channel
- Shows presence and engagement
- Prevents presence score decay
- Safe action, unlimited uses
- Effect: Presence score +5

**Prep Pod (Orange) [Phase 4+ only]:**
- Prepares escape pod for deployment
- Commitment signal to Captain
- Shows player is serious about survival
- Effect: Commitment score +10, enables DETACH

**Detach (Red) [Phase 4+ only]:**
- Triggers safe escape sequence
- Player survives, Captain dies (sacrifice ending)
- Irreversible action
- Requires prep pod first
- **Ending:** "Safe Ending" (Player survives)

**Risky Save (Magenta) [Phase 5 only, conditional]:**
- Appears only if empathy ≥ 60, commitment ≥ 70, presence ≥ 50
- Attempts 1-in-10 maneuver to save both
- Success requires meeting all emotional score thresholds
- Failure kills both
- **Ending:** "Hero Ending" (both survive) or "Tragic Failure" (both die)

### Emotional Score System

Three tracked metrics determine endings:

**Empathy (0-100):**
- Builds through: Listening to Captain's story, asking about Mei, showing care
- Dialogue choices that acknowledge his fear and sacrifice
- Accepting O2 transfers (recognizing his sacrifice)

**Commitment (0-100):**
- Builds through: Following through on actions, taking responsibility
- Using systems correctly, repairing when possible
- Preparing escape pod when time comes (not hesitating)

**Presence (0-100):**
- Builds through: Quick responses, staying engaged
- Using COMMS button regularly
- Not leaving long silences (decays -0.1 per second if inactive)

---

## State Variables

- **Player Oxygen:** 30-100%, decreases -0.5/sec
- **Captain Oxygen:** 60-100%, decreases -0.3/sec (faster during transfers)
- **Hull Integrity:** 80-100%, decreases -0.4/sec
- **Empathy Score:** 50-100%, player's emotional connection
- **Commitment Score:** 50-100%, player's follow-through
- **Presence Score:** 50-100%, player's engagement (decays if silent)
- **Phase:** 1-5, narrative progression
- **O2 Transfers:** Count of times player accepted oxygen
- **Detachment Triggered:** Boolean, safe escape chosen
- **Risky Triggered:** Boolean, risky maneuver attempted
- **Daughter Mentioned:** Boolean, Mei revelation (latched)

---

## Endings

### Success Endings

**Hero Ending (Best):**
- Conditions: Risky triggered, empathy ≥60, commitment ≥70, presence ≥50
- Message: "[sound of rushing water, then silence] [breathing] We... we made it. Both of us. [long pause] Thank you for not giving up on me."
- **Outcome:** Both survive against the odds

**Safe Ending (Bittersweet):**
- Conditions: Detachment triggered, Phase ≥4
- Message: "[mechanical sounds] Detachment sequence initiated. [pause] Tell Mei... tell her I was thinking of her. [static] Good luck up there."
- **Outcome:** Player survives, Captain sacrifices himself

### Failure Endings

**Player Suffocated:**
- Condition: Player oxygen ≤ 0
- Message: "[fading audio] Stay with me... stay... [static] [silence]"
- **Outcome:** Player dies before escape

**Hull Collapse:**
- Condition: Hull integrity ≤ 0, no escape triggered
- Message: "[massive groaning] The hull— [water rushing] [static] [silence]"
- **Outcome:** Both die in structural collapse

**Risky Failure (Tragic):**
- Condition: Risky triggered but emotional scores too low
- Message: "[alarms] It's not holding— [pause] I'm sorry. I thought we could— [falling sensation] [darkness]"
- **Outcome:** Both die attempting risky maneuver

---

## RAG Facts (NPC Knowledge)

### Captain Chen Hale
- Commanded submarines for 18 years, Pacific Fleet veteran
- Daughter Mei (age 7) lives with grandmother in San Diego
- Wife passed away during childbirth - Mei is everything to him
- Keeps photo of Mei in breast pocket, touches it when stressed
- Has never lost a crew member under his command (weighs heavily)

### The Submarine
- Deep-diving research vessel conducting seabed surveys
- Hull integrity drops under excessive pressure at depth
- Escape pod designed for one person (last resort)

### The Situation
- Rear compartment (player location) has limited oxygen reserves
- Captain has more oxygen (forward control has larger reserves)
- O2 valve allows Captain to transfer oxygen at his own cost
- Hull integrity below 40% means structural collapse imminent

### The Choice
- Safe Protocol (DETACH): Pod detaches with player, Captain stays and dies
- Risky Maneuver (RISKY SAVE): ~10% success rate, requires perfect timing + trust
- If player shows empathy + commitment, Captain attempts risky maneuver with confidence

### Emotional Context
- Captain initially presents as professional/corporate, hiding fear
- As situation worsens, becomes more personal and vulnerable
- Needs to know Mei will be told he loved her if he doesn't survive

---

## Design Pillars

1. **Earned Survival:** Success requires emotional intelligence, not just button-mashing
2. **Sacrifice as Theme:** Captain's willingness to sacrifice makes choice devastating
3. **Presence Matters:** Being there, responding quickly, staying engaged - all tracked
4. **Mei as Anchor:** Daughter revelation shifts Captain from professional to father
5. **1-in-10 Hope:** Risky maneuver is genuinely difficult - player must earn the chance
6. **No Easy Answers:** Safe ending is success but bittersweet (Captain dies)
