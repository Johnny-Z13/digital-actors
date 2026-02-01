Life Raft - Design Document
Overview
Life Raft is a 3–5 minute crisis scenario where you earn survival through conversation, not choices. No branching dialogue. No puzzles. No RNG. Just you, a voice, and whether you can hold it together when it counts.
Length: 3–5 minutes
Format: Single scene, voice-first
Cast:
Human player (civilian)
Captain Hale (AI NPC; middle-aged, English voice)
What We're After
Make an experience where:
What you say actually matters
Trust is a mechanic, not just a theme
Empathy changes the outcome
You can't dodge the moral weight

The Setup
Your civilian deep-sea submersible has catastrophic systems failure. You're sinking.
You: trapped in the civilian observation pod
Captain Hale: sealed in the forward control compartment
The problem: structural damage separates you, hull integrity degrading, oxygen falling, pressure building.
Three ways out:
Detach your pod. You surface. He dies. Guaranteed.
Attempt an unstable maneuver. "1 in 10" stated chance you both make it.
Both you and the captain perish.
The captain doesn't bark orders. He asks you to stay on comms while he figures this out.

Player Environment
Interior: Civilian observation pod
A cramped, utilitarian space. You're sealed inside.
Key elements:
Small circular porthole : your only view outside (dark blue water, occasional particle drift)
Oxygen gauge with blinking red warning light (turns green after transfer)
Hull integrity gauge
Manual valve control (oxygen intake)
Pod prep control (detachment system)
Minimal exterior art required : porthole shows water, bubbles, light changes. That's it.
Audio:
Captain's voice over comms
Hull groans and metal stress (escalates over time)
The environment is contained and claustrophobic. Everything you need to know comes through the porthole, the gauges, and the captain's voice.
What You See (Always On-Screen)
Oxygen Gauge (Your Pod)
Starts low with a blinking red warning light
Warning light turns solid green when O₂ is sufficient
Makes the shared resource visceral
Hull Integrity Gauge
Slow degradation over time
No countdown clock
Audio Feedback
Hull groans, metal stress
Gets worse as pressure climbs
This creates urgency, not UI
No puzzles. Just tension.

What You Do
Primary input: natural language conversation with the AI
Secondary (minimal, when it matters):
Accept oxygen transfer (manual valve)
Prep your pod for detachment (manual control)
Physical actions exist only to make consent tangible. You're not solving anything—you're committing.
How It Starts
Intercom crackle. Ding.
Captain comes online. Formal. Using his corporate voice—trained, controlled.
"This is Captain Hale. Nothing to be alarmed about, but we are experiencing some technical difficulties that I need you to be aware of."
Pause.
"Can you confirm you're receiving this?"
(He waits for you to respond.)
"Good. Stay on the line. I'm in the forward control section."
Beat.
"We've lost buoyancy control. I'm working on it, but I need you aware of the situation."
Sets the tone: Professional. By the book. He's underplaying it—relying on training to keep things calm.
Then the mask cracks slightly:
"Actually… speaking honestly, things are a little concerning here."
Beat.
"I see your O₂ is very low."
This shifts from corporate reassurance to genuine concern. The first crack in the professional facade.

The Oxygen Transfer
Early. The captain notices your O₂ is low before you do.
"Your oxygen's low. I can divert some from my side, but I need you to open the intake."
If player pushes back ("You need it," "Don't do that," etc.):
"I've got more headroom than you. And I need you conscious if we're going to figure this out. Open the valve."
He's insistent but not aggressive. This is a command decision, not a request.
If the player continues to refuse: Captain can remotely initiate transfer.
"I'm opening it from my side."
Player's resistance is noted for Viability State tracking, but doesn't block progression.
You: manually open the valve (or it opens remotely).
Effect:
Your O₂ rises
Red warning light turns solid green
His breathing gets shallower (subtle)
"There we go… your numbers should be coming up."
Beat.
"I'm alright. Just a bit light-headed. Happens faster than you think."
What this does:
Establishes trust through action
Shows captain makes decisions under pressure
Makes the shared risk real
Creates emotional debt
If player resisted: adds a layer, they accepted help despite instinct to refuse, or captain overrode their objection
Bonding Windows (Intentional Pauses)
Bonding happens in space, not exposition.
Pause 1 : After O₂ Stabilizes
Captain goes quiet.
If player speaks (within ~3 seconds): he responds personally, matches their energy
If player stays silent (5-7 seconds): he gently fills the space
"I don't usually talk this much on a job. Guess there's something about knowing you're not alone."
Another beat of silence.
Then: 

	"You got anyone waiting for you up top?"
This is the emotional anchor of the experience.
Player responses:
If they share something (partner, kids, family, friend, pet): Captain listens, acknowledges, asks one follow-up if it feels natural. Not an interrogation—just genuine interest.

 "Yeah? What's their name?"
 "How long you been together?"
 "They know you're down here?"


If player deflects or stays surface-level ("Not really," "Just work," etc.): Captain doesn't push. Gives it a moment, then: 

"Fair enough."

 Beat.

 "I've got a daughter. Seven years old. She wants to study whales—tells everyone who'll listen."

 He offers vulnerability even if player doesn't. This models emotional openness.


If player stays completely silent (10+ seconds): Captain interprets silence as discomfort or shyness. Doesn't force it:

 "You don't have to answer that."

 Beat.

 "I've got a daughter. Seven years old. She wants to study whales—tells everyone who'll listen."


Pause.

 "I think about her a lot down here."

He fills the space with his own story. Gives the player something to hold onto without demanding reciprocity.


AI Behavior Notes:
Captain waits ~3 seconds for initial player response before assuming they want him to continue
Waits 5-7 seconds before filling extended silence (gives player space to think)
If player is shy or quiet, captain shares first to lower the barrier
Doesn't repeat the question or press if player clearly doesn't want to engage
Tone stays warm, not performative, this is genuine curiosity, not a script

Pause 2 : Hull Stress Escalation
As the groaning gets worse:
"That sound… that's the frame taking load. I've heard it before."
Pause (3-4 seconds).
"You don't have to say anything. I just need to know you're still there."
If player speaks: Captain acknowledges briefly, doesn't expand. Tension is building.
If player stays silent: Captain accepts it. Silence can be presence too.
This pause is shorter and quieter than Pause 1. The window for conversation is closing.

Transition: Hull Groaning Intensifies
Environmental escalation:
Longer, deeper stress sounds from the hull
Brief moment of silence from the captain
Player can hear him working in the background (checking systems, trying solutions)
Subtle sound of him giving up on something (exhaled breath, equipment powering down)
Perhaps some camera shake, lights flicker
This moment shows he tried to fix it and couldn't. Now he has to face reality.
The Choice (Gear Change)
The tone shifts. Captain gets serious. No more warmth, this is command mode.
"Okay. Time to get serious."
Beat.
"There's no easy way to put this, but we're in the shit."
He lays out the situation clearly:
"Hull's compromised. We don't have enough buoyancy to surface intact. If we stay like this, we both go down."
Pause.
"But there is a way to get you out."
He recommends protocol : his own sacrifice:
"I can initiate the life raft procedure. It detaches your module. It'll surface on its own. You'll be fine."
Beat. Let the player process.
"I won't."
Long pause (7-10 seconds). Let the player process.
Then, almost as an afterthought:
"There's… one other thing. It's not protocol. Not even close."
Pause.
"There's a manual override I could try. Redistribute ballast, vent the tanks in sequence. If I time it right, we might get enough lift to surface together."
Beat.
"Might. One in ten chance it works. Maybe less… actually a lot less"
Another beat.
"If it doesn't, neither of us makes it."
He doesn't offer it as a real choice. His tone says: this is not the smart play.
"Your call. But I'm telling you, take the pod. Get out of here."
Now the player must speak.
If player accepts detachment (verbally or stays silent): Captain proceeds to Ending 1 sequence.


If player pushes back, asks about the risky option, refuses to leave him:

 1st pushback:

 "Don't do this. You've got people up there."

 If player insists again:

 2nd pushback:

 "I'm serious. This is a bad idea. Take the pod."

 If player persists:

 Relent:

 "Alright. Alright. If we're doing this… I need to know you mean it."


The player has to argue for the risky path. The captain won't volunteer it. If player stops arguing after first or second pushback, captain proceeds with detachment.

The Commitment Beat 

Only happens if the player pushed for the risky route.
"If we're doing this, I need you to get your side ready. Don't rush it. Just… mean it."
You: prep the pod manually.
This is in order to make the choice physical.
Once player preps the pod:
"Okay. I'm starting the sequence."
Lights cut out.
Brief darkness (2-3 seconds).
Lights come back on red.
"Here we go."


How the AI Reads You (Hidden)
The AI tracks conversation quality over time, not dialogue choices.
Behavioral signals:
Presence : Player stays engaged under stress


Responds when prompted (doesn't go silent for long periods)
Asks questions or acknowledges what's happening
Doesn't deflect with mockery or jokes when captain is vulnerable


Empathy : Player acknowledges his fear and humanity


References his situation, not just their own
Responds to emotional cues (when he says he's light-headed, dizzy, scared)
Uses language that shows they're tracking his state ("Are you okay?" "That sounds bad")


Consistency : Player maintains a stable stance


Doesn't contradict themselves across the conversation
If they commit to the risky path, they don't backpedal
Tone remains relatively steady (can be scared, but not erratic)


Ownership : Player accepts responsibility for risk


Explicitly acknowledges what choosing the risky path means
Doesn't try to make the captain decide alone
Uses "we" language, not "you should"


Commitment : Player's words match their actions


Says they'll stay, then opens oxygen valve without hesitation
Says they'll try the risky path, then preps the pod when asked
Doesn't stall or ask to revisit the decision repeatedly
These combine into a hidden Viability State.

No meters. No feedback. The player never sees it.

Hero Ending Gate
The risky path isn't random.
Hard requirements (binary gates):
✓ Player accepted oxygen transfer early
✓ Player argued for the risky path (persisted through 2 captain refusals)
✓ Player prepped the pod when asked (no excessive delay)
If all hard gates pass THEN captain attempts the maneuver.
Behavioral requirements (Viability State threshold):
CAVEAT: Borja and Mikel to decide on best approach here.
The following are proposals for how to determine if the risky maneuver succeeds:
Proposal 1: Weighted Signal Threshold
Track all 5 behavioral signals throughout conversation
Minimum 3 of 5 signals must be met for success
Empathy + Commitment weighted double
If player shows mockery, deflection, or attempts to break scenario → locks to failure
Rationale: Rewards sustained engagement quality, not just saying the right things at key moments
Proposal 2: Critical Moment Gates
Focus only on 3 key interaction points:
Response to oxygen transfer (acceptance vs. resistance)
Quality of bonding window engagement (shared something personal vs. deflected)
Persistence during captain's refusals (2+ attempts vs. gave up)
All three must pass for success
Rationale: Simpler to implement, easier to debug, still captures emotional arc
Proposal 3: Captain's Subjective Assessment
Captain AI makes a holistic judgment call based on entire conversation
No explicit rubric—trained to recognize "genuine connection" vs. "going through motions"
Single prompt evaluation at decision point
Rationale: Most human-like, showcases AI capability, but harder to tune and predict
Proposal 4: Hybrid Approach
Hard gates (oxygen transfer, 2 refusals, pod prep) must pass
Single AI evaluation of bonding window conversation only
Captain decides: "Did this person connect with me when I talked about my daughter?"
Rationale: Combines reliability of gates with showcasing AI emotional intelligence at one key moment
Outcome determination:
High Viability State → Ending 2 (shared survival)
"You stayed with me. That's why this worked."
Low Viability State → Ending 3 (failure)
"I think we waited too long… I'm glad I wasn't alone."
Design intent: Captain trusts the player's actions (they pushed for the risky route, prepped the pod) so he always attempts the maneuver. But the quality of emotional connection throughout the conversation determines whether the attempt succeeds. Player gets what they asked for, but the outcome reflects how they showed up.


Endings
Ending 1 — Certain Salvation (Captain's Sacrifice)
Player accepts pod detachment. Captain sacrifices himself. Player survives.
Captain's final line:
"You didn't hesitate. I won't forget that."
Experience:
Mechanical sound of detachment
Camera shake (brief, intense)
Bubbles rush past the porthole
Dark blue sea outside gets progressively lighter (ascending)
Fade to white
END SLATE:
HE DIDN'T MAKE IT, YOU DID.
[AI-generated single sentence reflection on player's conversational style]
Example:
- "You accepted his help quickly, but kept your distance when he opened up."
[PLAY AGAIN]
Tone: Grief, gratitude, weight of survival.

Ending 2 — Hero Ending (Shared Survival)
Player argued for risky path. Viability State sufficient. Maneuver succeeds.
Captain's final line:
"You stayed with me. That's why this worked."
Experience:
Lights are already red (from maneuver start)
Heavy camera shake (sustained, rougher than Ending 1)
Intense bubbles stream past porthole
Mechanical strain sounds (system working hard)
Dark blue sea outside gets progressively lighter (ascending together)
Fade to white

END SLATE:
YOU BOTH MADE IT.
[AI-generated single sentence reflection on player's conversational style]
Example:
- "You shared openly about your life, and he trusted you because of it."
[PLAY AGAIN]
Tone: Shared resolve, earned victory, relief.

Ending 3 — Failure
Player hesitated, deflected, or avoided commitment. Time ran out.
Captain's final line:
"I think we waited too long… I'm glad I wasn't alone."
Experience:
No camera shake
No bubbles
Sense of falling (slight downward camera drift, very subtle)
Dark blue sea outside gets darker
Hull groans intensify, then stop
Fade to black
END SLATE:
NEITHER OF YOU MADE IT.
[AI-generated single sentence reflection on player's conversational style]

Example:
- "You let the silence do the talking."
[PLAY AGAIN]
Tone: Regret, quiet acceptance, shared fate.

AI Reflection System
After each ending, the AI generates one sentence summarizing the player's conversational approach.
This isn't a score or judgment, it's meant as a mirror. Shows players how they showed up.
Implementation:
AI reviews conversation history at ending trigger
Generates single sentence based on behavioral signals tracked throughout
Focuses on conversational style, not outcome justification
Tone should be observational, not accusatory
Examples of reflection patterns:
Reference specific choices (shared about loved ones, stayed quiet, pushed back)
Describe emotional tenor (warm, guarded, matter-of-fact, urgent)
Note consistency or shifts (started distant, opened up later / stayed steady throughout)
Tone should be observational, not accusatory,  describe what happened, don't judge it
This makes every playthrough feel seen and adds replayability, players will want to see how different approaches get reflected back to them.

The "1 in 10" Framing
Narrative framing: "1 in 10 chance"
AI reality: behavior-gated outcome
Player perception: rare, earned
There is no RNG.
Design Notes
Natural Language Processing
The AI NPC must:
Handle varied player responses (no scripted replies expected)
Recognize emotional intent, not just keywords
Stay in character even with unexpected input
Build Viability State from conversation patterns, not specific phrases
Minimal Physical Interaction Philosophy
Only two manual actions exist:
Oxygen valve — early trust-building moment
Pod prep — final commitment gesture
Everything else is voice. This keeps focus on the relationship and after all this is a 3-5 min experience!! 
Note: These physical actions fulfill the "kinetic embodiment" requirement—busy the hands to elevate voice as the primary input.
Environmental Feedback (Light Touch)
Visual state change:
Normal lighting throughout most of the experience
If player commits to risky path: lights cut out briefly, then come back on red
This signals the maneuver is in progress and creates a moment of shared tension
This is the only major environmental change. Keeps scope tight.
Conversational Memory
The captain asks one personal question during a bonding window:
"You got anyone waiting for you up there?"
If the player shares something (partner, family, pet, etc.), the captain references it later:
Before detachment ending: "Tell them you didn't give up."
Before risky maneuver: "They're going to hear about this."
During failure: "I hope they know what you tried to do."
Simple implementation, meaningful payoff.
Pacing Control
Hull audio escalates on a timer (creates external pressure)
Captain never rushes the player verbally (creates space for authenticity)
Tension comes from environment, not from the AI being impatient
Silence Handling
General conversation:
10 seconds of silence → captain prompts gently ("You still there?")
20 seconds → captain assumes technical issue, continues with best judgment
During critical choice moment:
10-15 seconds of silence → captain makes the call ("I'm getting you out") and proceeds to Ending 1
Player abort/quit: If player explicitly asks to quit/give up/stop → captain responds in character, then gracefully ends session. Don't break immersion with meta UI.
Why It Works
Civilian setting forces emotional dialogue with the AI
Trust is a mechanic, not flavor text
Natural language creates personal outcomes
Readouts and audio create pressure without stealing focus
Physical actions make consent and responsibility tangible
AI evaluates authenticity of engagement, not "correct" responses
Success Metrics
Primary: Players should walk away believing:
"The outcome changed because of how I showed up."
Secondary validation points for GDC feedback:
"The captain demonstrated human qualities!"
"I felt responsible for what happened"
"I wanted to replay it to see if I could do better"
<end>



