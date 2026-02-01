"""
Base Character class.

All characters inherit from this class and override the configuration properties.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def load_backstory_file(character_id: str) -> str | None:
    """
    Load backstory from a markdown file if it exists.

    Looks for: characters/backstories/{character_id}_backstory.md
    Returns the file contents if found, None otherwise.
    """
    backstory_path = Path(__file__).parent / "backstories" / f"{character_id}_backstory.md"
    if backstory_path.exists():
        try:
            return backstory_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Warning: Could not load backstory file for {character_id}: {e}")
    return None


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
        emotion_expression_style: Dictionary defining how this character expresses emotions
            - expressiveness: 0.0 (monotone) to 1.0 (theatrical)
            - stability_baseline: Default stability for this character (0.0-1.0)
            - emotional_range: How much emotions affect voice (0.0-1.0)
            - restraint: How much character suppresses emotion (0.0-1.0)
    """

    id: str = "default"
    name: str = "Default Character"
    description: str = "A default character"
    back_story: str = "You are a helpful character."
    instruction_prefix: str = "You are playing a character role."
    color: int = 0x4FC3F7  # Cyan
    skills: list = field(default_factory=list)
    emotion_expression_style: dict = field(
        default_factory=lambda: {
            "expressiveness": 0.7,  # 0.0 (monotone) to 1.0 (theatrical)
            "stability_baseline": 0.5,  # Default stability for this character
            "emotional_range": 0.8,  # How much emotions affect voice (0.0-1.0)
            "restraint": 0.3,  # How much character suppresses emotion (0.0-1.0)
        }
    )

    def __post_init__(self):
        """Load backstory from file if available, appending to existing backstory."""
        file_backstory = load_backstory_file(self.id)
        if file_backstory:
            # Prepend file backstory to any existing backstory
            self.back_story = f"{file_backstory}\n\n---\n\n{self.back_story}"

    def to_dict(self) -> dict[str, Any]:
        """Convert character to dictionary format for web_server.py compatibility."""
        return {
            "name": self.name,
            "description": self.description,
            "back_story": self.back_story,
            "instruction_prefix": self.instruction_prefix,
            "skills": self.skills,
        }

    def has_skill(self, skill: str) -> bool:
        """Check if character has a specific skill."""
        return skill in self.skills

    def __str__(self) -> str:
        return f"{self.name} ({self.id})"
