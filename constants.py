"""
Project-wide constants.

Centralizes magic numbers and configuration values for maintainability.
"""

from typing import Final

# =============================================================================
# LLM Configuration
# =============================================================================
LLM_TEMPERATURE_DIALOGUE: Final[float] = 0.8
LLM_TEMPERATURE_QUERY: Final[float] = 0.2
LLM_TEMPERATURE_DIRECTOR: Final[float] = 0.7
LLM_MAX_TOKENS_DIALOGUE: Final[int] = 800
LLM_MAX_TOKENS_QUERY: Final[int] = 200
LLM_MAX_TOKENS_DIRECTOR: Final[int] = 500

# =============================================================================
# Game Mechanics - Timing
# =============================================================================
RAPID_ACTION_THRESHOLD_SECONDS: Final[float] = 3.0  # Time between actions to count as "rapid"
RAPID_ACTION_COUNT_THRESHOLD: Final[int] = 3  # Number of rapid actions before penalty
GAME_OVER_DELAY_SECONDS: Final[float] = 3.0  # Wait time before showing game over screen

# =============================================================================
# Game Mechanics - Penalties
# =============================================================================
INTERRUPTION_OXYGEN_PENALTY: Final[int] = 15
INTERRUPTION_TRUST_PENALTY: Final[int] = 10
RAPID_ACTION_OXYGEN_PENALTY: Final[int] = 10
RAPID_ACTION_TRUST_PENALTY: Final[int] = 5

# =============================================================================
# Personality Profile - Update Values
# =============================================================================
PERSONALITY_IMPULSIVENESS_INCREMENT: Final[int] = 3
PERSONALITY_IMPULSIVENESS_DECREMENT: Final[int] = 1
PERSONALITY_PATIENCE_INCREMENT: Final[int] = 2
PERSONALITY_PATIENCE_DECREMENT: Final[int] = 3
PERSONALITY_COOPERATION_INCREMENT: Final[int] = 3
PERSONALITY_COOPERATION_DECREMENT: Final[int] = 2
PERSONALITY_PROBLEM_SOLVING_INCREMENT: Final[int] = 2
PERSONALITY_PROBLEM_SOLVING_DECREMENT: Final[int] = 1

# Personality thresholds for descriptions
PERSONALITY_HIGH_THRESHOLD: Final[int] = 70
PERSONALITY_MID_THRESHOLD: Final[int] = 50

# =============================================================================
# Relationship & Trust
# =============================================================================
TRUST_HIGH_THRESHOLD: Final[int] = 50
TRUST_POSITIVE_THRESHOLD: Final[int] = 20
TRUST_NEGATIVE_THRESHOLD: Final[int] = -20
TRUST_LOW_THRESHOLD: Final[int] = -50
TRUST_MINIMUM: Final[int] = -100

# Familiarity thresholds
FAMILIARITY_NEW: Final[int] = 1
FAMILIARITY_MODERATE: Final[int] = 5

# =============================================================================
# World Director - Cooldowns
# =============================================================================
DIRECTOR_COOLDOWN_SPAWN_EVENT: Final[int] = 5
DIRECTOR_COOLDOWN_ADJUST_NPC: Final[int] = 3
DIRECTOR_COOLDOWN_GIVE_HINT: Final[int] = 4

# =============================================================================
# World Director - Dynamic Events
# =============================================================================
EVENT_CRISIS_OXYGEN_PENALTY: Final[int] = 20
EVENT_CRISIS_TRUST_PENALTY: Final[int] = 10
EVENT_HELP_OXYGEN_BONUS: Final[int] = 15
EVENT_HELP_TRUST_BONUS: Final[int] = 5

# =============================================================================
# Difficulty Adjustment
# =============================================================================
DIFFICULTY_EASY_SUCCESS_RATE: Final[float] = 0.3
DIFFICULTY_HARD_SUCCESS_RATE: Final[float] = 0.8
DIFFICULTY_SCENE_ATTEMPTS_THRESHOLD: Final[int] = 3

# Penalty multipliers
DIFFICULTY_EASY_PENALTY_MULTIPLIER: Final[float] = 0.7
DIFFICULTY_HARD_PENALTY_MULTIPLIER: Final[float] = 1.3

# Oxygen bonuses
DIFFICULTY_EASY_OXYGEN_BONUS: Final[int] = 30
DIFFICULTY_HARD_OXYGEN_PENALTY: Final[int] = 30

# =============================================================================
# Failure Thresholds
# =============================================================================
MAX_INCORRECT_ACTIONS: Final[int] = 5
CRITICAL_OXYGEN_LEVEL: Final[int] = 60

# =============================================================================
# Server Configuration
# =============================================================================
DEFAULT_SERVER_HOST: Final[str] = "0.0.0.0"
DEFAULT_SERVER_PORT: Final[int] = 8080

# =============================================================================
# Scene Hint Thresholds
# =============================================================================
HINT_SCENE_ATTEMPTS_THRESHOLD: Final[int] = 2  # Failed this many times before hints
