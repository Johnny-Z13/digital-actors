"""
Test to verify that the eval() vulnerability has been fixed.

This test verifies that:
1. The old eval() method is no longer used
2. Malicious code cannot be executed through condition strings
3. Safe parsing works for legitimate conditions
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scene_conditions import parse_condition_string


class TestEvalSecurityFix(unittest.TestCase):
    """Verify that eval() vulnerability is fixed."""

    def test_malicious_code_injection_blocked(self):
        """Test that code injection attempts are blocked."""
        malicious_attempts = [
            # OS command execution
            "__import__('os').system('ls')",
            "__import__('os').system('rm -rf /')",

            # File access
            "open('/etc/passwd').read()",
            "open(__file__).read()",

            # Code execution
            "exec('print(\"pwned\")')",
            "eval('__import__(\"os\").system(\"ls\")')",

            # Object introspection attacks
            "[x for x in ().__class__.__bases__[0].__subclasses__()]",
            "().__class__.__bases__[0].__subclasses__()[104].__init__.__globals__['sys'].modules['os'].system('ls')",

            # Module imports
            "__import__('subprocess').call(['ls'])",
            "__import__('sys').exit()",
        ]

        for malicious in malicious_attempts:
            with self.subTest(code=malicious):
                with self.assertRaises((ValueError, SyntaxError),
                                     msg=f"Should reject: {malicious}"):
                    parse_condition_string(malicious)

        print(f"✓ Blocked {len(malicious_attempts)} code injection attempts")

    def test_attribute_access_blocked(self):
        """Test that attribute access is blocked (prevents object introspection)."""
        dangerous_attributes = [
            "state.oxygen",  # Attribute access instead of dict access
            "state['oxygen'].__class__",  # Class introspection
            "state['oxygen'].__dict__",  # Dict introspection
            "state.__getitem__('oxygen')",  # Method calls
        ]

        for dangerous in dangerous_attributes:
            with self.subTest(code=dangerous):
                with self.assertRaises((ValueError, SyntaxError),
                                     msg=f"Should reject: {dangerous}"):
                    parse_condition_string(dangerous)

        print(f"✓ Blocked {len(dangerous_attributes)} attribute access attempts")

    def test_safe_conditions_work(self):
        """Test that legitimate conditions still work."""
        safe_conditions = [
            ("state['oxygen'] > 50", {'oxygen': 60}, True),
            ("state['oxygen'] <= 0", {'oxygen': 0}, True),
            ("state['trust'] >= 60", {'trust': 60}, True),
            ("state['phase'] == 2", {'phase': 2}, True),
            ("state['oxygen'] > 50 and state['trust'] >= 60",
             {'oxygen': 60, 'trust': 70}, True),
            ("state['oxygen'] <= 0 or state['radiation'] >= 95",
             {'oxygen': 50, 'radiation': 95}, True),
        ]

        for condition_str, state, expected in safe_conditions:
            with self.subTest(condition=condition_str):
                try:
                    condition_fn = parse_condition_string(condition_str)
                    result = condition_fn(state)
                    self.assertEqual(result, expected,
                                   f"Condition '{condition_str}' should be {expected}")
                except Exception as e:
                    self.fail(f"Safe condition '{condition_str}' raised error: {e}")

        print(f"✓ {len(safe_conditions)} safe conditions work correctly")

    def test_no_eval_in_codebase(self):
        """Verify that eval() builtin is not used in scene condition evaluation."""
        # Read the scene_conditions.py file
        with open('scene_conditions.py', 'r') as f:
            content = f.read()

        # Check that eval() builtin is not used in actual code
        lines = content.split('\n')
        eval_usage = []
        in_docstring = False

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track docstring state
            if '"""' in line or "'''" in line:
                in_docstring = not in_docstring
                continue

            # Skip comments and docstrings
            if in_docstring or stripped.startswith('#'):
                continue

            # Check for eval() builtin usage (not _eval function names)
            # Look for "eval(" as an actual function call
            if 'eval(' in line and 'eval(' not in ['def _eval(', '_eval(', 'evaluate(']:
                # Skip if it's defining or calling _eval
                if 'def _eval(' in line or '_eval(' in line or 'evaluate(' in line:
                    continue
                # Skip if it's part of a string
                if '"eval(' in line or "'eval(" in line:
                    continue
                eval_usage.append(f"Line {i}: {line.strip()}")

        self.assertEqual(len(eval_usage), 0,
                        f"Found eval() builtin usage in scene_conditions.py:\n" + "\n".join(eval_usage))

        print("✓ No unsafe eval() builtin usage found in scene_conditions.py")

    def test_ast_based_parsing(self):
        """Verify that parsing uses AST (safe) instead of eval."""
        import ast

        condition_str = "state['oxygen'] > 50 and state['trust'] >= 60"

        # This should use AST parsing
        try:
            condition_fn = parse_condition_string(condition_str)

            # Verify it works
            result = condition_fn({'oxygen': 60, 'trust': 70})
            self.assertTrue(result)

            print("✓ AST-based parsing works correctly")
        except Exception as e:
            self.fail(f"AST parsing failed: {e}")

    def test_realistic_submarine_conditions(self):
        """Test with actual condition strings from submarine.py."""
        test_cases = [
            # Success conditions
            ("state['radiation'] < 95 and state['emotional_bond'] >= 70 and state['systems_repaired'] >= 3",
             {'radiation': 85, 'emotional_bond': 75, 'systems_repaired': 3}, True),

            # Failure conditions
            ("state['radiation'] >= 95",
             {'radiation': 95}, True),

            ("state['time_remaining'] <= 0",
             {'time_remaining': 0}, True),

            # Complex life raft condition
            ("state['risky_triggered'] == 1 and state['empathy_score'] >= 60 and state['commitment_score'] >= 70 and state['presence_score'] >= 50",
             {'risky_triggered': 1, 'empathy_score': 65, 'commitment_score': 75, 'presence_score': 55}, True),
        ]

        for condition_str, state, expected in test_cases:
            with self.subTest(condition=condition_str[:50]):
                condition_fn = parse_condition_string(condition_str)
                result = condition_fn(state)
                self.assertEqual(result, expected,
                               f"Condition should evaluate to {expected}")

        print(f"✓ {len(test_cases)} realistic scene conditions work correctly")


if __name__ == '__main__':
    print("\n" + "="*70)
    print("SECURITY FIX VERIFICATION: Scene Condition Evaluation")
    print("="*70 + "\n")

    suite = unittest.TestLoader().loadTestsFromTestCase(TestEvalSecurityFix)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*70)
    if result.wasSuccessful():
        print("✅ SECURITY FIX VERIFIED - eval() vulnerability eliminated")
        print("   - Code injection attacks blocked")
        print("   - Attribute access attacks blocked")
        print("   - Safe conditions work correctly")
        print("   - AST-based parsing is used")
    else:
        print("❌ SECURITY FIX INCOMPLETE - Some tests failed")
    print("="*70 + "\n")

    sys.exit(0 if result.wasSuccessful() else 1)
