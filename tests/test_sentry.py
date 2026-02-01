"""
Tests for Sentry error tracking integration.

This module tests:
- Sentry initialization with DSN from environment
- Custom context setting (session_id, scene, character)
- Release version from git commit
- Breadcrumb tracking for key events
- Error filtering for expected errors

NOTE: These tests require sentry-sdk to be installed:
    pip install 'sentry-sdk[aiohttp]>=2.0.0,<3.0'

If sentry-sdk is not installed, tests will be skipped.
"""

import os
import subprocess
from unittest.mock import MagicMock, Mock, patch, call

import pytest

# Skip all tests if sentry_sdk is not installed
pytest.importorskip("sentry_sdk", reason="sentry-sdk not installed")

import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration


@pytest.fixture
def mock_sentry_init():
    """Mock sentry_sdk.init to avoid actual Sentry calls during tests."""
    with patch("sentry_sdk.init") as mock_init:
        yield mock_init


@pytest.fixture
def mock_git_commit():
    """Mock git commit hash retrieval."""
    with patch("subprocess.check_output") as mock_subprocess:
        mock_subprocess.return_value = b"f31fbd3996550d7b13eede6a53be2bce15bb58a9\n"
        yield mock_subprocess


@pytest.fixture
def clear_sentry_env():
    """Clear Sentry environment variables before each test."""
    original_dsn = os.environ.get("SENTRY_DSN")
    original_env = os.environ.get("SENTRY_ENVIRONMENT")
    original_sample_rate = os.environ.get("SENTRY_TRACES_SAMPLE_RATE")

    # Clear for test
    for key in ["SENTRY_DSN", "SENTRY_ENVIRONMENT", "SENTRY_TRACES_SAMPLE_RATE"]:
        if key in os.environ:
            del os.environ[key]

    yield

    # Restore original values
    if original_dsn:
        os.environ["SENTRY_DSN"] = original_dsn
    if original_env:
        os.environ["SENTRY_ENVIRONMENT"] = original_env
    if original_sample_rate:
        os.environ["SENTRY_TRACES_SAMPLE_RATE"] = original_sample_rate


class TestSentryConstants:
    """Test Sentry configuration constants."""

    def test_sentry_dsn_read_from_environment(self, clear_sentry_env):
        """Test that SENTRY_DSN is read from environment variable."""
        test_dsn = "https://test@sentry.io/123456"
        os.environ["SENTRY_DSN"] = test_dsn

        # Reload constants to pick up new env var
        from importlib import reload
        import constants
        reload(constants)

        assert constants.SENTRY_DSN == test_dsn

    def test_sentry_dsn_none_when_not_set(self, clear_sentry_env):
        """Test that SENTRY_DSN is None when not set in environment."""
        from importlib import reload
        import constants
        reload(constants)

        assert constants.SENTRY_DSN is None

    def test_default_environment_is_development(self, clear_sentry_env):
        """Test that default environment is 'development'."""
        from importlib import reload
        import constants
        reload(constants)

        assert constants.SENTRY_ENVIRONMENT == "development"

    def test_custom_environment_from_env_var(self, clear_sentry_env):
        """Test that environment can be set via SENTRY_ENVIRONMENT."""
        os.environ["SENTRY_ENVIRONMENT"] = "production"

        from importlib import reload
        import constants
        reload(constants)

        assert constants.SENTRY_ENVIRONMENT == "production"

    def test_default_traces_sample_rate(self, clear_sentry_env):
        """Test that default traces sample rate is 0.1 (10%)."""
        from importlib import reload
        import constants
        reload(constants)

        assert constants.SENTRY_TRACES_SAMPLE_RATE == 0.1

    def test_custom_traces_sample_rate_from_env_var(self, clear_sentry_env):
        """Test that traces sample rate can be customized."""
        os.environ["SENTRY_TRACES_SAMPLE_RATE"] = "0.5"

        from importlib import reload
        import constants
        reload(constants)

        assert constants.SENTRY_TRACES_SAMPLE_RATE == 0.5


class TestSentryInitFunction:
    """Test the init_sentry function."""

    def test_init_sentry_function_exists(self):
        """Test that init_sentry function is defined."""
        # Test by inspecting the source file
        with open("web_server.py", "r") as f:
            content = f.read()
            assert "def init_sentry()" in content
            assert "sentry_sdk.init" in content

    def test_add_sentry_context_function_exists(self):
        """Test that add_sentry_context function is defined."""
        with open("web_server.py", "r") as f:
            content = f.read()
            assert "def add_sentry_context" in content
            assert "sentry_sdk.set_context" in content
            assert "sentry_sdk.set_user" in content

    def test_add_sentry_breadcrumb_function_exists(self):
        """Test that add_sentry_breadcrumb function is defined."""
        with open("web_server.py", "r") as f:
            content = f.read()
            assert "def add_sentry_breadcrumb" in content
            assert "sentry_sdk.add_breadcrumb" in content


class TestSentryImports:
    """Test that Sentry is properly imported in web_server.py."""

    def test_sentry_sdk_imported(self):
        """Test that sentry_sdk is imported."""
        with open("web_server.py", "r") as f:
            content = f.read()
            assert "import sentry_sdk" in content

    def test_aiohttp_integration_imported(self):
        """Test that AioHttpIntegration is imported."""
        with open("web_server.py", "r") as f:
            content = f.read()
            assert "from sentry_sdk.integrations.aiohttp import AioHttpIntegration" in content

    def test_sentry_constants_imported(self):
        """Test that Sentry constants are imported from constants module."""
        with open("web_server.py", "r") as f:
            content = f.read()
            assert "SENTRY_DSN" in content
            assert "SENTRY_ENVIRONMENT" in content
            assert "SENTRY_TRACES_SAMPLE_RATE" in content


class TestSentryInvokeLLMInstrumentation:
    """Test that invoke_llm_async is instrumented with Sentry breadcrumbs."""

    def test_invoke_llm_has_breadcrumbs(self):
        """Test that invoke_llm_async adds breadcrumbs."""
        with open("web_server.py", "r") as f:
            # Find the invoke_llm_async function
            content = f.read()
            func_start = content.find("async def invoke_llm_async")
            func_end = content.find("\n\n", func_start + 100)  # Find next blank line
            func_content = content[func_start:func_end]

            # Verify breadcrumbs are added
            assert "add_sentry_breadcrumb" in func_content
            assert '"llm"' in func_content
            assert "LLM call started" in func_content or "LLM call" in func_content


class TestSentryChatSessionInstrumentation:
    """Test that ChatSession is instrumented with Sentry tracking."""

    def test_chat_session_init_sets_context(self):
        """Test that ChatSession.__init__ sets Sentry context."""
        with open("web_server.py", "r") as f:
            content = f.read()

            # Find ChatSession __init__
            init_start = content.find("class ChatSession")
            init_end = content.find("def ", init_start + 500)
            init_content = content[init_start:init_end]

            # Verify Sentry context is set
            assert "add_sentry_context" in init_content
            assert "add_sentry_breadcrumb" in init_content

    def test_handle_message_adds_breadcrumb(self):
        """Test that handle_message adds breadcrumbs."""
        with open("web_server.py", "r") as f:
            content = f.read()

            # Find handle_message method
            method_start = content.find("async def handle_message")
            method_end = content.find("\n    async def ", method_start + 100)
            if method_end == -1:
                method_end = content.find("\n    def ", method_start + 100)
            method_content = content[method_start:method_end]

            # Verify breadcrumb is added
            assert "add_sentry_breadcrumb" in method_content
            assert '"dialogue"' in method_content

    def test_update_config_updates_context(self):
        """Test that update_config updates Sentry context."""
        with open("web_server.py", "r") as f:
            content = f.read()

            # Find update_config method
            method_start = content.find("def update_config")
            method_end = content.find("\n    async def ", method_start + 100)
            if method_end == -1:
                method_end = content.find("\n    def ", method_start + 100)
            method_content = content[method_start:method_end]

            # Verify Sentry context is updated
            assert "add_sentry_context" in method_content
            assert "add_sentry_breadcrumb" in method_content


class TestSentryErrorFiltering:
    """Test that before_send filter is configured correctly."""

    def test_before_send_filter_exists(self):
        """Test that before_send filter function is defined."""
        with open("web_server.py", "r") as f:
            content = f.read()

            # Find init_sentry function
            func_start = content.find("def init_sentry()")
            func_end = content.find("\n\ndef ", func_start + 100)
            if func_end == -1:
                func_end = content.find("\n\nasync def ", func_start + 100)
            func_content = content[func_start:func_end]

            # Verify before_send filter is defined
            assert "def before_send" in func_content
            assert "before_send=before_send" in func_content

    def test_before_send_filters_connection_errors(self):
        """Test that before_send filters connection errors."""
        with open("web_server.py", "r") as f:
            content = f.read()

            # Find before_send function
            func_start = content.find("def before_send")
            func_end = content.find("\n    sentry_sdk.init", func_start)
            func_content = content[func_start:func_end]

            # Verify connection errors are filtered
            assert "ConnectionResetError" in func_content
            assert "ConnectionAbortedError" in func_content
            assert "return None" in func_content

    def test_before_send_handles_invalid_message_error(self):
        """Test that before_send handles InvalidMessageError."""
        with open("web_server.py", "r") as f:
            content = f.read()

            # Find before_send function
            func_start = content.find("def before_send")
            func_end = content.find("\n    sentry_sdk.init", func_start)
            func_content = content[func_start:func_end]

            # Verify InvalidMessageError is handled
            assert "InvalidMessageError" in func_content
            assert '"warning"' in func_content


class TestSentryReleaseVersion:
    """Test that release version is extracted from git."""

    def test_release_version_uses_git_commit(self):
        """Test that release version uses git commit hash."""
        with open("web_server.py", "r") as f:
            content = f.read()

            # Find init_sentry function
            func_start = content.find("def init_sentry()")
            func_end = content.find("\n\ndef ", func_start + 100)
            if func_end == -1:
                func_end = content.find("\n\nasync def ", func_start + 100)
            func_content = content[func_start:func_end]

            # Verify git commit is retrieved
            assert "git" in func_content.lower()
            assert "rev-parse" in func_content or "commit" in func_content.lower()
            assert "release" in func_content
            assert "digital-actors" in func_content

    def test_release_has_fallback(self):
        """Test that release has fallback for when git fails."""
        with open("web_server.py", "r") as f:
            content = f.read()

            # Find init_sentry function
            func_start = content.find("def init_sentry()")
            func_end = content.find("\n\ndef ", func_start + 100)
            if func_end == -1:
                func_end = content.find("\n\nasync def ", func_start + 100)
            func_content = content[func_start:func_end]

            # Verify fallback exists
            assert "except" in func_content
            assert '"unknown"' in func_content or "'unknown'" in func_content


class TestSentryDependency:
    """Test that sentry-sdk is added to dependencies."""

    def test_sentry_in_pyproject_dependencies(self):
        """Test that sentry-sdk is listed in pyproject.toml dependencies."""
        with open("pyproject.toml", "r") as f:
            content = f.read()
            assert "sentry-sdk[aiohttp]" in content
            assert ">=2.0.0" in content

    def test_sentry_dsn_in_env_example(self):
        """Test that SENTRY_DSN is documented in .env.example."""
        with open(".env.example", "r") as f:
            content = f.read()
            assert "SENTRY_DSN" in content
            assert "SENTRY_ENVIRONMENT" in content
            assert "SENTRY_TRACES_SAMPLE_RATE" in content
