# Welcome Scene Description

**Scene ID:** `welcome`
**Character:** Clippy (Paper Clip Assistant)
**Category:** Tutorial
**Display Name:** Welcome
**Scene Type:** Platform introduction

---

## Overview

The first scene users see when starting Digital Actors. Features Clippy the paper clip assistant (inspired by Microsoft's classic helper) who helps users understand the platform, explore available scenarios, and learn how to create their own experiences.

**Purpose:** Onboarding, orientation, feature explanation

---

## Visual Description (3D Environment)

### Setting: Digital Actors Welcome Screen

**The Interface:**
- Clean, modern, friendly interface
- Clippy appears as animated character (paper clip with googly eyes)
- Menu system visible: scenario selection, character browser, settings
- Minimalist design - not overwhelming
- Optional: Abstract background (soft gradients, particles)

**Clippy:**
- Friendly animated paper clip character
- Expressive animations: bouncing, nodding, thinking poses
- Appears to one side of screen (not center - allows UI visibility)
- Can gesture toward UI elements when explaining features

**Atmosphere:**
- Welcoming, approachable, low-pressure
- No time limits, no urgency
- Exploratory space - encourages questions
- Light, bright color palette

---

## World Labs Generation Prompt

**Environment:** Abstract digital welcome space. Clean, modern interface aesthetic. Friendly, approachable atmosphere. Not realistic 3D - stylized, UI-focused.

**Key Elements:**
- Clippy character: Animated paper clip (Microsoft Office throwback), googly eyes, friendly expressions
- Menu panels: Floating translucent cards showing scenario options
- Text elements: "Welcome to Digital Actors" header
- Background: Soft gradient (white to light blue) or abstract particle effects
- UI elements: Buttons, icons, navigation clearly visible

**Atmosphere:** Onboarding screen. Friendly, patient, exploratory. Not intimidating. Think modern app tutorial screens, clean UI design, friendly helper character aesthetic.

**Lighting:** Bright, even, no harsh shadows. Clean UI lighting. Clippy has subtle rim light or glow to stand out.

**Camera Position:** Static 2D or slight parallax. User navigates via UI, not 3D movement.

**Style Reference:** Microsoft Clippy aesthetic (nostalgic throwback), modern flat UI design, friendly tutorial interfaces. Clean, simple, approachable.

---

## Interaction Design

### Clippy's Role

Clippy acts as conversational guide. Player can ask:
- "What is Digital Actors?"
- "What scenarios are available?"
- "How do I create my own character?"
- "How do I make a new scenario?"
- "What can I do here?"

Clippy responds with friendly, concise explanations and directs player to relevant features.

### No Controls

Unlike other scenes, Welcome has no 3D interactive controls. Navigation is via:
- Menu system (click scenarios to explore)
- Conversation with Clippy (ask questions)
- Settings/configuration options

### Opening Behavior

- Clippy stays silent until player speaks first
- Encourages exploration: "Just say hello and ask Clippy anything!"
- No forced tutorial - player-driven exploration

---

## Content: What Clippy Explains

### Available Scenarios
- **Pressure Point:** Submarine survival (Lt. Commander Kovich)
- **Iconic Detectives:** Murder mystery phone call (Mara Vane)
- **Life Raft:** Escape pod survival (Captain Hale)
- **Crown Court:** Legal defense trial (Judge Whitmore)
- **Merlin's Workshop:** Fantasy wizard conversation (Merlin)
- **Introduction/Conversation:** Simple open-ended chat (Eliza)

### Platform Features
- AI NPCs (Digital Actors) with persistent memory across sessions
- Voice-driven interaction with text-to-speech
- Interactive 3D environments
- Branching narratives with multiple endings
- Emotional tracking and relationship building

### Creation Tools
- How to add custom characters
- How to define new scenarios
- Configuration options
- Scene system architecture (for developers)

---

## State Variables

Minimal state tracking:
- **Topics Explored:** 0-10, tracks how many help topics Clippy has covered

No time limit, no fail states. Purely exploratory.

---

## Design Pillars

1. **Zero Pressure:** No time limits, no wrong choices, purely exploratory
2. **Player-Driven:** Clippy responds to questions, doesn't force tutorial
3. **Nostalgic Charm:** Clippy throwback creates friendly, approachable vibe
4. **Gateway Experience:** Orients users before diving into intense scenarios
5. **Respects Intelligence:** Doesn't over-explain, answers questions concisely
