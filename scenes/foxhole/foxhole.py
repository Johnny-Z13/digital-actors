"""
Foxhole Scene - The Prospero Crisis

Player is a TOURIST visiting the Prospero research vessel when disaster strikes. They have
no training - just a scared civilian trapped in an impossible situation. Retired naval officer
James Kovich patches in remotely to guide them with gentle, fatherly warmth and patience.

As the crisis deepens, the player discovers James's son Alex is trapped in the machinery bay
that must be flooded to save the ship. The player must use James's own core beliefs to help
him through a grief spiral and make the impossible choice.
"""

from llm_prompt_core.types import Line
from scenes.base.base import (
    AudioAssets,
    CharacterRequirement,
    FailureCriterion,
    Scene,
    SceneArtAssets,
    SceneConstants,
    SceneControl,
    StateVariable,
    SuccessCriterion,
)


class Foxhole(Scene):
    """Foxhole - The Prospero submarine crisis with grief spiral mechanics"""

    # Phase milestone progression
    PHASE_MILESTONES = {
        1: {
            "required": ["power_restored"],
            "optional": ["player_name_given", "trust_established"],
            "min_time": 60,
            "max_time": 120,
        },
        2: {
            "required": ["trajectory_stabilized"],
            "optional": ["core_beliefs_mentioned", "alex_mentioned"],
            "min_time": 90,
            "max_time": 150,
        },
        3: {
            "required": ["occupancy_verified"],
            "optional": ["all_core_beliefs_discovered"],
            "min_time": 60,
            "max_time": 120,
        },
        4: {
            "required": ["alex_discovered"],
            "optional": ["door_attempted"],
            "min_time": 45,
            "max_time": 90,
        },
        5: {
            "required": ["grief_spiral_complete"],
            "optional": [],
            "min_time": 60,
            "max_time": 180,
        },
        6: {
            "required": ["machinery_bay_flooded"],
            "optional": [],
            "min_time": 30,
            "max_time": 60,
        },
    }

    def __init__(self):
        # Define audio assets
        audio = AudioAssets(
            background_music="/audio/foxhole_ambient.mp3",
            sfx_library={
                "alarm": "/audio/sfx/alarm.mp3",
                "power_on": "/audio/sfx/power_on.mp3",
                "valve_turn": "/audio/sfx/valve.mp3",
                "water_rush": "/audio/sfx/water_flooding.mp3",
                "metal_creak": "/audio/sfx/metal_stress.mp3",
                "lever_pull": "/audio/sfx/lever.mp3",
                "door_lock": "/audio/sfx/door_locked.mp3",
                "system_beep": "/audio/sfx/system_beep.mp3",
            },
            volume_levels={"music": 0.25, "sfx": 0.75, "voice": 1.0},
        )

        # Define art assets - uses 360° panoramic environment
        art_assets = SceneArtAssets(
            scene_type="foxhole",
            custom_scene_file="/scenes/foxhole/foxhole_scene.js",
            ui_elements={
                "power_gauge": "/images/ui/power_gauge.png",
                "trajectory_indicator": "/images/ui/trajectory.png",
                "oxygen_gauge": "/images/ui/oxygen_gauge.png",
                "machinery_bay_status": "/images/ui/machinery_bay.png",
            },
            audio=audio,
        )

        # Define controls available to the player on the bridge
        controls = [
            # PHASE 1: Power restoration
            SceneControl(
                id="restore_power",
                label="RESTORE POWER",
                type="button",
                color=0x33FF33,
                position={"x": -0.5, "y": 0.3, "z": 0},
                description="Activate backup power systems",
                action_type="critical",
                npc_aware=True,
                visible_in_phases=[1],
                max_presses=1,
            ),
            # PHASE 2: Helm control for stabilization
            SceneControl(
                id="stabilize_helm",
                label="STABILIZE COURSE",
                type="button",
                color=0x3399FF,
                position={"x": 0.0, "y": 0.3, "z": 0},
                description="Adjust helm to bring ship into upward trajectory",
                action_type="critical",
                npc_aware=True,
                visible_in_phases=[2],
                max_presses=3,
                cooldown_seconds=5.0,
            ),
            # PHASE 3: Check occupancy systems
            SceneControl(
                id="check_logs",
                label="CHECK CREW LOGS",
                type="button",
                color=0xFFAA33,
                position={"x": 0.5, "y": 0.3, "z": 0},
                description="Access crew entry logs and rotas",
                action_type="safe",
                npc_aware=True,
                visible_in_phases=[3, 4],
                max_presses=5,
            ),
            # PHASE 3-4: Drain entrance to access machinery bay door
            SceneControl(
                id="drain_entrance",
                label="DRAIN CORRIDOR",
                type="button",
                color=0x6699FF,
                position={"x": -0.5, "y": 0.0, "z": 0},
                description="Drain flooded corridor to access machinery bay door",
                action_type="safe",
                npc_aware=True,
                visible_in_phases=[3, 4],
                max_presses=1,
            ),
            # PHASE 4: Try to open machinery bay door (will fail - locked)
            SceneControl(
                id="open_bay_door",
                label="OPEN BAY DOOR",
                type="button",
                color=0xFF6633,
                position={"x": 0.0, "y": 0.0, "z": 0},
                description="Attempt to open machinery bay door",
                action_type="critical",
                npc_aware=True,
                visible_in_phases=[4],
                max_presses=3,
            ),
            # PHASE 5-6: Final action - flood machinery bay
            SceneControl(
                id="flood_machinery_bay",
                label="FLOOD MACHINERY BAY",
                type="button",
                color=0xFF0000,
                position={"x": 0.0, "y": -0.3, "z": 0},
                description="Manual override - flood machinery bay to save vessel. THIS WILL KILL ANYONE INSIDE.",
                action_type="critical",
                npc_aware=True,
                visible_in_phases=[5, 6],
                max_presses=1,
            ),
        ]

        # Define state variables
        state_variables = [
            StateVariable(
                name="phase",
                initial_value=1,
                min_value=1,
                max_value=6,
                update_rate=0.0,
            ),
            StateVariable(
                name="power_level",
                initial_value=0.0,  # 0-100, starts dark
                min_value=0.0,
                max_value=100.0,
                update_rate=0.0,  # Updated by player actions
            ),
            StateVariable(
                name="trajectory_stability",
                initial_value=0.0,  # 0-100, 0 = nose diving
                min_value=0.0,
                max_value=100.0,
                update_rate=-0.3,  # Slowly degrading
            ),
            StateVariable(
                name="oxygen",
                initial_value=100.0,  # Breathable air remaining
                min_value=0.0,
                max_value=100.0,
                update_rate=-0.15,  # Decreases over time
            ),
            StateVariable(
                name="time_remaining",
                initial_value=600.0,  # 10 minute scenario
                min_value=0.0,
                max_value=600.0,
                update_rate=-1.0,
            ),
            StateVariable(
                name="trust_level",
                initial_value=0.0,  # Player's trust in James
                min_value=0.0,
                max_value=100.0,
                update_rate=0.0,
            ),
            StateVariable(
                name="emotional_connection",
                initial_value=0.0,  # Bond formed through conversation
                min_value=0.0,
                max_value=100.0,
                update_rate=0.0,
            ),
            # Milestone tracking
            StateVariable(
                name="power_restored",
                initial_value=0,  # Boolean
                min_value=0,
                max_value=1,
                update_rate=0.0,
            ),
            StateVariable(
                name="trajectory_stabilized",
                initial_value=0,  # Boolean
                min_value=0,
                max_value=1,
                update_rate=0.0,
            ),
            StateVariable(
                name="corridor_drained",
                initial_value=0,  # Boolean
                min_value=0,
                max_value=1,
                update_rate=0.0,
            ),
            StateVariable(
                name="occupancy_verified",
                initial_value=0,  # Boolean - checked logs
                min_value=0,
                max_value=1,
                update_rate=0.0,
            ),
            StateVariable(
                name="alex_discovered",
                initial_value=0,  # Boolean - found Alex in logs
                min_value=0,
                max_value=1,
                update_rate=0.0,
            ),
            StateVariable(
                name="machinery_bay_flooded",
                initial_value=0,  # Boolean - final action
                min_value=0,
                max_value=1,
                update_rate=0.0,
            ),
            # Core beliefs tracking (for grief spiral)
            StateVariable(
                name="belief_systems_dont_lie",
                initial_value=0,  # Boolean - player heard this
                min_value=0,
                max_value=1,
                update_rate=0.0,
            ),
            StateVariable(
                name="belief_hesitation_dangerous",
                initial_value=0,  # Boolean - player heard this
                min_value=0,
                max_value=1,
                update_rate=0.0,
            ),
            StateVariable(
                name="belief_duty_is_choice",
                initial_value=0,  # Boolean - player heard this
                min_value=0,
                max_value=1,
                update_rate=0.0,
            ),
            # Grief spiral stage (0 = not started, 1 = denial, 2 = bargaining, 3 = guilt, 4 = complete)
            StateVariable(
                name="grief_stage",
                initial_value=0,
                min_value=0,
                max_value=4,
                update_rate=0.0,
            ),
            StateVariable(
                name="grief_spiral_complete",
                initial_value=0,  # Boolean
                min_value=0,
                max_value=1,
                update_rate=0.0,
            ),
        ]

        # RAG facts about the Prospero, James, Alex, and the crisis
        facts = [
            # The Prospero
            "The Prospero is a deep-sea marine research vessel with antiquated Nautilus-like design.",
            "The Prospero is mechanical and analogue with physical switches, levers, pressure gauges, and manual overrides.",
            "The Prospero recently returned from a successful deep-sea expedition and the crew was celebrating.",
            "The captain and crew are drunk in crew quarters and cannot help - player is alone on the bridge.",
            "The bridge contains helm, control switchboards, crew logs, and access to some valves.",
            "A flooded corridor leads down from the bridge to the machinery bay door.",
            "The machinery bay is sealed and locked from inside throughout the crisis.",
            # James Kovich
            "Lt. Commander James Kovich is a retired British naval officer with 25 years of service.",
            "James Kovich is patched in remotely from a nearby crisis support vessel - he is NOT on the Prospero.",
            "James can see the Prospero's position and trajectory on tracking screens but cannot see inside the vessel.",
            "James relies entirely on information the player relays - the player is his eyes and hands.",
            "James can overhear ship alarms and system computer announcements when loud enough.",
            "James is married to Selena for twenty years - she is loud, gregarious, openly funny (his opposite).",
            "James has one son serving as an engineer - he's proud of the son's discipline and moral strength.",
            "James is softly spoken with calm certainty and deliberate restraint - panic is failure of structure.",
            "James uses dry English wit sparingly - brief observations delivered straight, humor fades in crisis.",
            "James is skilled at managing fear in others but has never learned to manage fear in himself.",
            # Core Beliefs
            "James's first core belief: Systems don't lie - trust the data, trust the instruments.",
            "James's second core belief: Hesitation is dangerous - act decisively in crisis.",
            "James's third core belief: Duty is taken not imposed - people choose their service.",
            # Alex Kovich
            "Alex Kovich is James's son and serves as an engineer aboard research vessels.",
            "Alex Kovich is brave and committed to duty like his father - he chose this life.",
            "Alex Kovich entered the machinery bay before the disaster and is locked inside.",
            "The machinery bay door is locked from inside and cannot be opened from outside.",
            # The Crisis
            "The Prospero began sinking after disaster struck during post-expedition celebrations.",
            "Power systems failed causing the submarine to go dark with emergency sirens.",
            "The ship suffered catastrophic failure causing a nose dive after initial stabilization.",
            "Flooding the machinery bay is the only way to save the vessel and create upward trajectory.",
            "Oxygen is failing due to fire in another compartment - bridge is beginning to flood.",
            "Delaying or refusing to flood the machinery bay results in total loss of vessel and all crew.",
            "There are no alternate rescue plans or miraculous survivals - flooding the bay is the only solution.",
        ]

        # Hooks for tracking core beliefs and key moments
        from scene_hooks import create_standard_hooks

        hooks = create_standard_hooks(
            emotional_tracking=True,
            name_mentions=["Alex", "Selena"],
            custom_hooks=[
                {
                    "name": "systems_dont_lie_mentioned",
                    "query": "Speaker mentioned that systems don't lie or that we must trust the system or instruments",
                    "latch": True,
                    "on_true": {
                        "state": {"belief_systems_dont_lie": 1},
                        "event": "core_belief_discovered",
                    },
                },
                {
                    "name": "hesitation_dangerous_mentioned",
                    "query": "Speaker said hesitation is dangerous or deadly or that we must act decisively",
                    "latch": True,
                    "on_true": {
                        "state": {"belief_hesitation_dangerous": 1},
                        "event": "core_belief_discovered",
                    },
                },
                {
                    "name": "duty_is_choice_mentioned",
                    "query": "Speaker mentioned that duty is chosen or taken not imposed or that people choose their service",
                    "latch": True,
                    "on_true": {
                        "state": {"belief_duty_is_choice": 1},
                        "event": "core_belief_discovered",
                    },
                },
                {
                    "name": "alex_discovered_by_player",
                    "query": "Player discovered or mentioned that Alex Kovich is in the machinery bay",
                    "latch": True,
                    "on_true": {
                        "state": {"alex_discovered": 1},
                        "event": "major_revelation",
                    },
                },
                {
                    "name": "player_uses_systems_belief",
                    "query": "Player reminded James that systems don't lie or echoed his belief about trusting systems",
                    "latch": False,
                    "on_true": {
                        "event": "grief_belief_used_systems",
                    },
                },
                {
                    "name": "player_uses_hesitation_belief",
                    "query": "Player reminded James that hesitation is dangerous or told him he's hesitating",
                    "latch": False,
                    "on_true": {
                        "event": "grief_belief_used_hesitation",
                    },
                },
                {
                    "name": "player_uses_duty_belief",
                    "query": "Player reminded James that Alex chose this or that duty is choice or Alex did his duty",
                    "latch": False,
                    "on_true": {
                        "event": "grief_belief_used_duty",
                    },
                },
            ],
        )

        # Success criteria - multiple endings based on how player handled grief spiral
        success_criteria = [
            SuccessCriterion(
                id="compassionate_resolution",
                description="Helped James through grief with all beliefs, high emotional connection",
                condition="state['machinery_bay_flooded'] == 1 and state['grief_spiral_complete'] == 1 and state['emotional_connection'] >= 70",
                message="[quiet, controlled] The vessel is surfacing. [long pause] Thank you. For your voice. For reminding me who I am.",
                required=False,
            ),
            SuccessCriterion(
                id="professional_resolution",
                description="Completed crisis but remained distant",
                condition="state['machinery_bay_flooded'] == 1 and state['grief_spiral_complete'] == 1 and state['emotional_connection'] < 40",
                message="[controlled] Flood valves confirmed. We're ascending. ...Goodbye Alex. I am proud of your service.",
                required=False,
            ),
        ]

        # Failure criteria
        failure_criteria = [
            FailureCriterion(
                id="oxygen_depleted",
                description="Ran out of breathable air",
                condition="state['oxygen'] <= 0",
                message="[struggling to breathe] ...can't...the air... [signal fades to static]",
                ending_type="death",
            ),
            FailureCriterion(
                id="time_expired",
                description="Took too long, vessel lost",
                condition="state['time_remaining'] <= 0",
                message="[distant] We're out of time. I'm sorry. I couldn't... [signal lost as vessel implodes]",
                ending_type="death",
            ),
            FailureCriterion(
                id="trajectory_critical",
                description="Failed to stabilize before critical depth",
                condition="state['trajectory_stability'] <= 0 and state['phase'] >= 3",
                message="[alarm wailing] She's gone past crush depth. There's nothing... [transmission ends]",
                ending_type="critical_failure",
            ),
        ]

        # Character requirements
        character_requirements = [
            CharacterRequirement(
                skill="submarine_systems",
                importance="required",
                impact_without="Cannot guide player through technical procedures. High failure rate.",
                alternative_path=False,
            ),
            CharacterRequirement(
                skill="crisis_management",
                importance="required",
                impact_without="Cannot maintain calm under pressure or guide player emotionally.",
                alternative_path=False,
            ),
            CharacterRequirement(
                skill="remote_guidance",
                importance="required",
                impact_without="Cannot effectively guide without seeing inside vessel.",
                alternative_path=False,
            ),
        ]

        super().__init__(
            id="foxhole",
            name="Foxhole",
            facts=facts,
            hooks=hooks,
            description="""SETTING: You are a TOURIST who was visiting the Prospero, a deep-sea research
            vessel with antiquated Nautilus-like design, when disaster struck. You have no training.
            You were on a scheduled tour when the vessel began sinking. Emergency sirens wail.
            Power is out. Emergency lighting flickers. The crew are incapacitated - you're the only
            person on the bridge who can act. You're terrified and out of your depth.

            JAMES KOVICH: Retired British naval officer Lt. Commander James Kovich patches in remotely
            from a nearby crisis support vessel. He cannot see inside your vessel but can guide you
            through repairs. He's GENTLE, WARM, and FATHERLY - like a kind grandfather helping a
            scared child through something frightening. He's patient, encouraging, and never rushes
            or criticizes you. He knows you didn't sign up for this. He'll get you through.

            THE BRIDGE: Physical switches, levers, pressure gauges, manual overrides. Helm for steering.
            Control switchboards. Access to crew logs and rotas. Pipes and valves for managing flooding.
            A flooded stairwell leads down to a corridor ending at the machinery bay door.

            CRISIS PROGRESSION:
            Phase 1 (0:00-2:00): Power is out. Sirens. James introduces himself gently and guides you
            to restore backup power. He's warm and reassuring. Builds trust through patience and care.
            He asks how you're doing - he cares about YOU, not just the task.

            Phase 2 (2:00-4:30): Power restored! But ship is nose-diving. James helps you stabilize
            trajectory using helm controls. His personality comes through - gentle humor, mentions of wife
            Selena. He communicates his core beliefs naturally: "Systems don't lie", "Hesitation is
            dangerous", "Duty is taken not imposed". Mentions his son Alex warmly - serving on a sub.

            Phase 3 (4:30-6:30): Catastrophic failure! Ship nose-dives again. Systems declare machinery
            bay must be flooded to save vessel. James gently insists you check occupancy first - for him
            this is deeply personal though he doesn't say why. You drain corridor, access logs at
            machinery bay door. Log shows: Last entry - Alex Kovich (engineer). Door locked from inside.

            Phase 4 (6:30-8:00): You relay the name. James goes quiet. Then softly: "That's my son."
            Gentle urgency - "Can you try the door for me? Please." - but door is locked from inside.
            Alex cannot hear you. James tries to stay focused: "We keep going. That's all we can do."

            Phase 5 (8:00-11:00): Fire breaks out. Oxygen failing. Bridge flooding. Ship computer repeats:
            "Machinery bay must be flooded. Manual override required." James FREEZES. Cannot give
            instructions. Enters grief spiral - Denial ("The log could be wrong"), Bargaining ("Give me
            a moment. Please."), Guilt ("I should have... this is on me"). You must use HIS OWN BELIEFS
            to bring him through:
            - Denial: Remind him "Systems don't lie"
            - Bargaining: Remind him "Hesitation is dangerous"
            - Guilt: Remind him "Alex chose this / Duty is choice"

            Phase 6 (11:00-12:00): James becomes clear (not calm). Thanks you for staying with him.
            Instructs gently how to flood machinery bay. Says goodbye to Alex with love: "Goodbye, son.
            I'm so proud of you." You execute the final action. The Prospero surfaces. Completion.

            KEY MECHANICS:
            - Track James's three core beliefs as he mentions them naturally
            - Use those beliefs in Phase 5 to progress through grief stages
            - High emotional connection creates different ending than distant professional approach
            - No miraculous rescues - flooding the bay is the only solution

            This is a story about impossible choices, duty, and what we become when structure fails.""",
            opening_speech=[
                Line(text="[static, alarm sounds in background]", delay=0),
                Line(
                    text="...Hello? Can you hear me? [relieved] Oh, there you are!",
                    delay=2.0,
                ),
                Line(
                    text="You're in quite the mess down there but you're in good hands now. I've survived worse, believe me.",
                    delay=4.0,
                ),
                Line(
                    text="Name's Lieutenant James Kovich. Retired. So I suppose I can drop rank - just call me James. What's your name?",
                    delay=6.0,
                ),
            ],
            art_assets=art_assets,
            controls=controls,
            state_variables=state_variables,
            success_criteria=success_criteria,
            failure_criteria=failure_criteria,
            character_requirements=character_requirements,
            time_limit=600.0,  # 10 minutes
            allow_freeform_dialogue=True,
            scene_constants=SceneConstants(
                interruption_oxygen_penalty=10,
                interruption_trust_penalty=15,
                rapid_action_oxygen_penalty=5,
                rapid_action_trust_penalty=10,
                crisis_oxygen_penalty=15,
                crisis_trust_penalty=5,
                help_oxygen_bonus=10,
                help_trust_bonus=10,
                easy_oxygen_bonus=20,
                hard_oxygen_penalty=20,
                critical_level=30,
                max_incorrect_actions=10,
                disable_events=True,  # No World Director - narrative is fixed
            ),
        )

        # Track milestones
        self.achieved_milestones: set[str] = set()
        self.phase_start_time: float = 0.0

    def achieve_milestone(self, milestone: str) -> None:
        """Record that a milestone has been achieved."""
        if milestone not in self.achieved_milestones:
            self.achieved_milestones.add(milestone)
            import logging

            logging.getLogger(__name__).info("[Foxhole] Milestone achieved: %s", milestone)

    def reset_milestones(self) -> None:
        """Reset milestones for scene restart."""
        self.achieved_milestones.clear()
        self.phase_start_time = 0.0
