"""
General Conversation Scene

Casual, open-ended conversation.
"""

from llm_prompt_core.types import Line
from scenes.base.base import Scene


class Conversation(Scene):
    """General Conversation - Casual chat"""

    def __init__(self):
        super().__init__(
            id="conversation",
            name="General Conversation",
            description="Casual conversation.",
            opening_speech=[
                Line(text="What would you like to talk about?", delay=0),
            ],
        )
