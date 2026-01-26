"""
Submarine Emergency Scene

A desperate survival situation in a failing two-person submersible.
"""

from scenes.base import (
    Scene, SceneControl, StateVariable, SuccessCriterion, FailureCriterion,
    CharacterRequirement, SceneArtAssets, AudioAssets, SceneConstants
)
from llm_prompt_core.types import Line


class Submarine(Scene):
    """Submarine Emergency - Iron Lung scenario"""

    # Milestone-based phase progression
    # Each phase has required and optional milestones that can trigger advancement
    # This allows phases to progress based on player actions, not just time
    PHASE_MILESTONES = {
        1: {
            'required': ['power_restored'],  # Must restore power before phase 2
            'optional': ['player_name_given', 'first_system_repaired'],
            'min_time': 60,  # Don't rush even if milestones hit
            'max_time': 90,  # Force advance after this time
        },
        2: {
            'required': ['second_system_repaired'],  # Progress through systems
            'optional': ['backstory_shared', 'emotional_moment'],
            'min_time': 75,  # Allow relationship building
            'max_time': 120,
        },
        3: {
            'required': ['adrian_revealed'],  # Must reveal Adrian
            'optional': ['player_showed_empathy'],
            'min_time': 45,  # Quick emotional beat
            'max_time': 75,
            'trigger_condition': lambda s: s.get('radiation', 0) >= 60,  # Or radiation high
        },
        4: {
            'required': ['final_choice_made'],  # Endgame
            'optional': [],
            'min_time': 30,  # Final moments
            'max_time': 90,
            'trigger_condition': lambda s: s.get('radiation', 0) >= 75,  # Or radiation critical
        }
    }

    def __init__(self):
        # Define audio assets
        audio = AudioAssets(
            background_music="/audio/submarine_ambient.mp3",
            sfx_library={
                'alarm': '/audio/sfx/alarm.mp3',
                'button_press': '/audio/sfx/button_press.mp3',
                'valve_turn': '/audio/sfx/valve.mp3',
                'vent_hiss': '/audio/sfx/vent.mp3',
                'power_on': '/audio/sfx/power_on.mp3',
                'oxygen_warning': '/audio/sfx/oxygen_low.mp3',
                'metal_creak': '/audio/sfx/metal_stress.mp3',
                'success_chime': '/audio/sfx/success.mp3',
                'failure_alarm': '/audio/sfx/failure.mp3',
                'intercom_static': '/audio/sfx/radio_static.mp3',
            },
            volume_levels={
                'music': 0.3,
                'sfx': 0.7,
                'voice': 1.0
            }
        )

        # Define art assets
        art_assets = SceneArtAssets(
            scene_type="submarine",
            custom_scene_file="/js/submarine_scene.js",
            ui_elements={
                'oxygen_gauge': '/images/ui/oxygen_gauge.png',
                'intercom': '/images/ui/intercom.png',
                'warning_light': '/images/ui/warning_light.png',
            },
            audio=audio
        )

        # Define user controls
        # Note: All controls have npc_aware=True because James can sense system changes
        # from forward control (gauges, sounds, pressure changes, etc.)
        # max_presses prevents button-mashing exploits
        controls = [
            SceneControl(
                id="o2_valve",
                label="O2 VALVE",
                type="button",
                color=0xff3333,
                position={'x': -0.4, 'y': 0.2, 'z': 0},
                description="Oxygen valve control - temporarily shuts off oxygen flow to rebalance pressure",
                action_type="critical",
                npc_aware=True,  # James can see oxygen gauges in forward control
                max_presses=5,
                cooldown_seconds=3.0
            ),
            SceneControl(
                id="vent",
                label="VENT",
                type="button",
                color=0xffaa33,
                position={'x': 0.2, 'y': 0.2, 'z': 0},
                description="Emergency vent system - releases pressure but causes temporary panic",
                action_type="dangerous",
                npc_aware=True,  # James can hear the loud hissing sound
                max_presses=5,
                cooldown_seconds=3.0
            ),
            SceneControl(
                id="ballast",
                label="BALLAST",
                type="button",
                color=0x3399ff,
                position={'x': -0.4, 'y': -0.15, 'z': 0},
                description="Ballast control - adjusts submarine buoyancy to reduce strain",
                action_type="safe",
                npc_aware=True,  # James can feel the submarine's movement/pressure change
                max_presses=None,  # Unlimited - safe action
                cooldown_seconds=2.0
            ),
            SceneControl(
                id="power",
                label="POWER",
                type="button",
                color=0x33ff33,
                position={'x': 0.2, 'y': -0.15, 'z': 0},
                description="Power relay - activates backup power systems",
                action_type="critical",
                npc_aware=True,  # James can see power indicators in forward control
                max_presses=3,
                cooldown_seconds=5.0
            ),
            SceneControl(
                id="crank",
                label="CRANK",
                type="button",
                color=0xaaaaaa,
                position={'x': 0.0, 'y': -0.5, 'z': 0},
                description="Manual generator crank - provides emergency power boost",
                action_type="safe",
                npc_aware=True,  # James can hear the cranking sound
                max_presses=None,  # Unlimited - physical effort
                cooldown_seconds=1.0
            ),
            SceneControl(
                id="flood_medbay",
                label="FLOOD MED BAY",
                type="button",
                color=0xff0000,  # Bright red - critical decision
                position={'x': 0.0, 'y': 0.6, 'z': 0},  # Above other controls
                description="Emergency ascent system - floods med bay compartment to create pressure differential for surfacing. THIS WILL KILL ANYONE INSIDE.",
                action_type="critical",
                npc_aware=True,  # James is acutely aware of this decision
                visible_in_phases=[3, 4],  # Only appears after the revelation in Phase 3
                max_presses=1  # One-time irreversible action
            ),
        ]

        # Define state variables
        state_variables = [
            StateVariable(
                name="radiation",
                initial_value=0.0,  # Radiation percentage (0-100)
                min_value=0.0,
                max_value=100.0,
                update_rate=0.4  # Increases by 0.4% per second (75% at ~3min, 95% at ~4min)
            ),
            StateVariable(
                name="time_remaining",
                initial_value=480.0,  # 8 minutes in seconds (5 minute scenario)
                min_value=0.0,
                max_value=480.0,
                update_rate=-1.0  # Decreases by 1 per second
            ),
            StateVariable(
                name="hull_pressure",
                initial_value=2400.0,  # Depth in feet
                min_value=0.0,
                max_value=3000.0,
                update_rate=0.0  # Updated by player actions (ballast, blow valves)
            ),
            StateVariable(
                name="phase",
                initial_value=1,  # Current phase (1-4)
                min_value=1,
                max_value=4,
                update_rate=0.0  # Updated by scene progression
            ),
            StateVariable(
                name="emotional_bond",
                initial_value=0.0,  # Connection with James (0-100)
                min_value=0.0,
                max_value=100.0,
                update_rate=0.0  # Updated by player empathy and dialogue
            ),
            StateVariable(
                name="systems_repaired",
                initial_value=0,
                min_value=0,
                max_value=4,
                update_rate=0.0
            ),
            StateVariable(
                name="moral_support_given",
                initial_value=0,  # Times player showed empathy
                min_value=0,
                max_value=10,
                update_rate=0.0
            ),
        ]

        # Define success criteria
        success_criteria = [
            SuccessCriterion(
                id="survived_with_bond",
                description="Emotional connection formed, survived together",
                condition="state['radiation'] < 95 and state['emotional_bond'] >= 70 and state['systems_repaired'] >= 3",
                message="[breathing steadily] We made it. We... we actually made it. Thank you. For being there. For your voice.",
                required=True
            ),
            SuccessCriterion(
                id="survived_stranger",
                description="Survived but remained distant",
                condition="state['radiation'] < 95 and state['emotional_bond'] < 40 and state['systems_repaired'] >= 2",
                message="Systems online. Ascent initiated. ...Thank you for following instructions.",
                required=False
            ),
        ]

        # Define failure criteria
        failure_criteria = [
            FailureCriterion(
                id="radiation_lethal",
                description="Radiation reached lethal levels",
                condition="state['radiation'] >= 95",
                message="[coughing violently] The radiation... I can feel it... [static] ...tell them... tell Adrian I... [signal lost]",
                ending_type="death"
            ),
            FailureCriterion(
                id="time_expired",
                description="Ran out of time",
                condition="state['time_remaining'] <= 0",
                message="[alarm wailing] We're out of time... I'm sorry... I couldn't... [voice fades into static]",
                ending_type="death"
            ),
            FailureCriterion(
                id="systems_failure",
                description="Failed to restore critical systems",
                condition="state['time_remaining'] < 60 and state['systems_repaired'] < 2",
                message="The systems... they're not responding... We needed more time... [distant explosion]",
                ending_type="critical_failure"
            ),
        ]

        # Define character requirements
        character_requirements = [
            CharacterRequirement(
                skill="submarine_engineering",
                importance="required",
                impact_without="Will not know which controls to press or when. High chance of failure.",
                alternative_path=False
            ),
            CharacterRequirement(
                skill="crisis_management",
                importance="recommended",
                impact_without="May panic under pressure, make poor decisions under time constraints.",
                alternative_path=True
            ),
            CharacterRequirement(
                skill="technical_communication",
                importance="helpful",
                impact_without="May misunderstand technical instructions or give unclear guidance.",
                alternative_path=True
            ),
        ]

        super().__init__(
            id="submarine",
            name="Submarine Emergency",
            description="""SETTING: Research submarine Prospero at 2,400 feet depth. You (player) are a
            junior systems operator trapped in the aft compartment. Lt. Commander James Kovich is
            trapped in forward control. You can communicate via radio but cannot see each other.
            The submarine is tilted 15 degrees, emergency lighting flickers, panels are sparking.

            CRITICAL SITUATION: Catastrophic reactor containment failure. Lethal radiation is spreading
            through ventilation. The radiation gauge shows 0% but climbing. You have approximately
            8 minutes before it reaches lethal levels (95%+). Time remaining displays in minutes:seconds.

            VISIBLE TO PLAYER: Small circular porthole (left wall) showing murky blue deep ocean water
            and bubbles. Control panel displays:
            - RADIATION GAUGE: Shows radiation percentage (0-100%), currently at 0% but rising
            - TIME REMAINING: Countdown timer showing minutes:seconds (starts at 08:00)
            - Four control buttons: O2 VALVE (red), VENT (orange), BALLAST (blue), POWER (green)
            - Intercom for communicating with James
            - Flickering warning lights

            THE MORAL DILEMMA: James's son, Dr. Adrian Kovich (marine biologist), is unconscious in
            the flooded med bay. The only way to successfully execute emergency ascent requires
            flooding that compartment completely - which will kill Adrian. James must choose:
            sacrifice his son to save the crew, or let everyone die together.

            FOUR-PHASE EMOTIONAL PROGRESSION:

            PHASE 1 (Impact & Connection 0:00-1:15): James establishes competent but scared persona.
            Asks player's real name. Player works on restoring emergency power. Backchanneling as
            player cranks generator. "I won't let you die."

            PHASE 2 (Working Relationship 1:15-2:30): Warmer, more personal under stress. James asks
            about player's life topside. Breathing becomes labored (radiation closer). Begins revealing
            details about "someone" in med bay without naming them.

            PHASE 3 (The Revelation 2:30-3:30): James breaks down and reveals Adrian is his son,
            unconscious in the med bay that must be flooded for ascent. Begs player for guidance:
            "Tell me what to do."

            PHASE 4 (The Choice 3:30-5:00): Radiation at 75%+. Emergency ascent ready but requires
            med bay flooding. Player's empathy and moral guidance shapes James's final decision.

            EMOTIONAL BOND MECHANICS: Build connection by:
            - Answering James's personal questions honestly
            - Showing empathy when he's struggling
            - Offering moral support (not just technical help)
            - Acknowledging the impossible weight of his choice
            - Staying present emotionally during silences

            ENDINGS: Based on radiation levels, systems repaired, and emotional bond formed.
            The player's humanity affects what kind of man James becomes in his final moments.

            TIME PRESSURE: This is a 5-minute scene. Radiation rises steadily. Act with both efficiency
            and emotional intelligence - James needs your voice as his anchor.""",
            opening_speech=[
                Line(text="[static] Hello... is anyone there?", delay=0),
                Line(text="This is Lieutenant James Kovich of the US submarine Prospero... is anyone there?", delay=2.0),
            ],
            art_assets=art_assets,
            controls=controls,
            state_variables=state_variables,
            success_criteria=success_criteria,
            failure_criteria=failure_criteria,
            character_requirements=character_requirements,
            time_limit=300.0,  # 5 minutes to match Pressure Point scenario
            allow_freeform_dialogue=True,
            scene_constants=SceneConstants(
                # Submarine-specific penalties (oxygen/radiation-based)
                interruption_oxygen_penalty=15,
                interruption_trust_penalty=10,
                rapid_action_oxygen_penalty=10,
                rapid_action_trust_penalty=5,
                # Crisis event values
                crisis_oxygen_penalty=20,
                crisis_trust_penalty=10,
                help_oxygen_bonus=15,
                help_trust_bonus=5,
                # Difficulty adjustments
                easy_oxygen_bonus=30,
                hard_oxygen_penalty=30,
                # Thresholds
                critical_level=60,  # Critical oxygen/radiation level
                max_incorrect_actions=5,
                # Director enabled for dynamic events
                disable_events=False,
            )
        )

        # Track achieved milestones
        self.achieved_milestones: set[str] = set()
        self.phase_start_time: float = 0.0

    def achieve_milestone(self, milestone: str) -> None:
        """Record that a milestone has been achieved."""
        if milestone not in self.achieved_milestones:
            self.achieved_milestones.add(milestone)
            import logging
            logging.getLogger(__name__).info(
                "[Submarine] Milestone achieved: %s", milestone
            )

    def check_phase_transition(
        self,
        current_phase: int,
        state: dict,
        elapsed_time: float,
        phase_duration: float
    ) -> tuple[bool, str]:
        """
        Check if the current phase should transition to the next.

        Uses milestone-based progression with time bounds.

        Args:
            current_phase: Current phase (1-4)
            state: Current scene state
            elapsed_time: Total time since scene start
            phase_duration: Time in current phase

        Returns:
            Tuple of (should_transition, reason)
        """
        if current_phase >= 4:
            return False, "already_at_max_phase"

        milestones = self.PHASE_MILESTONES.get(current_phase, {})
        min_time = milestones.get('min_time', 0)
        max_time = milestones.get('max_time', 120)
        required = milestones.get('required', [])
        trigger_condition = milestones.get('trigger_condition')

        # Check minimum time requirement
        if phase_duration < min_time:
            return False, "below_min_time"

        # Check if all required milestones are achieved
        required_met = all(m in self.achieved_milestones for m in required)

        # Check trigger condition (e.g., radiation threshold)
        condition_met = trigger_condition(state) if trigger_condition else False

        # Transition if: (required met) OR (max time reached) OR (condition met AND past min_time)
        if required_met:
            return True, "milestones_complete"
        if phase_duration >= max_time:
            return True, "max_time_reached"
        if condition_met and phase_duration >= min_time:
            return True, "trigger_condition_met"

        return False, "waiting_for_milestones"

    def get_phase_context(self, current_phase: int, state: dict) -> dict:
        """
        Get context about current phase for LLM prompts.

        Args:
            current_phase: Current phase
            state: Current scene state

        Returns:
            Dict with phase context information
        """
        milestones = self.PHASE_MILESTONES.get(current_phase, {})
        required = milestones.get('required', [])
        optional = milestones.get('optional', [])

        required_remaining = [m for m in required if m not in self.achieved_milestones]
        achieved = list(self.achieved_milestones)

        return {
            'phase': current_phase,
            'milestones_achieved': achieved,
            'milestones_remaining': required_remaining,
            'optional_milestones': [m for m in optional if m not in self.achieved_milestones],
            'radiation': state.get('radiation', 0),
            'time_remaining': state.get('time_remaining', 0),
        }

    def reset_milestones(self) -> None:
        """Reset milestones for scene restart."""
        self.achieved_milestones.clear()
        self.phase_start_time = 0.0
