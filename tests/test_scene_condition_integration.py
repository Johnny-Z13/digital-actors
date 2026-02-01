"""
Integration tests for Scene condition evaluation.

Tests that Scene.evaluate_condition works correctly with both
string-based and function-based conditions.
"""

import unittest
from scenes.base import Scene, SuccessCriterion, FailureCriterion
from scene_conditions import and_, gt, gte, lte


class TestSceneConditionIntegration(unittest.TestCase):
    """Test Scene condition evaluation integration."""

    def test_string_condition_evaluation(self):
        """Test that Scene can evaluate string conditions safely."""
        scene = Scene(
            id="test",
            name="Test Scene",
            success_criteria=[
                SuccessCriterion(
                    id="success1",
                    description="Oxygen above 50 and trust above 60",
                    condition="state['oxygen'] > 50 and state['trust'] >= 60",
                    message="Success!"
                )
            ],
            failure_criteria=[
                FailureCriterion(
                    id="failure1",
                    description="Oxygen depleted",
                    condition="state['oxygen'] <= 0",
                    message="Game over"
                )
            ]
        )

        # Test success condition - should pass
        state_success = {'oxygen': 60, 'trust': 70}
        success = scene.check_success(state_success)
        self.assertIsNotNone(success)
        self.assertEqual(success.id, "success1")

        # Test success condition - should fail
        state_not_success = {'oxygen': 40, 'trust': 70}
        success = scene.check_success(state_not_success)
        self.assertIsNone(success)

        # Test failure condition - should pass
        state_failure = {'oxygen': 0, 'trust': 70}
        failure = scene.check_failure(state_failure)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.id, "failure1")

        # Test failure condition - should fail
        state_not_failure = {'oxygen': 10, 'trust': 70}
        failure = scene.check_failure(state_not_failure)
        self.assertIsNone(failure)

    def test_function_condition_evaluation(self):
        """Test that Scene can evaluate function-based conditions."""
        scene = Scene(
            id="test",
            name="Test Scene",
            success_criteria=[
                SuccessCriterion(
                    id="success1",
                    description="Oxygen above 50 and trust above 60",
                    condition=and_(
                        gt('oxygen', 50),
                        gte('trust', 60)
                    ),
                    message="Success!"
                )
            ],
            failure_criteria=[
                FailureCriterion(
                    id="failure1",
                    description="Oxygen depleted",
                    condition=lte('oxygen', 0),
                    message="Game over"
                )
            ]
        )

        # Test success condition
        state_success = {'oxygen': 60, 'trust': 70}
        success = scene.check_success(state_success)
        self.assertIsNotNone(success)
        self.assertEqual(success.id, "success1")

        # Test failure condition
        state_failure = {'oxygen': 0, 'trust': 70}
        failure = scene.check_failure(state_failure)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.id, "failure1")

    def test_mixed_condition_types(self):
        """Test mixing string and function conditions in same scene."""
        scene = Scene(
            id="test",
            name="Test Scene",
            success_criteria=[
                SuccessCriterion(
                    id="success_string",
                    description="String condition",
                    condition="state['oxygen'] > 50",
                    message="String success"
                ),
                SuccessCriterion(
                    id="success_function",
                    description="Function condition",
                    condition=gt('trust', 60),
                    message="Function success"
                )
            ]
        )

        # State where oxygen passes but trust doesn't
        state1 = {'oxygen': 60, 'trust': 50}
        success1 = scene.check_success(state1)
        self.assertIsNotNone(success1)
        self.assertEqual(success1.id, "success_string")

        # State where trust passes but oxygen doesn't
        state2 = {'oxygen': 40, 'trust': 70}
        success2 = scene.check_success(state2)
        self.assertIsNotNone(success2)
        self.assertEqual(success2.id, "success_function")

    def test_invalid_condition_handling(self):
        """Test that invalid conditions are handled gracefully."""
        scene = Scene(
            id="test",
            name="Test Scene",
            success_criteria=[
                SuccessCriterion(
                    id="invalid",
                    description="Invalid condition",
                    condition="state['nonexistent'] > 50",  # Key doesn't exist
                    message="Won't happen"
                )
            ]
        )

        # Should not crash, should return None
        state = {'oxygen': 60}
        success = scene.check_success(state)
        self.assertIsNone(success)

    def test_security_protection_in_scene(self):
        """Test that malicious conditions are rejected at scene level."""
        # Attempt to create scene with malicious condition
        with self.assertRaises(ValueError):
            scene = Scene(
                id="malicious",
                name="Malicious Scene",
                success_criteria=[
                    SuccessCriterion(
                        id="bad",
                        description="Malicious",
                        condition="__import__('os').system('ls')",
                        message="Should not evaluate"
                    )
                ]
            )
            # Try to evaluate it
            scene.check_success({'oxygen': 50})

    def test_real_world_submarine_conditions(self):
        """Test with actual conditions from submarine.py."""
        # Simulate submarine scene success criteria
        scene = Scene(
            id="submarine",
            name="Submarine",
            success_criteria=[
                SuccessCriterion(
                    id="good_ending",
                    description="Escaped with high bond",
                    condition="state['radiation'] < 95 and state['emotional_bond'] >= 70 and state['systems_repaired'] >= 3",
                    message="Excellent teamwork!"
                ),
                SuccessCriterion(
                    id="survival_ending",
                    description="Escaped with low bond",
                    condition="state['radiation'] < 95 and state['emotional_bond'] < 40 and state['systems_repaired'] >= 2",
                    message="You survived, but barely."
                )
            ],
            failure_criteria=[
                FailureCriterion(
                    id="radiation_death",
                    description="Radiation too high",
                    condition="state['radiation'] >= 95",
                    message="Radiation levels critical"
                ),
                FailureCriterion(
                    id="time_out",
                    description="Time ran out",
                    condition="state['time_remaining'] <= 0",
                    message="You ran out of time"
                )
            ]
        )

        # Test good ending
        state_good = {
            'radiation': 85,
            'emotional_bond': 75,
            'systems_repaired': 3,
            'time_remaining': 60
        }
        success = scene.check_success(state_good)
        self.assertIsNotNone(success)
        self.assertEqual(success.id, "good_ending")

        # Test survival ending
        state_survival = {
            'radiation': 90,
            'emotional_bond': 30,
            'systems_repaired': 2,
            'time_remaining': 60
        }
        success = scene.check_success(state_survival)
        self.assertIsNotNone(success)
        self.assertEqual(success.id, "survival_ending")

        # Test radiation death
        state_radiation = {
            'radiation': 95,
            'emotional_bond': 50,
            'systems_repaired': 2,
            'time_remaining': 60
        }
        failure = scene.check_failure(state_radiation)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.id, "radiation_death")

        # Test time out
        state_timeout = {
            'radiation': 50,
            'emotional_bond': 50,
            'systems_repaired': 1,
            'time_remaining': 0
        }
        failure = scene.check_failure(state_timeout)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.id, "time_out")


if __name__ == '__main__':
    unittest.main()
