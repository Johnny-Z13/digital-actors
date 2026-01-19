"""
Base Scene class.

All scenes inherit from this class and override the configuration properties.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from llm_prompt_core.types import Line


@dataclass
class Scene:
    """
    Base class for all scenes.

    Attributes:
        id: Unique identifier (lowercase, no spaces)
        name: Display name shown in UI
        description: Context about this scene for the LLM
        opening_speech: List of lines the character says when scene starts
    """

    id: str = "default"
    name: str = "Default Scene"
    description: str = "A default scene."
    opening_speech: List[Line] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert scene to dictionary format for web_server.py compatibility."""
        return {
            'name': self.name,
            'description': self.description,
            'opening_speech': self.opening_speech,
        }

    def __str__(self) -> str:
        return f"{self.name} ({self.id})"
