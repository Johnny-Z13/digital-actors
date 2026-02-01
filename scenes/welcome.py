"""
Welcome Scene - Default Boot-up Experience

The first scene users see when starting Digital Actors. Features Clippy
the paper clip assistant who helps users understand the platform.
"""

from scenes.base.base import (
    AudioAssets,
    CharacterRequirement,
    Scene,
    SceneArtAssets,
    StateVariable,
)


class Welcome(Scene):
    """Welcome - Introduction to Digital Actors with Clippy"""

    def __init__(self):
        # Define audio assets
        audio = AudioAssets(
            background_music=None,  # No background music for welcome
            sfx_library={
                "click": "/audio/sfx/click.mp3",
                "success": "/audio/sfx/success.mp3",
            },
            volume_levels={"music": 0.0, "sfx": 0.5, "voice": 1.0},
        )

        # Define art assets
        art_assets = SceneArtAssets(
            scene_type="welcome",
            custom_scene_file="/js/welcome_scene.js",
            ui_elements={},
            audio=audio,
        )

        # No 3D controls - welcome scene uses UI menus for navigation
        controls = []

        # Minimal state for welcome scene
        state_variables = [
            StateVariable(
                name="topics_explored", initial_value=0, min_value=0, max_value=10, update_rate=0.0
            ),
        ]

        # Character requirements
        character_requirements = [
            CharacterRequirement(
                skill="user_assistance",
                importance="required",
                impact_without="Cannot guide users through the platform.",
                alternative_path=False,
            ),
        ]

        super().__init__(
            id="welcome",
            name="Welcome",
            description="""WELCOME TO DIGITAL ACTORS

            A playground to play, configure and create AI NPCs (APCs).
            Create Scenarios and interactive stories.

            Speak with Clippy here to find out more, or dive into the menus.

            Have fun! :)

            CLIPPY can help you:
            - Explore available scenarios (submarine survival, detective noir, and more)
            - Meet the Digital Actors (AI characters with unique personalities)
            - Learn how to create your own scenarios and characters
            - Understand how the platform works

            Just say hello and ask Clippy anything!""",
            opening_speech=[],  # Clippy stays silent until player speaks first
            art_assets=art_assets,
            controls=controls,
            state_variables=state_variables,
            success_criteria=[],
            failure_criteria=[],
            character_requirements=character_requirements,
            time_limit=None,  # No time limit for welcome
            allow_freeform_dialogue=True,
        )
