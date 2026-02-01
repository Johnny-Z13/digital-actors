# Iconic Detectives Scene Description

**Scene ID:** `iconic_detectives`
**Character:** Mara Vane (Detective)
**Category:** Mystery
**Display Name:** Iconic Detectives
**Scene Type:** Phone call investigation

---

## Overview

A rain-soaked night in Manhattan, 1987. The player is a detective sitting alone in a dimly lit office with a string board tracking the murder of Dr. Elias Crowe. A payphone caller named Mara Vane has information about the case - but she may be a witness, an informant, or the killer herself.

**Core Mechanic:** Branching phone conversation where the detective examines evidence pins on their string board and watches for Mara's contradictions and slips. Trust management determines which ending the player reaches.

---

## Visual Description (3D Environment)

### Setting: Detective Office, Hell's Kitchen, 12th Floor

**The Office:**
- Worn wooden desk in foreground, scratched and stained
- Black rotary telephone (centerpiece - player's connection to Mara)
- Rain-streaked window behind desk showing neon lights bleeding through darkness
- Venetian blinds casting striped shadows across the room
- Dim lighting: single desk lamp with green glass shade (film noir aesthetic)
- Cigarette smoke atmosphere (optional haze)
- Files and papers scattered on desk
- Half-empty coffee cup
- Ashray (period appropriate)

**The String Board (Wall-Mounted Evidence Board):**
Critical gameplay element - player references these pins during conversation:

1. **MAP:** Marlow Street / Riverwalk / Old Glassworks with locations circled in red
2. **PHOTO:** Crowe's front door with scratch marks around the lock (close-up)
3. **PHOTO:** Crowe's study - wall safe is MISSING (not opened, completely removed)
4. **RECEIPT:** Kestrel Pawn - Brass Key Blank purchase (2 days before murder)
5. **CCTV:** Hooded figure with umbrella, reflective strip visible on sleeve
6. **NOTE:** Fragment reading "...don't open it. Not after what happened at the Glassworks..."
7. **CALL LOG:** Unknown number called Crowe three times on day of death

**Red string connects evidence pieces in web pattern**

**Atmosphere:**
- Rain sound: constant, heavy rain against window
- Distant traffic sounds from street below
- Neon light flicker through window (red/blue/yellow)
- Telephone ring at scene start (sharp, old-school bell)
- Static on phone line throughout conversation
- 1980s NYC noir aesthetic - think *Blade Runner* meets *Chinatown*

**Color Palette:**
- Dark blues and grays (night, rain)
- Warm amber (desk lamp)
- Red (neon bleed, string on board)
- Muted yellows (old papers, evidence photos)
- Cold steel (telephone, filing cabinets)

---

## World Labs Generation Prompt

**Environment:** Private detective's office in Hell's Kitchen, Manhattan, 1987. Night. 12th floor. Rain-soaked windows with neon light bleeding through venetian blinds. Film noir atmosphere.

**Key Elements:**
- Worn wooden desk (1960s vintage) with green-shaded lamp as primary light source
- Black rotary telephone (critical prop - player's connection to caller)
- String board mounted on wall: cork board, red string connecting 7 evidence pieces (photos, maps, receipts, notes)
- Venetian blinds creating stripe shadow patterns across walls and desk
- Rain-streaked window showing blurred NYC skyline and neon signs
- Filing cabinets (metal, olive green)
- Leather desk chair (cracked, aged)
- Wood-paneled walls or exposed brick
- Ceiling: water-stained tiles, single hanging bulb (off)

**Atmosphere:** Classic 1980s detective noir. Dark, moody, rain-heavy. Not modern clean aesthetic - gritty, lived-in, authentic period detail. Smoke haze optional. Sense of late-night isolation - detective working alone.

**Lighting:**
- Primary: Desk lamp with green glass shade (warm amber glow, focused on desk surface)
- Secondary: Neon light through window (red/blue, flickering, intermittent)
- Ambient: Very low - most of room in shadow
- String board: Illuminated by desk lamp spill or separate pin light

**Camera Position:** First-person from detective's chair. Player looks at desk (phone), can turn to examine string board on wall behind/beside them. Limited movement - seated perspective.

**Style Reference:** *Blade Runner* (1982), *Chinatown* (1974), *LA Confidential* (1997), *The Maltese Falcon* (1941). Classic noir cinematography with rain, neon, and shadow.

---

## Gameplay Mechanics

### Phase Structure

**Phase 1: Opening (0:00-1:00)**
- Phone rings, player answers
- Mara introduces herself cautiously: "I'm calling about a case. Someone's dead, and the story you've been told is wrong."
- Establishes Dr. Elias Crowe murder case
- Hints at robbery narrative being false

**Phase 2: The Hooks (1:00-3:00)**
- Three core "hooks" available as button choices:
  - **WHO ARE YOU?** - Press Mara's identity
  - **WHAT'S WRONG WITH THE TIMING?** - Press timeline inconsistency
  - **WHY STEAL A KEY?** - Press significance of stolen object
- Player explores hooks to gather information
- Mara reveals details, may slip/contradict herself
- Trust fluctuates based on player's tone

**Phase 3: Branch Point (3:00-4:00)**
- Mara presents two investigation paths:
  - **FOLLOW THE KEY** (Path 1) - Object-driven conspiracy thread
  - **FOLLOW THE LIE** (Path 2) - Investigate staged robbery narrative
- Player chooses one path, locks out the other

**Phase 4: Path 1 Exploration (if chosen)**
- Sub-options:
  - How do you know Sable Storage?
  - What's in the box?
  - Who else knows? (reveals Hollis Rook)
- Leads to Ending 1: Sable Storage lead

**Phase 5: Path 2 Exploration (if chosen)**
- Sub-options:
  - Who staged it?
  - Why an argument? (TRAP - can reveal slip)
  - Give me a killer detail (weapon location clue)
- Leads to Ending 2: Mara becomes prime suspect

### Evidence Pin Interactions

Player can reference pins on the string board during conversation. Mara reacts dynamically:

**Pin Map (Glassworks):**
- Mara shows tension when Glassworks is mentioned
- Reveals: "That place isn't abandoned the way people think."

**Pin Door (Scratch Marks):**
- Mara demonstrates knowledge: "Those scratches... they're not from a break-in."
- Suggests key copying or testing

**Pin Study (Missing Safe):**
- Mara surprised player noticed: "You're observant. Most people miss that."
- Safe wasn't cracked - it was removed completely

**Pin Receipt (Key Blank):**
- Sharp intake of breath: "Then you already know more than you should."
- Reveals key was copied from photograph

**Pin CCTV (Reflective Sleeve):**
- Recognition: "Like a cycling jacket. Or a riverwalk courier."
- Hints at Mara's own involvement (she was a courier)

**Pin Note (Glassworks Fragment):**
- Immediate tension: "Don't say that out loud."
- Expands motive beyond robbery: conspiracy, cover-up

**Pin Call Log (Unknown Caller):**
- Careful deflection: "A lot of people called Crowe."
- If pressed: "One of those calls... might have been me."

### Contradiction Detection

**Slip Detection (Post-Speak Hook):**
- System catches "when I..." reveals automatically
- Example: "The kettle was still warm when I... when someone left." → CAUGHT

**Manual Challenge:**
- If contradictions ≥ 2, player can press "YOU WERE THERE" button
- Mara breaks: admits arriving after death
- Can lead to weapon location reveal (umbrella stand)

---

## State Variables

- **Trust:** 0-100 (Mara's willingness to share, starts at 50)
- **Contradictions:** 0-5 (slips player catches)
- **Hooks Explored:** 0-3 (A/B/C core hooks)
- **Path Chosen:** 0=none, 1=key, 2=lie
- **Path Options Explored:** 0-3 (sub-questions within chosen path)
- **Phase:** 1-5 (narrative progression)
- **Time Remaining:** 600 seconds (10 minutes)
- **Pins Referenced:** Bitfield tracking which evidence pieces mentioned
- **Presence Revealed:** Boolean (if Mara slipped about being at scene)
- **Weapon Clue:** Boolean (if weapon location revealed)

---

## Endings

### Success Endings

**Ending 1: Key Success (Sable Storage Lead)**
- Conditions: Path 1 chosen, explored ≥ 2 options
- Mara: "Go to Sable Storage. Ask for Box 47. If they deny it, mention Crowe's phrase: 'they made a copy.' That'll make the clerk blink."
- **Outcome:** Solid investigative lead, Mara remains cooperative informant

**Ending 2: Twist (Mara is Suspect)**
- Conditions: Path 2 chosen, contradictions ≥ 2
- Mara (after long silence): "...In the umbrella stand. By the front door. That's where he kept it. [click - line goes dead]"
- **Outcome:** Weapon location revealed, Mara hangs up, player loses informant but gains critical evidence

**Ending 3: Hollis Rook Named**
- Conditions: Path options explored ≥ 3, trust ≥ 60
- Mara: "A man named Hollis Rook. If you have his name on your board already, you're ahead. If you don't - pin it now."
- **Outcome:** New person-of-interest identified

### Failure Endings

**Ending 4: Blackmail (Trust Collapse)**
- Condition: Trust < 25
- Mara turns tables: "Look at your board. The pawn receipt. The CCTV. The Glassworks note. Those aren't three separate threads. They're one rope - and it's around YOUR neck now. Someone wanted me to call you. Congratulations: you've been introduced. [click]"
- **Outcome:** Player becomes target, loses case

**Ending 5: Time Expired**
- Condition: Time remaining ≤ 0
- Mara: "I... I have to go. They're watching. Maybe you'll figure it out. Maybe not. [click - static - silence]"
- **Outcome:** Partial information, inconclusive

---

## Audio Design

**Voice Effect:** Extreme phone receiver effect (80s landline handset)
- Highpass: 400Hz (aggressive bass cut)
- Lowpass: 2800Hz (narrow bandwidth)
- Mid boost: 1000Hz, +5dB (telephone presence)
- Compression: -20dB threshold, 6:1 ratio (tight)
- Distortion: 35% (noticeable line grit)
- Noise: -35dB (audible static)
- Mono output

**Background Audio:**
- Rain ambience: constant, heavy
- Distant traffic from street below
- Phone static/crackle throughout
- Paper rustle when referencing evidence
- Pin click when examining string board
- String stretch sound (optional)

---

## Design Pillars

1. **Asymmetric Information:** Mara knows more than she reveals - player must extract truth
2. **Trust as Currency:** Aggressive questioning lowers trust, empathy builds it
3. **Contradiction Cascade:** Small slips accumulate to major revelations
4. **Branching Consequences:** Path choice locks player into one narrative thread
5. **Evidence Integration:** String board is not decoration - it's core gameplay
6. **Period Authenticity:** 1987 NYC noir aesthetic must be consistent (rotary phone, no cell phones, analog evidence)
