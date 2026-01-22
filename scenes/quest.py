"""
Merlin's Room Scene

An enchanted alchemy workshop where Merlin the wizard resides.
"""

from scenes.base import Scene, SceneArtAssets, AudioAssets
from llm_prompt_core.types import Line


class MerlinsRoom(Scene):
    """Merlin's Room - An enchanted alchemy workshop"""

    def __init__(self):
        # Art assets with 3D environment model
        art_assets = SceneArtAssets(
            scene_type="custom",
            environment_model="/models/merlins_workshop.glb",
            audio=AudioAssets(
                volume_levels={
                    'music': 0.3,
                    'sfx': 0.6,
                    'voice': 1.0
                }
            )
        )

        super().__init__(
            id="merlins_room",
            name="Merlin's Room",
            description="""SETTING: Merlin's enchanted alchemy workshop - a cluttered but magical space
filled with bubbling potions, ancient tomes, glowing crystals, and mysterious artifacts.
Shelves line the walls with jars of peculiar ingredients. A large cauldron simmers in the corner.
Candles float in the air, casting dancing shadows across weathered stone walls.

The wizard Merlin resides here, surrounded by centuries of accumulated wisdom and arcane knowledge.
He speaks in riddles and metaphors, but always with purpose.""",
            opening_speech=[
                Line(text='Ah, a visitor! Come in, come in...', delay=0),
                Line(text='Mind the cauldron - it bites.', delay=1.5),
                Line(text='Now then, what brings you to my humble workshop?', delay=3.0),
            ],
            art_assets=art_assets
        )
