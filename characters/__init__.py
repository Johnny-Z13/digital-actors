"""
Character definitions for the chat system.

Each character is defined in its own module with personality, backstory,
and configuration.
"""

from characters.base import Character
from characters.eliza import Eliza
from characters.wizard import Wizard
from characters.detective import Detective
from characters.custom import Custom
from characters.engineer import Engineer
from characters.judge import Judge
from characters.mara_vane import MaraVane
from characters.captain_hale import CaptainHale
from characters.clippy import Clippy

# Registry of all available characters
CHARACTERS = {
    'clippy': Clippy(),
    'eliza': Eliza(),
    'wizard': Wizard(),
    'detective': Detective(),
    'custom': Custom(),
    'engineer': Engineer(),
    'judge': Judge(),
    'mara_vane': MaraVane(),
    'captain_hale': CaptainHale(),
}

__all__ = ['Character', 'CHARACTERS', 'Eliza', 'Wizard', 'Detective', 'Custom', 'Engineer', 'Judge', 'MaraVane', 'CaptainHale', 'Clippy']
