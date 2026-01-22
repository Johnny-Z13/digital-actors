"""
Dialogue State Machine

Tracks conversation progression to prevent loops, ensure natural flow,
and coordinate with the World Director for state-appropriate responses.

Key Features:
- Prevents repetitive dialogue by tracking state progression
- Provides state-aware context for LLM prompts
- Coordinates with phase system for narrative beats
- Tracks turn counts to prevent conversations from stagnating
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DialogueState(Enum):
    """
    States representing the emotional/narrative arc of a conversation.

    Progression typically follows: GREETING → ESTABLISHING → WORKING → CRISIS → REVELATION → RESOLUTION
    Not all conversations will hit all states.
    """
    GREETING = "greeting"           # Initial contact, establishing connection
    ESTABLISHING = "establishing"   # Building rapport, sharing context
    WORKING = "working"             # Main task/puzzle solving phase
    CRISIS = "crisis"               # Tension peak, urgent situation
    REVELATION = "revelation"       # Key information revealed
    RESOLUTION = "resolution"       # Wrapping up, final moments


class TurnType(Enum):
    """
    Types of player input for context-aware responses.

    Used to generate turn-type instructions for the LLM.
    """
    QUESTION = "question"       # Player asked something
    STATEMENT = "statement"     # Player made a statement/observation
    ACTION = "action"           # Player took a game action (button press)
    SILENCE = "silence"         # Player hasn't responded
    EMOTION = "emotion"         # Player expressed emotion
    UNKNOWN = "unknown"         # Can't categorize


@dataclass
class DialogueContext:
    """
    Context about the current dialogue state for LLM prompts.
    """
    state: DialogueState
    turn_count: int
    turns_in_state: int
    should_advance: bool
    suggested_topics: list[str]
    avoid_topics: list[str]  # Recently discussed, don't repeat


class DialogueStateMachine:
    """
    Tracks dialogue progression and provides state-aware context.

    Usage:
        machine = DialogueStateMachine()
        machine.record_turn("player", "What's your name?")
        context = machine.get_context()
        # Use context to inform LLM prompt
    """

    # Maximum turns allowed in each state before suggesting advancement
    MAX_TURNS_PER_STATE = {
        DialogueState.GREETING: 3,
        DialogueState.ESTABLISHING: 6,
        DialogueState.WORKING: 15,
        DialogueState.CRISIS: 8,
        DialogueState.REVELATION: 4,
        DialogueState.RESOLUTION: 5,
    }

    # State transition rules
    VALID_TRANSITIONS = {
        DialogueState.GREETING: [DialogueState.ESTABLISHING, DialogueState.WORKING],
        DialogueState.ESTABLISHING: [DialogueState.WORKING, DialogueState.CRISIS],
        DialogueState.WORKING: [DialogueState.CRISIS, DialogueState.RESOLUTION],
        DialogueState.CRISIS: [DialogueState.REVELATION, DialogueState.RESOLUTION],
        DialogueState.REVELATION: [DialogueState.RESOLUTION, DialogueState.WORKING],
        DialogueState.RESOLUTION: [],  # Terminal state
    }

    def __init__(self, initial_state: DialogueState = DialogueState.GREETING):
        """Initialize the dialogue state machine."""
        self.state = initial_state
        self.turn_count = 0
        self.turns_in_state = 0

        # Track recent topics to avoid repetition
        self.recent_topics: list[str] = []
        self.max_recent_topics = 5

        # Track what's been discussed
        self.discussed_topics: set[str] = set()

        # Turn history for context
        self.turn_history: list[dict[str, Any]] = []
        self.max_history = 20

        logger.info("[DialogueState] Initialized in state: %s", self.state.value)

    def record_turn(
        self,
        speaker: str,
        content: str,
        turn_type: Optional[TurnType] = None,
        topics: Optional[list[str]] = None
    ) -> None:
        """
        Record a turn in the conversation.

        Args:
            speaker: "player" or "npc"
            content: What was said
            turn_type: Optional categorization of the turn
            topics: Optional list of topics mentioned
        """
        self.turn_count += 1
        self.turns_in_state += 1

        # Auto-detect turn type if not provided
        if turn_type is None:
            turn_type = self._detect_turn_type(content)

        # Record turn
        turn = {
            'speaker': speaker,
            'content': content[:200],  # Truncate for storage
            'turn_type': turn_type.value,
            'turn_number': self.turn_count,
            'state': self.state.value
        }
        self.turn_history.append(turn)

        # Trim history if too long
        if len(self.turn_history) > self.max_history:
            self.turn_history = self.turn_history[-self.max_history:]

        # Track topics
        if topics:
            for topic in topics:
                self.discussed_topics.add(topic)
                self.recent_topics.append(topic)

            # Trim recent topics
            if len(self.recent_topics) > self.max_recent_topics:
                self.recent_topics = self.recent_topics[-self.max_recent_topics:]

        logger.debug(
            "[DialogueState] Turn %d recorded: %s (%s) in state %s",
            self.turn_count,
            speaker,
            turn_type.value,
            self.state.value
        )

    def _detect_turn_type(self, content: str) -> TurnType:
        """Auto-detect the type of turn from content."""
        content_lower = content.lower().strip()

        # Check for questions
        if '?' in content or any(content_lower.startswith(q) for q in
            ['what', 'who', 'where', 'when', 'why', 'how', 'is ', 'are ', 'can ', 'do ', 'does ']):
            return TurnType.QUESTION

        # Check for emotional content
        emotion_indicators = ['feel', 'scared', 'afraid', 'worried', 'happy', 'sad', 'angry',
                             'sorry', 'thank', 'hope', 'wish', 'love', 'hate']
        if any(indicator in content_lower for indicator in emotion_indicators):
            return TurnType.EMOTION

        # Check for action indicators
        action_indicators = ['activated', 'pressed', 'turned', 'clicked', 'did', 'done']
        if any(indicator in content_lower for indicator in action_indicators):
            return TurnType.ACTION

        # Default to statement
        return TurnType.STATEMENT

    def advance_state(self, new_state: Optional[DialogueState] = None) -> bool:
        """
        Advance to the next dialogue state.

        Args:
            new_state: Specific state to transition to, or auto-advance if None

        Returns:
            True if state changed, False otherwise
        """
        if new_state is None:
            # Auto-advance to next logical state
            valid_next = self.VALID_TRANSITIONS.get(self.state, [])
            if valid_next:
                new_state = valid_next[0]
            else:
                return False  # No valid transition

        # Validate transition
        if new_state not in self.VALID_TRANSITIONS.get(self.state, []):
            logger.warning(
                "[DialogueState] Invalid transition: %s → %s",
                self.state.value,
                new_state.value
            )
            return False

        old_state = self.state
        self.state = new_state
        self.turns_in_state = 0

        logger.info(
            "[DialogueState] State transition: %s → %s (after %d turns)",
            old_state.value,
            new_state.value,
            self.turn_count
        )

        return True

    def should_advance(self) -> bool:
        """Check if we've been in the current state too long."""
        max_turns = self.MAX_TURNS_PER_STATE.get(self.state, 10)
        return self.turns_in_state >= max_turns

    def get_context(self) -> DialogueContext:
        """
        Get current dialogue context for LLM prompts.

        Returns:
            DialogueContext with state information
        """
        return DialogueContext(
            state=self.state,
            turn_count=self.turn_count,
            turns_in_state=self.turns_in_state,
            should_advance=self.should_advance(),
            suggested_topics=self._get_suggested_topics(),
            avoid_topics=list(self.recent_topics)
        )

    def _get_suggested_topics(self) -> list[str]:
        """Get topic suggestions based on current state."""
        suggestions = {
            DialogueState.GREETING: ["name", "situation", "how_you_feel"],
            DialogueState.ESTABLISHING: ["background", "relationship", "goals"],
            DialogueState.WORKING: ["current_task", "progress", "next_steps"],
            DialogueState.CRISIS: ["urgency", "options", "consequences"],
            DialogueState.REVELATION: ["truth", "meaning", "decision"],
            DialogueState.RESOLUTION: ["outcome", "reflection", "future"],
        }
        return suggestions.get(self.state, [])

    def get_turn_type_instruction(self, turn_type: TurnType) -> str:
        """
        Get instruction suffix based on what the player just did.

        Args:
            turn_type: Type of the player's last turn

        Returns:
            Instruction string to append to LLM prompt
        """
        instructions = {
            TurnType.QUESTION: (
                "The player asked a QUESTION. Answer it directly and concisely, "
                "then you may add one follow-up thought."
            ),
            TurnType.STATEMENT: (
                "The player made a STATEMENT. Acknowledge it briefly, "
                "then move the conversation forward."
            ),
            TurnType.ACTION: (
                "The player took an ACTION. React to the action's result, "
                "guide next steps if needed."
            ),
            TurnType.SILENCE: (
                "The player is SILENT or idle. Prompt them gently or continue your thought. "
                "Don't repeat yourself."
            ),
            TurnType.EMOTION: (
                "The player expressed EMOTION. Respond with appropriate empathy, "
                "acknowledge their feelings."
            ),
            TurnType.UNKNOWN: (
                "Respond naturally to what the player said."
            ),
        }
        return instructions.get(turn_type, instructions[TurnType.UNKNOWN])

    def get_state_instruction(self) -> str:
        """
        Get instruction based on current dialogue state.

        Returns:
            Instruction string describing expected behavior for this state
        """
        instructions = {
            DialogueState.GREETING: (
                "You are in the GREETING phase. Establish connection. "
                "Ask the player's name if you haven't. Be welcoming but appropriate to the situation."
            ),
            DialogueState.ESTABLISHING: (
                "You are in the ESTABLISHING phase. Build rapport. "
                "Share relevant information. Get to know each other."
            ),
            DialogueState.WORKING: (
                "You are in the WORKING phase. Focus on the task at hand. "
                "Guide the player through what needs to be done."
            ),
            DialogueState.CRISIS: (
                "You are in the CRISIS phase. Show urgency and stress. "
                "Make the stakes feel real. Time is running out."
            ),
            DialogueState.REVELATION: (
                "You are in the REVELATION phase. This is a key emotional moment. "
                "Share something important. Be vulnerable."
            ),
            DialogueState.RESOLUTION: (
                "You are in the RESOLUTION phase. This is the end. "
                "Wrap up meaningfully. Reflect on what happened."
            ),
        }
        return instructions.get(self.state, "")

    def reset(self, initial_state: DialogueState = DialogueState.GREETING) -> None:
        """Reset the state machine for a new conversation."""
        self.state = initial_state
        self.turn_count = 0
        self.turns_in_state = 0
        self.recent_topics.clear()
        self.discussed_topics.clear()
        self.turn_history.clear()
        logger.info("[DialogueState] Reset to state: %s", self.state.value)

    def get_status(self) -> dict[str, Any]:
        """Get current status for debugging."""
        return {
            'state': self.state.value,
            'turn_count': self.turn_count,
            'turns_in_state': self.turns_in_state,
            'should_advance': self.should_advance(),
            'recent_topics': self.recent_topics,
            'discussed_topics_count': len(self.discussed_topics),
        }
