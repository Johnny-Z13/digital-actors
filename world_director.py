"""
World Director - The Dungeon Master AI

Orchestrates the experience by:
- Evaluating situations after player actions
- Spawning dynamic events to keep things interesting
- Adjusting NPC behavior based on context
- Managing scene transitions
- Personalizing difficulty based on player memory
"""

import json
from typing import Dict, Any, Optional, List
from llm_prompt_core.models.anthropic import ClaudeHaikuModel
from llm_prompt_core.utils import prompt_llm


class DirectorDecision:
    """Represents a decision made by the World Director."""

    def __init__(self, decision_type: str, data: Dict[str, Any]):
        self.type = decision_type  # 'continue', 'event', 'transition', 'adjust_npc', 'hint'
        self.data = data

    def __repr__(self):
        return f"DirectorDecision(type={self.type}, data={self.data})"


class WorldDirector:
    """
    The Dungeon Master AI that orchestrates the experience.

    Runs after player actions to decide what should happen next.
    """

    def __init__(self):
        self.model = ClaudeHaikuModel(temperature=0.7, max_tokens=500)
        self.decision_cooldown = 0  # Prevent too-frequent interventions

    async def evaluate_situation(
        self,
        scene_id: str,
        scene_state: Dict[str, Any],
        dialogue_history: str,
        player_memory: Any,
        character_id: str,
        last_action: str = None
    ) -> DirectorDecision:
        """
        Evaluate the current situation and decide what should happen next.

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
{{
    "assessment": "brief analysis of current situation",
    "tension_level": "low/medium/high",
    "player_struggling": true/false,
    "action": "continue/spawn_event/adjust_npc/give_hint/transition",
    "details": {{
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
    }}
}}"""

        # Get director decision
        try:
            chain = prompt_llm(prompt, self.model)
            response = chain.invoke({})

            # Parse JSON response
            decision_data = self._parse_director_response(response)

            # Set cooldown based on action type
            if decision_data['action'] == 'spawn_event':
                self.decision_cooldown = 5  # Don't spawn events too frequently
            elif decision_data['action'] == 'adjust_npc':
                self.decision_cooldown = 3
            elif decision_data['action'] == 'give_hint':
                self.decision_cooldown = 4

            return DirectorDecision(decision_data['action'], decision_data['details'])

        except Exception as e:
            print(f"World Director error: {e}")
            return DirectorDecision('continue', {})

    def _build_director_context(
        self,
        scene_id: str,
        scene_state: Dict[str, Any],
        dialogue_history: str,
        player_memory: Any,
        character_id: str,
        last_action: str
    ) -> str:
        """Build context string for director prompt."""

        # Get recent dialogue (last 5 exchanges)
        recent_dialogue = "\n".join(dialogue_history.split("\n")[-10:])

        # Get player personality summary
        personality = player_memory.get_personality_summary() if player_memory else "Unknown player"

        # Check if player is struggling
        scene_attempts = player_memory.scene_attempts.get(scene_id, 0) if player_memory else 0

        context = f"""=== CURRENT SITUATION ===
Scene: {scene_id}
Character: {character_id}
Last Player Action: {last_action or 'None'}

Scene State:
{json.dumps(scene_state, indent=2)}

Player Profile:
{personality}

Scene History:
- Attempts at this scene: {scene_attempts}
- Pattern: {'Struggling - failed multiple times' if scene_attempts >= 2 else 'First attempt or doing well'}

Recent Dialogue:
{recent_dialogue}

=== YOUR ROLE ===
You are the dungeon master. Your job is to:
1. Keep the experience engaging
2. Help struggling players without making it too easy
3. Challenge skilled players
4. Create dramatic tension at the right moments
5. Know when to let natural dialogue flow vs when to intervene
"""
        return context

    def _parse_director_response(self, response: str) -> Dict[str, Any]:
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
            print(f"Failed to parse director response: {e}")
            print(f"Response was: {response}")
            return {
                'action': 'continue',
                'details': {}
            }

    def generate_dynamic_event(
        self,
        scene_id: str,
        event_type: str,
        event_description: str,
        scene_state: Dict[str, Any]
    ) -> Dict[str, Any]:
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

        # Apply appropriate state changes based on event type
        if event_type == 'crisis':
            # Make situation worse
            if 'oxygen' in scene_state:
                event['state_changes']['oxygen'] = -20
                event['narrative'] = f"[EMERGENCY] {event_description} - Oxygen dropping fast!"
            if 'trust' in scene_state:
                event['state_changes']['trust'] = -10

        elif event_type == 'help':
            # Give player a break
            if 'oxygen' in scene_state:
                event['state_changes']['oxygen'] = 15
                event['narrative'] = f"[LUCKY BREAK] {event_description} - You gained some oxygen!"
            if 'trust' in scene_state:
                event['state_changes']['trust'] = 5

        elif event_type == 'challenge':
            # Create tension without being catastrophic
            event['narrative'] = f"[CHALLENGE] {event_description}"

        return event

    def should_force_game_over(
        self,
        scene_state: Dict[str, Any],
        player_memory: Any
    ) -> Optional[str]:
        """
        Check if director should force an early game over.

        Returns outcome type if game should end, None otherwise.
        """

        # Critical failure - oxygen completely depleted
        if scene_state.get('oxygen', 999) <= 0:
            return 'failure'

        # Too many incorrect actions
        if scene_state.get('incorrect_actions', 0) >= 5:
            return 'failure'

        # Trust completely broken + low oxygen
        if scene_state.get('trust', 0) < -50 and scene_state.get('oxygen', 999) < 60:
            return 'failure'

        return None

    def generate_npc_behavior_adjustment(
        self,
        character_id: str,
        behavior_change: str,
        current_state: Dict[str, Any]
    ) -> str:
        """
        Generate instruction to adjust NPC behavior mid-scene.

        Returns:
            Instruction suffix to add to NPC prompt
        """

        adjustments = {
            'more_helpful': "\n\nDIRECTOR NOTE: The player is struggling. Be MORE HELPFUL with your next response. Give clearer, more specific instructions. Show patience.",

            'more_urgent': "\n\nDIRECTOR NOTE: Situation is getting critical. Show MORE URGENCY and STRESS in your dialogue. Make the danger feel real.",

            'more_frustrated': "\n\nDIRECTOR NOTE: Player keeps making mistakes. Show FRUSTRATION but not hostility. Express concern about their safety.",

            'more_trusting': "\n\nDIRECTOR NOTE: Player is doing well. Show CONFIDENCE and TRUST. Be more relaxed and conversational.",

            'more_worried': f"\n\nDIRECTOR NOTE: Oxygen is at {current_state.get('oxygen', 0)}s. Show SERIOUS CONCERN. This is life or death now.",

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
        scene_state: Dict[str, Any],
        player_memory: Any
    ) -> Optional[str]:
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
        player_memory: Any,
        scene_id: str
    ) -> Dict[str, Any]:
        """
        Recommend difficulty adjustments based on player performance.

        Returns:
            Dict with penalty/reward multipliers
        """

        if not player_memory:
            return {'penalty_multiplier': 1.0, 'hint_frequency': 'normal'}

        # Get player skill level
        success_rate = (
            player_memory.total_successes / max(1, player_memory.total_scenes_played)
        )
        scene_attempts = player_memory.scene_attempts.get(scene_id, 0)

        # Struggling player - make it easier
        if success_rate < 0.3 or scene_attempts >= 3:
            return {
                'penalty_multiplier': 0.7,  # 30% less harsh penalties
                'hint_frequency': 'frequent',
                'oxygen_bonus': 30,  # Start with more oxygen
            }

        # Skilled player - make it harder
        elif success_rate > 0.8 and scene_attempts < 2:
            return {
                'penalty_multiplier': 1.3,  # 30% harsher penalties
                'hint_frequency': 'rare',
                'oxygen_bonus': -30,  # Start with less oxygen
            }

        # Normal difficulty
        else:
            return {
                'penalty_multiplier': 1.0,
                'hint_frequency': 'normal',
                'oxygen_bonus': 0,
            }


def create_world_director() -> WorldDirector:
    """Factory function to create World Director instance."""
    return WorldDirector()
