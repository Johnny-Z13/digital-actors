"""
Unit tests for WorldDirector

Tests director decision making, difficulty adjustments, context building,
and integration with the rules engine.
"""

import sys
import os

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json
import time

from world_director import (
    WorldDirector,
    DirectorDecision,
    TemporalState,
    SCENE_SPECIFIC_CONSTANTS,
    create_world_director,
)
from director_rules import RuleAction, RuleDecision
from player_memory import PlayerMemory


class TestTemporalState(unittest.TestCase):
    """Test TemporalState dataclass for trend tracking."""

    def setUp(self):
        """Set up test fixtures."""
        self.temporal_state = TemporalState()

    def test_default_state(self):
        """Test default TemporalState values."""
        self.assertEqual(self.temporal_state.oxygen_trend, "stable")
        self.assertEqual(self.temporal_state.engagement_trend, "stable")
        self.assertEqual(self.temporal_state.recent_actions, [])
        self.assertEqual(self.temporal_state.time_since_last_beat, 0.0)
        self.assertEqual(self.temporal_state.dialogue_density, 0.0)
        self.assertEqual(self.temporal_state.phase_duration, 0.0)

    def test_update_oxygen_stable(self):
        """Test oxygen tracking remains stable."""
        self.temporal_state.update_oxygen(100.0)
        self.temporal_state.update_oxygen(99.5)
        self.temporal_state.update_oxygen(99.0)

        self.assertEqual(self.temporal_state.oxygen_trend, "stable")

    def test_update_oxygen_declining(self):
        """Test oxygen tracking detects declining trend."""
        self.temporal_state.update_oxygen(100.0)
        self.temporal_state.update_oxygen(98.5)
        self.temporal_state.update_oxygen(96.5)

        self.assertEqual(self.temporal_state.oxygen_trend, "declining")

    def test_update_oxygen_critical_decline(self):
        """Test oxygen tracking detects critical decline."""
        self.temporal_state.update_oxygen(100.0)
        self.temporal_state.update_oxygen(93.0)
        self.temporal_state.update_oxygen(86.0)

        self.assertEqual(self.temporal_state.oxygen_trend, "critical_decline")

    def test_record_action(self):
        """Test recording player actions."""
        timestamp = time.time()
        self.temporal_state.record_action("check_valve", timestamp)

        self.assertEqual(len(self.temporal_state.recent_actions), 1)
        self.assertIn("check_valve", self.temporal_state.recent_actions)

    def test_record_action_max_limit(self):
        """Test that recent actions are limited to last 5."""
        timestamp = time.time()
        for i in range(10):
            self.temporal_state.record_action(f"action_{i}", timestamp + i)

        self.assertEqual(len(self.temporal_state.recent_actions), 5)
        self.assertEqual(self.temporal_state.recent_actions[-1], "action_9")

    def test_dialogue_density_calculation(self):
        """Test dialogue density (actions per minute) calculation."""
        base_time = time.time()
        # 3 actions in 30 seconds = 6 actions per minute
        self.temporal_state.record_action("action_1", base_time)
        self.temporal_state.record_action("action_2", base_time + 15)
        self.temporal_state.record_action("action_3", base_time + 30)

        # Should be around 6 actions per minute
        self.assertGreater(self.temporal_state.dialogue_density, 3.0)

    def test_engagement_trend_increasing(self):
        """Test engagement trend detection for active player."""
        base_time = time.time()
        # Rapid actions = high engagement
        for i in range(5):
            self.temporal_state.record_action(f"action_{i}", base_time + i * 5)

        self.assertEqual(self.temporal_state.engagement_trend, "increasing")

    def test_engagement_trend_declining(self):
        """Test engagement trend detection for inactive player."""
        base_time = time.time()
        # Slow actions = low engagement (< 1 per minute)
        # 2 actions in 150 seconds = 0.8 actions per minute
        self.temporal_state.record_action("action_1", base_time)
        self.temporal_state.record_action("action_2", base_time + 150)

        # Should be < 1 action per minute = declining
        self.assertEqual(self.temporal_state.engagement_trend, "declining")

    def test_reset(self):
        """Test resetting temporal state."""
        # Set up some state
        self.temporal_state.update_oxygen(50.0)
        self.temporal_state.record_action("test", time.time())
        self.temporal_state.oxygen_trend = "critical_decline"

        # Reset
        self.temporal_state.reset()

        # Verify reset
        self.assertEqual(self.temporal_state.oxygen_trend, "stable")
        self.assertEqual(self.temporal_state.recent_actions, [])
        self.assertEqual(self.temporal_state._oxygen_history, [])
        self.assertEqual(self.temporal_state._action_timestamps, [])


class TestDirectorDecision(unittest.TestCase):
    """Test DirectorDecision class."""

    def test_create_continue_decision(self):
        """Test creating a continue decision."""
        decision = DirectorDecision('continue', {})

        self.assertEqual(decision.type, 'continue')
        self.assertEqual(decision.data, {})

    def test_create_spawn_event_decision(self):
        """Test creating a spawn event decision."""
        data = {
            'event_type': 'crisis',
            'event_description': 'Oxygen leak detected'
        }
        decision = DirectorDecision('spawn_event', data)

        self.assertEqual(decision.type, 'spawn_event')
        self.assertEqual(decision.data['event_type'], 'crisis')

    def test_decision_repr(self):
        """Test DirectorDecision string representation."""
        decision = DirectorDecision('give_hint', {'hint_type': 'subtle'})
        repr_str = repr(decision)

        self.assertIn('give_hint', repr_str)
        self.assertIn('hint_type', repr_str)


class TestWorldDirectorInit(unittest.TestCase):
    """Test WorldDirector initialization."""

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_init(self, mock_rules, mock_model):
        """Test WorldDirector initialization."""
        director = WorldDirector()

        # Verify model was created
        mock_model.assert_called_once()

        # Verify rules engine was retrieved
        mock_rules.assert_called_once()

        # Verify initial state
        self.assertEqual(director.decision_cooldown, 0)
        self.assertIsNotNone(director.temporal_state)
        self.assertIsNotNone(director.scene_start_time)

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_reset_scene_timing(self, mock_rules, mock_model):
        """Test resetting scene timing."""
        mock_rules_instance = Mock()
        mock_rules.return_value = mock_rules_instance

        director = WorldDirector()

        # Set up some state
        director.decision_cooldown = 10
        director.temporal_state.oxygen_trend = "critical_decline"

        old_start_time = director.scene_start_time
        time.sleep(0.01)  # Small delay to ensure time changes

        # Reset
        director.reset_scene_timing()

        # Verify reset
        self.assertEqual(director.decision_cooldown, 0)
        self.assertEqual(director.temporal_state.oxygen_trend, "stable")
        self.assertGreater(director.scene_start_time, old_start_time)
        mock_rules_instance.reset_cooldowns.assert_called_once()

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_record_player_action(self, mock_rules, mock_model):
        """Test recording player actions."""
        director = WorldDirector()

        old_action_time = director.last_player_action_time
        time.sleep(0.01)

        director.record_player_action("check_valve")

        # Verify action was recorded
        self.assertGreater(director.last_player_action_time, old_action_time)
        self.assertIn("check_valve", director.temporal_state.recent_actions)

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_update_oxygen_tracking(self, mock_rules, mock_model):
        """Test updating oxygen tracking."""
        director = WorldDirector()

        director.update_oxygen_tracking(75.0)
        director.update_oxygen_tracking(72.0)
        director.update_oxygen_tracking(70.0)

        # Should detect declining trend (3.5 decline > 2)
        self.assertEqual(director.temporal_state.oxygen_trend, "declining")

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_get_temporal_context(self, mock_rules, mock_model):
        """Test getting temporal context."""
        director = WorldDirector()

        director.temporal_state.oxygen_trend = "critical_decline"
        director.temporal_state.engagement_trend = "increasing"
        director.temporal_state.dialogue_density = 5.2

        context = director.get_temporal_context()

        self.assertEqual(context['oxygen_trend'], "critical_decline")
        self.assertEqual(context['engagement_trend'], "increasing")
        self.assertIn("5.2", context['dialogue_density'])
        self.assertIn('phase_duration', context)


class TestWorldDirectorRulesIntegration(unittest.TestCase):
    """Test WorldDirector integration with rules engine."""

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_convert_rule_continue(self, mock_rules, mock_model):
        """Test converting CONTINUE rule to decision."""
        director = WorldDirector()

        rule_decision = RuleDecision(
            action=RuleAction.CONTINUE,
            reason="Normal flow"
        )

        decision = director._convert_rule_to_decision(rule_decision)

        self.assertEqual(decision.type, 'continue')
        self.assertEqual(decision.data, {})

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_convert_rule_advance_phase(self, mock_rules, mock_model):
        """Test converting ADVANCE_PHASE rule to decision."""
        director = WorldDirector()

        rule_decision = RuleDecision(
            action=RuleAction.ADVANCE_PHASE,
            data={'from_phase': 1, 'to_phase': 2},
            reason="Time elapsed"
        )

        decision = director._convert_rule_to_decision(rule_decision)

        self.assertEqual(decision.type, 'continue')  # Phase handled by state loop

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_convert_rule_trigger_urgency(self, mock_rules, mock_model):
        """Test converting TRIGGER_URGENCY rule to decision."""
        director = WorldDirector()

        rule_decision = RuleDecision(
            action=RuleAction.TRIGGER_URGENCY,
            data={'behavior_change': 'more_urgent'},
            reason="Oxygen low"
        )

        decision = director._convert_rule_to_decision(rule_decision)

        self.assertEqual(decision.type, 'adjust_npc')
        self.assertIn('behavior_change', decision.data)

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_convert_rule_give_hint(self, mock_rules, mock_model):
        """Test converting GIVE_HINT rule to decision."""
        director = WorldDirector()

        rule_decision = RuleDecision(
            action=RuleAction.GIVE_HINT,
            data={'hint_type': 'direct', 'hint_content': 'Check the valve'},
            reason="Player struggling"
        )

        decision = director._convert_rule_to_decision(rule_decision)

        self.assertEqual(decision.type, 'give_hint')
        self.assertEqual(decision.data['hint_type'], 'direct')

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_convert_rule_spawn_crisis(self, mock_rules, mock_model):
        """Test converting SPAWN_CRISIS rule to decision."""
        director = WorldDirector()

        rule_decision = RuleDecision(
            action=RuleAction.SPAWN_CRISIS,
            data={'event_type': 'crisis', 'event_description': 'Oxygen leak'},
            reason="Critical oxygen"
        )

        decision = director._convert_rule_to_decision(rule_decision)

        self.assertEqual(decision.type, 'spawn_event')
        self.assertEqual(decision.data['event_type'], 'crisis')


class TestWorldDirectorEvaluateSituation(unittest.IsolatedAsyncioTestCase):
    """Test WorldDirector.evaluate_situation method."""

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    async def test_evaluate_events_disabled(self, mock_rules, mock_model):
        """Test evaluation when events are disabled for scene."""
        director = WorldDirector()

        decision = await director.evaluate_situation(
            scene_id='iconic_detectives',  # Has disable_events=True
            scene_state={'trust': 50},
            dialogue_history="Test dialogue",
            player_memory=None,
            character_id='holmes'
        )

        self.assertEqual(decision.type, 'continue')

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    async def test_evaluate_rule_matched(self, mock_rules, mock_model):
        """Test evaluation when rules engine matches."""
        mock_rules_instance = Mock()
        mock_rules.return_value = mock_rules_instance

        # Rules engine returns a decision
        mock_rules_instance.evaluate.return_value = RuleDecision(
            action=RuleAction.GIVE_HINT,
            data={'hint_type': 'subtle'},
            reason="Player struggling"
        )

        director = WorldDirector()

        decision = await director.evaluate_situation(
            scene_id='submarine',
            scene_state={'oxygen': 50, 'phase': 2},
            dialogue_history="Test dialogue",
            player_memory=None,
            character_id='engineer'
        )

        # Should convert rule to decision without LLM call
        self.assertEqual(decision.type, 'give_hint')
        mock_rules_instance.evaluate.assert_called_once()

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    @patch('world_director.prompt_llm')
    async def test_evaluate_llm_consultation(self, mock_prompt, mock_rules, mock_model):
        """Test evaluation when LLM consultation is needed."""
        mock_rules_instance = Mock()
        mock_rules.return_value = mock_rules_instance

        # Rules engine defers to LLM
        mock_rules_instance.evaluate.return_value = RuleDecision(
            action=RuleAction.CONSULT_LLM,
            reason="No rule matched"
        )

        # Mock LLM response - use Mock with return_value, not AsyncMock
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value=json.dumps({
            'action': 'spawn_event',
            'details': {
                'event_type': 'challenge',
                'event_description': 'New challenge appears'
            }
        }))
        mock_prompt.return_value = mock_chain

        director = WorldDirector()
        director.decision_cooldown = 0  # Ensure not on cooldown

        decision = await director.evaluate_situation(
            scene_id='submarine',
            scene_state={'oxygen': 75, 'phase': 2},
            dialogue_history="Test dialogue",
            player_memory=None,
            character_id='engineer'
        )

        self.assertEqual(decision.type, 'spawn_event')
        mock_prompt.assert_called_once()

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    async def test_evaluate_cooldown_active(self, mock_rules, mock_model):
        """Test evaluation respects cooldown."""
        mock_rules_instance = Mock()
        mock_rules.return_value = mock_rules_instance

        # Rules engine defers to LLM
        mock_rules_instance.evaluate.return_value = RuleDecision(
            action=RuleAction.CONSULT_LLM,
            reason="No rule matched"
        )

        director = WorldDirector()
        director.decision_cooldown = 10  # Active cooldown

        decision = await director.evaluate_situation(
            scene_id='submarine',
            scene_state={'oxygen': 75, 'phase': 2},
            dialogue_history="Test dialogue",
            player_memory=None,
            character_id='engineer'
        )

        # Should return continue due to cooldown
        self.assertEqual(decision.type, 'continue')
        self.assertEqual(director.decision_cooldown, 9)  # Decremented

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    @patch('world_director.prompt_llm')
    async def test_evaluate_llm_error_handling(self, mock_prompt, mock_rules, mock_model):
        """Test evaluation handles LLM errors gracefully."""
        mock_rules_instance = Mock()
        mock_rules.return_value = mock_rules_instance

        mock_rules_instance.evaluate.return_value = RuleDecision(
            action=RuleAction.CONSULT_LLM,
            reason="No rule matched"
        )

        # Mock LLM to raise exception
        mock_chain = AsyncMock()
        mock_chain.invoke.side_effect = Exception("LLM error")
        mock_prompt.return_value = mock_chain

        director = WorldDirector()
        director.decision_cooldown = 0

        decision = await director.evaluate_situation(
            scene_id='submarine',
            scene_state={'oxygen': 75, 'phase': 2},
            dialogue_history="Test dialogue",
            player_memory=None,
            character_id='engineer'
        )

        # Should return continue on error
        self.assertEqual(decision.type, 'continue')


class TestBuildDirectorContext(unittest.TestCase):
    """Test context building for LLM prompts."""

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_build_context_submarine(self, mock_rules, mock_model):
        """Test building context for submarine scene."""
        director = WorldDirector()

        mock_memory = Mock()
        mock_memory.get_personality_summary.return_value = "Impulsive player"
        mock_memory.scene_attempts = {'submarine': 0}

        context = director._build_director_context(
            scene_id='submarine',
            scene_state={'oxygen': 75, 'trust': 60, 'phase': 2},
            dialogue_history="Player: What should I do?\nEngineer: Check the valve!",
            player_memory=mock_memory,
            character_id='engineer',
            last_action='check_valve'
        )

        self.assertIn('submarine', context.lower())
        self.assertIn('oxygen', context.lower())
        self.assertIn('Impulsive player', context)
        self.assertIn('check_valve', context)

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_build_context_court(self, mock_rules, mock_model):
        """Test building context for courtroom scene."""
        director = WorldDirector()

        mock_memory = Mock()
        mock_memory.get_personality_summary.return_value = "Patient player"
        mock_memory.scene_attempts = {'crown_court': 1}

        context = director._build_director_context(
            scene_id='crown_court',
            scene_state={'jury_sympathy': 50, 'judge_trust': 70},
            dialogue_history="Judge: Proceed with caution.",
            player_memory=mock_memory,
            character_id='judge',
            last_action='object_to_evidence'
        )

        self.assertIn('court', context.lower())
        self.assertIn('jury sympathy', context.lower())
        # Context should describe courtroom, not submarine
        self.assertNotIn('submarine', context.lower())

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_build_context_struggling_player(self, mock_rules, mock_model):
        """Test context indicates struggling player."""
        director = WorldDirector()

        mock_memory = Mock()
        mock_memory.get_personality_summary.return_value = "New player"
        mock_memory.scene_attempts = {'submarine': 3}  # Multiple attempts

        context = director._build_director_context(
            scene_id='submarine',
            scene_state={'oxygen': 50},
            dialogue_history="",
            player_memory=mock_memory,
            character_id='engineer',
            last_action=None
        )

        self.assertIn('3', context)
        self.assertIn('Struggling', context)

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_build_context_no_memory(self, mock_rules, mock_model):
        """Test building context without player memory."""
        director = WorldDirector()

        context = director._build_director_context(
            scene_id='submarine',
            scene_state={'oxygen': 75},
            dialogue_history="Test",
            player_memory=None,
            character_id='engineer',
            last_action='test_action'
        )

        self.assertIn('Unknown player', context)
        self.assertIn('0', context)  # 0 attempts


class TestParseDirectorResponse(unittest.TestCase):
    """Test parsing LLM responses."""

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_parse_valid_json(self, mock_rules, mock_model):
        """Test parsing valid JSON response."""
        director = WorldDirector()

        response = json.dumps({
            'action': 'spawn_event',
            'details': {'event_type': 'crisis'}
        })

        parsed = director._parse_director_response(response)

        self.assertEqual(parsed['action'], 'spawn_event')
        self.assertEqual(parsed['details']['event_type'], 'crisis')

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_parse_json_with_markdown(self, mock_rules, mock_model):
        """Test parsing JSON wrapped in markdown code blocks."""
        director = WorldDirector()

        response = """```json
        {
            "action": "give_hint",
            "details": {"hint_type": "subtle"}
        }
        ```"""

        parsed = director._parse_director_response(response)

        self.assertEqual(parsed['action'], 'give_hint')

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_parse_invalid_json(self, mock_rules, mock_model):
        """Test parsing invalid JSON falls back to continue."""
        director = WorldDirector()

        response = "This is not valid JSON"

        parsed = director._parse_director_response(response)

        self.assertEqual(parsed['action'], 'continue')
        self.assertEqual(parsed['details'], {})


class TestGenerateDynamicEvent(unittest.TestCase):
    """Test dynamic event generation."""

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_generate_crisis_event_submarine(self, mock_rules, mock_model):
        """Test generating crisis event for submarine scene."""
        director = WorldDirector()

        event = director.generate_dynamic_event(
            scene_id='submarine',
            event_type='crisis',
            event_description='Oxygen line rupture',
            scene_state={'oxygen': 75, 'trust': 60}
        )

        self.assertEqual(event['type'], 'dynamic_event')
        self.assertEqual(event['event_type'], 'crisis')
        self.assertIn('oxygen', event['state_changes'])
        self.assertLess(event['state_changes']['oxygen'], 0)  # Negative change
        self.assertIn('trust', event['state_changes'])
        self.assertIn('EMERGENCY', event['narrative'])

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_generate_help_event_submarine(self, mock_rules, mock_model):
        """Test generating help event for submarine scene."""
        director = WorldDirector()

        event = director.generate_dynamic_event(
            scene_id='submarine',
            event_type='help',
            event_description='Emergency oxygen tank found',
            scene_state={'oxygen': 30, 'trust': 40}
        )

        self.assertEqual(event['event_type'], 'help')
        self.assertIn('oxygen', event['state_changes'])
        self.assertGreater(event['state_changes']['oxygen'], 0)  # Positive change
        self.assertIn('RELIEF', event['narrative'])

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_generate_crisis_event_courtroom(self, mock_rules, mock_model):
        """Test generating crisis event for courtroom scene."""
        director = WorldDirector()

        event = director.generate_dynamic_event(
            scene_id='crown_court',
            event_type='crisis',
            event_description='Damaging testimony revealed',
            scene_state={'jury_sympathy': 60, 'judge_trust': 70}
        )

        self.assertIn('jury_sympathy', event['state_changes'])
        self.assertLess(event['state_changes']['jury_sympathy'], 0)
        self.assertIn('SETBACK', event['narrative'])

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_generate_challenge_event(self, mock_rules, mock_model):
        """Test generating challenge event."""
        director = WorldDirector()

        event = director.generate_dynamic_event(
            scene_id='submarine',
            event_type='challenge',
            event_description='New complication arises',
            scene_state={'oxygen': 75}
        )

        self.assertEqual(event['event_type'], 'challenge')
        self.assertIn('CHALLENGE', event['narrative'])


class TestShouldForceGameOver(unittest.TestCase):
    """Test game over conditions."""

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_oxygen_depleted(self, mock_rules, mock_model):
        """Test game over when oxygen depleted."""
        director = WorldDirector()

        result = director.should_force_game_over(
            scene_id='submarine',
            scene_state={'oxygen': 0, 'trust': 50},
            player_memory=None
        )

        self.assertEqual(result, 'failure')

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_oxygen_still_remaining(self, mock_rules, mock_model):
        """Test no game over when oxygen still remains."""
        director = WorldDirector()

        result = director.should_force_game_over(
            scene_id='submarine',
            scene_state={'oxygen': 25, 'trust': 50},
            player_memory=None
        )

        self.assertIsNone(result)

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_too_many_failures(self, mock_rules, mock_model):
        """Test game over when too many incorrect actions."""
        director = WorldDirector()

        result = director.should_force_game_over(
            scene_id='submarine',
            scene_state={'oxygen': 75, 'incorrect_actions': 5},
            player_memory=None
        )

        self.assertEqual(result, 'failure')

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_trust_broken_with_low_oxygen(self, mock_rules, mock_model):
        """Test game over when trust is low and oxygen critical."""
        director = WorldDirector()

        # Both trust < -50 (low_threshold) AND oxygen < 60 (critical_level for submarine)
        result = director.should_force_game_over(
            scene_id='submarine',
            scene_state={'oxygen': 55, 'trust': -60},
            player_memory=None
        )

        self.assertEqual(result, 'failure')

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_jury_sympathy_critical(self, mock_rules, mock_model):
        """Test game over when jury sympathy too low."""
        director = WorldDirector()

        result = director.should_force_game_over(
            scene_id='crown_court',
            scene_state={'jury_sympathy': 15, 'judge_trust': 50},
            player_memory=None
        )

        self.assertEqual(result, 'failure')


class TestNPCBehaviorAdjustment(unittest.TestCase):
    """Test NPC behavior adjustment generation."""

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_more_helpful_adjustment(self, mock_rules, mock_model):
        """Test generating more helpful behavior."""
        director = WorldDirector()

        instruction = director.generate_npc_behavior_adjustment(
            character_id='engineer',
            behavior_change='more_helpful',
            current_state={'oxygen': 60}
        )

        self.assertIn('MORE HELPFUL', instruction)
        self.assertIn('DIRECTOR NOTE', instruction)

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_more_urgent_adjustment_with_oxygen(self, mock_rules, mock_model):
        """Test urgent behavior with oxygen context."""
        director = WorldDirector()

        instruction = director.generate_npc_behavior_adjustment(
            character_id='engineer',
            behavior_change='more_urgent',
            current_state={'oxygen': 25},
            scene_id='submarine'
        )

        self.assertIn('URGENCY', instruction)
        self.assertIn('DIRECTOR NOTE', instruction)

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_more_worried_adjustment(self, mock_rules, mock_model):
        """Test worried behavior adjustment."""
        director = WorldDirector()

        instruction = director.generate_npc_behavior_adjustment(
            character_id='engineer',
            behavior_change='more_worried',
            current_state={'oxygen': 15}
        )

        self.assertIn('CONCERN', instruction)

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_custom_behavior_change(self, mock_rules, mock_model):
        """Test custom behavior change fallback."""
        director = WorldDirector()

        instruction = director.generate_npc_behavior_adjustment(
            character_id='engineer',
            behavior_change='show skepticism',
            current_state={'trust': 30}
        )

        self.assertIn('show skepticism', instruction)
        self.assertIn('DIRECTOR NOTE', instruction)


class TestGenerateHint(unittest.TestCase):
    """Test hint generation."""

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_subtle_hint(self, mock_rules, mock_model):
        """Test generating subtle hint."""
        director = WorldDirector()

        hint = director.generate_hint(
            scene_id='submarine',
            hint_type='subtle',
            hint_content='check the oxygen valve',
            character_id='engineer'
        )

        self.assertIn('SUBTLE', hint)
        self.assertIn('check the oxygen valve', hint)
        self.assertIn("Don't tell them directly", hint)

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_direct_hint(self, mock_rules, mock_model):
        """Test generating direct hint."""
        director = WorldDirector()

        hint = director.generate_hint(
            scene_id='submarine',
            hint_type='direct',
            hint_content='open the emergency valve',
            character_id='engineer'
        )

        self.assertIn('DIRECT', hint)
        self.assertIn('CLEAR', hint)
        self.assertIn('open the emergency valve', hint)


class TestDifficultyAdjustment(unittest.TestCase):
    """Test difficulty adjustment based on player performance."""

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_easy_difficulty_low_success_rate(self, mock_rules, mock_model):
        """Test easy difficulty for struggling player."""
        director = WorldDirector()

        mock_memory = Mock()
        mock_memory.total_successes = 1
        mock_memory.total_scenes_played = 5
        mock_memory.scene_attempts = {'submarine': 1}

        adjustment = director.get_difficulty_adjustment(mock_memory, 'submarine')

        self.assertLess(adjustment['penalty_multiplier'], 1.0)
        self.assertEqual(adjustment['hint_frequency'], 'frequent')
        self.assertGreater(adjustment['resource_bonus'], 0)

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_easy_difficulty_many_attempts(self, mock_rules, mock_model):
        """Test easy difficulty for player with many failed attempts."""
        director = WorldDirector()

        mock_memory = Mock()
        mock_memory.total_successes = 3
        mock_memory.total_scenes_played = 5
        mock_memory.scene_attempts = {'submarine': 4}  # Many attempts

        adjustment = director.get_difficulty_adjustment(mock_memory, 'submarine')

        self.assertLess(adjustment['penalty_multiplier'], 1.0)
        self.assertEqual(adjustment['hint_frequency'], 'frequent')

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_hard_difficulty_high_success(self, mock_rules, mock_model):
        """Test hard difficulty for skilled player."""
        director = WorldDirector()

        mock_memory = Mock()
        mock_memory.total_successes = 9
        mock_memory.total_scenes_played = 10
        mock_memory.scene_attempts = {'submarine': 0}

        adjustment = director.get_difficulty_adjustment(mock_memory, 'submarine')

        self.assertGreater(adjustment['penalty_multiplier'], 1.0)
        self.assertEqual(adjustment['hint_frequency'], 'rare')
        self.assertLess(adjustment['resource_bonus'], 0)

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_normal_difficulty(self, mock_rules, mock_model):
        """Test normal difficulty for average player."""
        director = WorldDirector()

        mock_memory = Mock()
        mock_memory.total_successes = 5
        mock_memory.total_scenes_played = 10
        mock_memory.scene_attempts = {'submarine': 1}

        adjustment = director.get_difficulty_adjustment(mock_memory, 'submarine')

        self.assertEqual(adjustment['penalty_multiplier'], 1.0)
        self.assertEqual(adjustment['hint_frequency'], 'normal')
        self.assertEqual(adjustment['resource_bonus'], 0)

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_no_memory(self, mock_rules, mock_model):
        """Test difficulty adjustment without player memory."""
        director = WorldDirector()

        adjustment = director.get_difficulty_adjustment(None, 'submarine')

        self.assertEqual(adjustment['penalty_multiplier'], 1.0)
        self.assertEqual(adjustment['hint_frequency'], 'normal')


class TestSceneTransition(unittest.IsolatedAsyncioTestCase):
    """Test scene transition evaluation."""

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    async def test_evaluate_for_scene_transition(self, mock_rules, mock_model):
        """Test scene transition evaluation (currently returns None)."""
        director = WorldDirector()

        result = await director.evaluate_for_scene_transition(
            current_scene='submarine',
            scene_state={'oxygen': 50},
            player_memory=None
        )

        # Currently not implemented - returns None
        self.assertIsNone(result)


class TestFactoryFunction(unittest.TestCase):
    """Test factory function."""

    @patch('world_director.ClaudeHaikuModel')
    @patch('world_director.get_director_rules')
    def test_create_world_director(self, mock_rules, mock_model):
        """Test factory function creates WorldDirector."""
        director = create_world_director()

        self.assertIsInstance(director, WorldDirector)


class TestSceneSpecificConstants(unittest.TestCase):
    """Test scene-specific constants."""

    def test_submarine_constants(self):
        """Test submarine scene constants."""
        constants = SCENE_SPECIFIC_CONSTANTS['submarine']

        self.assertEqual(constants['critical_level'], 60)
        self.assertEqual(constants['resource_name'], 'oxygen')
        self.assertEqual(constants['relationship_name'], 'trust')
        self.assertFalse(constants.get('disable_events', False))

    def test_crown_court_constants(self):
        """Test crown court scene constants."""
        constants = SCENE_SPECIFIC_CONSTANTS['crown_court']

        self.assertEqual(constants['critical_level'], 20)
        self.assertEqual(constants['resource_name'], 'jury_sympathy')
        self.assertEqual(constants['relationship_name'], 'judge_trust')

    def test_iconic_detectives_constants(self):
        """Test iconic detectives scene constants."""
        constants = SCENE_SPECIFIC_CONSTANTS['iconic_detectives']

        self.assertEqual(constants['critical_level'], 25)
        self.assertTrue(constants['disable_events'])  # No random events in phone call


if __name__ == '__main__':
    unittest.main()
