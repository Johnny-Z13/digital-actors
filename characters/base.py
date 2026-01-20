"""
Base Character class.

All characters inherit from this class and override the configuration properties.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class Character:
    """
    Base class for all characters.

    Attributes:
        id: Unique identifier (lowercase, no spaces)
        name: Display name
        description: Short description shown in UI
        back_story: Full personality and context for the LLM
        instruction_prefix: Instructions for the LLM role-play
        color: Hex color for 3D model (e.g., 0x4fc3f7)
        skills: List of skills/expertise this character has (matches scene requirements)
    """

    id: str = "default"
    name: str = "Default Character"
    description: str = "A default character"
    back_story: str = "You are a helpful character."
    instruction_prefix: str = "You are playing a character role."
    color: int = 0x4fc3f7  # Cyan
    skills: list = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert character to dictionary format for web_server.py compatibility."""
        return {
            'name': self.name,
            'description': self.description,
            'back_story': self.back_story,
            'instruction_prefix': self.instruction_prefix,
            'skills': self.skills,
        }

    def has_skill(self, skill: str) -> bool:
        """Check if character has a specific skill."""
        return skill in self.skills

    def __str__(self) -> str:
        return f"{self.name} ({self.id})"
