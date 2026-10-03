"""
blackbox/agents/tasks/qa.py
────────────────────────────
Question-answering tasks using search + retrieval tools.

Step plan
─────────
  0: llm_call   — analyse question, form search query
  1: tool_call  — search(query) → list of documents
  2: tool_call  — retrieve(doc_id) → full document
  3: llm_call   — extract relevant fact from document
  4: llm_call   — compose and return final answer
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Any

from blackbox.capture.schema import TaskType


@dataclass
class QATask:
    task_id:         str
    question:        str
    search_query:    str          # what to search for
    target_doc_id:   str          # which document contains the answer
    expected_answer: str
    task_type:       TaskType = TaskType.QA
    meta:            dict     = field(default_factory=dict)


def build_plan(task: QATask) -> list[dict[str, Any]]:
    return [
        {
            "step_type": "llm_call",
            "description": "Analyse the question and decide what to search for.",
            "llm_response": f'I will search for: "{task.search_query}"',
            "true_output":  task.search_query,
        },
        {
            "step_type": "tool_call",
            "tool": "search",
            "description": f"Search for documents relevant to: {task.search_query}",
            "query": task.search_query,
            "true_output": "search_results",   # actual output filled at runtime
        },
        {
            "step_type": "tool_call",
            "tool": "retrieve",
            "description": f"Retrieve full document {task.target_doc_id}",
            "doc_id": task.target_doc_id,
            "true_output": "document_content",
        },
        {
            "step_type": "llm_call",
            "description": "Extract the specific fact needed to answer the question.",
            "llm_response": f"The relevant fact is: {task.expected_answer}",
            "true_output":  task.expected_answer,
        },
        {
            "step_type": "llm_call",
            "description": "Compose the final answer.",
            "llm_response": task.expected_answer,
            "true_output":  task.expected_answer,
        },
    ]


SAMPLES = [
    QATask("qa-01",
           "How tall is the Eiffel Tower?",
           search_query="Eiffel Tower height",
           target_doc_id="d01",
           expected_answer="330 metres"),
    QATask("qa-02",
           "When was Python programming language first released?",
           search_query="Python language history release",
           target_doc_id="d02",
           expected_answer="1991"),
    QATask("qa-03",
           "At what temperature does water boil at sea level?",
           search_query="water boiling point temperature",
           target_doc_id="d03",
           expected_answer="100 degrees Celsius"),
    QATask("qa-04",
           "What is the speed of light?",
           search_query="speed of light vacuum",
           target_doc_id="d04",
           expected_answer="299,792 km/s"),
    QATask("qa-05",
           "How long is the Amazon River?",
           search_query="Amazon River length km",
           target_doc_id="d06",
           expected_answer="approximately 6,400 km"),
]


def sample(rng: random.Random | None = None) -> QATask:
    rng = rng or random.Random()
    return rng.choice(SAMPLES)
