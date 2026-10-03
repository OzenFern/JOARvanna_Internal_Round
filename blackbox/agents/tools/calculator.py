"""blackbox/agents/tools/calculator.py — Safe arithmetic tool."""
from __future__ import annotations
import ast, operator as op
from typing import Any

_OPS = {
    ast.Add: op.add, ast.Sub: op.sub,
    ast.Mult: op.mul, ast.Div: op.truediv,
    ast.Pow: op.pow, ast.USub: op.neg,
}

def _eval(node: ast.expr) -> float:
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.BinOp):
        fn = _OPS.get(type(node.op))
        if fn is None:
            raise ValueError(f"Unsupported op: {type(node.op).__name__}")
        return fn(_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        fn = _OPS.get(type(node.op))
        if fn is None:
            raise ValueError(f"Unsupported unary: {type(node.op).__name__}")
        return fn(_eval(node.operand))
    raise ValueError(f"Unsupported node: {type(node).__name__}")

def calculator(expression: str) -> float:
    """Evaluate a safe arithmetic expression and return a float."""
    if not isinstance(expression, str):
        raise TypeError(f"expression must be str, got {type(expression).__name__}")
    tree = ast.parse(expression.strip(), mode="eval")
    return round(_eval(tree.body), 6)
