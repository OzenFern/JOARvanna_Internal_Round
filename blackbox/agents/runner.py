"""
blackbox/agents/runner.py
──────────────────────────
Scripted agent execution loop.

Runs a task through its predefined step plan, optionally injecting a fault
at one step.  Records every step via TraceContext and returns an AgentTrace.

The "scripted" approach means the LLM decisions are fixed — this is
intentional for training data generation (we need exact ground truth).
"""
from __future__ import annotations

import random
import re
import time
from datetime import datetime, timezone
from typing import Any

from blackbox.capture.instrument import TraceContext
from blackbox.capture.schema import AgentTrace, StepType, TaskType
from blackbox.agents.tools.calculator import calculator
from blackbox.agents.tools.database import execute_sql, get_schema
from blackbox.agents.tools.search import search, retrieve
from blackbox.agents.tasks import math as math_tasks
from blackbox.agents.tasks import qa as qa_tasks
from blackbox.agents.tasks import text2sql as sql_tasks
from blackbox.faults.injector import FaultInjector

def _close_enough(a: Any, b: Any, tol: float = 0.02) -> bool:
    # Numeric expected answers (math): pull the last number out of the text,
    # so "$439.40" or "The final answer is $439.40." matches 439.4.
    if isinstance(b, (int, float)):
        nums = re.findall(r"-?\d[\d,]*\.?\d*", str(a))
        if not nums:
            return False
        return abs(float(nums[-1].replace(",", "")) - float(b)) <= tol
    return str(a).strip().lower() == str(b).strip().lower()


def run_math(
    task: math_tasks.MathTask,
    *,
    run_id: str,
    injector: FaultInjector | None = None,
) -> AgentTrace:
    plan = math_tasks.build_plan(task)
    ctx  = TraceContext(run_id=run_id, task_id=task.task_id)
    state: dict[str, Any] = {"result": None}

    for i, step_plan in enumerate(plan):
        stype = StepType(step_plan["step_type"])
        true_out = step_plan["true_output"]
        actual_out = true_out

        # Fault injection
        if injector and injector.should_inject(i):
            actual_out = injector.corrupt(i, true_out, step_plan)

        with ctx.step(stype, tool=step_plan.get("tool"), inputs=step_plan) as rec:
            if stype == StepType.LLM_CALL:
                resp = actual_out if isinstance(actual_out, str) else step_plan["llm_response"]
                rec.set_output(resp)
                rec.set_model_call("mock", step_plan["description"], resp, 50, 20)
            else:
                rec.set_output(actual_out)
                rec.set_tool_call(
                    step_plan["tool"], {"expression": step_plan.get("expression", "")},
                    actual_out,
                )
            rec.set_meta(true_output=true_out, step_plan=step_plan.get("description"))
            state["result"] = actual_out

    final = state["result"]
    try:
        success = _close_enough(final, task.expected_answer)
    except Exception:
        success = False

    return ctx.build_trace(
        task_type=TaskType.MATH,
        task_description=task.description,
        expected_output=task.expected_answer,
        final_output=final,
        success=success,
        fault_type=injector.fault_type if injector else None,
        fault_step=injector.fault_step if injector else None,
        meta=task.meta,
    )


def run_qa(
    task: qa_tasks.QATask,
    *,
    run_id: str,
    injector: FaultInjector | None = None,
) -> AgentTrace:
    plan = qa_tasks.build_plan(task)
    ctx  = TraceContext(run_id=run_id, task_id=task.task_id)
    state: dict[str, Any] = {"result": None, "docs": [], "doc": None}

    for i, step_plan in enumerate(plan):
        stype = StepType(step_plan["step_type"])
        true_out = step_plan.get("true_output", "")
        actual_out = true_out

        if injector and injector.should_inject(i):
            actual_out = injector.corrupt(i, true_out, step_plan)

        with ctx.step(stype, tool=step_plan.get("tool"), inputs=step_plan) as rec:
            if stype == StepType.LLM_CALL:
                resp = step_plan.get("llm_response", str(actual_out))
                if injector and injector.should_inject(i):
                    resp = str(actual_out)
                rec.set_output(resp)
                rec.set_model_call("mock", step_plan["description"], resp, 60, 25)
                state["result"] = resp
            elif step_plan.get("tool") == "search":
                query = actual_out if isinstance(actual_out, str) else task.search_query
                results = search(query)
                rec.set_output([{"doc_id": d.doc_id, "title": d.title, "score": d.score}
                                 for d in results])
                rec.set_tool_call("search", {"query": query}, results)
                state["docs"] = results
            elif step_plan.get("tool") == "retrieve":
                doc_id = task.target_doc_id
                doc = retrieve(doc_id)
                content = doc.content if doc else ""
                if injector and injector.should_inject(i):
                    content = str(actual_out)
                rec.set_output(content)
                rec.set_tool_call("retrieve", {"doc_id": doc_id}, content)
                state["doc"] = content
            rec.set_meta(true_output=true_out)

    final = state["result"]
    success = _close_enough(final, task.expected_answer)
    return ctx.build_trace(
        task_type=TaskType.QA,
        task_description=task.question,
        expected_output=task.expected_answer,
        final_output=final,
        success=success,
        fault_type=injector.fault_type if injector else None,
        fault_step=injector.fault_step if injector else None,
    )


def run_text2sql(
    task: sql_tasks.Text2SQLTask,
    *,
    run_id: str,
    injector: FaultInjector | None = None,
) -> AgentTrace:
    plan = sql_tasks.build_plan(task)
    ctx  = TraceContext(run_id=run_id, task_id=task.task_id)
    state: dict[str, Any] = {"sql": task.correct_sql, "result": None}

    for i, step_plan in enumerate(plan):
        stype = StepType(step_plan["step_type"])
        true_out = step_plan.get("true_output", "")
        actual_out = true_out

        if injector and injector.should_inject(i):
            actual_out = injector.corrupt(i, true_out, step_plan)

        with ctx.step(stype, tool=step_plan.get("tool"), inputs=step_plan) as rec:
            if stype == StepType.LLM_CALL:
                if i == 2:  # SQL generation step
                    sql = actual_out if isinstance(actual_out, str) else task.correct_sql
                    rec.set_output(sql)
                    rec.set_model_call("mock", step_plan["description"], sql, 80, 30)
                    state["sql"] = sql
                else:
                    resp = step_plan.get("llm_response", str(actual_out))
                    rec.set_output(resp)
                    rec.set_model_call("mock", step_plan["description"], resp, 50, 20)
                    state["result"] = resp
            elif step_plan.get("tool") == "get_schema":
                schema = get_schema()
                rec.set_output(schema)
                rec.set_tool_call("get_schema", {}, schema)
            elif step_plan.get("tool") == "execute_sql":
                sql = state["sql"]
                try:
                    rows = execute_sql(sql)
                    if injector and injector.should_inject(i):
                        rows = actual_out if isinstance(actual_out, list) else rows
                except Exception as e:
                    rows = []
                    rec.set_error("DatabaseError", str(e))
                rec.set_output(rows)
                rec.set_tool_call("execute_sql", {"sql": sql}, rows)
            rec.set_meta(true_output=true_out)

    final = state.get("result", "")
    success = _close_enough(final, task.expected_answer)
    return ctx.build_trace(
        task_type=TaskType.TEXT2SQL,
        task_description=task.question,
        expected_output=task.expected_answer,
        final_output=final,
        success=success,
        fault_type=injector.fault_type if injector else None,
        fault_step=injector.fault_step if injector else None,
    )


# ── Dispatch ───────────────────────────────────────────────────────────────────

def run(task_type: str, task: Any, *, run_id: str,
        injector: FaultInjector | None = None) -> AgentTrace:
    if task_type == "math":
        return run_math(task, run_id=run_id, injector=injector)
    if task_type == "qa":
        return run_qa(task, run_id=run_id, injector=injector)
    if task_type == "text2sql":
        return run_text2sql(task, run_id=run_id, injector=injector)
    raise ValueError(f"Unknown task type: {task_type!r}")
