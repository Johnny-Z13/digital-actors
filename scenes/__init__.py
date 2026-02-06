"""
Scene definitions for the chat system.

Each scene represents a specific conversation context or story moment.
"""

from scenes.base.base import Scene
from scenes.conversation import Conversation
from scenes.crown_court import CrownCourt
from scenes.detective.iconic_detectives import IconicDetectives
from scenes.foxhole.foxhole import Foxhole
from scenes.introduction import Introduction
from scenes.life_raft import LifeRaft
from scenes.wizard.quest import MerlinsRoom
from scenes.submarine.submarine import Submarine
from scenes.welcome import Welcome

# Registry of all available scenes
SCENES = {
    "welcome": Welcome(),
    "introduction": Introduction(),
    "conversation": Conversation(),
    "merlins_room": MerlinsRoom(),
    "submarine": Submarine(),
    "foxhole": Foxhole(),
    "crown_court": CrownCourt(),
    "iconic_detectives": IconicDetectives(),
    "life_raft": LifeRaft(),
}

__all__ = [
    "SCENES",
    "Conversation",
    "CrownCourt",
    "Foxhole",
    "IconicDetectives",
    "Introduction",
    "LifeRaft",
    "MerlinsRoom",
    "Scene",
    "Submarine",
    "Welcome",
]
