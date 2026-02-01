# Crown Court Scene Description

**Scene ID:** `crown_court`
**Character:** Judge Whitmore
**Category:** Drama
**Display Name:** Crown Court
**Scene Type:** Legal defense trial

---

## Overview

A 12-minute courtroom drama where the player acts as defense attorney for Daniel Price, accused of arson resulting in the death of Margaret Holloway (age 67). Navigate evidence challenges, jury sympathy, and Judge Whitmore's strict procedural standards to achieve acquittal, plea deal, or face guilty verdict.

**The Dilemma:** Daniel admits privately that he was at the scene - but claims he was trying to rescue Mrs. Holloway when he panicked. Should you reveal this truth or hide it?

---

## Visual Description (3D Environment)

### Setting: Crown Court, London

**The Courtroom:**
- Solemn wood-paneled courtroom with high ceilings
- Natural light streaming through tall windows (Victorian architecture)
- Judge's bench: elevated platform with dark wood, papers spread
- Jury box: 12 seats with 12 faces (some skeptical, some sympathetic)
- Defense table: Polished wood with notes, files, legal pads
- Witness stand: Empty or occupied during cross-examination phases
- Public gallery: Behind player, murmuring crowd
- Crown symbols, British royal crests on walls

**The Judge:**
- Judge Whitmore: Female, late 50s, reading glasses on nose
- Black robes, white collar
- Stern but fair demeanor
- Gestures with gavel for emphasis

**The Client:**
- Daniel Price (34 years old) sits behind defense table
- Hollow-eyed, sleepless, hands clasped tightly
- Terrified expression, occasionally looks to player for reassurance

**Atmosphere:**
- Formal, imposing, high stakes
- Wood and brass aesthetic (Victorian/Edwardian)
- Natural daylight from tall windows (midday trial)
- Occasional crowd murmurs, paper rustling
- Gavel strikes for order
- Tension in air - people's fates decided here

**Color Palette:**
- Rich dark woods (mahogany, oak)
- Brass fittings
- White/cream (judge's collar, papers)
- Black (robes, formal attire)
- Natural daylight (soft, diffused through tall windows)

---

## World Labs Generation Prompt

**Environment:** Crown Court courtroom, London. Victorian-era wood-paneled room with high ceilings and tall windows. Formal, imposing atmosphere. Midday natural light.

**Key Elements:**
- Judge's bench: Elevated dark wood platform with crown emblem, papers spread, gavel
- Jury box: 12 seats arranged in two rows, faces showing mixed expressions
- Defense table: Polished wood table with legal pads, files, evidence folders
- Witness stand: Small enclosed box next to judge's bench (occasionally occupied)
- Public gallery: Wooden benches behind courtroom bar, observers present
- Wood paneling: Rich dark mahogany walls, floor-to-ceiling
- Tall windows: Gothic or Victorian arched windows with natural daylight
- Brass fittings: Door handles, railings, decorative elements
- Crown symbols: Royal crests on walls, judge's bench
- Ceiling: High vaulted or coffered ceiling with decorative molding

**Atmosphere:** Formal British courtroom. Solemn, heavy with consequence. Not modern sterile - traditional, historic. People's fates decided here. Murmuring crowd, occasional gavel strike. Victorian/Edwardian aesthetic.

**Lighting:**
- Primary: Natural daylight through tall windows (soft, diffused)
- Secondary: Ambient room lighting (warm incandescent suggestion)
- No harsh spotlights - even, formal illumination
- Paper surfaces catch light (evidence folders, judge's papers)

**Camera Position:** First-person from defense table. Player can stand to address jury/judge, sit to review notes. Can turn to face jury box, judge's bench, or witness stand. Limited movement within courtroom well (no approaching judge without permission).

**Style Reference:** British legal dramas - *A Few Good Men*, *The Verdict*, *To Kill a Mockingbird* courtroom scenes. Formal, traditional, wood-heavy aesthetic. Not modern American courtroom.

---

## Gameplay Mechanics

### Four-Phase Trial Structure

**Phase 1: Opening (0:00-2:00)**
- Judge presents prosecution's case
- Evidence summary:
  - Eyewitness testimony (neighbor Thomas Berkley, 40m away in darkness)
  - Forensic evidence (Daniel's fingerprints on accelerant container)
  - Motive (£15,000 unpaid rent debt)
- Player listens, prepares opening argument
- No controls visible yet

**Phase 2: Cross-Examination (2:00-5:00)**
- Interactive control phase
- Three challenge options appear:
  - **CHALLENGE EYEWITNESS** (risky) - Question Berkley's 40m darkness identification
  - **CALL CHARACTER WITNESS** (safe) - Vouch for Daniel's good character
  - **QUESTION FORENSICS** (risky) - Challenge fingerprint chain of custody
- Player can make freeform arguments or use buttons
- Judge reacts to procedural respect/violations

**Phase 3: Defense Case (5:00-9:00)**
- Present defense theory
- Controls available:
  - **CALL CHARACTER WITNESS** (if not used earlier)
  - **REVEAL THE TRUTH** (critical) - Admit Daniel was there, claim rescue attempt
- Jury sympathy and prosecution strength shift based on arguments
- Character witnesses humanize Daniel

**Phase 4: Closing Arguments (9:00-12:00)**
- **CLOSING ARGUMENT** button appears
- Player delivers final statement to jury
- Judge's trust + jury sympathy + prosecution strength determine verdict
- Endings triggered

### Control Interactions

**Challenge Eyewitness (Orange) [Phase 2]:**
- Risky but effective if argued well
- Questions: 40m distance, darkness, rain, window obstruction
- Success: Prosecution strength -15, Judge trust depends on procedural respect
- Failure: Judge trust -10 if poorly argued

**Call Character Witness (Blue) [Phases 2-3]:**
- Safe emotional appeal
- Brings in someone who vouches for Daniel's character
- Effect: Jury sympathy +15, moral weight +10
- No risk to judge's trust

**Question Forensics (Orange-Red) [Phase 2]:**
- Technical challenge to chain of custody
- Fingerprints could be from weeks ago (odd jobs for Mrs. Holloway)
- Success: Prosecution strength -20, Evidence challenged +1
- Requires legal expertise to argue convincingly

**Reveal the Truth (Red) [Phases 3-4]:**
- Critical irreversible decision
- Admits Daniel was at scene, argues rescue attempt defense
- Changes entire trial strategy
- Effect: Jury sympathy +20, Moral weight +30, but Prosecution strength +10
- Risky - requires emotional framing to succeed

**Closing Argument (Gold) [Phase 4]:**
- Triggers final verdict
- Player delivers closing statement
- System evaluates:
  - Prosecution strength < 40 and Jury sympathy > 70 = Full acquittal
  - Prosecution strength < 50 and Jury sympathy > 50 = Acquittal by doubt
  - Prosecution strength > 60 and Moral weight > 10 = Plea deal
  - Otherwise = Guilty verdict

---

## State Variables

- **Prosecution Strength:** 75-100%, starts strong (player must weaken)
- **Jury Sympathy:** 30-100%, defendant looks guilty initially
- **Judge Trust:** 50-100%, starts neutral (respect procedure or lose it)
- **Evidence Challenged:** 0-5 count of successfully challenged evidence
- **Moral Weight:** -50 to +50, negative=indefensible, positive=victim of circumstance
- **Time Remaining:** 720 seconds (12 minutes)
- **Phase:** 1-4 (Opening → Cross-Exam → Defense → Closing)

---

## The Case: Crown v. Daniel Price

### Prosecution's Evidence

**Eyewitness Testimony:**
- Thomas Berkley (neighbor) claims to have seen "a man matching Daniel's description" fleeing scene at 11:47 PM
- **Weakness:** 40 meters away, darkness, rain, looking through rain-streaked window
- **Challenge:** How reliable is identification under these conditions?

**Forensic Evidence:**
- Daniel's fingerprints on plastic container that held white spirit accelerant
- Container found 15 feet from rear door
- **Weakness:** Daniel admits doing odd jobs for Mrs. Holloway - could have touched container weeks ago
- **Challenge:** Chain of custody, timeframe of prints

**Motive:**
- Daniel owed £15,000 in unpaid rent to Mrs. Holloway
- Given notice to vacate
- **Prosecution Theory:** Set fire to destroy debt records
- **Weakness:** Would he really kill over rent? No history of violence

### Defense Inconsistencies

**Fire Origin:**
- Fire started in KITCHEN, not where accelerant container found (rear garden shed area)
- Suggests fire origin doesn't match accelerant location

**Eyewitness Reliability:**
- 40m distance, darkness, rain, window obstruction
- How certain can identification be?

**Daniel's Character:**
- No criminal record, no history of violence
- Carpenter, soft-spoken, well-liked
- **Why would he call 999 himself?** His call came at 11:52 PM, five minutes after "fleeing"

### Daniel's Private Confession

Daniel told player (defense attorney) in private:
- He WAS at the scene that night
- He heard Mrs. Holloway screaming inside burning building
- He tried to save her but panicked when flames engulfed kitchen
- He ran in fear
- Now too terrified to admit truth publicly (fears it proves guilt)

**Player's Dilemma:**
- Hide the truth and argue Daniel wasn't there (easier but less moral)
- Reveal the truth and argue failed rescue attempt (harder but potentially acquittal with strong emotional framing)

---

## Endings

### Success Endings

**Full Acquittal:**
- Conditions: Prosecution strength < 40, Jury sympathy > 70, Judge trust > 60
- Message: "[Judge bangs gavel] The jury finds the defendant... not guilty. Mr. Price, you are free to go. [pause] Counselor, well argued."
- **Outcome:** Complete victory, Daniel walks free

**Acquittal by Reasonable Doubt:**
- Conditions: Prosecution strength < 50, Jury sympathy > 50
- Message: "[Judge, measured tone] Not guilty. However, Mr. Price, I hope you understand the gravity of what occurred. This court is adjourned."
- **Outcome:** Daniel acquitted but shadow remains

**Plea Deal:**
- Conditions: Prosecution strength > 60, Jury sympathy < 40, Moral weight > 10
- Message: "[Judge nods] The court accepts the plea agreement. Mr. Price will serve 18 months with parole eligibility. A reasonable resolution."
- **Outcome:** Reduced sentence, avoids full conviction

### Failure Endings

**Guilty Verdict:**
- Conditions: Prosecution strength > 70 OR Jury sympathy < 20
- Message: "[Judge, solemn] The jury finds the defendant guilty of arson resulting in fatality. Sentencing will be scheduled. [long pause] I'm sorry, Counselor. You did what you could."
- **Outcome:** Daniel convicted, faces decades in prison

**Mistrial:**
- Condition: Judge trust < 20
- Message: "[Judge, sharp tone] Counselor, your conduct has compromised these proceedings. I am declaring a mistrial. We will reconvene with new counsel."
- **Outcome:** Procedural failure, case reset

**Time Expired:**
- Condition: Time remaining ≤ 0
- Message: "[Judge] We've run out of time. Based on the evidence presented, I must instruct the jury to deliberate. [pause] I fear the outcome will not favor your client."
- **Outcome:** Partial failure, likely guilty verdict

---

## Design Pillars

1. **Evidence Over Emotion:** Judge values procedure and facts, but jury responds to empathy
2. **Moral Complexity:** "Reveal Truth" button is morally right but tactically risky
3. **Character vs. Facts:** Balance humanizing Daniel with challenging prosecution's evidence
4. **Procedural Respect:** Losing judge's trust through theatrics or violations = losing case
5. **Time Pressure:** 12 minutes forces strategic choices about which arguments to pursue
6. **Multiple Paths:** Can win via emotional appeal (character) OR technical challenge (evidence) OR moral framing (rescue narrative)
