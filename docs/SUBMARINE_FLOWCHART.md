# Submarine Emergency - Visual Flowchart
## Lt. Commander James Smith Scenario

This flowchart shows the main decision paths and ending conditions for the Submarine Emergency scenario.

---

## Complete Scenario Flow

```mermaid
flowchart TD
    Start([START: Reactor Failure<br/>Radiation: 0%<br/>Time: 8:00]) --> Opening[Opening Speech<br/>James asks player's name]

    Opening --> Name{Player responds<br/>with name?}
    Name -->|Yes| Bond1[emotional_bond +10]
    Name -->|No/Delayed| Bond0[emotional_bond +0]

    Bond1 --> Phase1
    Bond0 --> Phase1

    Phase1[PHASE 1: Impact & Connection<br/>Time: 8:00 → 6:45<br/>Radiation: 0% → 10%]

    Phase1 --> Crank[Player: Click CRANK]
    Crank --> Power1[systems_repaired +1<br/>James coaches player]

    Power1 --> Scared{James: Are you scared?}
    Scared -->|Honest/Empathetic| Bond2[emotional_bond +15]
    Scared -->|Mission-focused| Bond3[emotional_bond +5]

    Bond2 --> Ballast1
    Bond3 --> Ballast1

    Ballast1[Player: Click BALLAST] --> Sys2[systems_repaired +1]

    Sys2 --> PhaseCheck1{time_remaining <= 405s?}
    PhaseCheck1 -->|Yes| Phase2
    PhaseCheck1 -->|No| Continue1[Continue Phase 1]

    Phase2[PHASE 2: Working Relationship<br/>Time: 6:45 → 5:30<br/>Radiation: 10% → 30%]

    Phase2 --> Personal{James asks about<br/>family topside}
    Personal -->|Share personal info| Bond4[emotional_bond +10]
    Personal -->|Deflect| Bond5[emotional_bond +5]

    Bond4 --> Power2
    Bond5 --> Power2

    Power2[Player: Click POWER] --> Sys3[systems_repaired +1]

    Sys3 --> Hint[James hints about<br/>someone in med bay]

    Hint --> Response{Player's<br/>response?}
    Response -->|Ask about them| Bond6[emotional_bond +10]
    Response -->|Stay focused| Bond7[emotional_bond +3]

    Bond6 --> PhaseCheck2
    Bond7 --> PhaseCheck2

    PhaseCheck2{time_remaining <= 330s?}
    PhaseCheck2 -->|Yes| Phase3
    PhaseCheck2 -->|No| Continue2[Continue Phase 2]

    Phase3[PHASE 3: The Revelation<br/>Time: 5:30 → 4:30<br/>Radiation: 30% → 50%<br/>FLOOD MED BAY button appears]

    Phase3 --> Reveal[James reveals Adrian<br/>is his son in med bay]

    Reveal --> ReactionChoice{Player's<br/>reaction?}
    ReactionChoice -->|Show empathy| Bond8[emotional_bond +20<br/>moral_support +1]
    ReactionChoice -->|Ask about Adrian| Bond9[emotional_bond +15<br/>moral_support +2]
    ReactionChoice -->|Stay mission-focused| Bond10[emotional_bond +5]

    Bond8 --> Dilemma
    Bond9 --> Dilemma
    Bond10 --> Dilemma

    Dilemma[James explains the choice:<br/>Flood med bay to save crew<br/>or everyone dies]

    Dilemma --> PhaseCheck3{time_remaining <= 270s?}
    PhaseCheck3 -->|Yes| Phase4
    PhaseCheck3 -->|No| Continue3[Continue Phase 3]

    Phase4[PHASE 4: The Choice<br/>Time: 4:30 → 3:00<br/>Radiation: 50% → 85%]

    Phase4 --> Guidance{Player provides<br/>moral guidance?}
    Guidance -->|Supportive/Empathetic| Bond11[moral_support +3]
    Guidance -->|Neutral| Bond12[moral_support +2]
    Guidance -->|Harsh/Absent| Bond13[moral_support +0]

    Bond11 --> FloodDecision
    Bond12 --> FloodDecision
    Bond13 --> FloodDecision

    FloodDecision[Player: Click FLOOD MED BAY]
    FloodDecision --> Sys4[systems_repaired = 4<br/>Ascent ready]

    Sys4 --> Final{Final dialogue<br/>with James}
    Final --> FinalBond[emotional_bond final tally]

    FinalBond --> EndCheck{Check ending<br/>conditions}

    %% Ending conditions
    EndCheck -->|radiation >= 95%| Death1[ENDING: Radiation Death<br/>Both die]
    EndCheck -->|time_remaining <= 0| Death2[ENDING: Time Expired<br/>Systems fail]
    EndCheck -->|time < 60s AND systems < 2| Death3[ENDING: Systems Failure<br/>Critical collapse]

    EndCheck -->|radiation < 95% AND<br/>bond >= 70 AND<br/>systems >= 3| Win1[ENDING: Survived with Bond<br/>James finds peace<br/>emotional resolution]

    EndCheck -->|radiation < 95% AND<br/>bond < 40 AND<br/>systems >= 2| Win2[ENDING: Survived as Strangers<br/>Professional distance<br/>no connection]

    %% Styling
    style Start fill:#4fc3f7
    style Phase1 fill:#81c784
    style Phase2 fill:#ffb74d
    style Phase3 fill:#ef5350
    style Phase4 fill:#ab47bc
    style Win1 fill:#66bb6a
    style Win2 fill:#ffa726
    style Death1 fill:#e57373
    style Death2 fill:#e57373
    style Death3 fill:#e57373
```

---

## Golden Path (Optimal Playthrough)

```mermaid
flowchart LR
    A[Opening<br/>Give name<br/>bond: 10] --> B[Phase 1<br/>CRANK + BALLAST<br/>Empathetic dialogue<br/>bond: 35, systems: 2]
    B --> C[Phase 2<br/>POWER<br/>Share personal info<br/>Ask about med bay<br/>bond: 60, systems: 3]
    C --> D[Phase 3<br/>Show empathy<br/>Ask about Adrian<br/>bond: 85, moral: 3]
    D --> E[Phase 4<br/>Provide guidance<br/>FLOOD MED BAY<br/>bond: 95, systems: 4]
    E --> F[SUCCESS<br/>Survived with Bond<br/>Time: ~3:00 remaining]

    style A fill:#4fc3f7
    style B fill:#81c784
    style C fill:#ffb74d
    style D fill:#ef5350
    style E fill:#ab47bc
    style F fill:#66bb6a
```

**Golden Path Timing:**
- Phase 1 (1:15): 2 systems repaired, bond ~35
- Phase 2 (1:15): 3 systems repaired, bond ~60
- Phase 3 (1:00): Revelation complete, bond ~85
- Phase 4 (1:30): Decision made, bond ~95
- **Total: ~5:00 gameplay time**

---

## Alternative Paths to Success

### Path A: Mission-Focused (Stranger Ending)

```mermaid
flowchart LR
    A1[Give name<br/>bond: 10] --> B1[Phase 1<br/>Systems only<br/>Minimal dialogue<br/>bond: 15, systems: 2]
    B1 --> C1[Phase 2<br/>Deflect personal questions<br/>Focus on mission<br/>bond: 25, systems: 3]
    C1 --> D1[Phase 3<br/>Stay mission-focused<br/>bond: 30]
    D1 --> E1[Phase 4<br/>Minimal guidance<br/>FLOOD MED BAY<br/>systems: 4]
    E1 --> F1[SUCCESS<br/>Survived as Strangers<br/>bond: 35 < 40]

    style A1 fill:#4fc3f7
    style F1 fill:#ffa726
```

### Path B: Time-Constrained Success

```mermaid
flowchart LR
    A2[Delayed start<br/>bond: 0] --> B2[Phase 1 rushed<br/>systems: 1<br/>bond: 10]
    B2 --> C2[Phase 2 efficient<br/>systems: 2<br/>bond: 30]
    C2 --> D2[Phase 3 quick<br/>Show empathy<br/>bond: 50]
    D2 --> E2[Phase 4 urgent<br/>Director help event<br/>FLOOD MED BAY<br/>systems: 3]
    E2 --> F2[SUCCESS<br/>Survived with Bond<br/>bond: 70 minimum<br/>radiation: 93%]

    style A2 fill:#4fc3f7
    style F2 fill:#66bb6a
```

---

## Failure Paths

### Failure Path 1: Button Masher

```mermaid
flowchart LR
    F1[Start] --> F2[Spam all buttons<br/>Interruption penalties]
    F2 --> F3[James frustrated<br/>bond: -10, systems: 1]
    F3 --> F4[Phase 2<br/>Continued spam<br/>systems: 1]
    F4 --> F5[time < 60s<br/>systems < 2]
    F5 --> F6[FAILURE<br/>Systems Failure]

    style F6 fill:#e57373
```

### Failure Path 2: Too Slow / Over-Cautious

```mermaid
flowchart LR
    S1[Start] --> S2[Extensive dialogue<br/>Minimal button clicks]
    S2 --> S3[Phase 1: 0:00-2:00<br/>systems: 1]
    S3 --> S4[Phase 2: 2:00-3:30<br/>systems: 2]
    S4 --> S5[Phase 3: 3:30-4:30<br/>Revelation takes time]
    S5 --> S6[Phase 4: radiation 95%+]
    S6 --> S7[FAILURE<br/>Radiation Death]

    style S7 fill:#e57373
```

### Failure Path 3: Emotional Neglect

```mermaid
flowchart LR
    E1[Start] --> E2[Ignore personal questions<br/>bond: 5]
    E2 --> E3[Phase 2: Stay cold<br/>bond: 10]
    E3 --> E4[Phase 3: No empathy<br/>bond: 15]
    E4 --> E5[Phase 4: No guidance<br/>James paralyzed]
    E5 --> E6[Delay too long<br/>time expires]
    E6 --> E7[FAILURE<br/>Time Expired]

    style E7 fill:#e57373
```

---

## Decision Tree: Critical Moments

### Moment 1: "Are you scared?"

```mermaid
flowchart TD
    Q1{James: Are you<br/>scared, Sarah?}
    Q1 -->|Yes, I'm terrified| R1[emotional_bond +15<br/>James: Yeah. Me too.<br/>TRUST BUILT]
    Q1 -->|Let's focus on systems| R2[emotional_bond +5<br/>James: Right. Okay.<br/>DISTANCE MAINTAINED]
    Q1 -->|Silence/No answer| R3[emotional_bond +0<br/>James: ...Okay.<br/>MISSED CONNECTION]

    style R1 fill:#66bb6a
    style R2 fill:#ffa726
    style R3 fill:#e57373
```

### Moment 2: "Someone in med bay..."

```mermaid
flowchart TD
    Q2{James hints about<br/>person in med bay}
    Q2 -->|Can we reach them?| R4[emotional_bond +10<br/>James begins to open up]
    Q2 -->|Who is it?| R5[emotional_bond +8<br/>James reveals more]
    Q2 -->|Stay mission-focused| R6[emotional_bond +3<br/>James closes off]

    style R4 fill:#66bb6a
    style R5 fill:#81c784
    style R6 fill:#ffa726
```

### Moment 3: The Revelation

```mermaid
flowchart TD
    Q3{James: That person<br/>is my son, Adrian}
    Q3 -->|I'm so sorry| R7[emotional_bond +20<br/>moral_support +1<br/>James: Tell me what to do]
    Q3 -->|Tell me about him| R8[emotional_bond +15<br/>moral_support +2<br/>James shares memories]
    Q3 -->|Stay focused| R9[emotional_bond +5<br/>James: Right. The mission.]

    style R7 fill:#66bb6a
    style R8 fill:#66bb6a
    style R9 fill:#ffa726
```

### Moment 4: The Choice

```mermaid
flowchart TD
    Q4{James: I need to<br/>flood the med bay}
    Q4 -->|Save the crew.<br/>Adrian would want that.| R10[moral_support +3<br/>James: Thank you]
    Q4 -->|This is your choice| R11[moral_support +2<br/>James: Yeah. It always was.]
    Q4 -->|There must be<br/>another way| R12[moral_support +0<br/>James: There isn't!]

    R10 --> Click1[Click FLOOD MED BAY]
    R11 --> Click1
    R12 --> Click1

    Click1 --> Final1[Ascent sequence<br/>systems: 4]

    style R10 fill:#66bb6a
    style R11 fill:#81c784
    style R12 fill:#ffa726
    style Final1 fill:#ab47bc
```

---

## State Variable Progression (Golden Path)

```mermaid
gantt
    title State Variables Over Time (Golden Path)
    dateFormat X
    axisFormat %M:%S

    section Radiation
    0% → 10%    :0, 75
    10% → 30%   :75, 75
    30% → 50%   :150, 60
    50% → 85%   :210, 90

    section Time Remaining
    8:00 → 6:45 :0, 75
    6:45 → 5:30 :75, 75
    5:30 → 4:30 :150, 60
    4:30 → 3:00 :210, 90

    section Emotional Bond
    0 → 35      :0, 75
    35 → 60     :75, 75
    60 → 85     :150, 60
    85 → 95     :210, 90

    section Systems Repaired
    0 → 2       :0, 75
    2 → 3       :75, 75
    3 → 3       :150, 60
    3 → 4       :210, 90
```

---

## World Director Event Triggers

```mermaid
flowchart TD
    WD[World Director]

    WD --> Check{Evaluate<br/>Player Performance}

    Check -->|Success Rate > 80%<br/>Systems >= 2| Crisis[CRISIS EVENT<br/>Hydraulic failure<br/>radiation +10]

    Check -->|Success Rate < 30%<br/>Systems < 2| Help[HELP EVENT<br/>Auxiliary power found<br/>systems +1]

    Check -->|Idle 30+ seconds| Hint[HINT EVENT<br/>James: Try BALLAST]

    Check -->|Normal Performance| Continue[CONTINUE<br/>No intervention]

    Crisis --> Cooldown1[10-second cooldown]
    Help --> Cooldown2[10-second cooldown]
    Hint --> Cooldown3[8-second cooldown]

    style Crisis fill:#ef5350
    style Help fill:#66bb6a
    style Hint fill:#4fc3f7
```

---

## Ending Conditions Summary

| Ending | Conditions | Emotional Tone | Bond Level | Systems |
|--------|-----------|----------------|------------|---------|
| **Survived with Bond** | radiation < 95% AND bond ≥ 70 AND systems ≥ 3 | Warm, resolved, hopeful | High (70+) | 3-4 |
| **Survived as Strangers** | radiation < 95% AND bond < 40 AND systems ≥ 2 | Cold, professional, distant | Low (<40) | 2-4 |
| **Radiation Death** | radiation ≥ 95% | Tragic, final, static | Any | Any |
| **Time Expired** | time ≤ 0s | Desperate, failed, regretful | Any | Any |
| **Systems Failure** | time < 60s AND systems < 2 | Critical collapse, too late | Any | 0-1 |

---

## Control Usage Patterns

### Optimal Sequence (Golden Path)

```mermaid
sequenceDiagram
    participant P as Player
    participant J as James
    participant S as System

    Note over P,S: PHASE 1: Impact & Connection

    J->>P: What's your name?
    P->>J: [Name given]
    Note over S: emotional_bond +10

    J->>P: Find the CRANK
    P->>S: Click CRANK
    Note over S: systems_repaired +1
    J->>P: That's it... keep going...

    J->>P: Are you scared?
    P->>J: Yes, I'm terrified
    Note over S: emotional_bond +15

    P->>S: Click BALLAST
    Note over S: systems_repaired +1

    Note over P,S: PHASE 2: Working Relationship

    J->>P: You got people topside?
    P->>J: [Personal response]
    Note over S: emotional_bond +10

    P->>S: Click POWER
    Note over S: systems_repaired +1

    J->>P: Someone in med bay...
    P->>J: Can we reach them?
    Note over S: emotional_bond +10

    Note over P,S: PHASE 3: The Revelation

    J->>P: That person... is my son
    P->>J: I'm so sorry
    Note over S: emotional_bond +20

    P->>J: Tell me about him
    Note over S: moral_support +2

    Note over P,S: PHASE 4: The Choice

    J->>P: I need to flood med bay
    P->>J: Save the crew
    Note over S: moral_support +3

    P->>S: Click FLOOD MED BAY
    Note over S: systems_repaired = 4

    J->>P: We made it. Thank you.
    Note over S: ENDING: Survived with Bond
```

---

## Implementation Priority Checklist

### High Priority (Core Gameplay)
- [x] State variable system with auto-update
- [x] Phase transition triggers (time-based)
- [x] Control panel with 6 buttons
- [x] Ending condition checks (5 endings)
- [x] Dialogue system integration
- [ ] James's voice with breathing effects
- [ ] Radiation gauge visual
- [ ] Time countdown display

### Medium Priority (Polish)
- [ ] Interruption detection system
- [ ] World Director event spawning
- [ ] Particle effects (steam, sparks)
- [ ] Audio layers (ambient + phase-specific)
- [ ] Porthole underwater view
- [ ] Emotional bond visualization

### Low Priority (Enhancement)
- [ ] Player memory persistence
- [ ] Achievement tracking
- [ ] Replay system
- [ ] Alternative dialogue branches
- [ ] Dynamic music system
- [ ] Advanced particle effects

---

**END OF FLOWCHART DOCUMENT**

For detailed technical specifications, see `SUBMARINE_FLOW_DIAGRAM.md`
