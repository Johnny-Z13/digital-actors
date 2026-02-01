"""
Tests for background task tracking system.

Verifies that:
1. Tasks are tracked in the _background_tasks set
2. Failed tasks are logged
3. Cleanup cancels and waits for all tasks
"""

import asyncio
import unittest
import logging
from io import StringIO


class MockWebSocket:
    """Mock WebSocket for testing."""
    async def send_json(self, data):
        pass


class MockChatSession:
    """Simplified ChatSession for testing task tracking."""

    def __init__(self):
        self._background_tasks: set[asyncio.Task] = set()
        self.logger = logging.getLogger(__name__)

    def _create_tracked_task(self, coro, name: str = "unknown") -> asyncio.Task:
        """Create a tracked background task (same as in web_server.py)."""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)

        def _task_done_callback(t: asyncio.Task) -> None:
            self._background_tasks.discard(t)
            try:
                t.result()
            except asyncio.CancelledError:
                self.logger.debug(f"Task '{name}' was cancelled")
            except Exception as e:
                self.logger.error(f"Task '{name}' failed: {e}", exc_info=True)

        task.add_done_callback(_task_done_callback)
        return task

    async def _cleanup_background_tasks(self) -> None:
        """Cancel all background tasks (same as in web_server.py)."""
        if not self._background_tasks:
            return

        for task in self._background_tasks:
            if not task.done():
                task.cancel()

        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()


class TestTaskTracking(unittest.TestCase):
    """Test task tracking functionality."""

    def setUp(self):
        """Set up logging capture."""
        self.log_stream = StringIO()
        self.log_handler = logging.StreamHandler(self.log_stream)
        self.log_handler.setLevel(logging.DEBUG)
        logger = logging.getLogger()
        logger.addHandler(self.log_handler)
        logger.setLevel(logging.DEBUG)

    def tearDown(self):
        """Clean up logging."""
        logger = logging.getLogger()
        logger.removeHandler(self.log_handler)

    async def async_test_task_added_to_set(self):
        """Test that tasks are added to tracking set."""
        session = MockChatSession()

        async def dummy_task():
            await asyncio.sleep(0.1)

        # Create tracked task
        task = session._create_tracked_task(dummy_task(), name="test_task")

        # Task should be in set
        self.assertIn(task, session._background_tasks)
        self.assertEqual(len(session._background_tasks), 1)

        # Wait for completion
        await task

        # Task should be removed after completion
        await asyncio.sleep(0.01)  # Give callback time to run
        self.assertEqual(len(session._background_tasks), 0)

        print("✓ Task correctly added and removed from tracking set")

    async def async_test_failed_task_logged(self):
        """Test that failed tasks are logged."""
        session = MockChatSession()

        async def failing_task():
            await asyncio.sleep(0.01)
            raise ValueError("Intentional test error")

        # Create task that will fail
        task = session._create_tracked_task(failing_task(), name="failing_task")

        # Wait for it to complete (and fail)
        await asyncio.sleep(0.05)

        # Check logs for error
        log_output = self.log_stream.getvalue()
        self.assertIn("failing_task", log_output)
        self.assertIn("failed", log_output)
        self.assertIn("ValueError", log_output)

        # Task should still be removed from set
        self.assertEqual(len(session._background_tasks), 0)

        print("✓ Failed task logged correctly")

    async def async_test_cleanup_cancels_tasks(self):
        """Test that cleanup cancels running tasks."""
        session = MockChatSession()

        task_started = asyncio.Event()
        task_cancelled = False

        async def long_running_task():
            nonlocal task_cancelled
            task_started.set()
            try:
                await asyncio.sleep(10)  # Long running
            except asyncio.CancelledError:
                task_cancelled = True
                raise

        # Create long-running task
        task = session._create_tracked_task(long_running_task(), name="long_task")

        # Wait for task to start
        await task_started.wait()

        # Task should be in set
        self.assertEqual(len(session._background_tasks), 1)

        # Clean up
        await session._cleanup_background_tasks()

        # Task should be cancelled
        self.assertTrue(task_cancelled)
        self.assertEqual(len(session._background_tasks), 0)

        print("✓ Cleanup correctly cancelled running tasks")

    async def async_test_multiple_tasks(self):
        """Test tracking multiple tasks simultaneously."""
        session = MockChatSession()

        async def task_1():
            await asyncio.sleep(0.01)

        async def task_2():
            await asyncio.sleep(0.02)

        async def task_3():
            await asyncio.sleep(0.03)

        # Create multiple tasks
        t1 = session._create_tracked_task(task_1(), name="task1")
        t2 = session._create_tracked_task(task_2(), name="task2")
        t3 = session._create_tracked_task(task_3(), name="task3")

        # All should be tracked
        self.assertEqual(len(session._background_tasks), 3)

        # Wait for all to complete
        await asyncio.gather(t1, t2, t3)
        await asyncio.sleep(0.01)  # Give callbacks time to run

        # All should be removed
        self.assertEqual(len(session._background_tasks), 0)

        print("✓ Multiple tasks tracked correctly")

    def test_task_tracking(self):
        """Run all async tests."""
        asyncio.run(self.async_test_task_added_to_set())
        asyncio.run(self.async_test_failed_task_logged())
        asyncio.run(self.async_test_cleanup_cancels_tasks())
        asyncio.run(self.async_test_multiple_tasks())


if __name__ == '__main__':
    print("\n" + "="*70)
    print("TASK TRACKING VERIFICATION")
    print("="*70 + "\n")

    suite = unittest.TestLoader().loadTestsFromTestCase(TestTaskTracking)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*70)
    if result.wasSuccessful():
        print("✅ ALL TASK TRACKING TESTS PASSED")
        print("   - Tasks added to tracking set")
        print("   - Failed tasks logged")
        print("   - Cleanup cancels running tasks")
        print("   - Multiple tasks tracked correctly")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*70 + "\n")
