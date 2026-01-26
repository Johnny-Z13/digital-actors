"""
World Director - The Dungeon Master AI

Orchestrates the experience by:
- Evaluating situations after player actions
- Spawning dynamic events to keep things interesting
- Adjusting NPC behavior based on context
- Managing scene transitions
- Personalizing difficulty based on player memory

Architecture:
- Fast rules layer (director_rules.py) handles predictable scenarios
- LLM layer handles complex, nuanced decisions
- Rules layer runs FIRST for ~500ms → ~5ms improvement on rule-matched cases
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, List

from constants import (
    DIFFICULTY_EASY_PENALTY_MULTIPLIER,
    DIFFICULTY_EASY_SUCCESS_RATE,
    DIFFICULTY_HARD_PENALTY_MULTIPLIER,
    DIFFICULTY_HARD_SUCCESS_RATE,
    DIFFICULTY_SCENE_ATTEMPTS_THRESHOLD,
    DIRECTOR_COOLDOWN_ADJUST_NPC,
    DIRECTOR_COOLDOWN_GIVE_HINT,
    DIRECTOR_COOLDOWN_SPAWN_EVENT,
    LLM_MAX_TOKENS_DIRECTOR,
    LLM_TEMPERATURE_DIRECTOR,
)

# Import fast rules-based director layer
from director_rules import DirectorRules, RuleAction, RuleDecision, get_director_rules

# Scene-specific constants (not imported - defined dynamically based on scene type)
SCENE_SPECIFIC_CONSTANTS = {
    'submarine': {
        'critical_level': 60,  # Critical oxygen level
        'crisis_penalty': 20,
        'help_bonus': 15,
        'max_failures': 5,
        'low_threshold': -50,
        'resource_name': 'oxygen',
        'relationship_name': 'trust',
    },
    'crown_court': {
        'critical_level': 20,  # Critical prosecution strength
        'crisis_penalty': 15,
        'help_bonus': 10,
        'max_failures': 5,
        'low_threshold': 20,
        'resource_name': 'jury_sympathy',
        'relationship_name': 'judge_trust',
    },
    'iconic_detectives': {
        'critical_level': 25,  # Critical trust level (below this = blackmail ending)
        'crisis_penalty': 10,
        'help_bonus': 10,
        'max_failures': 3,  # Contradictions threshold for twist ending
        'low_threshold': 25,
        'resource_name': 'trust',
        'relationship_name': 'trust',
        'disable_events': True,  # Phone call scene - no random events
    },
    'default': {
        'critical_level': 0,
        'crisis_penalty': 10,
        'help_bonus': 10,
        'max_failures': 5,
        'low_threshold': 20,
        'resource_name': None,
        'relationship_name': None,
    }
}
import logging

from llm_prompt_core.models.anthropic import ClaudeHaikuModel
from llm_prompt_core.utils import prompt_llm

if TYPE_CHECKING:
    from player_memory import PlayerMemory

logger = logging.getLogger(__name__)


@dataclass
class TemporalState:
    """
    Tracks trends over time for smarter Director decisions.

    Instead of just snapshot-based decisions, this tracks how values
    are changing to enable trend-aware pacing.
    """
    oxygen_trend: str = "stable"  # "stable", "declining", "critical_decline"
    engagement_trend: str = "stable"  # "increasing", "stable", "declining"
    recent_actions: List[str] = field(default_factory=list)  # Last 5 player actions
    time_since_last_beat: float = 0.0  # Seconds since last story moment
    dialogue_density: float = 0.0  # Messages per minute
    phase_duration: float = 0.0  # How long in current phase

    # Historical snapshots for trend calculation
    _oxygen_history: List[float] = field(default_factory=list)
    _action_timestamps: List[float] = field(default_factory=list)

    def update_oxygen(self, current_oxygen: float) -> None:
        """Update oxygen tracking and calculate trend."""
        self._oxygen_history.append(current_oxygen)
        # Keep last 10 readings (10 seconds of data)
        if len(self._oxygen_history) > 10:
            self._oxygen_history = self._oxygen_history[-10:]

        # Calculate trend
        if len(self._oxygen_history) >= 3:
            recent = self._oxygen_history[-3:]
            decline = recent[0] - recent[-1]
            if decline > 5:
                self.oxygen_trend = "critical_decline"
            elif decline > 2:
                self.oxygen_trend = "declining"
            else:
                self.oxygen_trend = "stable"

    def record_action(self, action: str, timestamp: float) -> None:
        """Record a player action for engagement tracking."""
        self.recent_actions.append(action)
        self._action_timestamps.append(timestamp)

        # Keep last 5 actions
        if len(self.recent_actions) > 5:
            self.recent_actions = self.recent_actions[-5:]
        if len(self._action_timestamps) > 10:
            self._action_timestamps = self._action_timestamps[-10:]

        # Calculate dialogue density (actions per minute)
        if len(self._action_timestamps) >= 2:
            time_span = self._action_timestamps[-1] - self._action_timestamps[0]
            if time_span > 0:
                self.dialogue_density = len(self._action_timestamps) / (time_span / 60.0)

        # Update engagement trend
        if self.dialogue_density > 3:
            self.engagement_trend = "increasing"
        elif self.dialogue_density < 1:
            self.engagement_trend = "declining"
        else:
            self.engagement_trend = "stable"

    def reset(self) -> None:
        """Reset temporal tracking for new scene."""
        self.oxygen_trend = "stable"
        self.engagement_trend = "stable"
        self.recent_actions.clear()
        self.time_since_last_beat = 0.0
        self.dialogue_density = 0.0
        self.phase_duration = 0.0
        self._oxygen_history.clear()
        self._action_timestamps.clear()


class DirectorDecision:
    """Represents a decision made by the World Director."""

    def __init__(self, decision_type: str, data: dict[str, Any]) -> None:
        self.type = decision_type  # 'continue', 'event', 'transition', 'adjust_npc', 'hint'
        self.data = data

    def __repr__(self) -> str:
        return f"DirectorDecision(type={self.type}, data={self.data})"


class WorldDirector:
    """
    The Dungeon Master AI that orchestrates the experience.

    Runs after player actions to decide what should happen next.

    Architecture:
    - Fast rules layer handles predictable scenarios (~5ms)
    - LLM layer handles complex decisions (~500ms)
    - Rules are checked FIRST; LLM is only consulted when needed
    """

    def __init__(self) -> None:
        self.model = ClaudeHaikuModel(
            temperature=LLM_TEMPERATURE_DIRECTOR,
            max_tokens=LLM_MAX_TOKENS_DIRECTOR,
        )
        self.decision_cooldown = 0  # Prevent too-frequent interventions

        # Fast rules-based decision layer
        self.rules_engine = get_director_rules()

        # Timing tracking for rules engine
        self.scene_start_time: float = time.time()
        self.last_player_action_time: float = time.time()

        # Temporal state tracking for trend-aware decisions
        self.temporal_state = TemporalState()

        logger.info("[WorldDirector] Initialized with fast rules layer and temporal tracking")

    def reset_scene_timing(self) -> None:
        """Reset timing trackers for a new scene - FULL context wipe."""
        self.scene_start_time = time.time()
        self.last_player_action_time = time.time()
        self.decision_cooldown = 0  # Reset cooldown for new scene
        self.rules_engine.reset_cooldowns()
        self.temporal_state.reset()
        logger.info("[WorldDirector] Scene timing, cooldowns, and temporal state reset")

    def record_player_action(self, action: str = "unknown") -> None:
        """Record that the player just took an action."""
        current_time = time.time()
        self.last_player_action_time = current_time
        self.temporal_state.record_action(action, current_time)

    def update_oxygen_tracking(self, oxygen_level: float) -> None:
        """Update oxygen tracking for trend detection."""
        self.temporal_state.update_oxygen(oxygen_level)

    def get_temporal_context(self) -> dict[str, Any]:
        """Get temporal context for Director decisions."""
        return {
            'oxygen_trend': self.temporal_state.oxygen_trend,
            'engagement_trend': self.temporal_state.engagement_trend,
            'recent_actions': self.temporal_state.recent_actions[-5:],
            'dialogue_density': f"{self.temporal_state.dialogue_density:.1f}/min",
            'phase_duration': time.time() - self.scene_start_time,
        }

    async def evaluate_situation(
        self,
        scene_id: str,
        scene_state: dict[str, Any],
        dialogue_history: str,
        player_memory: PlayerMemory | None,
        character_id: str,
        last_action: str | None = None,
    ) -> DirectorDecision:
        """
        Evaluate the current situation and decide what should happen next.

        Uses a two-layer approach:
        1. Fast rules layer (~5ms) - handles predictable scenarios
        2. LLM layer (~500ms) - handles complex decisions

        Args:
            scene_id: Current scene identifier
            scene_state: Current state (oxygen, trust, etc.)
            dialogue_history: Recent dialogue
            player_memory: Player's personality and history
            character_id: Current character
            last_action: What the player just did

        Returns:
            DirectorDecision with type and data
        """
        # Check if events are disabled for this scene (e.g., phone call scenes)
        scene_constants = SCENE_SPECIFIC_CONSTANTS.get(scene_id, SCENE_SPECIFIC_CONSTANTS['default'])
        if scene_constants.get('disable_events', False):
            logger.debug("[Director] Events disabled for scene %s - continuing", scene_id)
            return DirectorDecision('continue', {})

        # Record player action for idle tracking
        if last_action and last_action != "waited_patiently":
            self.record_player_action()

        # Calculate timing metrics for rules engine
        elapsed_time = time.time() - self.scene_start_time
        player_idle_seconds = time.time() - self.last_player_action_time
        player_failed_attempts = player_memory.scene_attempts.get(scene_id, 0) if player_memory else 0

        # STEP 1: Try fast rules layer first (no LLM needed)
        rule_decision = self.rules_engine.evaluate(
            scene_state=scene_state,
            elapsed_time=elapsed_time,
            player_idle_seconds=player_idle_seconds,
            player_failed_attempts=player_failed_attempts,
            scene_id=scene_id
        )

        # Handle rule-based decisions (no LLM consultation needed)
        if rule_decision.action != RuleAction.CONSULT_LLM:
            logger.info("[Director] Fast rule matched: %s - %s", rule_decision.action.value, rule_decision.reason)
            return self._convert_rule_to_decision(rule_decision)

        # STEP 2: No rule matched - fall through to LLM layer
        # Don't intervene too often - let the scene breathe
        self.decision_cooldown -= 1
        if self.decision_cooldown > 0:
            return DirectorDecision('continue', {})

        # Build context for director
        context = self._build_director_context(
            scene_id, scene_state, dialogue_history,
            player_memory, character_id, last_action
        )

        # Get director's assessment
        prompt = f"""You are the World Director, the dungeon master for a narrative experience.

{context}

TASK: Analyze the situation and decide what should happen next.

RULES:
1. Don't intervene too often - let natural dialogue flow
2. Only spawn events if situation is getting stale OR player is in trouble
3. Adjust NPC behavior if player's actions warrant it
4. Suggest scene transitions only at natural story beats
5. Give hints if player is clearly stuck (failed 2+ times)

Respond in JSON format:
{{{{
    "assessment": "brief analysis of current situation",
    "tension_level": "low/medium/high",
    "player_struggling": true/false,
    "action": "continue/spawn_event/adjust_npc/give_hint/transition",
    "details": {{{{
        // If action=spawn_event:
        "event_type": "crisis/challenge/help",
        "event_description": "what happens",

        // If action=adjust_npc:
        "behavior_change": "how NPC should act differently",

        // If action=give_hint:
        "hint_type": "subtle/direct",
        "hint_content": "what to suggest",

        // If action=transition:
        "next_scene": "scene_id",
        "reason": "why transition now"
    }}}}
}}}}"""

        # Get director decision
        try:
            chain = prompt_llm(prompt, self.model)
            response = chain.invoke({})

            # Parse JSON response
            decision_data = self._parse_director_response(response)

            # Set cooldown based on action type
            if decision_data['action'] == 'spawn_event':
                self.decision_cooldown = DIRECTOR_COOLDOWN_SPAWN_EVENT
            elif decision_data['action'] == 'adjust_npc':
                self.decision_cooldown = DIRECTOR_COOLDOWN_ADJUST_NPC
            elif decision_data['action'] == 'give_hint':
                self.decision_cooldown = DIRECTOR_COOLDOWN_GIVE_HINT

            return DirectorDecision(decision_data['action'], decision_data['details'])

        except Exception as e:
            logger.exception("World Director error: %s", e)
            return DirectorDecision('continue', {})

    def _convert_rule_to_decision(self, rule_decision: RuleDecision) -> DirectorDecision:
        """
        Convert a RuleDecision from the fast rules layer to a DirectorDecision.

        Args:
            rule_decision: Decision from the rules engine

        Returns:
            DirectorDecision in the format expected by the rest of the system
        """
        action_map = {
            RuleAction.CONTINUE: ('continue', {}),
            RuleAction.ADVANCE_PHASE: ('continue', {}),  # Phase is handled by state update loop
            RuleAction.TRIGGER_URGENCY: ('adjust_npc', rule_decision.data),
            RuleAction.PROMPT_PLAYER: ('give_hint', {
                'hint_type': rule_decision.data.get('hint_type', 'subtle'),
                'hint_content': 'what to do next'
            }),
            RuleAction.GIVE_HINT: ('give_hint', rule_decision.data),
            RuleAction.SPAWN_CRISIS: ('spawn_event', rule_decision.data),
        }

        decision_type, data = action_map.get(rule_decision.action, ('continue', {}))

        # Set appropriate cooldown for rules-based decisions
        if decision_type == 'spawn_event':
            self.decision_cooldown = DIRECTOR_COOLDOWN_SPAWN_EVENT
        elif decision_type == 'adjust_npc':
            self.decision_cooldown = DIRECTOR_COOLDOWN_ADJUST_NPC
        elif decision_type == 'give_hint':
            self.decision_cooldown = DIRECTOR_COOLDOWN_GIVE_HINT

        return DirectorDecision(decision_type, data)

    def _build_director_context(
        self,
        scene_id: str,
        scene_state: dict[str, Any],
        dialogue_history: str,
        player_memory: PlayerMemory | None,
        character_id: str,
        last_action: str | None,
    ) -> str:
        """Build context string for director prompt."""

        # Get recent dialogue (last 5 exchanges)
        recent_dialogue = "\n".join(dialogue_history.split("\n")[-10:])

        # Get player personality summary
        personality = player_memory.get_personality_summary() if player_memory else "Unknown player"

        # Check if player is struggling
        scene_attempts = player_memory.scene_attempts.get(scene_id, 0) if player_memory else 0

        # Escape curly braces for LangChain template compatibility
        scene_state_str = json.dumps(scene_state, indent=2).replace('{', '{{').replace('}', '}}')
        pattern_str = 'Struggling - failed multiple times' if scene_attempts >= 2 else 'First attempt or doing well'

        # Determine scene type for context-specific behavior
        scene_type_desc = ""
        if 'submarine' in scene_id.lower():
            scene_type_desc = "This is a SUBMARINE CRISIS scene with oxygen/radiation mechanics."
        elif 'court' in scene_id.lower():
            scene_type_desc = "This is a COURTROOM LEGAL scene with jury sympathy and judge trust."
        elif 'quest' in scene_id.lower():
            scene_type_desc = "This is an ADVENTURE QUEST scene with exploration and challenges."
        else:
            scene_type_desc = "This is a CONVERSATION scene focused on dialogue and character interaction."

        context = f"""=== CURRENT SITUATION ===
Scene: {scene_id}
Scene Type: {scene_type_desc}
Character: {character_id}
Last Player Action: {last_action or 'None'}

Scene State:
{scene_state_str}

Player Profile:
{personality}

Scene History:
- Attempts at this scene: {scene_attempts}
- Pattern: {pattern_str}

Recent Dialogue:
{recent_dialogue}

=== YOUR ROLE ===
You are the dungeon master. Your job is to:
1. Keep the experience engaging and APPROPRIATE TO THE SCENE TYPE
2. Help struggling players without making it too easy
3. Challenge skilled players
4. Create dramatic tension at the right moments
5. Know when to let natural dialogue flow vs when to intervene

CRITICAL: Base your decisions on the SCENE TYPE and STATE VARIABLES shown above.
Do NOT reference mechanics from other scenes (e.g., don't mention oxygen in a courtroom scene).
"""
        return context

    def _parse_director_response(self, response: str) -> dict[str, Any]:
        """Parse the LLM's JSON response."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            data = json.loads(json_str)
            return data
        except Exception as e:
            logger.warning("Failed to parse director response: %s", e)
            logger.debug("Response was: %s", response)
            return {
                'action': 'continue',
                'details': {}
            }

    def generate_dynamic_event(
        self,
        scene_id: str,
        event_type: str,
        event_description: str,
        scene_state: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate a dynamic event that affects the scene.

        Args:
            scene_id: Current scene
            event_type: 'crisis', 'challenge', or 'help'
            event_description: What the event is
            scene_state: Current state to modify

        Returns:
            Event data with state changes and narrative
        """

        event = {
            'type': 'dynamic_event',
            'event_type': event_type,
            'description': event_description,
            'state_changes': {},
            'narrative': ''
        }

        # Get scene-specific constants
        scene_key = 'submarine' if 'submarine' in scene_id.lower() else \
                    'crown_court' if 'court' in scene_id.lower() else 'default'
        scene_constants = SCENE_SPECIFIC_CONSTANTS.get(scene_key, SCENE_SPECIFIC_CONSTANTS['default'])

        # Apply appropriate state changes based on event type
        if event_type == 'crisis':
            # Make situation worse - use scene-appropriate variables
            if 'oxygen' in scene_state:
                event['state_changes']['oxygen'] = -scene_constants['crisis_penalty']
                event['narrative'] = f"[EMERGENCY] {event_description}"
            elif 'jury_sympathy' in scene_state:
                event['state_changes']['jury_sympathy'] = -scene_constants['crisis_penalty']
                event['narrative'] = f"[SETBACK] {event_description}"
            elif 'prosecution_strength' in scene_state:
                event['state_changes']['prosecution_strength'] = scene_constants['crisis_penalty']
                event['narrative'] = f"[COMPLICATION] {event_description}"
            else:
                event['narrative'] = f"[CRISIS] {event_description}"

            # Also affect relationship variable if present
            if 'trust' in scene_state:
                event['state_changes']['trust'] = -10
            elif 'judge_trust' in scene_state:
                event['state_changes']['judge_trust'] = -10

        elif event_type == 'help':
            # Give player a break - use scene-appropriate variables
            if 'oxygen' in scene_state:
                event['state_changes']['oxygen'] = scene_constants['help_bonus']
                event['narrative'] = f"[RELIEF] {event_description}"
            elif 'jury_sympathy' in scene_state:
                event['state_changes']['jury_sympathy'] = scene_constants['help_bonus']
                event['narrative'] = f"[ADVANTAGE] {event_description}"
            elif 'prosecution_strength' in scene_state:
                event['state_changes']['prosecution_strength'] = -scene_constants['help_bonus']
                event['narrative'] = f"[BREAKTHROUGH] {event_description}"
            else:
                event['narrative'] = f"[LUCKY BREAK] {event_description}"

            # Also improve relationship variable if present
            if 'trust' in scene_state:
                event['state_changes']['trust'] = 5
            elif 'judge_trust' in scene_state:
                event['state_changes']['judge_trust'] = 5

        elif event_type == 'challenge':
            # Create tension without being catastrophic
            event['narrative'] = f"[CHALLENGE] {event_description}"

        return event

    def should_force_game_over(
        self,
        scene_id: str,
        scene_state: dict[str, Any],
        player_memory: PlayerMemory | None,
    ) -> str | None:
        """
        Check if director should force an early game over.

        Returns outcome type if game should end, None otherwise.
        """

        # Get scene-specific constants
        scene_key = 'submarine' if 'submarine' in scene_id.lower() else \
                    'crown_court' if 'court' in scene_id.lower() else 'default'
        scene_constants = SCENE_SPECIFIC_CONSTANTS.get(scene_key, SCENE_SPECIFIC_CONSTANTS['default'])

        # Critical failure - resource completely depleted (scene-specific)
        if 'oxygen' in scene_state and scene_state['oxygen'] <= 0:
            return 'failure'

        if 'jury_sympathy' in scene_state and scene_state['jury_sympathy'] <= scene_constants['critical_level']:
            return 'failure'

        # Too many incorrect actions
        if scene_state.get('incorrect_actions', 0) >= scene_constants['max_failures']:
            return 'failure'

        # Relationship completely broken (scene-specific)
        if 'trust' in scene_state and scene_state['trust'] < scene_constants['low_threshold']:
            # Also check if resource is critically low
            if 'oxygen' in scene_state and scene_state['oxygen'] < scene_constants['critical_level']:
                return 'failure'

        if 'judge_trust' in scene_state and scene_state['judge_trust'] < scene_constants['low_threshold']:
            return 'failure'

        return None

    def generate_npc_behavior_adjustment(
        self,
        character_id: str,
        behavior_change: str,
        current_state: dict[str, Any],
        scene_id: str = "unknown",
    ) -> str:
        """
        Generate instruction to adjust NPC behavior mid-scene.

        Returns:
            Instruction suffix to add to NPC prompt
        """

        # Determine resource variable name for scene
        resource_var = 'oxygen' if 'oxygen' in current_state else \
                      'jury_sympathy' if 'jury_sympathy' in current_state else \
                      'time_remaining' if 'time_remaining' in current_state else None

        # Get scene-appropriate critical message
        critical_msg = ""
        if resource_var == 'oxygen':
            critical_msg = f"Oxygen is at {current_state.get('oxygen', 0)}s. Show SERIOUS CONCERN. This is life or death now."
        elif resource_var == 'jury_sympathy':
            critical_msg = f"Jury sympathy is at {current_state.get('jury_sympathy', 0)}%. The case is slipping away."
        elif resource_var == 'time_remaining':
            critical_msg = f"Time is at {current_state.get('time_remaining', 0)}s. The situation is becoming urgent."

        adjustments = {
            'more_helpful': "\n\nDIRECTOR NOTE: The player is struggling. Be MORE HELPFUL with your next response. Give clearer, more specific guidance. Show patience.",

            'more_urgent': "\n\nDIRECTOR NOTE: Situation is getting critical. Show MORE URGENCY and STRESS in your dialogue. Make the stakes feel real.",

            'more_frustrated': "\n\nDIRECTOR NOTE: Player keeps making mistakes. Show FRUSTRATION but not hostility. Express concern for the outcome.",

            'more_trusting': "\n\nDIRECTOR NOTE: Player is doing well. Show CONFIDENCE and TRUST. Be more relaxed and conversational.",

            'more_worried': f"\n\nDIRECTOR NOTE: {critical_msg}" if critical_msg else "\n\nDIRECTOR NOTE: Show SERIOUS CONCERN. The situation is dire.",

            'encouraging': "\n\nDIRECTOR NOTE: Player is improving. Give ENCOURAGEMENT and positive reinforcement. Build their confidence.",
        }

        # Try to match behavior_change to predefined adjustments
        for key, instruction in adjustments.items():
            if key in behavior_change.lower():
                return instruction

        # Fallback - use the raw behavior change
        return f"\n\nDIRECTOR NOTE: {behavior_change}"

    def generate_hint(
        self,
        scene_id: str,
        hint_type: str,
        hint_content: str,
        character_id: str
    ) -> str:
        """
        Generate a hint for struggling players.

        Args:
            scene_id: Current scene
            hint_type: 'subtle' or 'direct'
            hint_content: What to hint at
            character_id: Who gives the hint

        Returns:
            Hint instruction for NPC
        """

        if hint_type == 'subtle':
            return f"\n\nDIRECTOR NOTE: Give a SUBTLE HINT about {hint_content}. Don't tell them directly - hint at it through dialogue."
        else:  # direct
            return f"\n\nDIRECTOR NOTE: Player has failed multiple times. Give a DIRECT, CLEAR instruction about {hint_content}. Be explicit."

    async def evaluate_for_scene_transition(
        self,
        current_scene: str,
        scene_state: dict[str, Any],
        player_memory: PlayerMemory | None,
    ) -> str | None:
        """
        Check if it's time to transition to a new scene.

        Returns:
            Next scene ID if transition recommended, None otherwise
        """

        # For now, let explicit success/failure conditions handle transitions
        # In the future, director could suggest mid-scene transitions
        return None

    def get_difficulty_adjustment(
        self,
        player_memory: PlayerMemory | None,
        scene_id: str,
    ) -> dict[str, Any]:
        """
        Recommend difficulty adjustments based on player performance.

        Returns:
            Dict with penalty/reward multipliers and scene-appropriate bonuses
        """

        if not player_memory:
            return {'penalty_multiplier': 1.0, 'hint_frequency': 'normal', 'resource_bonus': 0}

        # Get player skill level
        success_rate = (
            player_memory.total_successes / max(1, player_memory.total_scenes_played)
        )
        scene_attempts = player_memory.scene_attempts.get(scene_id, 0)

        # Get scene-specific constants
        scene_key = 'submarine' if 'submarine' in scene_id.lower() else \
                    'crown_court' if 'court' in scene_id.lower() else 'default'
        scene_constants = SCENE_SPECIFIC_CONSTANTS.get(scene_key, SCENE_SPECIFIC_CONSTANTS['default'])

        # Struggling player - make it easier
        if (
            success_rate < DIFFICULTY_EASY_SUCCESS_RATE
            or scene_attempts >= DIFFICULTY_SCENE_ATTEMPTS_THRESHOLD
        ):
            adjustment = {
                'penalty_multiplier': DIFFICULTY_EASY_PENALTY_MULTIPLIER,
                'hint_frequency': 'frequent',
                'resource_bonus': 30,  # Generic bonus, applied to appropriate variable
            }
            # Add scene-specific bonus key
            if 'oxygen' in scene_constants['resource_name'] if scene_constants['resource_name'] else False:
                adjustment['oxygen_bonus'] = 30
            return adjustment

        # Skilled player - make it harder
        elif success_rate > DIFFICULTY_HARD_SUCCESS_RATE and scene_attempts < 2:
            adjustment = {
                'penalty_multiplier': DIFFICULTY_HARD_PENALTY_MULTIPLIER,
                'hint_frequency': 'rare',
                'resource_bonus': -30,
            }
            if 'oxygen' in scene_constants['resource_name'] if scene_constants['resource_name'] else False:
                adjustment['oxygen_bonus'] = -30
            return adjustment

        # Normal difficulty
        else:
            return {
                'penalty_multiplier': 1.0,
                'hint_frequency': 'normal',
                'resource_bonus': 0,
                'oxygen_bonus': 0,  # For backward compatibility
            }

def create_world_director() -> WorldDirector:
    """Factory function to create World Director instance."""
    return WorldDirector()
