"""
Test for race condition fix in ResponseQueue.get_next_sequence_id().

This test verifies that concurrent calls to get_next_sequence_id() from
multiple tasks/connections produce unique, sequential IDs without duplicates.
"""

import asyncio
import unittest
from typing import Optional
from response_queue import ResponseQueue


class TestSequenceIDRaceCondition(unittest.TestCase):
    """Test that sequence ID generation is thread-safe."""

    async def mock_send_callback(self, content: str, emotion: Optional[str]) -> None:
        """Mock callback for ResponseQueue."""
        pass

    async def test_concurrent_sequence_id_generation(self):
        """Test that concurrent calls produce unique sequence IDs."""
        queue = ResponseQueue(self.mock_send_callback)

        # Simulate 100 concurrent calls to get_next_sequence_id
        num_calls = 100
        tasks = [queue.get_next_sequence_id() for _ in range(num_calls)]

        # Execute all tasks concurrently
        sequence_ids = await asyncio.gather(*tasks)

        # Verify all IDs are unique
        self.assertEqual(len(sequence_ids), len(set(sequence_ids)),
                        f"Found duplicate sequence IDs: {sequence_ids}")

        # Verify IDs are sequential (1 to num_calls)
        self.assertEqual(sorted(sequence_ids), list(range(1, num_calls + 1)),
                        "Sequence IDs are not sequential")

        print(f"✓ Generated {num_calls} unique sequence IDs: {min(sequence_ids)} to {max(sequence_ids)}")

    async def test_multiple_queue_instances(self):
        """Test that different queue instances have independent sequence counters."""
        queue1 = ResponseQueue(self.mock_send_callback)
        queue2 = ResponseQueue(self.mock_send_callback)

        id1 = await queue1.get_next_sequence_id()
        id2 = await queue2.get_next_sequence_id()

        # Both should start at 1 (independent counters)
        self.assertEqual(id1, 1)
        self.assertEqual(id2, 1)

        print(f"✓ Independent queue instances have separate counters: {id1}, {id2}")

    async def test_sequential_ordering_under_load(self):
        """Test that IDs remain sequential even with high concurrency."""
        queue = ResponseQueue(self.mock_send_callback)

        # Simulate very high concurrency
        num_calls = 1000

        # Create tasks in batches to simulate realistic load
        batch_size = 50
        all_ids = []

        for batch_start in range(0, num_calls, batch_size):
            tasks = [queue.get_next_sequence_id() for _ in range(batch_size)]
            batch_ids = await asyncio.gather(*tasks)
            all_ids.extend(batch_ids)

        # Verify all IDs are unique
        self.assertEqual(len(all_ids), len(set(all_ids)),
                        "Found duplicate sequence IDs under load")

        # Verify IDs are sequential
        self.assertEqual(sorted(all_ids), list(range(1, num_calls + 1)),
                        "Sequence IDs are not sequential under load")

        print(f"✓ Generated {num_calls} unique sequential IDs under high load")

    def test_sync_wrapper(self):
        """Run async tests using asyncio.run()."""
        asyncio.run(self.test_concurrent_sequence_id_generation())
        asyncio.run(self.test_multiple_queue_instances())
        asyncio.run(self.test_sequential_ordering_under_load())


if __name__ == '__main__':
    # Run the tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSequenceIDRaceCondition)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n✅ All race condition tests passed!")
    else:
        print("\n❌ Some tests failed")
        exit(1)
