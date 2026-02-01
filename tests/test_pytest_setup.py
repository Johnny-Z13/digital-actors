"""
Test to verify pytest configuration is working correctly.

This file tests both synchronous and asynchronous test execution
to ensure pytest-asyncio is configured properly.
"""

import asyncio


def test_pytest_works():
    """Verify basic pytest functionality."""
    assert True


def test_basic_arithmetic():
    """Test basic arithmetic to ensure pytest assertions work."""
    assert 1 + 1 == 2
    assert 10 - 5 == 5
    assert 2 * 3 == 6


async def test_async_works():
    """Verify async tests work with pytest-asyncio."""
    await asyncio.sleep(0.001)
    assert True


async def test_async_operations():
    """Test async operations work correctly."""
    result = await async_add(5, 3)
    assert result == 8


async def async_add(a: int, b: int) -> int:
    """Helper async function for testing."""
    await asyncio.sleep(0.001)
    return a + b
