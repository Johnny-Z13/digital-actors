"""
Unit tests for the refactored session components.

Tests the focused session modules:
- ResponseHandler
- GameStateManager
- DialogueEngine
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest


class TestResponseHandler:
    """Test ResponseHandler class."""

    @pytest.fixture
    def mock_ws(self):
        """Create a mock WebSocket."""
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        return ws

    @pytest.fixture
    def mock_tts_manager(self):
        """Create a mock TTS manager."""
        tts = Mock()
        tts.is_enabled = Mock(return_value=True)
        return tts

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger adapter."""
        logger = Mock()
        logger.info_event = Mock()
        logger.debug_event = Mock()
        logger.warning_event = Mock()
        return logger

    @pytest.fixture
    def character_config(self):
        """Create a test character config."""
        return {
            "name": "Test Character",
            "id": "test_char",
            "back_story": "A test character",
        }

    @pytest.fixture
    def response_handler(self, mock_ws, mock_tts_manager, character_config, mock_logger):
        """Create a ResponseHandler instance for testing."""
        from sessions.response_handler import ResponseHandler

        handler = ResponseHandler(
            ws=mock_ws,
            tts_manager=mock_tts_manager,
            character_config=character_config,
            logger_adapter=mock_logger,
        )
        return handler

    def test_response_handler_initialization(self, response_handler, character_config):
        """Test that ResponseHandler initializes correctly."""
        assert response_handler.character_config == character_config
        assert response_handler.tts_mode == "expressive"
        assert response_handler.game_over is False
        assert response_handler.death_sequence_active is False
        assert response_handler.response_queue is not None

    def test_set_context(self, response_handler):
        """Test setting TTS context."""
        response_handler.set_context(
            character_id="test_char",
            scene_id="test_scene",
            scene_phase=2,
        )

        assert response_handler.character_id == "test_char"
        assert response_handler.scene_id == "test_scene"
        assert response_handler.scene_phase == 2

    @pytest.mark.asyncio
    async def test_death_sequence_blocks_responses(self, response_handler, mock_ws):
        """Test that death sequence blocks non-death responses."""
        response_handler.death_sequence_active = True

        # Try to send a non-death response
        await response_handler._send_character_response_direct(
            content="This should be blocked",
            is_death_speech=False,
        )

        # Should not send any JSON (blocked)
        mock_ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_death_speech_bypasses_death_sequence(self, response_handler, mock_ws):
        """Test that death speeches bypass the death sequence block."""
        response_handler.death_sequence_active = True

        # Mock TTS to prevent actual synthesis
        with patch("sessions.response_handler.synthesize_npc_speech", new=AsyncMock(return_value=None)):
            await response_handler._send_character_response_direct(
                content="Final words...",
                is_death_speech=True,
            )

        # Should send text response (death speech allowed)
        assert mock_ws.send_json.call_count >= 1
        call_args = mock_ws.send_json.call_args_list[0][0][0]
        assert call_args["type"] == "character_response_text"
        assert "Final words..." in call_args["content"]

    @pytest.mark.asyncio
    async def test_dispatch_event(self, response_handler, mock_ws):
        """Test event dispatching."""
        await response_handler.dispatch_event("test_event")

        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "scene_event"
        assert call_args["event"] == "test_event"


class TestGameStateManager:
    """Test GameStateManager class."""

    @pytest.fixture
    def mock_ws(self):
        """Create a mock WebSocket."""
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        return ws

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger adapter."""
        logger = Mock()
        logger.info_event = Mock()
        logger.debug_event = Mock()
        return logger

    @pytest.fixture
    def mock_player_memory(self):
        """Create a mock player memory."""
        memory = Mock()
        return memory

    @pytest.fixture
    def scene_config(self):
        """Create a test scene config."""
        return {
            "name": "Test Scene",
            "description": "A test scene",
            "controls": [
                {"id": "btn1", "label": "Button 1", "max_presses": 3, "cooldown_seconds": 2.0},
                {"id": "btn2", "label": "Button 2"},  # No max_presses (unlimited)
            ],
            "state_variables": [
                {"name": "health", "initial_value": 100, "min_value": 0, "max_value": 100},
                {"name": "score", "initial_value": 0, "update_rate": 1},  # Increments by 1/sec
            ],
            "success_criteria": [
                {"id": "win", "condition": "state['score'] >= 100", "message": "You won!"},
            ],
            "failure_criteria": [
                {"id": "lose", "condition": "state['health'] <= 0", "message": "You lost!"},
            ],
        }

    @pytest.fixture
    def game_state_manager(self, mock_ws, scene_config, mock_logger, mock_player_memory):
        """Create a GameStateManager instance for testing."""
        from sessions.game_state_manager import GameStateManager

        manager = GameStateManager(
            ws=mock_ws,
            scene_config=scene_config,
            scene_id="test_scene",
            logger_adapter=mock_logger,
            player_memory=mock_player_memory,
        )
        return manager

    def test_game_state_manager_initialization(self, game_state_manager):
        """Test that GameStateManager initializes correctly."""
        assert game_state_manager.scene_id == "test_scene"
        assert game_state_manager.scene_state["health"] == 100
        assert game_state_manager.scene_state["score"] == 0
        assert game_state_manager.game_over is False
        assert game_state_manager.game_outcome is None

    def test_button_caps_from_controls(self, game_state_manager):
        """Test that button caps are built correctly from controls."""
        assert game_state_manager.button_press_caps == {"Button 1": 3}
        # Button 2 has no max_presses, so it shouldn't be in caps

    def test_get_control_cooldown(self, game_state_manager):
        """Test getting control cooldown."""
        assert game_state_manager.get_control_cooldown("Button 1") == 2.0
        assert game_state_manager.get_control_cooldown("Button 2") == 0.0
        assert game_state_manager.get_control_cooldown("Nonexistent") == 0.0

    def test_evaluate_condition_success(self, game_state_manager):
        """Test condition evaluation for success case."""
        game_state_manager.scene_state["score"] = 100
        assert game_state_manager.evaluate_condition("state['score'] >= 100") is True

    def test_evaluate_condition_failure(self, game_state_manager):
        """Test condition evaluation for failure case."""
        assert game_state_manager.evaluate_condition("state['score'] >= 100") is False

    def test_evaluate_condition_invalid(self, game_state_manager):
        """Test that invalid conditions return False."""
        assert game_state_manager.evaluate_condition("invalid python code!!!") is False

    def test_check_game_over_conditions_failure(self, game_state_manager):
        """Test that failure conditions are detected."""
        game_state_manager.scene_state["health"] = 0
        game_state_manager.check_game_over_conditions()

        assert game_state_manager.game_over is True
        assert game_state_manager.game_outcome["type"] == "failure"
        assert game_state_manager.game_outcome["id"] == "lose"

    def test_check_game_over_conditions_success(self, game_state_manager):
        """Test that success conditions are detected."""
        game_state_manager.scene_state["score"] = 100
        game_state_manager.check_game_over_conditions()

        assert game_state_manager.game_over is True
        assert game_state_manager.game_outcome["type"] == "success"
        assert game_state_manager.game_outcome["id"] == "win"

    def test_update_state(self, game_state_manager):
        """Test updating state values."""
        game_state_manager.update_state({"health": 50, "score": 10})

        assert game_state_manager.scene_state["health"] == 50
        assert game_state_manager.scene_state["score"] == 10

    def test_get_state(self, game_state_manager):
        """Test getting state copy."""
        state = game_state_manager.get_state()
        assert state == {"health": 100, "score": 0}

        # Verify it's a copy
        state["health"] = 0
        assert game_state_manager.scene_state["health"] == 100

    def test_reset_state(self, game_state_manager):
        """Test resetting state to initial values."""
        game_state_manager.scene_state["health"] = 0
        game_state_manager.game_over = True

        game_state_manager.reset_state()

        assert game_state_manager.scene_state["health"] == 100
        assert game_state_manager.game_over is False
        assert game_state_manager.game_outcome is None


class TestDialogueEngine:
    """Test DialogueEngine class."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger adapter."""
        logger = Mock()
        logger.info_event = Mock()
        logger.debug_event = Mock()
        logger.warning_event = Mock()
        return logger

    @pytest.fixture
    def mock_player_memory(self):
        """Create a mock player memory."""
        memory = Mock()
        memory.get_full_context_for_llm = Mock(return_value="Player context")
        return memory

    @pytest.fixture
    def mock_rag_engine(self):
        """Create a mock RAG engine."""
        rag = Mock()
        rag.retrieve = Mock(return_value=Mock(facts=[]))
        return rag

    @pytest.fixture
    def character_config(self):
        """Create a test character config."""
        return {
            "id": "test_char",
            "name": "Test Character",
            "back_story": "A test character",
            "instruction_prefix": "Test instruction",
        }

    @pytest.fixture
    def scene_config(self):
        """Create a test scene config."""
        return {
            "name": "Test Scene",
            "description": "A test scene",
        }

    @pytest.fixture
    def scene_data(self):
        """Create test scene data."""
        # Use a mock instead of actual SceneData to avoid import issues
        scene_data = Mock()
        scene_data.scene_name = "test_scene"
        scene_data.scene_description = "Test scene"
        scene_data.dialogue_preamble = "Test preamble"
        scene_data.actors = ["Test Character", "Player"]
        return scene_data

    @pytest.fixture
    def dialogue_engine(
        self,
        character_config,
        scene_config,
        scene_data,
        mock_player_memory,
        mock_rag_engine,
        mock_logger,
    ):
        """Create a DialogueEngine instance for testing."""
        from sessions.dialogue_engine import DialogueEngine

        engine = DialogueEngine(
            character_config=character_config,
            scene_config=scene_config,
            scene_data=scene_data,
            scene_id="test_scene",
            player_memory=mock_player_memory,
            rag_engine=mock_rag_engine,
            logger_adapter=mock_logger,
        )
        return engine

    def test_dialogue_engine_initialization(self, dialogue_engine):
        """Test that DialogueEngine initializes correctly."""
        assert dialogue_engine.character_id == "test_char"
        assert dialogue_engine.scene_id == "test_scene"
        assert dialogue_engine.dialogue_history == ""

    def test_get_rag_facts_context_empty(self, dialogue_engine, mock_rag_engine):
        """Test RAG context when no facts are found."""
        mock_rag_engine.retrieve = Mock(return_value=Mock(facts=[]))
        context = dialogue_engine.get_rag_facts_context("test query")
        assert context == ""

    def test_get_rag_facts_context_with_facts(self, dialogue_engine, mock_rag_engine):
        """Test RAG context with facts."""
        mock_rag_engine.retrieve = Mock(
            return_value=Mock(facts=["Fact 1", "Fact 2"])
        )
        context = dialogue_engine.get_rag_facts_context("test query")

        assert "RELEVANT CONTEXT" in context
        assert "Fact 1" in context
        assert "Fact 2" in context

    def test_get_phase_context_unknown_scene(self, dialogue_engine):
        """Test phase context for unknown scene."""
        scene_state = {"phase": 1}
        context = dialogue_engine.get_phase_context(scene_state)
        assert context == ""

    def test_get_phase_context_submarine(self, dialogue_engine):
        """Test phase context for submarine scene."""
        dialogue_engine.scene_id = "submarine"
        scene_state = {"phase": 1, "radiation": 10, "emotional_bond": 20}
        context = dialogue_engine.get_phase_context(scene_state)

        assert "PHASE 1" in context
        assert "Impact & Connection" in context

    def test_add_system_message(self, dialogue_engine):
        """Test adding system messages to dialogue history."""
        dialogue_engine.add_system_message("Test message")
        assert "[SYSTEM: Test message]" in dialogue_engine.dialogue_history

    def test_get_dialogue_history(self, dialogue_engine):
        """Test getting dialogue history."""
        dialogue_engine.dialogue_history = "Test history"
        assert dialogue_engine.get_dialogue_history() == "Test history"

    def test_reset_dialogue_history(self, dialogue_engine):
        """Test resetting dialogue history."""
        dialogue_engine.dialogue_history = "Some history"
        dialogue_engine.reset_dialogue_history()
        assert dialogue_engine.dialogue_history == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
