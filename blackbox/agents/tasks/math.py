"""
blackbox/agents/tasks/math.py
──────────────────────────────
Multi-step math tasks.  The agent uses the calculator tool to work through
an arithmetic word problem step-by-step.  The plan is scripted (so we
know the ground-truth answer and can inject faults reproducibly).

Step plan
─────────
  0: llm_call   — parse problem, identify operations needed
  1: tool_call  — calculator: compute subtraction (A - B)
  2: tool_call  — calculator: compute multiplication (result * C)
  3: tool_call  — calculator: apply percentage discount
  4: tool_call  — calculator: final rounding
  5: llm_call   — format answer as string
"""
from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Any

from blackbox.capture.schema import TaskType


@dataclass
class MathTask:
    task_id:          str
    description:      str
    task_type:        TaskType = TaskType.MATH
    # Ground-truth intermediate values
    base_price:       float = 0.0
    quantity:         int   = 1
    discount_rate:    float = 0.0
    tax_rate:         float = 0.0
    expected_answer:  float = 0.0
    meta:             dict  = None

    def __post_init__(self):
        if self.meta is None:
            self.meta = {
                "base_price":    self.base_price,
                "quantity":      self.quantity,
                "discount_rate": self.discount_rate,
                "tax_rate":      self.tax_rate,
            }


# Scripted plan steps — each entry is what the agent "decides" to do
def build_plan(task: MathTask) -> list[dict[str, Any]]:
    subtotal    = round(task.base_price * task.quantity, 4)
    discounted  = round(subtotal * (1 - task.discount_rate), 4)
    with_tax    = round(discounted * (1 + task.tax_rate), 4)
    final       = round(with_tax, 2)
    return [
        {
            "step_type": "llm_call",
            "description": "Parse the problem and identify the computation steps.",
            "llm_response": (
                f"I need to: (1) multiply {task.base_price} × {task.quantity}, "
                f"(2) apply {task.discount_rate:.0%} discount, "
                f"(3) apply {task.tax_rate:.0%} tax."
            ),
            "true_output": "plan",
        },
        {
            "step_type": "tool_call",
            "tool": "calculator",
            "description": f"Compute subtotal: {task.base_price} × {task.quantity}",
            "expression": f"{task.base_price} * {task.quantity}",
            "true_output": subtotal,
        },
        {
            "step_type": "tool_call",
            "tool": "calculator",
            "description": f"Apply {task.discount_rate:.0%} discount",
            "expression": f"{subtotal} * (1 - {task.discount_rate})",
            "true_output": discounted,
        },
        {
            "step_type": "tool_call",
            "tool": "calculator",
            "description": f"Apply {task.tax_rate:.0%} tax",
            "expression": f"{discounted} * (1 + {task.tax_rate})",
            "true_output": with_tax,
        },
        {
            "step_type": "tool_call",
            "tool": "calculator",
            "description": "Round to 2 decimal places",
            "expression": f"round({with_tax}, 2)",
            "true_output": final,
        },
        {
            "step_type": "llm_call",
            "description": "Format the final answer.",
            "llm_response": f"The final answer is ${final:.2f}.",
            "true_output": f"${final:.2f}",
        },
    ]


SAMPLES = [
    MathTask("math-01",
             "An item costs $149.99. Buy 3 items. Apply 10% discount. Add 8.5% tax.",
             base_price=149.99, quantity=3, discount_rate=0.10, tax_rate=0.085,
             expected_answer=round(149.99 * 3 * 0.90 * 1.085, 2)),
    MathTask("math-02",
             "Laptop costs $899. Buy 2. Member discount 15%. No tax.",
             base_price=899.0, quantity=2, discount_rate=0.15, tax_rate=0.0,
             expected_answer=round(899.0 * 2 * 0.85, 2)),
    MathTask("math-03",
             "Monthly subscription $29.99 × 12 months. Student discount 5%. No tax.",
             base_price=29.99, quantity=12, discount_rate=0.05, tax_rate=0.0,
             expected_answer=round(29.99 * 12 * 0.95, 2)),
    MathTask("math-04",
             "Book costs $24.50. Buy 5. No discount. 6.25% tax.",
             base_price=24.50, quantity=5, discount_rate=0.0, tax_rate=0.0625,
             expected_answer=round(24.50 * 5 * 1.0625, 2)),
    MathTask("math-05",
             "Headset at $329. Qty 1. 8% loyalty discount. 13% tax.",
             base_price=329.0, quantity=1, discount_rate=0.08, tax_rate=0.13,
             expected_answer=round(329.0 * 0.92 * 1.13, 2)),
]


def sample(rng: random.Random | None = None) -> MathTask:
    rng = rng or random.Random()
    return rng.choice(SAMPLES)
