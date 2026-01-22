"""
Scene definitions for the chat system.

Each scene represents a specific conversation context or story moment.
"""

from scenes.base import Scene
from scenes.introduction import Introduction
from scenes.conversation import Conversation
from scenes.quest import MerlinsRoom
from scenes.submarine import Submarine
from scenes.crown_court import CrownCourt
from scenes.iconic_detectives import IconicDetectives

# Registry of all available scenes
SCENES = {
    'introduction': Introduction(),
    'conversation': Conversation(),
    'merlins_room': MerlinsRoom(),
    'submarine': Submarine(),
    'crown_court': CrownCourt(),
    'iconic_detectives': IconicDetectives(),
}

__all__ = ['Scene', 'SCENES', 'Introduction', 'Conversation', 'MerlinsRoom', 'Submarine', 'CrownCourt', 'IconicDetectives']
