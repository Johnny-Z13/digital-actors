"""
Crown Court - Legal Defense Scene

The player acts as defense attorney for Daniel Price, accused of arson resulting
in fatality. Navigate evidence, jury sympathy, and the judge's trust to achieve
acquittal, plea deal, or face guilty verdict.
"""

from llm_prompt_core.types import Line
from scenes.base.base import (
    AudioAssets,
    CharacterRequirement,
    FailureCriterion,
    Scene,
    SceneArtAssets,
    SceneControl,
    StateVariable,
    SuccessCriterion,
)


class CrownCourt(Scene):
    """Crown Court - Legal Defense of Daniel Price"""

    def __init__(self):
        # Audio assets for courtroom atmosphere
        audio = AudioAssets(
            background_music="/audio/courtroom_ambience.mp3",
            sfx_library={
                "gavel": "/audio/sfx/gavel.mp3",
                "murmur": "/audio/sfx/crowd_murmur.mp3",
                "paper_shuffle": "/audio/sfx/papers.mp3",
                "door_close": "/audio/sfx/courtroom_door.mp3",
            },
            volume_levels={"music": 0.2, "sfx": 0.6, "voice": 1.0},
        )

        # Art assets configuration
        art_assets = SceneArtAssets(
            scene_type="character",  # Use default character scene (Judge sphere)
            background_image=None,  # Could add courtroom background in future
            audio=audio,
        )

        # Define interactive controls (decision points in the trial)
        controls = [
            SceneControl(
                id="challenge_eyewitness",
                label="CHALLENGE EYEWITNESS",
                type="button",
                color=0xFFA500,  # Orange - risky but potentially rewarding
                position={"x": -0.6, "y": 0.0, "z": 0},
                description="Question the credibility of the witness who claims to have seen Daniel fleeing the scene.",
                action_type="risky",
                npc_aware=True,
                visible_in_phases=[2],  # Only visible in Phase 2 (cross-examination)
            ),
            SceneControl(
                id="character_witness",
                label="CALL CHARACTER WITNESS",
                type="button",
                color=0x4169E1,  # Royal blue - safe, emotional appeal
                position={"x": -0.2, "y": 0.0, "z": 0},
                description="Bring in someone who can vouch for Daniel's good character.",
                action_type="safe",
                npc_aware=True,
                visible_in_phases=[2, 3],  # Visible in Phases 2-3
            ),
            SceneControl(
                id="question_fingerprint",
                label="QUESTION FORENSICS",
                type="button",
                color=0xFF4500,  # Orange-red - technical challenge
                position={"x": 0.2, "y": 0.0, "z": 0},
                description="Challenge the chain of custody and reliability of fingerprint evidence.",
                action_type="risky",
                npc_aware=True,
                visible_in_phases=[2],  # Only visible in Phase 2
            ),
            SceneControl(
                id="reveal_truth",
                label="REVEAL THE TRUTH",
                type="button",
                color=0xFF0000,  # Red - critical, irreversible decision
                position={"x": 0.6, "y": 0.0, "z": 0},
                description="Reveal that Daniel confessed privately that he was at the scene, but claims he was trying to rescue someone inside.",
                action_type="critical",
                npc_aware=True,
                visible_in_phases=[3, 4],  # Visible in Phases 3-4
            ),
            SceneControl(
                id="closing_argument",
                label="CLOSING ARGUMENT",
                type="button",
                color=0xFFD700,  # Gold - climactic moment
                position={"x": 0.0, "y": 0.3, "z": 0},
                description="Deliver your final argument to the jury.",
                action_type="critical",
                npc_aware=True,
                visible_in_phases=[4],  # Only visible in Phase 4
            ),
        ]

        # Define state variables that track the trial's progress
        state_variables = [
            StateVariable(
                name="prosecution_strength",
                initial_value=75.0,  # Prosecution starts with strong case
                min_value=0.0,
                max_value=100.0,
                update_rate=None,  # Changed by player actions, not time
            ),
            StateVariable(
                name="jury_sympathy",
                initial_value=30.0,  # Defendant looks guilty initially
                min_value=0.0,
                max_value=100.0,
                update_rate=None,  # Changed by player arguments
            ),
            StateVariable(
                name="judge_trust",
                initial_value=50.0,  # Judge starts neutral
                min_value=0.0,
                max_value=100.0,
                update_rate=None,  # Changed by procedural respect/violations
            ),
            StateVariable(
                name="evidence_challenged",
                initial_value=0,  # Count of successfully challenged evidence
                min_value=0,
                max_value=5,
                update_rate=None,
            ),
            StateVariable(
                name="moral_weight",
                initial_value=0.0,  # Neutral framing
                min_value=-50.0,  # Negative = indefensible
                max_value=50.0,  # Positive = victim of circumstance
                update_rate=None,
            ),
            StateVariable(
                name="time_remaining",
                initial_value=720.0,  # 12 minutes
                min_value=0.0,
                max_value=720.0,
                update_rate=-1.0,  # Decreases 1 second per second
            ),
            StateVariable(
                name="phase",
                initial_value=1,  # Start in Phase 1 (Opening)
                min_value=1,
                max_value=4,
                update_rate=None,  # Changed based on time thresholds
            ),
        ]

        # Define success criteria (winning outcomes)
        success_criteria = [
            SuccessCriterion(
                id="full_acquittal",
                description="Full acquittal with strong defense",
                condition="state['prosecution_strength'] < 40 and state['jury_sympathy'] > 70 and state['judge_trust'] > 60",
                message="[Judge bangs gavel] The jury finds the defendant... not guilty. Mr. Price, you are free to go. [pause] Counselor, well argued.",
                required=False,
            ),
            SuccessCriterion(
                id="acquittal_doubt",
                description="Acquittal through reasonable doubt",
                condition="state['prosecution_strength'] < 50 and state['jury_sympathy'] > 50",
                message="[Judge, measured tone] Not guilty. However, Mr. Price, I hope you understand the gravity of what occurred. This court is adjourned.",
                required=False,
            ),
            SuccessCriterion(
                id="plea_deal",
                description="Plea deal accepted",
                condition="state['prosecution_strength'] > 60 and state['jury_sympathy'] < 40 and state['moral_weight'] > 10",
                message="[Judge nods] The court accepts the plea agreement. Mr. Price will serve 18 months with parole eligibility. A reasonable resolution.",
                required=False,
            ),
        ]

        # Define failure criteria (losing outcomes)
        failure_criteria = [
            FailureCriterion(
                id="guilty_verdict",
                description="Jury finds defendant guilty",
                condition="state['prosecution_strength'] > 70 or state['jury_sympathy'] < 20",
                message="[Judge, solemn] The jury finds the defendant guilty of arson resulting in fatality. Sentencing will be scheduled. [long pause] I'm sorry, Counselor. You did what you could.",
                ending_type="failure",
            ),
            FailureCriterion(
                id="mistrial",
                description="Mistrial due to procedural failure",
                condition="state['judge_trust'] < 20",
                message="[Judge, sharp tone] Counselor, your conduct has compromised these proceedings. I am declaring a mistrial. We will reconvene with new counsel.",
                ending_type="failure",
            ),
            FailureCriterion(
                id="time_expired",
                description="Time runs out before closing arguments",
                condition="state['time_remaining'] <= 0",
                message="[Judge] We've run out of time. Based on the evidence presented, I must instruct the jury to deliberate. [pause] I fear the outcome will not favor your client.",
                ending_type="partial_failure",
            ),
        ]

        # Define character skill requirements
        character_requirements = [
            CharacterRequirement(
                skill="legal_expertise",
                importance="highly_recommended",
                impact_without="Will struggle to make procedural arguments and may miss evidence challenges.",
                alternative_path=True,  # Can succeed with emotional jury appeal
            ),
            CharacterRequirement(
                skill="ethical_reasoning",
                importance="recommended",
                impact_without="May miss moral framing opportunities and find it harder to navigate the 'reveal truth' dilemma.",
                alternative_path=True,
            ),
            CharacterRequirement(
                skill="investigation",
                importance="helpful",
                impact_without="Less effective at challenging eyewitness testimony and forensic evidence.",
                alternative_path=True,
            ),
        ]

        # Define opening speech with tight pacing (0.3s between lines)
        opening_speech = [
            Line(text="[Judge enters, courtroom rises]", delay=0),
            Line(text="[Sound of gavel] Be seated.", delay=0.3),
            Line(text="We are here for the case of The Crown versus Daniel Price.", delay=0.6),
            Line(
                text="Mr. Price stands accused of arson resulting in the death of one Margaret Holloway, age 67.",
                delay=0.9,
            ),
            Line(
                text="[Adjusts glasses, looks at player] Counselor, the prosecution has presented their case.",
                delay=1.2,
            ),
            Line(
                text="They claim your client was seen fleeing the scene at 11:47 PM, and his fingerprints were found on a container of accelerant.",
                delay=1.5,
            ),
            Line(
                text="[Leans forward] Yet you maintain his innocence. Very well. You may begin your defense.",
                delay=1.8,
            ),
            Line(
                text="But be warned—this court values evidence over emotion, and procedure over theatrics.",
                delay=2.1,
            ),
            Line(text="[Gestures] Proceed when ready, Counselor.", delay=2.4),
        ]

        # Initialize the scene
        super().__init__(
            id="crown_court",
            name="Crown Court - Legal Defense",
            description="""SETTING: Crown Court, London. A solemn wood-paneled courtroom with high ceilings and natural light streaming through tall windows. The judge sits elevated at the bench, papers spread before her, reading glasses perched on her nose. You stand at the defense table, notes in hand, heart pounding.

The jury box holds twelve faces—some skeptical, some sympathetic, all watchful. They will decide your client's fate based on what you say and do here today.

Behind you sits your client, Daniel Price: 34 years old, hollow-eyed from sleepless nights, hands clasped tightly together. He's terrified. He's already told you privately, in whispered desperation, that he was at the scene that night. But he swears—swears on his mother's grave—that he was trying to save Mrs. Holloway when he heard her screaming inside the burning building. He panicked when he saw flames engulfing the kitchen. He ran. And now he's here, accused of murder by arson.

The prosecution's case is strong on the surface:
- EYEWITNESS TESTIMONY: A neighbor, Mr. Thomas Berkley, claims he saw "a man matching Daniel's description" fleeing the scene at 11:47 PM. But the witness was 40 meters away, in darkness, looking through a rain-streaked window.
- FORENSIC EVIDENCE: Daniel's fingerprints were found on a plastic container that once held white spirit accelerant. The container was found 15 feet from the rear door of the house. But Daniel admits he'd done odd jobs for Mrs. Holloway before—he could have touched that container weeks ago.
- MOTIVE: Daniel owed Mrs. Holloway £15,000 in unpaid rent. He'd been given notice to vacate. The prosecution argues he set the fire to destroy the debt records. But would he really kill over rent?

But inconsistencies exist:
- The fire started in the KITCHEN, not where the accelerant container was found (rear garden shed area).
- The "eyewitness" saw someone from 40 meters away in darkness and rain—how reliable is that identification?
- Daniel has no history of violence. No criminal record. He's a carpenter, soft-spoken, well-liked by those who know him.
- Why would he call 999 himself if he was the arsonist? His call came in at 11:52 PM, five minutes after the neighbor claims to have seen him "fleeing."

Your job as defense counsel:
1. CREATE REASONABLE DOUBT - The prosecution must prove guilt beyond reasonable doubt. Find the cracks in their case.
2. APPEAL TO JURY SYMPATHY - Make them see Daniel as human, not a monster. But balance emotion with evidence.
3. NAVIGATE THE JUDGE'S STRICT PROCEDURAL STANDARDS - Judge Thorne values legal rigor. Respect procedure, or lose her trust.
4. DECIDE WHETHER TO REVEAL THE TRUTH - Daniel was there. He admits it to you. Should you reveal this in court and argue he was a failed rescuer, not an arsonist? Or keep it hidden and argue he wasn't there at all?

The clock is ticking. You have limited time to build your case, challenge evidence, call witnesses, and deliver a closing argument that could save Daniel's life—or condemn him to decades in prison.

The judge looks at you expectantly. The jury waits. Your client's future rests in your hands.

What will you say?""",
            opening_speech=opening_speech,
            art_assets=art_assets,
            controls=controls,
            state_variables=state_variables,
            success_criteria=success_criteria,
            failure_criteria=failure_criteria,
            character_requirements=character_requirements,
            time_limit=720.0,  # 12 minutes
            allow_freeform_dialogue=True,
        )
