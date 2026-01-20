"""
Scene definitions for the chat system.

Each scene represents a specific conversation context or story moment.
"""

from scenes.base import Scene
from scenes.introduction import Introduction
from scenes.conversation import Conversation
from scenes.quest import Quest
from scenes.submarine import Submarine

# Registry of all available scenes
SCENES = {
    'introduction': Introduction(),
    'conversation': Conversation(),
    'quest': Quest(),
    'submarine': Submarine(),
}

__all__ = ['Scene', 'SCENES', 'Introduction', 'Conversation', 'Quest', 'Submarine']
