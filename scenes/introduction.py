"""
Introduction Scene

First meeting between character and player.
"""

from scenes.base import Scene
from llm_prompt_core.types import Line


class Introduction(Scene):
    """Introduction - First meeting"""

    def __init__(self):
        super().__init__(
            id="introduction",
            name="Introduction",
            description="Meeting for the first time.",
            opening_speech=[
                Line(text='Hello! Nice to meet you.', delay=0),
                Line(text='How can I help you today?', delay=2.0),
            ]
        )
