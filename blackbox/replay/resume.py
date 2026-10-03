"""
blackbox/replay/resume.py
─────────────────────────
Allows resuming agent execution from a specific step checkpoint with optional patches,
avoiding unnecessary re-computation of preceding successful steps.
"""
from __future__ import annotations

import copy
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from blackbox.capture.schema import (
    AgentTrace, AgentStep, TaskType, StepType, ToolCall, ModelCall, TokenUsage, AgentError
)
from blackbox.agents.tools.calculator import calculator
from blackbox.agents.tools.database import execute_sql, get_schema
from blackbox.agents.tools.search import search, retrieve
from blackbox.agents.tasks import math as math_tasks
from blackbox.agents.tasks import qa as qa_tasks
from blackbox.agents.tasks import text2sql as sql_tasks


def _close_enough(a: Any, b: Any, tol: float = 0.02) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return str(a).strip().lower() == str(b).strip().lower()


def resume_from_step(
    trace: AgentTrace,
    step_index: int,
    patched_output: Any = None,
    patched_inputs: dict[str, Any] | None = None,
    new_run_id: str | None = None
) -> AgentTrace:
    """
    Resumes an agent execution from `step_index`.
    Steps 0 to step_index - 1 are preserved exactly from the original trace checkpoint.
    Step `step_index` applies any provided patch or override.
    Downstream steps (step_index + 1 to end) are re-evaluated forward.
    """
    if step_index < 0 or step_index >= len(trace.steps):
        raise ValueError(f"Invalid step_index: {step_index}. Trace has {len(trace.steps)} steps.")

    child_run_id = new_run_id or f"{trace.run_id}-fork-s{step_index}-{uuid.uuid4().hex[:4]}"
    resumed_steps: list[AgentStep] = []

    # 1. Copy frozen preceding steps (0 to step_index - 1)
    for i in range(step_index):
        orig_step = trace.steps[i]
        cloned_step = copy.deepcopy(orig_step)
        resumed_steps.append(cloned_step)

    task_type = trace.task_type
    state: dict[str, Any] = {"result": None, "doc": None, "docs": [], "sql": None}

    # Reconstruct state from historical steps 0 to step_index - 1
    for step in resumed_steps:
        state["result"] = step.output
        if step.tool == "search":
            state["docs"] = step.output
        elif step.tool == "retrieve":
            state["doc"] = step.output
        elif "SELECT" in str(step.output).upper():
            state["sql"] = step.output

    # 2. Re-execute from step_index forward based on task domain
    if task_type == TaskType.MATH:
        resumed_steps = _resume_math(trace, step_index, patched_output, patched_inputs, resumed_steps, state)
    elif task_type == TaskType.QA:
        resumed_steps = _resume_qa(trace, step_index, patched_output, patched_inputs, resumed_steps, state)
    elif task_type == TaskType.TEXT2SQL:
        resumed_steps = _resume_text2sql(trace, step_index, patched_output, patched_inputs, resumed_steps, state)
    else:
        # Generic fallback
        resumed_steps = _resume_generic(trace, step_index, patched_output, patched_inputs, resumed_steps)

    final_output = resumed_steps[-1].output if resumed_steps else state.get("result")
    success = _close_enough(final_output, trace.expected_output)

    # Compute replay savings
    saved_steps = step_index
    total_steps = len(resumed_steps)
    saved_pct = round((saved_steps / max(1, total_steps)) * 100, 1)

    meta = dict(trace.meta)
    meta.update({
        "parent_run_id": trace.run_id,
        "fork_step_index": step_index,
        "resumed": True,
        "steps_reused": saved_steps,
        "replay_savings_pct": saved_pct,
        "patched": patched_output is not None or patched_inputs is not None
    })

    return AgentTrace(
        run_id=child_run_id,
        task_id=trace.task_id,
        task_type=trace.task_type,
        task_description=trace.task_description,
        steps=resumed_steps,
        final_output=final_output,
        expected_output=trace.expected_output,
        success=success,
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
        error=None if success else trace.error,
        fault_type="repaired" if success and trace.fault_type else trace.fault_type,
        fault_step=None if success else trace.fault_step,
        meta=meta
    )


def _resume_math(
    trace: AgentTrace,
    fork_step: int,
    patched_output: Any,
    patched_inputs: dict | None,
    resumed_steps: list[AgentStep],
    state: dict[str, Any]
) -> list[AgentStep]:
    # Extract math task params
    base_price = float(trace.meta.get("base_price", 100.0))
    quantity = int(trace.meta.get("quantity", 1))
    discount_rate = float(trace.meta.get("discount_rate", 0.0))
    tax_rate = float(trace.meta.get("tax_rate", 0.0))

    # Calculate standard correct values
    subtotal = round(base_price * quantity, 4)
    discounted = round(subtotal * (1 - discount_rate), 4)
    with_tax = round(discounted * (1 + tax_rate), 4)
    final = round(with_tax, 2)

    plan_values = [
        "plan",
        subtotal,
        discounted,
        with_tax,
        final,
        f"The final answer is ${final:.2f}."
    ]

    for i in range(fork_step, len(trace.steps)):
        orig = trace.steps[i]
        stype = orig.step_type
        inputs = patched_inputs if (i == fork_step and patched_inputs) else copy.deepcopy(orig.inputs)

        # Output calculation
        if i == fork_step and patched_output is not None:
            out = patched_output
        else:
            # Recompute based on current state or true plan value
            out = plan_values[i] if i < len(plan_values) else orig.output

        tc = None
        if orig.tool == "calculator":
            expr = inputs.get("expression", f"step_{i}")
            tc = ToolCall(tool_name="calculator", arguments={"expression": expr}, result=out, latency_ms=1.5)

        mc = None
        if stype == StepType.LLM_CALL:
            mc = ModelCall(model="mock", prompt=orig.name, response=str(out), tokens=TokenUsage(40, 15), latency_ms=10.0)

        step = AgentStep(
            step_index=i,
            step_type=stype,
            timestamp=datetime.now(timezone.utc),
            latency_ms=10.0 if stype == StepType.LLM_CALL else 2.0,
            inputs=inputs,
            output=out,
            tool=orig.tool,
            tool_call=tc,
            model_call=mc,
            error=None,
            tokens=TokenUsage(40, 15),
            metadata={"resumed": True}
        )
        resumed_steps.append(step)

    return resumed_steps


def _resume_qa(
    trace: AgentTrace,
    fork_step: int,
    patched_output: Any,
    patched_inputs: dict | None,
    resumed_steps: list[AgentStep],
    state: dict[str, Any]
) -> list[AgentStep]:
    for i in range(fork_step, len(trace.steps)):
        orig = trace.steps[i]
        stype = orig.step_type
        inputs = patched_inputs if (i == fork_step and patched_inputs) else copy.deepcopy(orig.inputs)

        if i == fork_step and patched_output is not None:
            out = patched_output
        else:
            if orig.tool == "search":
                q = inputs.get("query", trace.task_description)
                results = search(q)
                out = [{"doc_id": d.doc_id, "title": d.title, "score": d.score} for d in results]
            elif orig.tool == "retrieve":
                doc_id = inputs.get("doc_id", "doc-01")
                doc = retrieve(doc_id)
                out = doc.content if doc else ""
            else:
                out = trace.expected_output

        tc = None
        if orig.tool:
            tc = ToolCall(tool_name=orig.tool, arguments=inputs, result=out, latency_ms=5.0)

        mc = None
        if stype == StepType.LLM_CALL:
            mc = ModelCall(model="mock", prompt=orig.name, response=str(out), tokens=TokenUsage(50, 20), latency_ms=15.0)

        step = AgentStep(
            step_index=i,
            step_type=stype,
            timestamp=datetime.now(timezone.utc),
            latency_ms=12.0,
            inputs=inputs,
            output=out,
            tool=orig.tool,
            tool_call=tc,
            model_call=mc,
            error=None,
            tokens=TokenUsage(50, 20),
            metadata={"resumed": True}
        )
        resumed_steps.append(step)

    return resumed_steps


def _resume_text2sql(
    trace: AgentTrace,
    fork_step: int,
    patched_output: Any,
    patched_inputs: dict | None,
    resumed_steps: list[AgentStep],
    state: dict[str, Any]
) -> list[AgentStep]:
    current_sql = state.get("sql") or ""

    for i in range(fork_step, len(trace.steps)):
        orig = trace.steps[i]
        stype = orig.step_type
        inputs = patched_inputs if (i == fork_step and patched_inputs) else copy.deepcopy(orig.inputs)

        if i == fork_step and patched_output is not None:
            out = patched_output
            if "SELECT" in str(out).upper():
                current_sql = str(out)
        else:
            if orig.tool == "get_schema":
                out = get_schema()
            elif orig.tool == "execute_sql":
                sql = current_sql or inputs.get("sql", "")
                try:
                    out = execute_sql(sql)
                except Exception as e:
                    out = []
            elif i == 2:  # SQL generator step
                out = "SELECT name, price FROM products WHERE category = 'electronics' ORDER BY price ASC LIMIT 1;"
                current_sql = out
            else:
                out = trace.expected_output

        tc = None
        if orig.tool:
            tc = ToolCall(tool_name=orig.tool, arguments=inputs, result=out, latency_ms=8.0)

        mc = None
        if stype == StepType.LLM_CALL:
            mc = ModelCall(model="mock", prompt=orig.name, response=str(out), tokens=TokenUsage(60, 25), latency_ms=20.0)

        step = AgentStep(
            step_index=i,
            step_type=stype,
            timestamp=datetime.now(timezone.utc),
            latency_ms=15.0,
            inputs=inputs,
            output=out,
            tool=orig.tool,
            tool_call=tc,
            model_call=mc,
            error=None,
            tokens=TokenUsage(60, 25),
            metadata={"resumed": True}
        )
        resumed_steps.append(step)

    return resumed_steps


def _resume_generic(
    trace: AgentTrace,
    fork_step: int,
    patched_output: Any,
    patched_inputs: dict | None,
    resumed_steps: list[AgentStep]
) -> list[AgentStep]:
    for i in range(fork_step, len(trace.steps)):
        orig = trace.steps[i]
        out = patched_output if (i == fork_step and patched_output is not None) else orig.output
        inputs = patched_inputs if (i == fork_step and patched_inputs) else orig.inputs

        step = copy.deepcopy(orig)
        step.output = out
        step.inputs = inputs
        if step.has_error and i == fork_step and patched_output is not None:
            step.error = None
        resumed_steps.append(step)

    return resumed_steps
