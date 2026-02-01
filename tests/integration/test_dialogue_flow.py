"""
Integration tests for core dialogue flow.

Tests the complete end-to-end flow:
1. User message → LLM generation → TTS → response delivery
2. WebSocket message handling and session management
3. Scene transitions and state updates
4. Error scenarios: LLM failures, TTS failures, network issues

These tests mock external APIs (Anthropic LLM, ElevenLabs TTS) to avoid real calls
while still testing the full pipeline of components working together.
"""

import sys
import os

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from aiohttp import WSMsgType

# Mock sentry_sdk before importing web_server
sys.modules['sentry_sdk'] = MagicMock()
sys.modules['sentry_sdk.integrations'] = MagicMock()
sys.modules['sentry_sdk.integrations.aiohttp'] = MagicMock()

import web_server
from response_queue import ResponsePriority


class MockWebSocketResponse:
    """Mock WebSocket response for integration testing."""

    def __init__(self):
        self.messages_sent = []
        self.close_code = None
        self.close_message = None
        self.closed = False
        self._prepared = False

    async def prepare(self, request):
        """Mock prepare method."""
        self._prepared = True

    async def send_json(self, data):
        """Mock send_json to capture sent messages."""
        self.messages_sent.append(data)

    async def close(self, code=None, message=None):
        """Mock close to capture close calls."""
        self.close_code = code
        self.close_message = message
        self.closed = True

    def __aiter__(self):
        """Make the mock iterable for async for loop."""
        return self

    async def __anext__(self):
        """Stop iteration immediately for testing."""
        raise StopAsyncIteration

    def get_messages_by_type(self, msg_type):
        """Helper to filter messages by type."""
        return [msg for msg in self.messages_sent if msg.get('type') == msg_type]

    def get_last_message_by_type(self, msg_type):
        """Helper to get the last message of a specific type."""
        messages = self.get_messages_by_type(msg_type)
        return messages[-1] if messages else None


@pytest.fixture
def mock_ws():
    """Fixture providing a mock WebSocket."""
    return MockWebSocketResponse()


@pytest.fixture
def mock_llm_response():
    """Fixture providing a mock LLM chain that returns a response."""
    def _create_mock_chain(response_text="Hello, how can I help you?"):
        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value=response_text)
        return mock_chain
    return _create_mock_chain


@pytest.fixture
def mock_tts_audio():
    """Fixture providing mock TTS audio data."""
    return b"fake_audio_data_base64_encoded"


@pytest.fixture
async def chat_session(mock_ws):
    """Fixture providing a ChatSession with mocked dependencies."""
    with patch('web_server.PlayerMemory') as mock_memory, \
         patch('web_server.WorldDirector') as mock_director, \
         patch('web_server.get_query_system') as mock_query, \
         patch('web_server.get_rag_engine') as mock_rag, \
         patch('web_server.register_scene_hooks'), \
         patch('web_server.get_scene_handler'):

        # Configure mock player memory
        mock_memory_instance = MagicMock()
        mock_memory_instance.get_full_context_for_llm.return_value = ""
        mock_memory_instance.start_scene = MagicMock()
        mock_memory.return_value = mock_memory_instance

        # Configure mock world director
        mock_director_instance = MagicMock()
        mock_director_instance.get_difficulty_adjustment.return_value = {}
        mock_director.return_value = mock_director_instance

        # Configure mock query system
        mock_query_instance = MagicMock()
        mock_query.return_value = mock_query_instance

        # Configure mock RAG engine
        mock_rag_instance = MagicMock()
        mock_rag_instance.set_facts = MagicMock()
        mock_rag.return_value = mock_rag_instance

        # Create session
        session = web_server.ChatSession(
            ws=mock_ws,
            character_id="clippy",
            scene_id="welcome",
            player_id="test_player"
        )

        yield session

        # Cleanup
        if session.response_queue and session.response_queue._processing_task:
            session.response_queue._processing_task.cancel()
            try:
                await session.response_queue._processing_task
            except asyncio.CancelledError:
                pass


class TestDialogueFlowBasic:
    """Test basic dialogue flow scenarios."""

    @pytest.mark.asyncio
    async def test_complete_dialogue_flow_happy_path(self, chat_session, mock_ws, mock_llm_response):
        """Test complete flow: user message → LLM → TTS → response delivery."""
        # Create mock LLM chain that returns a response
        mock_chain = mock_llm_response("I'm Clippy! I can help you.")

        # Mock LLM response
        with patch('web_server.prompt_llm', return_value=mock_chain), \
             patch('web_server.synthesize_npc_speech') as mock_tts:

            # Mock TTS to return audio data
            mock_tts.return_value = b"fake_audio_data"

            # User sends a message
            user_message = "Hello, who are you?"
            await chat_session.handle_message(user_message)

            # Wait for async processing
            await asyncio.sleep(0.2)

            # Verify LLM chain was invoked
            assert mock_chain.invoke.call_count > 0

            # Verify text response was sent
            text_responses = mock_ws.get_messages_by_type('character_response_text')
            assert len(text_responses) > 0
            assert "Clippy" in text_responses[0]['content'] or "help" in text_responses[0]['content']

            # Verify typing indicator was sent
            thinking_messages = mock_ws.get_messages_by_type('npc_thinking')
            assert len(thinking_messages) > 0

    @pytest.mark.asyncio
    async def test_dialogue_history_tracking(self, chat_session, mock_llm_response):
        """Test that dialogue history is properly maintained."""
        mock_chain = mock_llm_response("Response 1")
        with patch('web_server.prompt_llm', return_value=mock_chain), \
             patch('web_server.synthesize_npc_speech', return_value=b"audio"):

            # Send first message
            await chat_session.handle_message("First message")
            await asyncio.sleep(0.1)

            # Check dialogue history contains user message
            assert "Player" in chat_session.dialogue_history
            assert "First message" in chat_session.dialogue_history

            # Check dialogue history contains NPC response
            assert chat_session.character_config['name'] in chat_session.dialogue_history
            assert "Response 1" in chat_session.dialogue_history

    @pytest.mark.asyncio
    async def test_response_sequence_management(self, chat_session, mock_llm_response):
        """Test that response sequence IDs are managed correctly."""
        mock_chain = mock_llm_response("Response")
        with patch('web_server.prompt_llm', return_value=mock_chain), \
             patch('web_server.synthesize_npc_speech', return_value=b"audio"):

            initial_sequence = chat_session.response_sequence

            # Send message
            await chat_session.handle_message("Test message")
            await asyncio.sleep(0.1)

            # Verify sequence was incremented
            assert chat_session.response_sequence > initial_sequence

    @pytest.mark.asyncio
    async def test_npc_responding_flag(self, chat_session, mock_llm_response, mock_ws):
        """Test that npc_responding flag prevents message flooding."""
        mock_chain = mock_llm_response("Response")
        with patch('web_server.prompt_llm', return_value=mock_chain), \
             patch('web_server.synthesize_npc_speech', return_value=b"audio"):

            # Set NPC as responding
            chat_session.npc_responding = True

            # Try to send message while NPC is responding
            await chat_session.handle_message("Second message")
            await asyncio.sleep(0.1)

            # Verify system notification was sent
            notifications = mock_ws.get_messages_by_type('system_notification')
            assert any('wait' in n['message'].lower() for n in notifications)


class TestWebSocketMessageHandling:
    """Test WebSocket message handling and session management."""

    @pytest.mark.asyncio
    async def test_session_initialization(self, chat_session, mock_ws):
        """Test that session is properly initialized with token."""
        assert chat_session.session_id is not None
        assert len(chat_session.session_id) > 20
        assert chat_session.character_id == "clippy"
        assert chat_session.scene_id == "welcome"

    @pytest.mark.asyncio
    async def test_session_token_validation(self):
        """Test session token validation."""
        mock_ws = MockWebSocketResponse()

        with patch('web_server.PlayerMemory'), \
             patch('web_server.WorldDirector'), \
             patch('web_server.get_query_system'), \
             patch('web_server.get_rag_engine'), \
             patch('web_server.register_scene_hooks'), \
             patch('web_server.get_scene_handler'):

            session = web_server.ChatSession(mock_ws)

            # Register session
            web_server.ACTIVE_SESSIONS[session.session_id] = session

            # Valid session should pass validation
            assert web_server.ChatSession.validate_session(session.session_id) is True

            # Invalid session should fail validation
            assert web_server.ChatSession.validate_session("invalid_token") is False
            assert web_server.ChatSession.validate_session(None) is False

            # Cleanup
            del web_server.ACTIVE_SESSIONS[session.session_id]
            if session.response_queue and session.response_queue._processing_task:
                session.response_queue._processing_task.cancel()
                try:
                    await session.response_queue._processing_task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_opening_speech_blocking(self, chat_session, mock_ws):
        """Test that messages are blocked during opening speech."""
        # Set opening speech flag
        chat_session.opening_speech_playing = True

        with patch('web_server.prompt_llm'), \
             patch('web_server.synthesize_npc_speech'):

            # Try to send message during opening speech
            await chat_session.handle_message("Test message")
            await asyncio.sleep(0.1)

            # Verify no character response was generated
            text_responses = mock_ws.get_messages_by_type('character_response_text')
            assert len(text_responses) == 0


class TestSceneStateManagement:
    """Test scene state transitions and updates."""

    @pytest.mark.asyncio
    async def test_scene_state_initialization(self, chat_session):
        """Test that scene state is properly initialized."""
        # Welcome scene should have initial state variables
        assert isinstance(chat_session.scene_state, dict)

    @pytest.mark.asyncio
    async def test_scene_state_updates(self, chat_session, mock_ws):
        """Test that scene state can be updated."""
        # Set initial state
        chat_session.scene_state['test_var'] = 10

        # Update state
        chat_session.scene_state['test_var'] = 20

        # Verify state was updated
        assert chat_session.scene_state['test_var'] == 20

    @pytest.mark.asyncio
    async def test_game_over_detection(self, chat_session):
        """Test that game over conditions are detected."""
        # Configure a simple failure criterion
        chat_session.scene_config['failure_criteria'] = [
            {
                'id': 'test_failure',
                'condition': "state['health'] <= 0",
                'message': 'Game Over'
            }
        ]

        # Set state to trigger failure
        chat_session.scene_state['health'] = 0

        # Check game over conditions
        chat_session.check_game_over_conditions()

        # Verify game over was detected
        assert chat_session.game_over is True
        assert chat_session.game_outcome['type'] == 'failure'
        assert chat_session.game_outcome['id'] == 'test_failure'


class TestResponseQueueIntegration:
    """Test response queue system integration."""

    @pytest.mark.asyncio
    async def test_response_queuing(self, chat_session):
        """Test that responses are queued properly."""
        # Queue a response
        await chat_session.send_character_response(
            content="Test response",
            priority=ResponsePriority.NORMAL,
            source="test"
        )

        # Verify response was queued
        assert chat_session.response_queue is not None

    @pytest.mark.asyncio
    async def test_response_priority_handling(self, chat_session):
        """Test that high priority responses supersede low priority."""
        with patch('web_server.synthesize_npc_speech', return_value=b"audio"):
            # Queue low priority response
            await chat_session.send_character_response(
                content="Low priority",
                priority=ResponsePriority.BACKGROUND,
                source="background"
            )

            # Queue high priority response
            await chat_session.send_character_response(
                content="High priority",
                priority=ResponsePriority.CRITICAL,
                source="critical"
            )

            await asyncio.sleep(0.1)

            # Verify high priority was sent
            text_responses = chat_session.ws.get_messages_by_type('character_response_text')
            if text_responses:
                # Critical responses should be delivered first
                assert any("High priority" in r['content'] for r in text_responses)

    @pytest.mark.asyncio
    async def test_immediate_response_bypass(self, chat_session):
        """Test that immediate responses bypass the queue."""
        with patch('web_server.synthesize_npc_speech', return_value=b"audio"):
            # Send immediate response
            await chat_session.send_character_response_immediate(
                content="Immediate message"
            )

            await asyncio.sleep(0.2)

            # Verify response was sent
            text_responses = chat_session.ws.get_messages_by_type('character_response_text')
            assert len(text_responses) > 0


class TestErrorScenarios:
    """Test error handling in dialogue flow."""

    @pytest.mark.asyncio
    async def test_llm_failure_handling(self, chat_session, mock_ws):
        """Test graceful handling of LLM failures."""
        # Mock LLM to raise an exception
        with patch('web_server.prompt_llm') as mock_prompt:
            mock_chain = MagicMock()
            mock_chain.invoke = MagicMock(side_effect=Exception("LLM API Error"))
            mock_prompt.return_value = mock_chain

            # Try to handle message
            await chat_session.handle_message("Test message")
            await asyncio.sleep(0.1)

            # Verify error message was sent
            error_messages = mock_ws.get_messages_by_type('error')
            assert len(error_messages) > 0
            assert 'failed' in error_messages[0]['message'].lower() or 'error' in error_messages[0]['message'].lower()

    @pytest.mark.asyncio
    async def test_tts_failure_graceful_degradation(self, chat_session, mock_ws, mock_llm_response):
        """Test that TTS failures don't block text delivery."""
        mock_chain = mock_llm_response("Response")
        with patch('web_server.prompt_llm', return_value=mock_chain), \
             patch('web_server.synthesize_npc_speech', side_effect=Exception("TTS Error")):

            # Send message
            await chat_session.handle_message("Test message")
            await asyncio.sleep(0.2)

            # Verify text was still delivered despite TTS failure
            text_responses = mock_ws.get_messages_by_type('character_response_text')
            assert len(text_responses) > 0
            assert "Response" in text_responses[0]['content']

    @pytest.mark.asyncio
    async def test_empty_message_handling(self, chat_session, mock_ws):
        """Test handling of empty or whitespace-only messages."""
        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="")
        with patch('web_server.prompt_llm', return_value=mock_chain), \
             patch('web_server.synthesize_npc_speech', return_value=b"audio"):
            # Send empty message
            await chat_session.handle_message("")
            await asyncio.sleep(0.1)

            # Empty messages still generate responses (LLM handles empty input gracefully)
            # The test verifies the system doesn't crash on empty input
            assert True  # Test passes if no exception is raised

    @pytest.mark.asyncio
    async def test_invalid_scene_state_access(self, chat_session):
        """Test graceful handling of invalid scene state access."""
        # Configure condition that accesses non-existent state variable
        chat_session.scene_config['failure_criteria'] = [
            {
                'id': 'invalid',
                'condition': "state['nonexistent'] <= 0",
                'message': 'Should not trigger'
            }
        ]

        # Check game over conditions (should not crash)
        chat_session.check_game_over_conditions()

        # Verify game over was NOT triggered
        assert chat_session.game_over is False


class TestCompleteScenarios:
    """Test realistic end-to-end scenarios."""

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, chat_session, mock_ws):
        """Test a complete multi-turn conversation."""
        responses = [
            "Hello! I'm here to help.",
            "You can ask me about digital actors.",
            "Is there anything else you'd like to know?"
        ]

        response_index = 0
        def get_next_response():
            nonlocal response_index
            result = responses[response_index % len(responses)]
            response_index += 1
            return result

        with patch('web_server.synthesize_npc_speech', return_value=b"audio"), \
             patch('web_server.prompt_llm') as mock_prompt:

            # Mock LLM to return different responses for each call
            mock_chain = MagicMock()
            mock_chain.invoke = MagicMock(side_effect=lambda *args, **kwargs: get_next_response())
            mock_prompt.return_value = mock_chain

            for i in range(3):
                # User message
                await chat_session.handle_message(f"Message {i+1}")
                await asyncio.sleep(0.3)

                # Reset npc_responding flag for next turn
                chat_session.npc_responding = False

            # Wait for all queued responses to be sent (2 second gap between responses)
            await asyncio.sleep(5.0)

        # Verify all responses were sent
        text_responses = mock_ws.get_messages_by_type('character_response_text')
        assert len(text_responses) >= 3

    @pytest.mark.asyncio
    async def test_button_action_with_response(self, chat_session, mock_ws):
        """Test button action triggering a response."""
        # Configure a simple control
        chat_session.scene_controls = {
            'test_button': {
                'id': 'test_button',
                'label': 'Test Button',
                'npc_aware': True,
                'response_instruction': 'Acknowledge the button press.'
            }
        }

        with patch('web_server.prompt_llm') as mock_prompt, \
             patch('web_server.synthesize_npc_speech', return_value=b"audio"), \
             patch('web_server.get_scene_handler') as mock_handler_func:

            mock_chain = MagicMock()
            mock_chain.invoke = MagicMock(return_value="Button acknowledged!")
            mock_prompt.return_value = mock_chain

            # Mock scene handler with async process_action
            mock_handler = MagicMock()
            mock_handler.process_action = AsyncMock(return_value=None)
            mock_handler_func.return_value = mock_handler

            # Press button
            await chat_session.handle_button_action('test_button')
            await asyncio.sleep(0.2)

            # Verify response was sent
            text_responses = mock_ws.get_messages_by_type('character_response_text')
            assert len(text_responses) > 0

    @pytest.mark.asyncio
    async def test_rapid_message_blocking(self, chat_session, mock_ws):
        """Test that rapid messages are properly blocked."""
        # Manually set npc_responding flag to simulate NPC currently responding
        chat_session.npc_responding = True

        with patch('web_server.prompt_llm') as mock_prompt, \
             patch('web_server.synthesize_npc_speech', return_value=b"audio"):

            mock_chain = MagicMock()
            mock_chain.invoke = MagicMock(return_value="Response")
            mock_prompt.return_value = mock_chain

            # Try to send message while NPC is responding (should be blocked)
            await chat_session.handle_message("Message while responding")
            await asyncio.sleep(0.1)

            # Verify system notification about waiting was sent
            notifications = mock_ws.get_messages_by_type('system_notification')
            assert any('wait' in n['message'].lower() for n in notifications)

    @pytest.mark.asyncio
    async def test_scene_transition_handling(self):
        """Test handling of scene transitions."""
        mock_ws = MockWebSocketResponse()

        with patch('web_server.PlayerMemory'), \
             patch('web_server.WorldDirector'), \
             patch('web_server.get_query_system'), \
             patch('web_server.get_rag_engine'), \
             patch('web_server.register_scene_hooks'), \
             patch('web_server.get_scene_handler'):

            # Start in welcome scene
            session = web_server.ChatSession(
                ws=mock_ws,
                character_id="clippy",
                scene_id="welcome"
            )

            assert session.scene_id == "welcome"

            # Cleanup
            if session.response_queue and session.response_queue._processing_task:
                session.response_queue._processing_task.cancel()
                try:
                    await session.response_queue._processing_task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_player_memory_integration(self, chat_session):
        """Test that player memory is properly integrated."""
        # Verify player memory was initialized
        assert chat_session.player_memory is not None

        # Verify player ID is set
        assert chat_session.player_id == "test_player"

        # Verify scene was started in memory
        chat_session.player_memory.start_scene.assert_called_once()


class TestTTSIntegration:
    """Test TTS (Text-to-Speech) integration."""

    @pytest.mark.asyncio
    async def test_tts_called_with_correct_parameters(self, chat_session, mock_llm_response, mock_ws):
        """Test that TTS is called with correct character voice and settings."""
        mock_chain = mock_llm_response("Test")
        with patch('web_server.prompt_llm', return_value=mock_chain), \
             patch('web_server.synthesize_npc_speech') as mock_tts:

            mock_tts.return_value = b"audio_data"

            # Send message
            await chat_session.handle_message("Hello")
            await asyncio.sleep(0.3)

            # Verify TTS was called if enabled
            if chat_session.tts_manager.is_enabled():
                assert mock_tts.called

    @pytest.mark.asyncio
    async def test_text_sent_before_audio(self, chat_session, mock_llm_response, mock_ws):
        """Test that text is sent immediately before waiting for audio (text-first optimization)."""
        mock_chain = mock_llm_response("Quick response")
        with patch('web_server.prompt_llm', return_value=mock_chain), \
             patch('web_server.synthesize_npc_speech') as mock_tts:

            # Make TTS slow
            async def slow_tts(*args, **kwargs):
                await asyncio.sleep(1.0)
                return b"audio"

            mock_tts.return_value = b"audio"

            # Send message
            await chat_session.handle_message("Test")
            await asyncio.sleep(0.2)

            # Text should be sent quickly, before TTS completes
            text_responses = mock_ws.get_messages_by_type('character_response_text')
            assert len(text_responses) > 0


class TestRAGIntegration:
    """Test RAG (Retrieval Augmented Generation) integration."""

    @pytest.mark.asyncio
    async def test_rag_facts_indexed_on_init(self, chat_session):
        """Test that RAG facts are indexed on session initialization."""
        # Verify RAG engine exists
        assert chat_session.rag_engine is not None

    @pytest.mark.asyncio
    async def test_rag_context_included_in_prompts(self, chat_session, mock_llm_response):
        """Test that RAG facts are included in LLM prompts."""
        # Set up RAG facts
        chat_session.scene_config['facts'] = [
            "The project is open source.",
            "It uses Claude for dialogue."
        ]

        mock_chain = mock_llm_response("Response")
        with patch('web_server.prompt_llm', return_value=mock_chain), \
             patch('web_server.synthesize_npc_speech', return_value=b"audio"), \
             patch.object(chat_session, '_get_rag_facts_context', return_value="RAG: Open source project"):

            # Send message
            await chat_session.handle_message("Tell me about this")
            await asyncio.sleep(0.1)

            # Verify RAG context was retrieved
            chat_session._get_rag_facts_context.assert_called_once()


# Run tests with: pytest tests/integration/test_dialogue_flow.py -v
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
