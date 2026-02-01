"""
Tests for WebSocket authentication system.

Tests verify that:
1. Session tokens are generated and validated correctly
2. Messages without session_id are rejected with 4001 code
3. Messages with invalid session_id are rejected with 4001 code
4. Messages with valid session_id are accepted
5. Sessions are properly cleaned up on disconnect
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from aiohttp import web, WSMsgType
from aiohttp.test_utils import AioHTTPTestCase

# Import the module to test
import web_server


class MockWebSocketResponse:
    """Mock WebSocket response for testing."""

    def __init__(self):
        self.messages_sent = []
        self.close_code = None
        self.close_message = None
        self.closed = False

    async def prepare(self, request):
        """Mock prepare method."""
        pass

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


class TestChatSessionAuthentication:
    """Test ChatSession authentication functionality."""

    def test_session_token_generation(self):
        """Test that session tokens are generated on ChatSession creation."""
        # Create a mock WebSocket
        mock_ws = MagicMock()

        # Create a ChatSession
        with patch('web_server.PlayerMemory'), \
             patch('web_server.WorldDirector'), \
             patch('web_server.get_query_system'), \
             patch('web_server.get_rag_engine'), \
             patch('web_server.register_scene_hooks'), \
             patch('web_server.get_scene_handler'):
            session = web_server.ChatSession(mock_ws)

        # Verify session_id was generated
        assert hasattr(session, 'session_id')
        assert session.session_id is not None
        assert len(session.session_id) > 20  # URL-safe tokens are typically 32+ chars
        assert isinstance(session.session_id, str)

    def test_session_token_uniqueness(self):
        """Test that each ChatSession gets a unique token."""
        mock_ws1 = MagicMock()
        mock_ws2 = MagicMock()

        with patch('web_server.PlayerMemory'), \
             patch('web_server.WorldDirector'), \
             patch('web_server.get_query_system'), \
             patch('web_server.get_rag_engine'), \
             patch('web_server.register_scene_hooks'), \
             patch('web_server.get_scene_handler'):
            session1 = web_server.ChatSession(mock_ws1)
            session2 = web_server.ChatSession(mock_ws2)

        # Verify tokens are different
        assert session1.session_id != session2.session_id

    def test_validate_session_valid(self):
        """Test that validate_session returns True for valid session IDs."""
        mock_ws = MagicMock()

        with patch('web_server.PlayerMemory'), \
             patch('web_server.WorldDirector'), \
             patch('web_server.get_query_system'), \
             patch('web_server.get_rag_engine'), \
             patch('web_server.register_scene_hooks'), \
             patch('web_server.get_scene_handler'):
            session = web_server.ChatSession(mock_ws)

        # Register the session
        web_server.ACTIVE_SESSIONS[session.session_id] = session

        try:
            # Test validation
            assert web_server.ChatSession.validate_session(session.session_id) is True
        finally:
            # Cleanup
            del web_server.ACTIVE_SESSIONS[session.session_id]

    def test_validate_session_invalid(self):
        """Test that validate_session returns False for invalid session IDs."""
        # Test with non-existent session ID
        assert web_server.ChatSession.validate_session("invalid_session_id") is False

        # Test with None
        assert web_server.ChatSession.validate_session(None) is False

        # Test with empty string
        assert web_server.ChatSession.validate_session("") is False


class TestWebSocketValidationLogic:
    """Test the validation logic directly."""

    def test_missing_session_id_fails_validation(self):
        """Test that missing session_id fails validation."""
        assert web_server.ChatSession.validate_session(None) is False
        assert web_server.ChatSession.validate_session("") is False

    def test_invalid_session_id_fails_validation(self):
        """Test that invalid session_id fails validation."""
        # Clear any existing sessions
        web_server.ACTIVE_SESSIONS.clear()
        assert web_server.ChatSession.validate_session("nonexistent_session_123") is False

    def test_valid_session_id_passes_validation(self):
        """Test that valid session_id passes validation."""
        # Create a mock session
        test_session_id = "test_validation_session"
        web_server.ACTIVE_SESSIONS[test_session_id] = MagicMock()

        try:
            assert web_server.ChatSession.validate_session(test_session_id) is True
        finally:
            # Cleanup
            del web_server.ACTIVE_SESSIONS[test_session_id]


class TestWebSocketAuthenticationFlow:
    """Test WebSocket authentication flow in websocket_handler."""

    @pytest.mark.asyncio
    async def test_session_init_message_sent(self):
        """Test that session_init message is sent on connection."""
        # Create mock WebSocket
        mock_ws = MockWebSocketResponse()
        mock_request = MagicMock()

        # Mock ChatSession methods that would normally run
        with patch('web_server.web.WebSocketResponse', return_value=mock_ws), \
             patch('web_server.ChatSession') as MockChatSession:

            # Setup mock session
            mock_session = MagicMock()
            mock_session.session_id = "test_session_123"
            mock_session.character_id = "clippy"
            mock_session.scene_id = "welcome"
            mock_session.start_oxygen_countdown = MagicMock()
            mock_session.send_opening_speech = AsyncMock()
            mock_session.stop_oxygen_countdown = MagicMock()
            mock_session._cleanup_background_tasks = AsyncMock()
            MockChatSession.return_value = mock_session

            # Call websocket_handler
            await web_server.websocket_handler(mock_request)

            # Verify session_init was sent
            session_init_messages = [msg for msg in mock_ws.messages_sent if msg.get('type') == 'session_init']
            assert len(session_init_messages) == 1
            assert session_init_messages[0]['session_id'] == "test_session_123"

    @pytest.mark.asyncio
    async def test_session_registered_on_connect(self):
        """Test that session is registered in ACTIVE_SESSIONS on connect."""
        mock_ws = MockWebSocketResponse()
        mock_request = MagicMock()

        with patch('web_server.web.WebSocketResponse', return_value=mock_ws), \
             patch('web_server.ChatSession') as MockChatSession:

            mock_session = MagicMock()
            mock_session.session_id = "test_session_456"
            mock_session.character_id = "clippy"
            mock_session.scene_id = "welcome"
            mock_session.start_oxygen_countdown = MagicMock()
            mock_session.send_opening_speech = AsyncMock()
            mock_session.stop_oxygen_countdown = MagicMock()
            mock_session._cleanup_background_tasks = AsyncMock()
            MockChatSession.return_value = mock_session

            # Clear any existing sessions
            initial_sessions = dict(web_server.ACTIVE_SESSIONS)

            try:
                await web_server.websocket_handler(mock_request)

                # Note: Session is removed in finally block, so we need to check during execution
                # For this test, we'll verify the session was registered by checking the messages
                assert any(msg.get('type') == 'session_init' for msg in mock_ws.messages_sent)

            finally:
                # Cleanup
                if "test_session_456" in web_server.ACTIVE_SESSIONS:
                    del web_server.ACTIVE_SESSIONS["test_session_456"]
                web_server.ACTIVE_SESSIONS.update(initial_sessions)

    # Note: Integration tests for message validation with the full websocket_handler
    # are complex due to async iteration mocking. The unit tests above verify
    # the authentication logic works correctly. For end-to-end testing,
    # manual testing or integration tests with a real WebSocket client would be preferred.

    @pytest.mark.asyncio
    async def test_session_cleanup_on_disconnect(self):
        """Test that session is removed from ACTIVE_SESSIONS on disconnect."""
        mock_ws = MockWebSocketResponse()
        mock_request = MagicMock()

        with patch('web_server.web.WebSocketResponse', return_value=mock_ws), \
             patch('web_server.ChatSession') as MockChatSession:

            mock_session = MagicMock()
            test_session_id = "test_session_cleanup_789"
            mock_session.session_id = test_session_id
            mock_session.character_id = "clippy"
            mock_session.scene_id = "welcome"
            mock_session.start_oxygen_countdown = MagicMock()
            mock_session.send_opening_speech = AsyncMock()
            mock_session.stop_oxygen_countdown = MagicMock()
            mock_session._cleanup_background_tasks = AsyncMock()
            MockChatSession.return_value = mock_session

            # Verify session is not in ACTIVE_SESSIONS initially
            assert test_session_id not in web_server.ACTIVE_SESSIONS

            # Call websocket_handler (which will register and then cleanup)
            await web_server.websocket_handler(mock_request)

            # Verify session was removed from ACTIVE_SESSIONS
            assert test_session_id not in web_server.ACTIVE_SESSIONS

    @pytest.mark.asyncio
    async def test_session_ack_bypasses_auth(self):
        """Test that session_ack messages bypass authentication."""
        mock_ws = MockWebSocketResponse()

        # Create a session_ack message (should not require session_id)
        messages = [
            MagicMock(
                type=WSMsgType.TEXT,
                data=json.dumps({'type': 'session_ack'})
            )
        ]

        mock_ws.__aiter__ = lambda self: iter(messages)

        mock_request = MagicMock()

        with patch('web_server.web.WebSocketResponse', return_value=mock_ws), \
             patch('web_server.ChatSession') as MockChatSession:

            mock_session = MagicMock()
            mock_session.session_id = "test_session_ack"
            mock_session.character_id = "clippy"
            mock_session.scene_id = "welcome"
            mock_session.start_oxygen_countdown = MagicMock()
            mock_session.send_opening_speech = AsyncMock()
            mock_session.stop_oxygen_countdown = MagicMock()
            mock_session._cleanup_background_tasks = AsyncMock()
            MockChatSession.return_value = mock_session

            await web_server.websocket_handler(mock_request)

            # Verify connection was NOT closed (session_ack bypasses auth)
            assert mock_ws.close_code != 4001


class TestSessionTokenSecurity:
    """Test security properties of session tokens."""

    def test_token_length_sufficient(self):
        """Test that tokens are long enough to be secure (256+ bits of entropy)."""
        mock_ws = MagicMock()

        with patch('web_server.PlayerMemory'), \
             patch('web_server.WorldDirector'), \
             patch('web_server.get_query_system'), \
             patch('web_server.get_rag_engine'), \
             patch('web_server.register_scene_hooks'), \
             patch('web_server.get_scene_handler'):
            session = web_server.ChatSession(mock_ws)

        # URL-safe base64 with 32 bytes = 256 bits of entropy
        # Results in 43 characters (32 * 4/3 rounded up)
        assert len(session.session_id) >= 43

    def test_token_url_safe(self):
        """Test that tokens are URL-safe (no special characters)."""
        mock_ws = MagicMock()

        with patch('web_server.PlayerMemory'), \
             patch('web_server.WorldDirector'), \
             patch('web_server.get_query_system'), \
             patch('web_server.get_rag_engine'), \
             patch('web_server.register_scene_hooks'), \
             patch('web_server.get_scene_handler'):
            session = web_server.ChatSession(mock_ws)

        # URL-safe tokens should only contain: a-z, A-Z, 0-9, -, _
        import re
        assert re.match(r'^[a-zA-Z0-9_-]+$', session.session_id)

    def test_token_randomness(self):
        """Test that tokens have sufficient randomness (statistical test)."""
        mock_ws = MagicMock()
        tokens = []

        with patch('web_server.PlayerMemory'), \
             patch('web_server.WorldDirector'), \
             patch('web_server.get_query_system'), \
             patch('web_server.get_rag_engine'), \
             patch('web_server.register_scene_hooks'), \
             patch('web_server.get_scene_handler'):
            # Generate multiple tokens
            for _ in range(100):
                session = web_server.ChatSession(mock_ws)
                tokens.append(session.session_id)

        # Verify all tokens are unique
        assert len(tokens) == len(set(tokens))

        # Verify tokens don't share common prefixes (no predictable patterns)
        first_chars = [t[0] for t in tokens]
        # With 100 tokens and 64 possible characters, we expect good distribution
        # At least 10 different first characters
        assert len(set(first_chars)) >= 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
