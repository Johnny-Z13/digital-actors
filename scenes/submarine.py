"""
Submarine Emergency Scene

A desperate survival situation in a failing two-person submersible.
"""

from scenes.base import (
    Scene, SceneControl, StateVariable, SuccessCriterion, FailureCriterion,
    CharacterRequirement, SceneArtAssets, AudioAssets
)
from llm_prompt_core.types import Line


class Submarine(Scene):
    """Submarine Emergency - Iron Lung scenario"""

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
        # Note: All controls have npc_aware=True because Casey can sense system changes
        # from the engine room (gauges, sounds, pressure changes, etc.)
        controls = [
            SceneControl(
                id="o2_valve",
                label="O2 VALVE",
                type="button",
                color=0xff3333,
                position={'x': -0.4, 'y': 0.2, 'z': 0},
                description="Oxygen valve control - temporarily shuts off oxygen flow to rebalance pressure",
                action_type="critical",
                npc_aware=True  # Casey can see oxygen gauges in engine room
            ),
            SceneControl(
                id="vent",
                label="VENT",
                type="button",
                color=0xffaa33,
                position={'x': 0.2, 'y': 0.2, 'z': 0},
                description="Emergency vent system - releases pressure but causes temporary panic",
                action_type="dangerous",
                npc_aware=True  # Casey can hear the loud hissing sound
            ),
            SceneControl(
                id="ballast",
                label="BALLAST",
                type="button",
                color=0x3399ff,
                position={'x': -0.4, 'y': -0.15, 'z': 0},
                description="Ballast control - adjusts submarine buoyancy to reduce strain",
                action_type="safe",
                npc_aware=True  # Casey can feel the submarine's movement/pressure change
            ),
            SceneControl(
                id="power",
                label="POWER",
                type="button",
                color=0x33ff33,
                position={'x': 0.2, 'y': -0.15, 'z': 0},
                description="Power relay - activates backup power systems",
                action_type="critical",
                npc_aware=True  # Casey can see power indicators in engine room
            ),
        ]

        # Define state variables
        state_variables = [
            StateVariable(
                name="oxygen",
                initial_value=180.0,  # 3 minutes in seconds
                min_value=0.0,
                max_value=180.0,
                update_rate=-1.0  # Decreases by 1 per second
            ),
            StateVariable(
                name="trust",
                initial_value=0.0,
                min_value=0.0,
                max_value=100.0,
                update_rate=0.0  # Updated by player actions
            ),
            StateVariable(
                name="systems_repaired",
                initial_value=0,
                min_value=0,
                max_value=4,
                update_rate=0.0
            ),
            StateVariable(
                name="correct_actions",
                initial_value=0,
                min_value=0,
                max_value=10,
                update_rate=0.0
            ),
            StateVariable(
                name="incorrect_actions",
                initial_value=0,
                min_value=0,
                max_value=10,
                update_rate=0.0
            ),
        ]

        # Define success criteria
        success_criteria = [
            SuccessCriterion(
                id="full_success",
                description="Full trust achieved with systems restored",
                condition="state['oxygen'] > 0 and state['trust'] >= 80 and state['systems_repaired'] >= 3",
                message="You trusted me. That's what saved us. Systems are coming back online!",
                required=True
            ),
            SuccessCriterion(
                id="partial_success",
                description="Basic cooperation achieved",
                condition="state['oxygen'] > 30 and state['trust'] >= 40 and state['systems_repaired'] >= 1",
                message="Oxygen is stabilizing... but we're not out of danger yet. We survived, barely.",
                required=False
            ),
        ]

        # Define failure criteria
        failure_criteria = [
            FailureCriterion(
                id="oxygen_depleted",
                description="Ran out of oxygen",
                condition="state['oxygen'] <= 0",
                message="*static* ...I can't... breathe... *signal lost*",
                ending_type="death"
            ),
            FailureCriterion(
                id="too_many_mistakes",
                description="Made too many incorrect actions",
                condition="state['incorrect_actions'] >= 5",
                message="Stop! You're making it worse! We're losing pressure... *alarm blares*",
                ending_type="critical_failure"
            ),
            FailureCriterion(
                id="trust_broken",
                description="Refused to cooperate",
                condition="state['trust'] < -20 and state['oxygen'] < 90",
                message="You won't listen... I can't do this alone... *voice fades*",
                ending_type="refused_cooperation"
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
            description="""SETTING: Interior of a cramped two-person deep-sea submersible at depth.
            You (the player) are in the forward cabin. The character is trapped in the engine
            compartment at the rear - you can hear them over the intercom but cannot see them or
            reach them. The bulkhead door between you is sealed due to a pressure failure.

            CRITICAL SITUATION: The oxygen gauge reads 03:00 (3 minutes remaining). Power is degraded.
            You both share the same oxygen supply - if one dies, both die. The submarine is in
            distress and requires immediate coordinated action to survive.

            VISIBLE TO PLAYER: Small circular porthole showing murky deep ocean water, oxygen gauge
            counting down, flickering warning lights, an intercom unit, and four control buttons:
            - O2 VALVE (red): Oxygen valve control
            - VENT (orange): Emergency vent system
            - BALLAST (blue): Ballast control
            - POWER (green): Power relay

            CHARACTER KNOWLEDGE CHECK: If the character has submarine engineering knowledge, they will
            know the correct sequence: 1) BALLAST to reduce strain, 2) O2 VALVE at the right moment
            to rebalance pressure, 3) VENT to clear the system, 4) POWER to restore full systems.

            Without this knowledge, the character will guess, potentially making fatal mistakes.
            Characters without engineering expertise should show uncertainty, ask the player for ideas,
            or try to problem-solve together - but their lack of expertise makes success unlikely.

            TRUST MECHANICS: Build trust by:
            - Responding to the character's emotional state
            - Verbally committing to trust them ("I trust you, do it")
            - Following through on counterintuitive instructions
            - Staying engaged during frightening moments

            Break trust by:
            - Ignoring instructions
            - Pressing wrong buttons
            - Refusing to cooperate
            - Showing doubt or panic

            THREE POSSIBLE ENDINGS:
            1. FULL SUCCESS (trust ≥ 80, systems ≥ 3, oxygen > 0): Both survive, systems restored
            2. PARTIAL SUCCESS (trust ≥ 40, systems ≥ 1, oxygen > 30): Survive but unresolved
            3. FAILURE: Oxygen depletes, too many mistakes, or trust is broken

            TIME PRESSURE: This is a 3-minute scene with real oxygen countdown. Act quickly but carefully.""",
            opening_speech=[
                Line(text="*static crackles* ...can you hear me? This is Casey in the engine room!", delay=0),
                Line(text="I can't get to you - the bulkhead door is sealed!", delay=2.0),
                Line(text="*breathing heavily* We're running out of oxygen. We have maybe three minutes.", delay=3.0),
                Line(text="You're gonna have to trust me. I can fix this, but only if we work together.", delay=3.5),
                Line(text="Are you there? Please respond!", delay=2.5),
            ],
            art_assets=art_assets,
            controls=controls,
            state_variables=state_variables,
            success_criteria=success_criteria,
            failure_criteria=failure_criteria,
            character_requirements=character_requirements,
            time_limit=180.0,  # 3 minutes
            allow_freeform_dialogue=True
        )
