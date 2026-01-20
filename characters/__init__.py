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

# Registry of all available characters
CHARACTERS = {
    'eliza': Eliza(),
    'wizard': Wizard(),
    'detective': Detective(),
    'custom': Custom(),
    'engineer': Engineer(),
}

__all__ = ['Character', 'CHARACTERS', 'Eliza', 'Wizard', 'Detective', 'Custom', 'Engineer']
