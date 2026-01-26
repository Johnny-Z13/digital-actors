"""
Configuration loader module.

Provides centralized access to scene mappings and other configuration.
This is the single source of truth for scene↔character relationships.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

# Load configuration once at module import
_CONFIG_DIR = Path(__file__).parent
_SCENE_MAPPINGS_PATH = _CONFIG_DIR / "scene_mappings.json"

# Cache for loaded config
_scene_mappings: Optional[Dict[str, Any]] = None


def get_scene_mappings() -> Dict[str, Any]:
    """
    Load and return scene mappings configuration.

    Returns cached version after first load.
    """
    global _scene_mappings

    if _scene_mappings is None:
        if not _SCENE_MAPPINGS_PATH.exists():
            raise FileNotFoundError(f"Scene mappings not found: {_SCENE_MAPPINGS_PATH}")

        with open(_SCENE_MAPPINGS_PATH, 'r') as f:
            _scene_mappings = json.load(f)

    return _scene_mappings


def get_scene_character_map() -> Dict[str, str]:
    """
    Get mapping of scene_id -> character_id.

    Example: {'submarine': 'engineer', 'iconic_detectives': 'mara_vane'}
    """
    mappings = get_scene_mappings()
    return {
        scene_id: config['character']
        for scene_id, config in mappings['scenes'].items()
    }


def get_character_scene_map() -> Dict[str, str]:
    """
    Get mapping of character_id -> scene_id.

    Example: {'engineer': 'submarine', 'mara_vane': 'iconic_detectives'}

    Note: Includes character aliases.
    """
    mappings = get_scene_mappings()

    # Build reverse mapping
    char_to_scene = {
        config['character']: scene_id
        for scene_id, config in mappings['scenes'].items()
    }

    # Add aliases
    for alias, canonical in mappings.get('characterAliases', {}).items():
        if canonical in char_to_scene:
            char_to_scene[alias] = char_to_scene[canonical]

    return char_to_scene


def get_custom_scene_ids() -> list[str]:
    """
    Get list of scene IDs that require custom 3D scene classes.

    These need special JavaScript scene instantiation.
    """
    mappings = get_scene_mappings()
    return [
        scene_id
        for scene_id, config in mappings['scenes'].items()
        if config.get('requiresCustomScene', False)
    ]


def get_scene_class_name(scene_id: str) -> str:
    """
    Get the JavaScript class name for a scene.

    Returns 'CharacterScene' as default if scene not found.
    """
    mappings = get_scene_mappings()
    scene_config = mappings['scenes'].get(scene_id, {})
    return scene_config.get('sceneClass', 'CharacterScene')


def get_character_for_scene(scene_id: str) -> Optional[str]:
    """Get the canonical character for a scene."""
    return get_scene_character_map().get(scene_id)


def get_scene_for_character(character_id: str) -> Optional[str]:
    """Get the canonical scene for a character."""
    return get_character_scene_map().get(character_id)


# Export commonly used items
__all__ = [
    'get_scene_mappings',
    'get_scene_character_map',
    'get_character_scene_map',
    'get_custom_scene_ids',
    'get_scene_class_name',
    'get_character_for_scene',
    'get_scene_for_character',
]
