"""
blackbox/agents/tasks/text2sql.py
──────────────────────────────────
Text-to-SQL tasks.  The agent looks up the schema, generates SQL,
validates it, executes it, and formats the result.

Step plan
─────────
  0: llm_call   — understand the question
  1: tool_call  — get_schema() → table/column info
  2: llm_call   — generate SQL query
  3: tool_call  — execute_sql(sql) → result rows
  4: llm_call   — format result as natural language answer
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Any

from blackbox.capture.schema import TaskType


@dataclass
class Text2SQLTask:
    task_id:         str
    question:        str
    correct_sql:     str
    expected_answer: str          # human-readable expected result
    expected_rows:   list[dict]   # raw query result
    task_type:       TaskType = TaskType.TEXT2SQL
    meta:            dict     = field(default_factory=dict)


def build_plan(task: Text2SQLTask) -> list[dict[str, Any]]:
    return [
        {
            "step_type": "llm_call",
            "description": "Understand the question and identify needed tables.",
            "llm_response": f'I need to query the database. Question: "{task.question}"',
            "true_output":  task.question,
        },
        {
            "step_type": "tool_call",
            "tool": "get_schema",
            "description": "Retrieve the database schema.",
            "true_output":  "schema",
        },
        {
            "step_type": "llm_call",
            "description": "Generate the SQL query from natural language.",
            "llm_response": task.correct_sql,
            "true_output":  task.correct_sql,
        },
        {
            "step_type": "tool_call",
            "tool": "execute_sql",
            "description": f"Execute: {task.correct_sql}",
            "sql": task.correct_sql,
            "true_output":  task.expected_rows,
        },
        {
            "step_type": "llm_call",
            "description": "Format the query result as a natural language answer.",
            "llm_response": task.expected_answer,
            "true_output":  task.expected_answer,
        },
    ]


SAMPLES = [
    Text2SQLTask(
        "sql-01",
        "How many orders were completed?",
        correct_sql="SELECT COUNT(*) FROM orders WHERE status = 'completed'",
        expected_answer="5 completed orders",
        expected_rows=[{"count": 5}],
    ),
    Text2SQLTask(
        "sql-02",
        "What is the total revenue from completed orders?",
        correct_sql="SELECT SUM(amount) FROM orders WHERE status = 'completed'",
        expected_answer="Total revenue: $1,525.00",
        expected_rows=[{"sum": 1525.0}],
    ),
    Text2SQLTask(
        "sql-03",
        "What is the average order amount?",
        correct_sql="SELECT AVG(amount) FROM orders",
        expected_answer="Average order amount: $363.81",
        expected_rows=[{"avg": 363.8125}],
    ),
    Text2SQLTask(
        "sql-04",
        "How many orders came from the north region?",
        correct_sql="SELECT COUNT(*) FROM orders WHERE region = 'north'",
        expected_answer="3 orders from north region",
        expected_rows=[{"count": 3}],
    ),
    Text2SQLTask(
        "sql-05",
        "What is the total amount for pending orders?",
        correct_sql="SELECT SUM(amount) FROM orders WHERE status = 'pending'",
        expected_answer="Total pending: $665.50",
        expected_rows=[{"sum": 665.5}],
    ),
]


def sample(rng: random.Random | None = None) -> Text2SQLTask:
    rng = rng or random.Random()
    return rng.choice(SAMPLES)
