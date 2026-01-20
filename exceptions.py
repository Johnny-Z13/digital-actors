"""
Custom exceptions for Digital Actors.

Provides specific exception types for better error handling and debugging.
"""

from __future__ import annotations


class DigitalActorsError(Exception):
    """Base exception for all Digital Actors errors."""

    pass


class LLMError(DigitalActorsError):
    """Raised when LLM operations fail."""

    pass


class LLMResponseError(LLMError):
    """Raised when LLM returns an invalid or empty response."""

    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""

    pass


class SceneError(DigitalActorsError):
    """Base exception for scene-related errors."""

    pass


class SceneNotFoundError(SceneError):
    """Raised when a requested scene doesn't exist."""

    def __init__(self, scene_id: str) -> None:
        self.scene_id = scene_id
        super().__init__(f"Scene not found: {scene_id}")


class SceneStateError(SceneError):
    """Raised when scene state is invalid or corrupted."""

    pass


class CharacterError(DigitalActorsError):
    """Base exception for character-related errors."""

    pass


class CharacterNotFoundError(CharacterError):
    """Raised when a requested character doesn't exist."""

    def __init__(self, character_id: str) -> None:
        self.character_id = character_id
        super().__init__(f"Character not found: {character_id}")


class CharacterSkillMismatchError(CharacterError):
    """Raised when a character lacks required skills for a scene."""

    def __init__(self, character_id: str, missing_skills: list[str]) -> None:
        self.character_id = character_id
        self.missing_skills = missing_skills
        super().__init__(
            f"Character '{character_id}' lacks required skills: {', '.join(missing_skills)}"
        )


class PlayerMemoryError(DigitalActorsError):
    """Base exception for player memory errors."""

    pass


class PlayerNotFoundError(PlayerMemoryError):
    """Raised when player data cannot be found."""

    def __init__(self, player_id: str) -> None:
        self.player_id = player_id
        super().__init__(f"Player not found: {player_id}")


class DatabaseError(PlayerMemoryError):
    """Raised when database operations fail."""

    pass


class WebSocketError(DigitalActorsError):
    """Base exception for WebSocket communication errors."""

    pass


class ConnectionClosedError(WebSocketError):
    """Raised when WebSocket connection is unexpectedly closed."""

    pass


class InvalidMessageError(WebSocketError):
    """Raised when receiving an invalid message format."""

    def __init__(self, message: str, reason: str) -> None:
        self.original_message = message
        self.reason = reason
        super().__init__(f"Invalid message: {reason}")


class WorldDirectorError(DigitalActorsError):
    """Base exception for World Director errors."""

    pass


class DirectorDecisionError(WorldDirectorError):
    """Raised when World Director fails to make a decision."""

    pass
