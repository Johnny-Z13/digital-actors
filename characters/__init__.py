"""
Character definitions for the chat system.

Each character is defined in its own module with personality, backstory,
and configuration.
"""

from characters.base import Character
from characters.captain_hale import CaptainHale
from characters.clippy import Clippy
from characters.custom import Custom
from characters.detective import Detective
from characters.eliza import Eliza
from characters.engineer import Engineer
from characters.judge import Judge
from characters.kovich import Kovich
from characters.mara_vane import MaraVane
from characters.wizard import Wizard

# Registry of all available characters
CHARACTERS = {
    "clippy": Clippy(),
    "eliza": Eliza(),
    "wizard": Wizard(),
    "detective": Detective(),
    "custom": Custom(),
    "engineer": Engineer(),
    "judge": Judge(),
    "kovich": Kovich(),
    "mara_vane": MaraVane(),
    "captain_hale": CaptainHale(),
}

__all__ = [
    "CHARACTERS",
    "CaptainHale",
    "Character",
    "Clippy",
    "Custom",
    "Detective",
    "Eliza",
    "Engineer",
    "Judge",
    "Kovich",
    "MaraVane",
    "Wizard",
]
