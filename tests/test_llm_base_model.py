"""
Tests for BaseLLMModel shared functionality.

This test module verifies that the shared base class methods work correctly
for API key resolution, client initialization, and error handling.
"""

import os
import pytest
from unittest.mock import Mock, patch
from llm_prompt_core.models.base import BaseLLMModel
from llm_prompt_core.models.anthropic import ClaudeModel
from llm_prompt_core.models.openai import OpenAIModel
from llm_prompt_core.models.gemini import GoogleGeminiModel


class TestGetApiKey:
    """Test the _get_api_key method."""

    @patch.dict(os.environ, {"TEST_API_KEY": "env_key_value"}, clear=False)
    def test_get_api_key_from_environment(self):
        """Test that API key is resolved from environment variable."""
        model = Mock(spec=BaseLLMModel)
        model.api_key = None
        model._get_api_key = BaseLLMModel._get_api_key.__get__(model, BaseLLMModel)

        result = model._get_api_key("TEST_API_KEY", "TestProvider")
        assert result == "env_key_value"

    def test_get_api_key_from_instance(self):
        """Test that instance API key takes precedence over environment."""
        model = Mock(spec=BaseLLMModel)
        model.api_key = "instance_key_value"
        model._get_api_key = BaseLLMModel._get_api_key.__get__(model, BaseLLMModel)

        with patch.dict(os.environ, {"TEST_API_KEY": "env_key_value"}, clear=False):
            result = model._get_api_key("TEST_API_KEY", "TestProvider")
            assert result == "instance_key_value"

    def test_get_api_key_required_raises_error(self):
        """Test that missing required API key raises EnvironmentError."""
        model = Mock(spec=BaseLLMModel)
        model.api_key = None
        model._get_api_key = BaseLLMModel._get_api_key.__get__(model, BaseLLMModel)

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EnvironmentError, match="MISSING_KEY environment variable must be set for TestProvider models."):
                model._get_api_key("MISSING_KEY", "TestProvider", required=True)

    def test_get_api_key_not_required_returns_none(self):
        """Test that missing non-required API key returns None."""
        model = Mock(spec=BaseLLMModel)
        model.api_key = None
        model._get_api_key = BaseLLMModel._get_api_key.__get__(model, BaseLLMModel)

        with patch.dict(os.environ, {}, clear=True):
            result = model._get_api_key("MISSING_KEY", "TestProvider", required=False)
            assert result is None


class TestInitializeClient:
    """Test the _initialize_client method."""

    def test_initialize_client_success(self):
        """Test successful client initialization."""
        model = Mock(spec=BaseLLMModel)
        model._initialize_client = BaseLLMModel._initialize_client.__get__(model, BaseLLMModel)

        MockClient = Mock(return_value="client_instance")
        result = model._initialize_client(MockClient, "test_key", "test-package")

        assert result == "client_instance"
        MockClient.assert_called_once_with(api_key="test_key")

    def test_initialize_client_with_kwargs(self):
        """Test client initialization with additional kwargs."""
        model = Mock(spec=BaseLLMModel)
        model._initialize_client = BaseLLMModel._initialize_client.__get__(model, BaseLLMModel)

        MockClient = Mock(return_value="client_instance")
        result = model._initialize_client(
            MockClient, "test_key", "test-package",
            timeout=30, max_retries=3
        )

        assert result == "client_instance"
        MockClient.assert_called_once_with(api_key="test_key", timeout=30, max_retries=3)

    def test_initialize_client_import_error(self):
        """Test that ImportError is raised with helpful message."""
        model = Mock(spec=BaseLLMModel)
        model._initialize_client = BaseLLMModel._initialize_client.__get__(model, BaseLLMModel)

        def mock_client(*args, **kwargs):
            raise ImportError("No module named 'fake_package'")

        with pytest.raises(ImportError, match="fake-package package not installed. Install it with: pip install fake-package"):
            model._initialize_client(mock_client, "test_key", "fake-package")


class TestHandleApiError:
    """Test the _handle_api_error method."""

    def test_handle_api_error_reraises_runtime_error(self):
        """Test that RuntimeError is re-raised without wrapping."""
        model = Mock(spec=BaseLLMModel)
        model._handle_api_error = BaseLLMModel._handle_api_error.__get__(model, BaseLLMModel)

        original_error = RuntimeError("Original error message")
        with pytest.raises(RuntimeError, match="Original error message"):
            model._handle_api_error(original_error, "TestProvider")

    def test_handle_api_error_wraps_connection_error(self):
        """Test that ConnectionError is wrapped with provider context."""
        model = Mock(spec=BaseLLMModel)
        model._handle_api_error = BaseLLMModel._handle_api_error.__get__(model, BaseLLMModel)

        original_error = ConnectionError("Network unreachable")
        with pytest.raises(ConnectionError, match="TestProvider API connection failed: Network unreachable"):
            model._handle_api_error(original_error, "TestProvider")

    def test_handle_api_error_wraps_timeout_error(self):
        """Test that TimeoutError is wrapped with provider context."""
        model = Mock(spec=BaseLLMModel)
        model._handle_api_error = BaseLLMModel._handle_api_error.__get__(model, BaseLLMModel)

        original_error = TimeoutError("Request timed out after 30s")
        with pytest.raises(TimeoutError, match="TestProvider API request timed out: Request timed out after 30s"):
            model._handle_api_error(original_error, "TestProvider")

    def test_handle_api_error_wraps_value_error(self):
        """Test that ValueError is wrapped with provider context."""
        model = Mock(spec=BaseLLMModel)
        model._handle_api_error = BaseLLMModel._handle_api_error.__get__(model, BaseLLMModel)

        original_error = ValueError("Invalid model name")
        with pytest.raises(ValueError, match="Invalid request parameters: Invalid model name"):
            model._handle_api_error(original_error, "TestProvider")

    def test_handle_api_error_wraps_generic_exception(self):
        """Test that generic exceptions are wrapped in RuntimeError."""
        model = Mock(spec=BaseLLMModel)
        model._handle_api_error = BaseLLMModel._handle_api_error.__get__(model, BaseLLMModel)

        original_error = Exception("Some API error")
        with pytest.raises(RuntimeError, match="TestProvider API call failed: Exception: Some API error"):
            model._handle_api_error(original_error, "TestProvider")

    def test_handle_api_error_preserves_exception_chain(self):
        """Test that exception chaining is preserved."""
        model = Mock(spec=BaseLLMModel)
        model._handle_api_error = BaseLLMModel._handle_api_error.__get__(model, BaseLLMModel)

        original_error = ConnectionError("Network error")
        try:
            model._handle_api_error(original_error, "TestProvider")
        except ConnectionError as e:
            assert e.__cause__ is original_error


class TestModelInitialization:
    """Test that actual model classes use the base methods correctly."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_anthropic_key"}, clear=False)
    def test_claude_model_uses_base_methods(self):
        """Test that ClaudeModel uses base class methods."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            model = ClaudeModel()

            # Verify client was initialized
            mock_anthropic.assert_called_once_with(api_key="test_anthropic_key")
            assert model._client == mock_client

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_openai_key"}, clear=False)
    def test_openai_model_uses_base_methods(self):
        """Test that OpenAIModel uses base class methods."""
        with patch("openai.OpenAI") as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client

            model = OpenAIModel()

            # Verify client was initialized
            mock_openai.assert_called_once_with(api_key="test_openai_key")
            assert model._client == mock_client

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_google_key"}, clear=False)
    def test_gemini_model_uses_base_methods(self):
        """Test that GoogleGeminiModel uses base class methods."""
        with patch("google.genai.Client") as mock_genai_client:
            mock_client = Mock()
            mock_genai_client.return_value = mock_client

            model = GoogleGeminiModel(model_name="gemini-2.5-flash")

            # Verify client was initialized
            mock_genai_client.assert_called_once_with(api_key="test_google_key")
            assert model._client == mock_client

    @patch.dict(os.environ, {}, clear=True)
    def test_claude_model_missing_key_raises_error(self):
        """Test that ClaudeModel raises error when API key is missing."""
        with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY environment variable must be set for Claude models."):
            ClaudeModel()

    @patch.dict(os.environ, {}, clear=True)
    def test_openai_model_missing_key_raises_error(self):
        """Test that OpenAIModel raises error when API key is missing."""
        with pytest.raises(EnvironmentError, match="OPENAI_API_KEY environment variable must be set for OpenAI models."):
            OpenAIModel()

    @patch.dict(os.environ, {}, clear=True)
    def test_gemini_model_missing_key_raises_error(self):
        """Test that GoogleGeminiModel raises error when API key is missing."""
        with pytest.raises(EnvironmentError, match="GOOGLE_API_KEY environment variable must be set for Google Gemini models."):
            GoogleGeminiModel(model_name="gemini-2.5-flash")
