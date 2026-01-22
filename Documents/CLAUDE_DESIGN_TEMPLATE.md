# Project Design Document Template
<!--
Instructions for your team:
- Fill in sections relevant to your project (delete sections that don't apply)
- Be specific - Claude works best with concrete details, not vague descriptions
- Include constraints and non-goals to prevent scope creep
- Add reference links, images, or examples where helpful
- Questions in [brackets] are prompts to help you think - replace with your answers
-->

---

## Project Overview

### Name
**Working Title:** [Your project name]
**Code Name:** [Optional internal name]

### Elevator Pitch
<!-- One or two sentences that capture the essence of the project -->
[Example: "A twin-stick shooter where you defend neural networks from corrupted data, with roguelike progression and synthwave aesthetics."]

### Genre / Category
- **Primary:** [e.g., Action, Puzzle, Productivity, Social]
- **Secondary:** [e.g., Roguelike, Simulation, Utility]
- **Platform(s):** [PC / Mobile / Web / Console]

### Target Audience
- **Primary:** [Who is this for? Age range, interests, skill level]
- **Secondary:** [Other potential users]
- **Comparable Products:** [What do they currently use/play?]

### References & Inspiration
<!-- Links, screenshots, or descriptions of similar products -->
| Reference | What to Take From It |
|-----------|---------------------|
| [Game/App Name] | [Specific mechanic, aesthetic, or feature] |
| [Game/App Name] | [Specific mechanic, aesthetic, or feature] |

---

## Core Concept

### Theme / Setting
<!-- What's the world, mood, or context? -->
[Example: "Digital cyberspace interior - think Tron meets vaporwave. Clean geometric shapes corrupted by glitch aesthetics when enemies appear."]

### Core Fantasy / Value Proposition
<!-- What feeling or benefit does the user get? -->
[Example: "Feel like a digital guardian protecting vital systems with precise, satisfying combat."]

### Unique Selling Points
1. [What makes this different from competitors?]
2. [What's the hook?]
3. [Why would someone choose this over alternatives?]

---

## Gameplay / Functionality

### Core Loop
<!-- The fundamental repeated action - be specific -->
```
[Action] -> [Feedback] -> [Reward] -> [Progression] -> (repeat)
```

**Example (Game):**
```
Shoot enemies -> Collect drops -> Upgrade weapons -> Face harder waves -> (repeat)
```

**Example (App):**
```
Capture idea -> Organize/tag -> Review later -> Build on it -> (repeat)
```

### Session Structure
- **Typical Session Length:** [5 min / 30 min / hours]
- **Save/Resume:** [How does the user pick up where they left off?]
- **Natural Stopping Points:** [When does it feel okay to quit?]

### Primary Mechanics
<!-- List and briefly describe each core mechanic -->

#### Mechanic 1: [Name]
- **Description:** [What does the user do?]
- **Controls/Input:** [How do they do it?]
- **Feedback:** [What happens in response?]
- **Depth:** [How does mastery develop?]

#### Mechanic 2: [Name]
- **Description:**
- **Controls/Input:**
- **Feedback:**
- **Depth:**

<!-- Add more mechanics as needed -->

### Secondary Mechanics
<!-- Supporting systems that enhance the core -->
- [Mechanic]: [Brief description]
- [Mechanic]: [Brief description]

---

## Systems Design

### Progression System
<!-- How does the user/player advance? -->

| Type | Description | Persistence |
|------|-------------|-------------|
| [e.g., XP/Levels] | [How it works] | [Per-run / Permanent] |
| [e.g., Unlocks] | [How it works] | [Per-run / Permanent] |
| [e.g., Currency] | [How it works] | [Per-run / Permanent] |

### Economy / Resources
<!-- What does the user collect, spend, or manage? -->
- **Resource 1:** [Name] - [How earned] - [How spent]
- **Resource 2:** [Name] - [How earned] - [How spent]

### Difficulty / Challenge Curve
<!-- How does difficulty scale? -->
- **Starting State:** [How accessible is the beginning?]
- **Scaling Method:** [Time-based / Performance-based / User-selected]
- **Failure State:** [What happens when the user fails? How punishing?]
- **Difficulty Modes:** [Easy/Normal/Hard? Accessibility options?]

---

## Combat / Conflict System
<!-- Delete this section if not applicable -->

### Health & Damage

| Entity | Health | Damage Output | Special Properties |
|--------|--------|---------------|-------------------|
| Player | [Value or range] | [Value or range] | [Shields, lives, etc.] |
| Enemy Type 1 | [Value] | [Value] | [Behaviors] |
| Enemy Type 2 | [Value] | [Value] | [Behaviors] |

### Combat Feel
- **Time-to-Kill:** [Instant / Quick / Sustained]
- **Player Power Fantasy:** [Glass cannon / Tank / Balanced]
- **Enemy Density:** [Few tough enemies / Swarms of weak ones / Mixed]

### Weapons / Tools / Abilities
| Name | Behavior | Acquisition | Upgrades |
|------|----------|-------------|----------|
| [Weapon 1] | [What it does] | [How to get it] | [How it improves] |
| [Weapon 2] | [What it does] | [How to get it] | [How it improves] |

### Status Effects / Modifiers
- **[Effect Name]:** [Description and duration]
- **[Effect Name]:** [Description and duration]

---

## Entities / Content

### Player Character / User Profile
- **Capabilities:** [What can they do?]
- **Limitations:** [What can't they do?]
- **Customization:** [What can be personalized?]

### Enemies / Obstacles / Challenges
<!-- What stands in the user's way? -->

| Name | Role | Behavior | Threat Level |
|------|------|----------|--------------|
| [Entity 1] | [Fodder/Elite/Boss] | [AI pattern or obstacle type] | [Low/Med/High] |
| [Entity 2] | [Fodder/Elite/Boss] | [AI pattern or obstacle type] | [Low/Med/High] |

### Items / Pickups / Collectibles
| Name | Effect | Duration | Rarity |
|------|--------|----------|--------|
| [Item 1] | [What it does] | [Instant/Timed/Permanent] | [Common/Rare] |
| [Item 2] | [What it does] | [Instant/Timed/Permanent] | [Common/Rare] |

### Levels / Environments / Screens
- **[Area/Screen 1]:** [Description and purpose]
- **[Area/Screen 2]:** [Description and purpose]

---

## User Interface

### HUD / Always-Visible Elements
<!-- What does the user always need to see? -->
- [Element]: [Purpose and position]
- [Element]: [Purpose and position]

### Menus / Screens
- **Main Menu:** [Options available]
- **Pause/Settings:** [What can be configured?]
- **[Other Screens]:** [Purpose]

### Feedback Systems
- **Visual Feedback:** [Screen shake, flash, particles, etc.]
- **Audio Feedback:** [Sound effects, music changes]
- **Haptic Feedback:** [Vibration patterns - if applicable]

---

## Audio & Visual Style

### Art Direction
- **Style:** [Realistic / Stylized / Pixel / Vector / etc.]
- **Color Palette:** [Describe or link to reference]
- **Mood:** [Bright / Dark / Neon / Muted / etc.]

### Audio Direction
- **Music Genre:** [Electronic / Orchestral / Ambient / etc.]
- **Sound Design:** [Punchy / Subtle / Retro / Realistic]
- **Voice:** [None / Narrator / Full VO]

---

## Technical Requirements

### Target Specs
- **Minimum:** [Hardware/OS requirements]
- **Recommended:** [Optimal experience]
- **Frame Rate Target:** [30 / 60 / 120+ FPS]

### Engine / Framework
- **Primary:** [Unity / Unreal / Godot / React / etc.]
- **Key Plugins/Packages:** [List dependencies]

### Data & Persistence
- **Save System:** [Local / Cloud / None]
- **Data to Persist:** [Settings, progress, unlocks, etc.]
- **Online Requirements:** [Offline-capable / Always-online / Optional]

---

## Scope & Constraints

### MVP Features (Must Have)
<!-- The absolute minimum for a viable product -->
1. [ ] [Feature]
2. [ ] [Feature]
3. [ ] [Feature]

### Phase 2 Features (Should Have)
<!-- Important but can ship without -->
1. [ ] [Feature]
2. [ ] [Feature]

### Nice-to-Have Features (Could Have)
<!-- Only if time/budget allows -->
1. [ ] [Feature]
2. [ ] [Feature]

### Non-Goals (Won't Have)
<!-- Explicitly out of scope - prevents scope creep -->
- [Feature/aspect you're NOT building]
- [Feature/aspect you're NOT building]

### Known Risks & Open Questions
<!-- Things that need answers or could cause problems -->
- [ ] [Question or risk]
- [ ] [Question or risk]

---

## Development Notes

### Existing Assets / Starting Point
<!-- What do you already have? -->
- [Asset type]: [Description or link]

### Key Technical Challenges
<!-- What's going to be hard? -->
- [Challenge]: [Why it's tricky]

### Testing Strategy
- **Playtesting:** [How and when?]
- **QA Focus Areas:** [What needs the most testing?]

---

## Appendix

### Glossary
<!-- Define project-specific terms -->
| Term | Definition |
|------|------------|
| [Term] | [Meaning in this project's context] |

### Revision History
| Date | Author | Changes |
|------|--------|---------|
| [Date] | [Name] | Initial draft |

---

<!--
TIPS FOR WORKING WITH CLAUDE:

1. Be specific over vague
   Bad: "Combat should feel good"
   Good: "Combat should feel punchy - 0.1s hitstop, screen shake on impact, enemies flash white and knockback 2 units"

2. Include constraints
   Claude can spiral into over-engineering. Tell it what NOT to do.

3. Reference existing code
   "Follow the pattern in PlayerController.cs" is more useful than describing the pattern.

4. Quantify when possible
   Numbers, ranges, and ratios are clearer than adjectives.

5. State your priorities
   "Polish is more important than features" or "Ship fast, iterate later"

6. Include examples
   Screenshots, code snippets, or links to similar features help enormously.
-->
