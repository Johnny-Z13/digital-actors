"""
Safe condition evaluation system for scene success/failure criteria.

This module provides a secure alternative to eval() for evaluating scene conditions.
Instead of eval'ing arbitrary strings, conditions are built from predefined safe functions.

Security:
- No code execution via eval()
- Conditions are type-checked and validated
- Cannot access arbitrary Python objects or modules

Usage:
    # Build conditions using safe operators
    condition = and_(
        gte("oxygen", 50),
        lt("trust", 80)
    )

    # Evaluate with scene state
    result = condition(state)
"""

from typing import Dict, Any, Callable, Union


# Type alias for condition functions
Condition = Callable[[Dict[str, Any]], bool]


# ============================================================================
# Basic Comparison Operators
# ============================================================================

def eq(key: str, value: Any) -> Condition:
    """
    Equal: state[key] == value

    Example: eq("phase", 3) -> state["phase"] == 3
    """
    def _eval(state: Dict[str, Any]) -> bool:
        return state.get(key) == value
    return _eval


def ne(key: str, value: Any) -> Condition:
    """
    Not equal: state[key] != value

    Example: ne("phase", 1) -> state["phase"] != 1
    """
    def _eval(state: Dict[str, Any]) -> bool:
        return state.get(key) != value
    return _eval


def gt(key: str, value: Union[int, float]) -> Condition:
    """
    Greater than: state[key] > value

    Example: gt("oxygen", 50) -> state["oxygen"] > 50
    """
    def _eval(state: Dict[str, Any]) -> bool:
        val = state.get(key)
        if val is None:
            return False
        return val > value
    return _eval


def gte(key: str, value: Union[int, float]) -> Condition:
    """
    Greater than or equal: state[key] >= value

    Example: gte("trust", 60) -> state["trust"] >= 60
    """
    def _eval(state: Dict[str, Any]) -> bool:
        val = state.get(key)
        if val is None:
            return False
        return val >= value
    return _eval


def lt(key: str, value: Union[int, float]) -> Condition:
    """
    Less than: state[key] < value

    Example: lt("oxygen", 20) -> state["oxygen"] < 20
    """
    def _eval(state: Dict[str, Any]) -> bool:
        val = state.get(key)
        if val is None:
            return False
        return val < value
    return _eval


def lte(key: str, value: Union[int, float]) -> Condition:
    """
    Less than or equal: state[key] <= value

    Example: lte("oxygen", 0) -> state["oxygen"] <= 0
    """
    def _eval(state: Dict[str, Any]) -> bool:
        val = state.get(key)
        if val is None:
            return False
        return val <= value
    return _eval


# ============================================================================
# Logical Operators
# ============================================================================

def and_(*conditions: Condition) -> Condition:
    """
    Logical AND: all conditions must be True

    Example: and_(gt("oxygen", 50), gte("trust", 60))
    """
    def _eval(state: Dict[str, Any]) -> bool:
        return all(cond(state) for cond in conditions)
    return _eval


def or_(*conditions: Condition) -> Condition:
    """
    Logical OR: at least one condition must be True

    Example: or_(lte("oxygen", 0), lte("hull_integrity", 0))
    """
    def _eval(state: Dict[str, Any]) -> bool:
        return any(cond(state) for cond in conditions)
    return _eval


def not_(condition: Condition) -> Condition:
    """
    Logical NOT: inverts the condition

    Example: not_(eq("phase", 1))
    """
    def _eval(state: Dict[str, Any]) -> bool:
        return not condition(state)
    return _eval


# ============================================================================
# Helper Functions
# ============================================================================

def exists(key: str) -> Condition:
    """
    Check if a state key exists

    Example: exists("secret_discovered")
    """
    def _eval(state: Dict[str, Any]) -> bool:
        return key in state
    return _eval


def between(key: str, min_val: Union[int, float], max_val: Union[int, float]) -> Condition:
    """
    Check if state[key] is between min_val and max_val (inclusive)

    Example: between("trust", 40, 80)
    """
    def _eval(state: Dict[str, Any]) -> bool:
        val = state.get(key)
        if val is None:
            return False
        return min_val <= val <= max_val
    return _eval


# ============================================================================
# Condition Parser (for backwards compatibility with string conditions)
# ============================================================================

def parse_condition_string(condition_str: str) -> Condition:
    """
    Parse a condition string into a safe Condition function.

    This provides backwards compatibility for existing string-based conditions.
    Supports a limited subset of Python expressions:
    - State comparisons: state['key'] op value
    - Logical operators: and, or
    - Comparison operators: ==, !=, >, >=, <, <=

    Args:
        condition_str: Condition string like "state['oxygen'] > 50 and state['trust'] >= 60"

    Returns:
        Condition function that can be safely evaluated

    Raises:
        ValueError: If condition string contains unsafe operations
    """
    import re
    import ast

    # Parse the condition string as Python AST
    try:
        tree = ast.parse(condition_str, mode='eval')
    except SyntaxError as e:
        raise ValueError(f"Invalid condition syntax: {e}")

    def _ast_to_condition(node: ast.AST) -> Condition:
        """Recursively convert AST node to Condition function."""

        if isinstance(node, ast.Expression):
            return _ast_to_condition(node.body)

        elif isinstance(node, ast.Compare):
            # Handle comparisons: state['key'] op value
            if not isinstance(node.left, ast.Subscript):
                raise ValueError("Comparisons must be in form state['key'] op value")

            # Extract state key
            if not (isinstance(node.left.value, ast.Name) and node.left.value.id == 'state'):
                raise ValueError("Left side must be state['key']")

            if not isinstance(node.left.slice, ast.Constant):
                raise ValueError("State key must be a constant string")

            key = node.left.slice.value

            # Handle single comparison
            if len(node.ops) != 1 or len(node.comparators) != 1:
                raise ValueError("Chained comparisons not supported")

            op = node.ops[0]
            comparator = node.comparators[0]

            # Extract comparison value
            if isinstance(comparator, ast.Constant):
                value = comparator.value
            elif isinstance(comparator, ast.UnaryOp) and isinstance(comparator.op, ast.USub):
                # Handle negative numbers
                if isinstance(comparator.operand, ast.Constant):
                    value = -comparator.operand.value
                else:
                    raise ValueError("Unsupported comparison value")
            else:
                raise ValueError("Comparison value must be a constant")

            # Map operator to function
            if isinstance(op, ast.Eq):
                return eq(key, value)
            elif isinstance(op, ast.NotEq):
                return ne(key, value)
            elif isinstance(op, ast.Gt):
                return gt(key, value)
            elif isinstance(op, ast.GtE):
                return gte(key, value)
            elif isinstance(op, ast.Lt):
                return lt(key, value)
            elif isinstance(op, ast.LtE):
                return lte(key, value)
            else:
                raise ValueError(f"Unsupported comparison operator: {op}")

        elif isinstance(node, ast.BoolOp):
            # Handle logical operators: and, or
            conditions = [_ast_to_condition(val) for val in node.values]

            if isinstance(node.op, ast.And):
                return and_(*conditions)
            elif isinstance(node.op, ast.Or):
                return or_(*conditions)
            else:
                raise ValueError(f"Unsupported logical operator: {node.op}")

        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            # Handle not operator
            condition = _ast_to_condition(node.operand)
            return not_(condition)

        else:
            raise ValueError(f"Unsupported AST node type: {type(node).__name__}")

    return _ast_to_condition(tree)


# ============================================================================
# Common Condition Patterns (Convenience Functions)
# ============================================================================

def oxygen_depleted() -> Condition:
    """Common pattern: oxygen <= 0"""
    return lte("oxygen", 0)


def oxygen_critical(threshold: int = 20) -> Condition:
    """Common pattern: oxygen < threshold"""
    return lt("oxygen", threshold)


def trust_high(threshold: int = 60) -> Condition:
    """Common pattern: trust >= threshold"""
    return gte("trust", threshold)


def trust_low(threshold: int = 25) -> Condition:
    """Common pattern: trust < threshold"""
    return lt("trust", threshold)


def phase_is(phase_num: int) -> Condition:
    """Common pattern: phase == phase_num"""
    return eq("phase", phase_num)


def phase_at_least(phase_num: int) -> Condition:
    """Common pattern: phase >= phase_num"""
    return gte("phase", phase_num)


def time_up() -> Condition:
    """Common pattern: time_remaining <= 0"""
    return lte("time_remaining", 0)


# ============================================================================
# Testing/Validation
# ============================================================================

def validate_condition(condition: Condition, example_state: Dict[str, Any]) -> bool:
    """
    Validate that a condition function works with an example state.

    Args:
        condition: Condition function to test
        example_state: Example state dict to evaluate against

    Returns:
        True if condition evaluates successfully (result can be True or False)
    """
    try:
        result = condition(example_state)
        return isinstance(result, bool)
    except Exception:
        return False
