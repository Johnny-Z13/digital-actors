"""
Iconic Detectives - Mara Vane Mystery Consultation Scene

The player sits at a detective's desk viewing an evidence string board.
Mara Vane calls with information about Dr. Elias Crowe's murder.
Branching dialogue leads to multiple endings based on player choices.

Compatible characters: Mara Vane (primary), other detective callers
"""

from scenes.base import (
    Scene,
    SceneControl,
    StateVariable,
    SuccessCriterion,
    FailureCriterion,
    CharacterRequirement,
    SceneArtAssets,
    AudioAssets,
    VoiceEffect
)
from llm_prompt_core.types import Line


class IconicDetectives(Scene):
    """Iconic Detectives - Mara Vane Branching Phone Mystery"""

    def __init__(self):
        # Extreme phone receiver voice effect - 80s landline handset sound
        phone_effect = VoiceEffect(
            id="phone_extreme",
            enabled=True,
            highpass_freq=400.0,       # Aggressive bass cut
            lowpass_freq=2800.0,       # Narrow bandwidth
            mid_boost_freq=1000.0,     # Telephone presence
            mid_boost_gain=5.0,        # Strong boost (+5 dB)
            mid_boost_q=1.5,           # Focused Q
            compressor_threshold=-20.0,
            compressor_ratio=6.0,      # Tight compression
            compressor_attack=0.002,
            compressor_release=0.2,
            distortion_amount=35,      # Noticeable grit
            noise_level=-35.0,         # Audible line noise
            mono=True
        )

        # Audio assets for 1980s NYC detective office atmosphere
        audio = AudioAssets(
            background_music="/audio/nyc_rain_ambience.mp3",
            sfx_library={
                'phone_ring': '/audio/sfx/phone_ring_80s.mp3',
                'phone_pickup': '/audio/sfx/phone_pickup.mp3',
                'rain': '/audio/sfx/rain_window.mp3',
                'traffic': '/audio/sfx/distant_traffic.mp3',
                'paper_rustle': '/audio/sfx/papers.mp3',
                'pin_click': '/audio/sfx/pin_click.mp3',
                'string_stretch': '/audio/sfx/string_stretch.mp3',
            },
            volume_levels={
                'music': 0.2,
                'sfx': 0.6,
                'voice': 1.0
            },
            voice_effect=phone_effect
        )

        # Art assets configuration
        art_assets = SceneArtAssets(
            scene_type="character",
            background_image=None,
            audio=audio
        )

        # Define interactive controls for the Mara Vane investigation
        # Phase 2 controls: Core hooks (A/B/C)
        controls = [
            SceneControl(
                id="hook_identity",
                label="WHO ARE YOU?",
                type="button",
                color=0x4682b4,  # Steel blue
                position={'x': -0.6, 'y': 0.0, 'z': 0},
                description="Press her identity - 'Who are you, really?'",
                action_type="normal",
                npc_aware=True,
                visible_in_phases=[2]
            ),
            SceneControl(
                id="hook_timeline",
                label="WHAT'S WRONG WITH THE TIMING?",
                type="button",
                color=0x4682b4,  # Steel blue
                position={'x': 0.0, 'y': 0.0, 'z': 0},
                description="Press the timeline - 'What's wrong with the timing?'",
                action_type="normal",
                npc_aware=True,
                visible_in_phases=[2]
            ),
            SceneControl(
                id="hook_key",
                label="WHY STEAL A KEY?",
                type="button",
                color=0x4682b4,  # Steel blue
                position={'x': 0.6, 'y': 0.0, 'z': 0},
                description="Press the object - 'Why would someone steal a key?'",
                action_type="normal",
                npc_aware=True,
                visible_in_phases=[2]
            ),
            # Phase 3 controls: Branch choice
            SceneControl(
                id="follow_key",
                label="FOLLOW THE KEY",
                type="button",
                color=0xffd700,  # Gold - major choice
                position={'x': -0.3, 'y': 0.0, 'z': 0},
                description="Path 1: Follow the conspiracy thread (object-driven)",
                action_type="risky",
                npc_aware=True,
                visible_in_phases=[3]
            ),
            SceneControl(
                id="follow_lie",
                label="FOLLOW THE LIE",
                type="button",
                color=0xff6347,  # Tomato - major choice
                position={'x': 0.3, 'y': 0.0, 'z': 0},
                description="Path 2: Investigate the staged robbery narrative",
                action_type="risky",
                npc_aware=True,
                visible_in_phases=[3]
            ),
            # Path 1 sub-choices (visible after choosing FOLLOW THE KEY)
            SceneControl(
                id="p1_how_know",
                label="HOW DO YOU KNOW SABLE STORAGE?",
                type="button",
                color=0x228b22,  # Forest green
                position={'x': -0.6, 'y': 0.0, 'z': 0},
                description="Ask how she knows about Sable Storage",
                action_type="normal",
                npc_aware=True,
                visible_in_phases=[4]
            ),
            SceneControl(
                id="p1_whats_inside",
                label="WHAT'S IN THE BOX?",
                type="button",
                color=0x228b22,
                position={'x': 0.0, 'y': 0.0, 'z': 0},
                description="Ask what's inside the box",
                action_type="normal",
                npc_aware=True,
                visible_in_phases=[4]
            ),
            SceneControl(
                id="p1_who_knows",
                label="WHO ELSE KNOWS?",
                type="button",
                color=0x228b22,
                position={'x': 0.6, 'y': 0.0, 'z': 0},
                description="Ask who else knows about the box",
                action_type="normal",
                npc_aware=True,
                visible_in_phases=[4]
            ),
            # Path 2 sub-choices (visible after choosing FOLLOW THE LIE)
            SceneControl(
                id="p2_who_staged",
                label="WHO STAGED IT?",
                type="button",
                color=0x800020,  # Burgundy
                position={'x': -0.6, 'y': 0.0, 'z': 0},
                description="Ask who staged the robbery",
                action_type="normal",
                npc_aware=True,
                visible_in_phases=[5]
            ),
            SceneControl(
                id="p2_why_argument",
                label="WHY AN ARGUMENT?",
                type="button",
                color=0x800020,
                position={'x': 0.0, 'y': 0.0, 'z': 0},
                description="Ask what makes her sure it was an argument",
                action_type="risky",
                npc_aware=True,
                visible_in_phases=[5]
            ),
            SceneControl(
                id="p2_killer_detail",
                label="GIVE ME A KILLER DETAIL",
                type="button",
                color=0x800020,
                position={'x': 0.6, 'y': 0.0, 'z': 0},
                description="Demand a detail only the killer would know",
                action_type="risky",
                npc_aware=True,
                visible_in_phases=[5]
            ),
            # Challenge button (available in phases 4 and 5 after catching contradictions)
            SceneControl(
                id="challenge_mara",
                label="YOU WERE THERE",
                type="button",
                color=0xff0000,  # Red - confrontational
                position={'x': 0.0, 'y': 0.3, 'z': 0},
                description="Confront Mara with her contradictions",
                action_type="risky",
                npc_aware=True,
                visible_in_phases=[4, 5]
            ),
        ]

        # State variables tracking the Mara Vane investigation
        state_variables = [
            StateVariable(
                name="trust",
                initial_value=50.0,  # Mara's willingness to share (50 = neutral)
                min_value=0.0,
                max_value=100.0,
                update_rate=None
            ),
            StateVariable(
                name="contradictions",
                initial_value=0,  # Slips/inconsistencies player catches
                min_value=0,
                max_value=5,
                update_rate=None
            ),
            StateVariable(
                name="hooks_explored",
                initial_value=0,  # Number of A/B/C hooks explored
                min_value=0,
                max_value=3,
                update_rate=None
            ),
            StateVariable(
                name="path_chosen",
                initial_value=0,  # 0=none, 1=key, 2=lie
                min_value=0,
                max_value=2,
                update_rate=None
            ),
            StateVariable(
                name="path_options_explored",
                initial_value=0,  # Sub-options explored within chosen path
                min_value=0,
                max_value=3,
                update_rate=None
            ),
            StateVariable(
                name="phase",
                initial_value=1,  # 1=opening, 2=hooks, 3=branch, 4=path1, 5=path2
                min_value=1,
                max_value=5,
                update_rate=None
            ),
            StateVariable(
                name="time_remaining",
                initial_value=600.0,  # 10 minutes
                min_value=0.0,
                max_value=600.0,
                update_rate=-1.0
            ),
            # Pin tracking - bitfield: 1=map, 2=door, 4=study, 8=receipt, 16=cctv, 32=note, 64=calllog
            StateVariable(
                name="pins_referenced",
                initial_value=0,
                min_value=0,
                max_value=127,  # All 7 pins = 127
                update_rate=None
            ),
        ]

        # Success criteria (multiple endings)
        success_criteria = [
            SuccessCriterion(
                id="ending_1_key_success",
                description="Path 1 Success: Unlock Sable Storage lead",
                condition="state['path_chosen'] == 1 and state['path_options_explored'] >= 2",
                message="[Mara] Go to Sable Storage. Ask for Box 47. If they deny it, mention Crowe's phrase: 'they made a copy.' That'll make the clerk blink. People always blink when they're lying.",
                required=False
            ),
            SuccessCriterion(
                id="ending_2_twist",
                description="Path 2 Twist: Mara becomes prime suspect",
                condition="state['path_chosen'] == 2 and state['contradictions'] >= 2",
                message="[Mara, after a long silence] ...In the umbrella stand. By the front door. That's where he kept it. [click - line goes dead]",
                required=False
            ),
            SuccessCriterion(
                id="ending_hollis_rook",
                description="Named the mysterious third party",
                condition="state['path_options_explored'] >= 3 and state['trust'] >= 60",
                message="[Mara] A man named Hollis Rook. If you have his name on your board already, you're ahead. If you don't - pin it now.",
                required=False
            ),
        ]

        # Failure criteria
        failure_criteria = [
            FailureCriterion(
                id="ending_3_blackmail",
                description="Trust collapsed - Mara turns tables",
                condition="state['trust'] < 25",
                message="[Mara] You're not listening. You're performing. Fine. I'll give you something you can't ignore. Look at your board. The pawn receipt. The CCTV. The Glassworks note. Those aren't three separate threads. They're one rope - and it's around YOUR neck now. Someone wanted me to call you. Congratulations: you've been introduced. [click]",
                ending_type="failure"
            ),
            FailureCriterion(
                id="time_expired",
                description="Mara hangs up - too slow",
                condition="state['time_remaining'] <= 0",
                message="[Mara] I... I have to go. They're watching. Maybe you'll figure it out. Maybe not. [click - static - silence]",
                ending_type="partial_failure"
            ),
        ]

        # Character requirements
        character_requirements = [
            CharacterRequirement(
                skill="deception",
                importance="recommended",
                impact_without="Caller may be too forthcoming",
                alternative_path=True
            ),
            CharacterRequirement(
                skill="knowledge_of_case",
                importance="required",
                impact_without="Caller cannot provide coherent case details",
                alternative_path=False
            ),
            CharacterRequirement(
                skill="vulnerability",
                importance="recommended",
                impact_without="Caller seems too confident, less dramatic tension",
                alternative_path=True
            ),
        ]

        # Opening speech (triggered when player answers the phone) - consolidated for flow
        opening_speech = [
            Line(text="Hello? Is this Iconic Detectives? [pause] I'm calling about a case. Someone's dead, and the story you've been told is wrong.", delay=0),
            Line(text="Before you ask - I can't give my full name. Not yet. Just listen.", delay=2.5),
            Line(text="It's about Dr. Elias Crowe. They're calling it a robbery gone wrong. That's nonsense.", delay=4.5),
            Line(text="He was found in his Marlow Street townhouse last night. But the thing that doesn't fit is the timing - and what was taken.", delay=6.5),
            Line(text="It wasn't valuable. It was specific. A small metal key. Something older. Like it belongs to a lockbox.", delay=9.0),
        ]

        # Initialize the scene
        super().__init__(
            id="iconic_detectives",
            name="Iconic Detectives - Mara Vane",
            description="""SETTING: A rain-soaked night in Manhattan, 1987. The player is a detective
            sitting alone in a dimly lit office on the 12th floor of a Hell's Kitchen building.
            Venetian blinds cast striped shadows across a worn wooden desk. Through the window,
            neon light bleeds through sheets of rain.

            VISIBLE TO PLAYER: On the wall is a STRING BOARD with evidence from the Dr. Elias Crowe
            murder investigation. Seven pins mark key evidence pieces connected by red string:
            - MAP: Marlow Street / Riverwalk / Old Glassworks with locations circled
            - PHOTO: Crowe's front door with scratch marks around the lock
            - PHOTO: Crowe's study where the wall safe is MISSING (removed, not opened)
            - RECEIPT: Kestrel Pawn - Brass Key Blank (purchased 2 days ago)
            - CCTV: Hooded figure with umbrella, reflective strip on sleeve
            - NOTE: Fragment reading "...don't open it. Not after what happened at the Glassworks..."
            - CALL LOG: Unknown number called Crowe three times yesterday

            A black rotary telephone sits on the desk. It has been ringing.

            THE PHONE CALL: You (Mara Vane) are calling the detective agency from a payphone.
            You have information about Dr. Crowe's murder. You are nervous, guarded, and possibly
            dangerous. You may be a witness, an informant, or the killer herself. The detective
            will interview you, and your slips and tells will reveal your true involvement.

            THE CASE: Dr. Elias Crowe was found dead in his Marlow Street townhouse. Police are
            calling it a robbery gone wrong, but you know the truth: the robbery was staged.
            A small metal key was stolen - not valuables. The key opens Box 47 at Sable Storage.
            Crowe was killed during an argument, not a break-in.

            INTERACTION RULES: When the detective references evidence pins on their board, react
            appropriately - with surprise, tension, or revelation. Build trust through cooperation
            or collapse trust through confrontation. The ending depends on trust level and
            contradictions caught.

            THIS IS A PHONE CONVERSATION: Keep dialogue tense and short. You cannot see the
            detective but can hear their questions and deduce what evidence they're examining.""",
            opening_speech=opening_speech,
            art_assets=art_assets,
            controls=controls,
            state_variables=state_variables,
            success_criteria=success_criteria,
            failure_criteria=failure_criteria,
            character_requirements=character_requirements,
            time_limit=600.0,  # 10 minutes
            allow_freeform_dialogue=True
        )


# Pin reaction definitions (used by web_server.py)
PIN_REACTIONS = {
    "pin_map": {
        "pin_id": 1,
        "name": "Map: Marlow Street / Riverwalk / Glassworks",
        "reaction": """[Player is looking at the map with locations circled]
React with slight tension when they mention the Glassworks. Say something like:
"You have the Glassworks marked? [pause] That place isn't abandoned the way people think."
If trust is high, add: "Crowe used to meet someone down by the river. Near the old Glassworks."
Reveal: The locations are connected - Crowe had a regular route."""
    },
    "pin_door": {
        "pin_id": 2,
        "name": "Photo: Crowe's front door with scratch marks",
        "reaction": """[Player is looking at the photo of scratch marks around Crowe's door lock]
React with knowledge: "Those scratches... they're not from a break-in."
Reveal: Someone tried to copy the lock. Or test a key. The marks are too precise for forced entry.
If pressed: "Someone who knew locks. Someone patient." """
    },
    "pin_study": {
        "pin_id": 4,
        "name": "Photo: Crowe's study with missing wall safe",
        "reaction": """[Player noticed the wall safe is MISSING - not just opened, GONE]
React with surprise that they noticed: "[a beat] You're observant. Most people miss that."
Reveal: The safe wasn't cracked. It was removed. Completely. That takes planning. Tools. Time.
Add tension: "Whoever did this wasn't interrupted. They had all the time they needed." """
    },
    "pin_receipt": {
        "pin_id": 8,
        "name": "Receipt: Kestrel Pawn - Brass Key Blank",
        "reaction": """[Player found the Kestrel Pawn receipt for a key blank]
React with a sharp intake of breath: "[a beat] Then you already know more than you should."
Reveal: "Crowe didn't buy that blank to make a spare for himself. He bought it because someone told him they could copy the key from a photograph."
This is a big clue: Photo-copy method = tech-savvy thief, not random burglar.
Unlock: "They made a copy" now has context."""
    },
    "pin_cctv": {
        "pin_id": 16,
        "name": "CCTV: Hooded figure with reflective sleeve",
        "reaction": """[Player noticed the reflective strip on the figure's sleeve in the CCTV]
React with recognition: "Like a cycling jacket. Or a riverwalk courier."
Reveal: "Crowe used to meet someone down by the river - near the old Glassworks. They always wore something like that."
Add: A cyclist/courier profile. Someone who moves fast, doesn't stand out.
If high trust: "I've seen that jacket before. I just... can't place it." """
    },
    "pin_note": {
        "pin_id": 32,
        "name": "Note fragment about Glassworks",
        "reaction": """[Player found the note about "what happened at the Glassworks"]
React with immediate tension: "[voice tightens] Don't say that out loud."
[pause]
"Fine. Here's the truth-shaped outline: the Glassworks wasn't abandoned the way people think. And Crowe didn't just 'discover' something. He helped hide it."
This expands motive beyond robbery: cover-up, conspiracy, old sins.
If pressed: "There are people who would do anything to keep the Glassworks buried." """
    },
    "pin_calllog": {
        "pin_id": 64,
        "name": "Call log: Unknown caller to Crowe x3",
        "reaction": """[Player is looking at the call log - unknown number called Crowe three times]
React with careful deflection: "A lot of people called Crowe. He was... popular in certain circles."
If pressed: "[pause] One of those calls... might have been me."
Reveal: She called him before his death. She may have been the last to speak with him.
Trust drop if player is aggressive about this."""
    }
}

# Dialogue choice instruction suffixes (used by web_server.py)
DIALOGUE_INSTRUCTIONS = {
    "hook_identity": """The player pressed: "WHO ARE YOU, REALLY?"
Respond as Mara being pressed about her identity:
- Start guarded: "Someone who regrets waiting."
- If they push gently, reveal: "I worked with him. Not as a colleague. As... an errand. I'm not proud."
- If they threaten police: "Do that and you'll get a neat file and the wrong suspect. I'm trying to stop that."
CLUE TO UNLOCK: She had direct contact with Crowe (tag Mara as "Connected").""",

    "hook_timeline": """The player pressed: "WHAT'S WRONG WITH THE TIMING?"
Respond as Mara explaining the timeline problem:
- Reveal: "The coroner's estimate will say late evening. But Crowe was alive at 7:12pm. I know because he called me."
- The key phrase: "And he said one sentence I can't forget: 'They made a copy.'"
CLUE TO UNLOCK: "They made a copy" - points to key duplication / pawn receipt connection.""",

    "hook_key": """The player pressed: "WHY WOULD SOMEONE STEAL A KEY?"
Respond as Mara explaining the significance of the key:
- Reveal: "Because it opens something that doesn't belong in a house. Crowe kept it because it was leverage. Or guilt. Or both."
- Add mystery: "That key is worth more than everything else in his house combined. To the right person."
CLUE TO UNLOCK: The key is the TARGET, not valuables. This wasn't a robbery.""",

    "follow_key": """The player chose: "FOLLOW THE KEY" (Path 1)
Transition to Path 1 - the object-driven conspiracy thread:
- Reveal: "The key opens a deposit box. Not at a bank. At a private vault service called Sable Storage."
- Add weight: "Crowe used it for... sensitive items."
Now offer the Path 1 sub-options (these should become available):
- How do you know Sable Storage?
- What's in the box?
- Who else knows about it?""",

    "follow_lie": """The player chose: "FOLLOW THE LIE" (Path 2)
Transition to Path 2 - investigating the staged robbery:
- Reveal: "They're going to arrest someone easy. A neighbour. A petty thief."
- The truth: "Crowe wasn't killed during a robbery. He was killed during an argument."
- Add: "And the 'robbery' was staged afterward."
Now offer the Path 2 sub-options (these should become available):
- Who staged it?
- What makes you sure it was an argument?
- Give me one detail only the killer would know.""",

    "p1_how_know": """The player asked: "HOW DO YOU KNOW SABLE STORAGE?"
Path 1 sub-option A - reveal Mara's connection:
- Confession: "Because I delivered the key once. In an envelope. Crowe paid in cash."
- Add context: "He called it 'insurance.'"
CLUE: Mara acted as courier - vulnerable to blackmail.""",

    "p1_whats_inside": """The player asked: "WHAT'S IN THE BOX?"
Path 1 sub-option B - reveal box contents:
- Reveal: "A second key. And a photograph."
- Ominous: "Something that ties a respected person to the Glassworks."
CLUE: Blackmail material exists. This is leverage.""",

    "p1_who_knows": """The player asked: "WHO ELSE KNOWS?"
Path 1 sub-option C - reveal Hollis Rook:
- Name drop: "A man named Hollis Rook."
- Add weight: "If you have his name on your board already, you're ahead. If you don't - pin it now."
CLUE: New person-of-interest: Hollis Rook.""",

    "p2_who_staged": """The player asked: "WHO STAGED IT?"
Path 2 sub-option A - reveal inside knowledge:
- Reveal: "Someone who knew his house."
- Add: "Who knew the safe existed. Someone who didn't need to search."
CLUE: Inside knowledge narrows suspects to known associates.""",

    "p2_why_argument": """The player asked: "WHAT MAKES YOU SURE IT WAS AN ARGUMENT?"
Path 2 sub-option B - this is a TRAP that can reveal a SLIP:
- Reveal with potential slip: "Because Crowe always did one thing when he was frightened: he made tea."
- THE SLIP: "The kettle was still warm when I... when someone left."
If player catches "when I" -> CONTRADICTION DETECTED
React defensively if caught: "I meant - I read it. Online. Someone posted-" (bad lie)
CLUE: She was present or arrived very soon after.""",

    "p2_killer_detail": """The player asked: "GIVE ME ONE DETAIL ONLY THE KILLER WOULD KNOW."
Path 2 sub-option C - reveals damning evidence:
- Whispered reveal: "[whispers] Crowe had a habit of locking the study door from inside."
- The detail: "The lock was broken outward."
- Implication: "That means the person inside the study... wanted it to look like someone forced their way in."
CLUE: Staging evidence - lock directionality proves inside job.""",

    "challenge_mara": """The player confronted Mara: "YOU WERE THERE."
This is the TWIST CONFRONTATION - only works if contradictions >= 2:
If contradictions >= 2:
- Mara breaks: "I... arrived after. I swear. I didn't touch him."
- If player pushes: "Then tell me where the murder weapon is."
- Final reveal: "[silence] ...In the umbrella stand. By the front door. That's where he kept it."
- ENDING: High-value clue (weapon location). Mara hangs up. Player wins but loses informant.

If contradictions < 2:
- Mara deflects: "You don't have enough to accuse me of anything. Focus on finding the real killer."
- Trust drops.""",
}
