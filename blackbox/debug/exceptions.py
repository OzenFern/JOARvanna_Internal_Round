"""
blackbox/debug/exceptions.py
────────────────────────────
Exception categorization, stack trace inspection, and root cause attribution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from blackbox.capture.schema import AgentTrace, AgentStep, AgentError


@dataclass
class ExceptionAnalysis:
    has_exception: bool
    origin_step_index: int | None
    origin_step_name: str | None
    exception_type: str | None
    exception_message: str | None
    category: str  # "syntax", "tool_runtime", "zero_division", "db_error", "timeout", "none"
    root_cause_summary: str


def analyze_exceptions(trace: AgentTrace) -> ExceptionAnalysis:
    """
    Scans trace steps for explicit or cascaded exceptions and categorizes them.
    """
    for step in trace.steps:
        if step.has_error and step.error:
            err = step.error
            msg = err.message.lower()
            etype = err.error_type

            if "zero" in msg or "division" in msg:
                cat = "zero_division"
                summary = f"ZeroDivisionError during calculation at step {step.step_index} ({step.name})."
            elif "syntax" in msg or "syntaxerror" in etype.lower():
                cat = "syntax"
                summary = f"Syntax error encountered in code or query at step {step.step_index}."
            elif "database" in etype.lower() or "sqlite" in msg or "column" in msg:
                cat = "db_error"
                summary = f"Database schema or execution error at step {step.step_index}: {err.message}"
            elif "timeout" in msg:
                cat = "timeout"
                summary = f"Execution timed out during {step.name} at step {step.step_index}."
            else:
                cat = "tool_runtime"
                summary = f"Runtime error in tool {step.tool or step.name}: {err.message}"

            return ExceptionAnalysis(
                has_exception=True,
                origin_step_index=step.step_index,
                origin_step_name=step.name,
                exception_type=err.error_type,
                exception_message=err.message,
                category=cat,
                root_cause_summary=summary
            )

    # Check top-level trace error
    if trace.error:
        return ExceptionAnalysis(
            has_exception=True,
            origin_step_index=len(trace.steps) - 1 if trace.steps else 0,
            origin_step_name=trace.steps[-1].name if trace.steps else "root",
            exception_type=trace.error.error_type,
            exception_message=trace.error.message,
            category="generic",
            root_cause_summary=f"Top-level execution error: {trace.error.message}"
        )

    return ExceptionAnalysis(
        has_exception=False,
        origin_step_index=None,
        origin_step_name=None,
        exception_type=None,
        exception_message=None,
        category="none",
        root_cause_summary="No runtime exceptions detected. Run suffered a silent semantic or calculation failure."
    )
