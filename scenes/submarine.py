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
            SceneControl(
                id="crank",
                label="CRANK",
                type="button",
                color=0xaaaaaa,
                position={'x': 0.0, 'y': -0.5, 'z': 0},
                description="Manual generator crank - provides emergency power boost",
                action_type="safe",
                npc_aware=True  # James can hear the cranking sound
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
                visible_in_phases=[3, 4]  # Only appears after the revelation in Phase 3
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
                Line(text="[distant, crackled radio] ...anyone copy? This is Kovich, forward control, does anyone copy...", delay=0),
                Line(text="[clearer, desperate] If anyone can hear this, the reactor containment is gone. Repeat, containment is gone. We are leaking radiation through ventilation and we are still sinking.", delay=3.5),
                Line(text="[sharp intake of breath] Oh thank God. Thank God. Okay. Okay, you're in aft compartment, right? I can see you on thermals.", delay=3.0),
                Line(text="[trying to steady voice] I'm Lieutenant Commander James Kovich. I'm... [pause, breathing] ...I'm trapped in forward control. The bulkhead door sealed when the reactor blew.", delay=3.5),
                Line(text="We've got maybe eight minutes before the radiation reaches you. Maybe less. I need you to trust my voice, okay? I'm going to get you out of this.", delay=4.0),
                Line(text="[voice drops, more human] What's your name? Your real name—not your rank.", delay=3.0),
            ],
            art_assets=art_assets,
            controls=controls,
            state_variables=state_variables,
            success_criteria=success_criteria,
            failure_criteria=failure_criteria,
            character_requirements=character_requirements,
            time_limit=300.0,  # 5 minutes to match Pressure Point scenario
            allow_freeform_dialogue=True
        )
