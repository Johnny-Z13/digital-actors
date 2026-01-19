"""
Quest Beginning Scene

Starting an adventure or task.
"""

from scenes.base import Scene
from llm_prompt_core.types import Line


class Quest(Scene):
    """Quest Beginning - Starting an adventure"""

    def __init__(self):
        super().__init__(
            id="quest",
            name="Quest Beginning",
            description="Starting an adventure or task.",
            opening_speech=[
                Line(text='I have something important to discuss.', delay=0),
                Line(text='Are you ready to hear about it?', delay=1.5),
            ]
        )
