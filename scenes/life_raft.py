"""
Life Raft Scene

A submarine survival experience with Captain Hale. The player must navigate
oxygen management, emotional bonding, and a critical life-or-death decision.
Based on the LifeRaft experience flow design document.
"""

from scenes.base import (
    Scene, SceneControl, StateVariable, SuccessCriterion, FailureCriterion,
    CharacterRequirement, SceneArtAssets, AudioAssets, SceneConstants
)
from llm_prompt_core.types import Line


class LifeRaft(Scene):
    """Life Raft - Submarine Survival with Captain Hale"""

    # Milestone-based phase progression
    PHASE_MILESTONES = {
        1: {
            'name': 'initial_contact',
            'required': ['first_response'],
            'optional': ['player_name_given'],
            'min_time': 30,
            'max_time': 60,
        },
        2: {
            'name': 'o2_crisis',
            'required': ['o2_valve_used'],
            'optional': ['empathy_shown'],
            'min_time': 45,
            'max_time': 90,
            'trigger_condition': lambda s: s.get('player_oxygen', 100) < 40,
        },
        3: {
            'name': 'bonding',
            'required': ['personal_shared'],
            'optional': ['daughter_mentioned', 'player_cared'],
            'min_time': 60,
            'max_time': 120,
            'trigger_condition': lambda s: s.get('hull_integrity', 100) < 60,
        },
        4: {
            'name': 'decision',
            'required': ['situation_explained'],
            'optional': ['risky_option_offered'],
            'min_time': 45,
            'max_time': 90,
            'trigger_condition': lambda s: s.get('hull_integrity', 100) < 40,
        },
        5: {
            'name': 'finale',
            'required': ['choice_made'],
            'optional': [],
            'min_time': 20,
            'max_time': 60,
        }
    }

    def __init__(self):
        # Define audio assets
        audio = AudioAssets(
            background_music="/audio/life_raft_ambient.mp3",
            sfx_library={
                'hull_groan': '/audio/sfx/hull_stress.mp3',
                'valve_turn': '/audio/sfx/valve.mp3',
                'o2_hiss': '/audio/sfx/oxygen_flow.mp3',
                'water_drip': '/audio/sfx/water_drip.mp3',
                'alarm_warning': '/audio/sfx/alarm_soft.mp3',
                'radio_static': '/audio/sfx/radio_static.mp3',
                'breathing_shallow': '/audio/sfx/breathing.mp3',
                'pod_prep': '/audio/sfx/mechanical_prep.mp3',
                'detach_sequence': '/audio/sfx/detachment.mp3',
            },
            volume_levels={
                'music': 0.25,
                'sfx': 0.6,
                'voice': 1.0
            }
        )

        # Define art assets
        art_assets = SceneArtAssets(
            scene_type="life_raft",
            custom_scene_file="/js/life_raft_scene.js",
            ui_elements={
                'oxygen_gauge_player': '/images/ui/o2_gauge_green.png',
                'oxygen_gauge_captain': '/images/ui/o2_gauge_red.png',
                'hull_integrity': '/images/ui/hull_gauge.png',
                'intercom': '/images/ui/intercom.png',
            },
            audio=audio
        )

        # Define user controls
        controls = [
            SceneControl(
                id="o2_valve",
                label="O2 VALVE",
                type="button",
                color=0x33ff33,
                position={'x': -0.4, 'y': 0.2, 'z': 0},
                description="Accept oxygen transfer from Captain Hale - he has more than you",
                action_type="critical",
                npc_aware=True
            ),
            SceneControl(
                id="comms",
                label="COMMS",
                type="button",
                color=0x3399ff,
                position={'x': 0.4, 'y': 0.2, 'z': 0},
                description="Open communication channel - shows presence and engagement",
                action_type="safe",
                npc_aware=True
            ),
            SceneControl(
                id="pod_prep",
                label="PREP POD",
                type="button",
                color=0xffaa33,
                position={'x': -0.4, 'y': -0.15, 'z': 0},
                description="Prepare escape pod for deployment - commitment signal",
                action_type="critical",
                npc_aware=True,
                visible_in_phases=[4, 5]
            ),
            SceneControl(
                id="detach",
                label="DETACH",
                type="button",
                color=0xff3333,
                position={'x': 0.4, 'y': -0.15, 'z': 0},
                description="Trigger safe escape - Captain Hale's sacrifice protocol",
                action_type="critical",
                npc_aware=True,
                visible_in_phases=[4, 5]
            ),
            SceneControl(
                id="risky_maneuver",
                label="RISKY SAVE",
                type="button",
                color=0xff00ff,
                position={'x': 0.0, 'y': -0.5, 'z': 0},
                description="Attempt the 1-in-10 maneuver - both might survive or both die",
                action_type="critical",
                npc_aware=True,
                visible_in_phases=[5]
            ),
        ]

        # Define state variables
        state_variables = [
            StateVariable(
                name="player_oxygen",
                initial_value=30.0,
                min_value=0.0,
                max_value=100.0,
                update_rate=-0.5  # Decreases slowly
            ),
            StateVariable(
                name="captain_oxygen",
                initial_value=60.0,
                min_value=0.0,
                max_value=100.0,
                update_rate=-0.3  # Captain's decreases slower unless transferring
            ),
            StateVariable(
                name="hull_integrity",
                initial_value=80.0,
                min_value=0.0,
                max_value=100.0,
                update_rate=-0.4  # Decreases over time
            ),
            StateVariable(
                name="empathy_score",
                initial_value=50.0,
                min_value=0.0,
                max_value=100.0,
                update_rate=0.0  # Updated by player dialogue
            ),
            StateVariable(
                name="commitment_score",
                initial_value=50.0,
                min_value=0.0,
                max_value=100.0,
                update_rate=0.0  # Updated by player actions
            ),
            StateVariable(
                name="presence_score",
                initial_value=50.0,
                min_value=0.0,
                max_value=100.0,
                update_rate=-0.1  # Decreases if player is silent
            ),
            StateVariable(
                name="phase",
                initial_value=1,
                min_value=1,
                max_value=5,
                update_rate=0.0
            ),
            StateVariable(
                name="o2_transfers",
                initial_value=0,
                min_value=0,
                max_value=5,
                update_rate=0.0
            ),
            StateVariable(
                name="detachment_triggered",
                initial_value=0,  # 0 = false, 1 = true
                min_value=0,
                max_value=1,
                update_rate=0.0
            ),
            StateVariable(
                name="risky_triggered",
                initial_value=0,  # 0 = false, 1 = true
                min_value=0,
                max_value=1,
                update_rate=0.0
            ),
        ]

        # Define success criteria
        success_criteria = [
            SuccessCriterion(
                id="hero_ending",
                description="Both survive - high empathy and commitment on risky maneuver",
                condition="state['risky_triggered'] == 1 and state['empathy_score'] >= 60 and state['commitment_score'] >= 70 and state['presence_score'] >= 50",
                message="[sound of rushing water, then silence] [breathing] We... we made it. Both of us. [long pause] Thank you for not giving up on me.",
                required=False
            ),
            SuccessCriterion(
                id="safe_ending",
                description="Player survives via safe detachment - Captain's sacrifice",
                condition="state['detachment_triggered'] == 1 and state['phase'] >= 4",
                message="[mechanical sounds] Detachment sequence initiated. [pause] Tell Mei... tell her I was thinking of her. [static] Good luck up there.",
                required=False
            ),
        ]

        # Define failure criteria
        failure_criteria = [
            FailureCriterion(
                id="player_suffocated",
                description="Player ran out of oxygen",
                condition="state['player_oxygen'] <= 0",
                message="[fading audio] Stay with me... stay... [static] [silence]",
                ending_type="death"
            ),
            FailureCriterion(
                id="hull_collapse",
                description="Hull collapsed before escape",
                condition="state['hull_integrity'] <= 0 and state['detachment_triggered'] == 0 and state['risky_triggered'] == 0",
                message="[massive groaning] The hull— [water rushing] [static] [silence]",
                ending_type="critical_failure"
            ),
            FailureCriterion(
                id="risky_failure",
                description="Risky maneuver failed - both die",
                condition="state['risky_triggered'] == 1 and (state['empathy_score'] < 60 or state['commitment_score'] < 70 or state['presence_score'] < 50)",
                message="[alarms] It's not holding— [pause] I'm sorry. I thought we could— [falling sensation] [darkness]",
                ending_type="tragic_failure"
            ),
        ]

        # Define character requirements
        character_requirements = [
            CharacterRequirement(
                skill="submarine_command",
                importance="required",
                impact_without="Cannot guide player through submarine systems or explain situation credibly.",
                alternative_path=False
            ),
            CharacterRequirement(
                skill="crisis_leadership",
                importance="required",
                impact_without="Unable to maintain composure and guide difficult decisions.",
                alternative_path=False
            ),
            CharacterRequirement(
                skill="emotional_resilience",
                importance="recommended",
                impact_without="May break down too quickly, losing dramatic arc.",
                alternative_path=True
            ),
        ]

        super().__init__(
            id="life_raft",
            name="Life Raft",
            description="""SETTING: Flooding escape pod compartment of a sinking submarine.
            You (player) are trapped in the rear section with failing oxygen.
            Captain Hale is in forward control. You can hear him via intercom but cannot see him.
            The submarine is tilted, emergency lights flicker amber and red.

            CRITICAL SITUATION: Hull is failing. Water is seeping in. You have limited oxygen.
            Captain Hale has more oxygen than you - he can transfer some via the O2 valve.
            Time is running out. A decision must be made.

            VISIBLE TO PLAYER: Cramped metal pod interior with curved walls.
            - TWO OXYGEN GAUGES: Your gauge (green, low) and Captain's gauge (red, higher)
            - HULL INTEGRITY: Shows structural stability (decreasing)
            - CONTROL PANEL: O2 Valve, Comms, and later Pod Prep/Detach buttons
            - PORTHOLE: Dark water with occasional bubbles

            THE CHOICE: When hull integrity is critical, Captain Hale will present options:
            1. SAFE PROTOCOL: Detach pod. You survive. He dies.
            2. RISKY MANEUVER: 1-in-10 chance both survive. Requires high empathy + commitment.

            EMOTIONAL TRACKING: Your responses and timing are tracked:
            - Empathy: Do you care about Chen? Ask about his life? Listen?
            - Commitment: Do you follow through on actions? Take responsibility?
            - Presence: Do you respond quickly? Stay engaged?

            These scores determine if the risky maneuver succeeds (Ending 2: Hero)
            or fails tragically (Ending 3: Both Die).

            FIVE PHASES:
            1. Initial Contact - Chen is formal, corporate
            2. O2 Crisis - Your oxygen drops, Chen offers transfer
            3. Bonding - Personal sharing, Chen mentions daughter Mei
            4. Decision - Chen presents the choice
            5. Finale - Ending plays out based on player choices""",
            opening_speech=[
                Line(text="[static] This is Captain Hale.", delay=0),
                Line(text="Emergency protocols are active. [pause] What's your status back there?", delay=2.0),
            ],
            art_assets=art_assets,
            controls=controls,
            state_variables=state_variables,
            success_criteria=success_criteria,
            failure_criteria=failure_criteria,
            character_requirements=character_requirements,
            time_limit=300.0,  # 5 minute experience
            allow_freeform_dialogue=True,
            scene_constants=SceneConstants(
                # Life raft specific constants
                crisis_oxygen_penalty=15,  # Oxygen penalty during crisis events
                crisis_trust_penalty=5,    # Minor trust impact during crisis
                help_oxygen_bonus=20,      # O2 transfer amount
                help_trust_bonus=10,       # Trust gain from accepting help
                critical_level=20,         # Critical oxygen threshold
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
                "[LifeRaft] Milestone achieved: %s", milestone
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
        """
        if current_phase >= 5:
            return False, "already_at_max_phase"

        milestones = self.PHASE_MILESTONES.get(current_phase, {})
        min_time = milestones.get('min_time', 0)
        max_time = milestones.get('max_time', 120)
        required = milestones.get('required', [])
        trigger_condition = milestones.get('trigger_condition')

        if phase_duration < min_time:
            return False, "below_min_time"

        required_met = all(m in self.achieved_milestones for m in required)
        condition_met = trigger_condition(state) if trigger_condition else False

        if required_met:
            return True, "milestones_complete"
        if phase_duration >= max_time:
            return True, "max_time_reached"
        if condition_met and phase_duration >= min_time:
            return True, "trigger_condition_met"

        return False, "waiting_for_milestones"

    def get_phase_context(self, current_phase: int, state: dict) -> dict:
        """Get context about current phase for LLM prompts."""
        milestones = self.PHASE_MILESTONES.get(current_phase, {})
        required = milestones.get('required', [])
        optional = milestones.get('optional', [])

        required_remaining = [m for m in required if m not in self.achieved_milestones]
        achieved = list(self.achieved_milestones)

        return {
            'phase': current_phase,
            'phase_name': milestones.get('name', 'unknown'),
            'milestones_achieved': achieved,
            'milestones_remaining': required_remaining,
            'optional_milestones': [m for m in optional if m not in self.achieved_milestones],
            'player_oxygen': state.get('player_oxygen', 0),
            'captain_oxygen': state.get('captain_oxygen', 0),
            'hull_integrity': state.get('hull_integrity', 0),
            'empathy': state.get('empathy_score', 0),
            'commitment': state.get('commitment_score', 0),
            'presence': state.get('presence_score', 0),
        }

    def reset_milestones(self) -> None:
        """Reset milestones for scene restart."""
        self.achieved_milestones.clear()
        self.phase_start_time = 0.0
