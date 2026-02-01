"""
Sessions Package

This package contains focused components for managing chat sessions.
These components are designed to replace the monolithic ChatSession class.

Components:
- DialogueEngine: Handles prompt building and LLM interactions
- GameStateManager: Manages scene state, game logic, and win/lose conditions
- ResponseHandler: Manages TTS, audio, and response delivery
- SessionOrchestrator: Coordinates all components (future replacement for ChatSession)

Usage:
    from sessions.dialogue_engine import DialogueEngine
    from sessions.game_state_manager import GameStateManager
    from sessions.response_handler import ResponseHandler
    from sessions.session_orchestrator import SessionOrchestrator

Note: Import directly from submodules to avoid circular import issues.
"""

__all__ = [
    "DialogueEngine",
    "GameStateManager",
    "ResponseHandler",
    "SessionOrchestrator",
]
