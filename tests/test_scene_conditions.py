"""
Tests for the safe scene condition evaluation system.

Verifies that:
1. Condition functions work correctly
2. String parsing is safe (no code execution)
3. Backwards compatibility with existing condition strings
"""

import unittest
from scene_conditions import (
    eq, ne, gt, gte, lt, lte,
    and_, or_, not_,
    exists, between,
    parse_condition_string,
    oxygen_depleted, trust_high, time_up
)


class TestBasicComparisons(unittest.TestCase):
    """Test basic comparison operators."""

    def setUp(self):
        self.state = {
            'oxygen': 50,
            'trust': 60,
            'phase': 2,
            'radiation': 30
        }

    def test_eq(self):
        """Test equality operator."""
        self.assertTrue(eq('phase', 2)(self.state))
        self.assertFalse(eq('phase', 1)(self.state))

    def test_ne(self):
        """Test not equal operator."""
        self.assertTrue(ne('phase', 1)(self.state))
        self.assertFalse(ne('phase', 2)(self.state))

    def test_gt(self):
        """Test greater than operator."""
        self.assertTrue(gt('oxygen', 40)(self.state))
        self.assertFalse(gt('oxygen', 60)(self.state))
        self.assertFalse(gt('oxygen', 50)(self.state))

    def test_gte(self):
        """Test greater than or equal operator."""
        self.assertTrue(gte('oxygen', 50)(self.state))
        self.assertTrue(gte('oxygen', 40)(self.state))
        self.assertFalse(gte('oxygen', 60)(self.state))

    def test_lt(self):
        """Test less than operator."""
        self.assertTrue(lt('radiation', 50)(self.state))
        self.assertFalse(lt('radiation', 20)(self.state))
        self.assertFalse(lt('radiation', 30)(self.state))

    def test_lte(self):
        """Test less than or equal operator."""
        self.assertTrue(lte('radiation', 30)(self.state))
        self.assertTrue(lte('radiation', 50)(self.state))
        self.assertFalse(lte('radiation', 20)(self.state))

    def test_missing_key(self):
        """Test handling of missing state keys."""
        self.assertFalse(gt('nonexistent', 10)(self.state))
        self.assertFalse(lt('nonexistent', 10)(self.state))


class TestLogicalOperators(unittest.TestCase):
    """Test logical operators."""

    def setUp(self):
        self.state = {
            'oxygen': 50,
            'trust': 60,
            'phase': 2
        }

    def test_and(self):
        """Test AND operator."""
        # Both true
        self.assertTrue(and_(
            gt('oxygen', 40),
            gte('trust', 60)
        )(self.state))

        # One false
        self.assertFalse(and_(
            gt('oxygen', 40),
            gt('trust', 70)
        )(self.state))

        # Both false
        self.assertFalse(and_(
            gt('oxygen', 60),
            gt('trust', 70)
        )(self.state))

    def test_or(self):
        """Test OR operator."""
        # Both true
        self.assertTrue(or_(
            gt('oxygen', 40),
            gte('trust', 60)
        )(self.state))

        # One true
        self.assertTrue(or_(
            gt('oxygen', 40),
            gt('trust', 70)
        )(self.state))

        # Both false
        self.assertFalse(or_(
            gt('oxygen', 60),
            gt('trust', 70)
        )(self.state))

    def test_not(self):
        """Test NOT operator."""
        self.assertTrue(not_(eq('phase', 1))(self.state))
        self.assertFalse(not_(eq('phase', 2))(self.state))

    def test_complex_logic(self):
        """Test complex nested logical expressions."""
        # (oxygen > 40 AND trust >= 60) OR phase == 3
        condition = or_(
            and_(
                gt('oxygen', 40),
                gte('trust', 60)
            ),
            eq('phase', 3)
        )
        self.assertTrue(condition(self.state))


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions."""

    def test_exists(self):
        """Test key existence check."""
        state = {'oxygen': 50, 'trust': 60}
        self.assertTrue(exists('oxygen')(state))
        self.assertFalse(exists('nonexistent')(state))

    def test_between(self):
        """Test between range check."""
        state = {'trust': 60}
        self.assertTrue(between('trust', 40, 80)(state))
        self.assertTrue(between('trust', 60, 80)(state))
        self.assertTrue(between('trust', 40, 60)(state))
        self.assertFalse(between('trust', 70, 90)(state))
        self.assertFalse(between('trust', 10, 50)(state))


class TestCommonPatterns(unittest.TestCase):
    """Test common condition patterns."""

    def test_oxygen_depleted(self):
        """Test oxygen depletion check."""
        self.assertTrue(oxygen_depleted()({'oxygen': 0}))
        self.assertTrue(oxygen_depleted()({'oxygen': -5}))
        self.assertFalse(oxygen_depleted()({'oxygen': 1}))

    def test_trust_high(self):
        """Test high trust check."""
        self.assertTrue(trust_high()({'trust': 60}))
        self.assertTrue(trust_high()({'trust': 80}))
        self.assertFalse(trust_high()({'trust': 59}))

    def test_time_up(self):
        """Test time expiration check."""
        self.assertTrue(time_up()({'time_remaining': 0}))
        self.assertTrue(time_up()({'time_remaining': -1}))
        self.assertFalse(time_up()({'time_remaining': 1}))


class TestStringParsing(unittest.TestCase):
    """Test parsing of condition strings (backwards compatibility)."""

    def setUp(self):
        self.state = {
            'oxygen': 50,
            'trust': 60,
            'phase': 2,
            'radiation': 95,
            'emotional_bond': 70
        }

    def test_simple_comparison(self):
        """Test parsing simple comparisons."""
        condition = parse_condition_string("state['oxygen'] > 40")
        self.assertTrue(condition(self.state))

        condition = parse_condition_string("state['trust'] >= 60")
        self.assertTrue(condition(self.state))

        condition = parse_condition_string("state['phase'] == 2")
        self.assertTrue(condition(self.state))

        condition = parse_condition_string("state['oxygen'] <= 0")
        self.assertFalse(condition(self.state))

    def test_logical_operators(self):
        """Test parsing logical operators."""
        # AND
        condition = parse_condition_string(
            "state['oxygen'] > 40 and state['trust'] >= 60"
        )
        self.assertTrue(condition(self.state))

        # OR
        condition = parse_condition_string(
            "state['oxygen'] <= 0 or state['trust'] < 20"
        )
        self.assertFalse(condition(self.state))

        condition = parse_condition_string(
            "state['oxygen'] > 40 or state['trust'] < 20"
        )
        self.assertTrue(condition(self.state))

    def test_complex_expression(self):
        """Test parsing complex expressions from actual scenes."""
        # From submarine.py
        condition = parse_condition_string(
            "state['radiation'] < 95 and state['emotional_bond'] >= 70"
        )
        self.assertFalse(condition(self.state))  # radiation is not < 95

        # From life_raft.py
        state = {
            'risky_triggered': 1,
            'empathy_score': 65,
            'commitment_score': 75,
            'presence_score': 55
        }
        condition = parse_condition_string(
            "state['risky_triggered'] == 1 and state['empathy_score'] >= 60 and "
            "state['commitment_score'] >= 70 and state['presence_score'] >= 50"
        )
        self.assertTrue(condition(state))

    def test_negative_numbers(self):
        """Test parsing negative number comparisons."""
        state = {'temperature': -10}
        condition = parse_condition_string("state['temperature'] < -5")
        self.assertTrue(condition(state))

        condition = parse_condition_string("state['temperature'] > -20")
        self.assertTrue(condition(state))

    def test_unsafe_operations_rejected(self):
        """Test that unsafe operations are rejected."""
        # Should reject function calls
        with self.assertRaises(ValueError):
            parse_condition_string("state['oxygen'] + __import__('os').system('ls')")

        # Should reject attribute access
        with self.assertRaises(ValueError):
            parse_condition_string("state.oxygen > 50")

        # Should reject arbitrary code
        with self.assertRaises(ValueError):
            parse_condition_string("exec('print(1)')")

    def test_real_scene_conditions(self):
        """Test with actual condition strings from scenes."""
        # From scenes/submarine.py
        test_cases = [
            ("state['radiation'] < 95 and state['emotional_bond'] >= 70", {'radiation': 90, 'emotional_bond': 80}, True),
            ("state['radiation'] >= 95", {'radiation': 95}, True),
            ("state['time_remaining'] <= 0", {'time_remaining': 0}, True),
        ]

        for condition_str, state, expected in test_cases:
            condition = parse_condition_string(condition_str)
            result = condition(state)
            self.assertEqual(result, expected,
                           f"Condition '{condition_str}' with state {state} should be {expected}, got {result}")


class TestSecurityProtection(unittest.TestCase):
    """Test that the system prevents code execution attacks."""

    def test_no_code_injection(self):
        """Test that code injection attempts are blocked."""
        malicious_strings = [
            "__import__('os').system('rm -rf /')",
            "exec('malicious code')",
            "eval('1+1')",
            "open('/etc/passwd').read()",
            "[x for x in ().__class__.__bases__[0].__subclasses__()]",
        ]

        for malicious in malicious_strings:
            with self.assertRaises((ValueError, SyntaxError)):
                parse_condition_string(malicious)

    def test_no_attribute_access(self):
        """Test that attribute access is blocked."""
        with self.assertRaises(ValueError):
            parse_condition_string("state.oxygen > 50")

        with self.assertRaises(ValueError):
            parse_condition_string("state['oxygen'].__class__")

    def test_only_safe_operations(self):
        """Test that only safe operations are allowed."""
        # These should all work (safe operations)
        safe_strings = [
            "state['oxygen'] > 50",
            "state['oxygen'] >= 50 and state['trust'] < 80",
            "state['phase'] == 2 or state['phase'] == 3",
            "state['value'] <= 0",
        ]

        state = {'oxygen': 60, 'trust': 70, 'phase': 2, 'value': -5}

        for safe_str in safe_strings:
            # Should not raise exception
            condition = parse_condition_string(safe_str)
            result = condition(state)
            self.assertIsInstance(result, bool)


if __name__ == '__main__':
    unittest.main()
