"""
blackbox/capture/instrument.py
───────────────────────────────
Observability hooks for agent execution.

Usage
─────
    with TraceContext(run_id="run-01", task_id="math-42") as ctx:
        with ctx.step("llm_call", tool=None) as step:
            response = llm.call(prompt)
            step.set_output(response)
        with ctx.step("tool_call", tool="calculator") as step:
            result = calculator(expression)
            step.set_output(result)
    trace = ctx.build_trace(task_type, task_description, expected, final_output, success)

Or use the @capture_tool decorator on tool functions.
"""
from __future__ import annotations

import functools
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Generator

from blackbox.capture.schema import (
    AgentError,
    AgentStep,
    AgentTrace,
    ModelCall,
    StepType,
    TaskType,
    ToolCall,
    TokenUsage,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Step recorder ──────────────────────────────────────────────────────────────

class StepRecorder:
    """Mutable builder for a single AgentStep, used inside a `with ctx.step(...)` block."""

    def __init__(self, index: int, step_type: StepType, tool: str | None, inputs: dict):
        self._index     = index
        self._step_type = step_type
        self._tool      = tool
        self._inputs    = inputs
        self._output: Any = None
        self._error: AgentError | None = None
        self._tokens: TokenUsage | None = None
        self._model_call: ModelCall | None = None
        self._tool_call:  ToolCall  | None = None
        self._metadata: dict = {}
        self._start     = time.perf_counter()
        self._timestamp = _now()

    def set_output(self, value: Any) -> None:
        self._output = value

    def set_error(self, error_type: str, message: str, tb: str | None = None) -> None:
        self._error = AgentError(error_type=error_type, message=message, traceback=tb)

    def set_tokens(self, input_tokens: int, output_tokens: int) -> None:
        self._tokens = TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)

    def set_model_call(self, model: str, prompt: Any, response: str,
                       input_tokens: int = 0, output_tokens: int = 0) -> None:
        self._model_call = ModelCall(
            model=model, prompt=prompt, response=response,
            tokens=TokenUsage(input_tokens, output_tokens),
            latency_ms=0,  # filled in on build
        )
        self.set_tokens(input_tokens, output_tokens)

    def set_tool_call(self, tool_name: str, arguments: dict, result: Any,
                      error: str | None = None) -> None:
        elapsed = (time.perf_counter() - self._start) * 1000
        self._tool_call = ToolCall(
            tool_name=tool_name, arguments=arguments, result=result,
            latency_ms=elapsed,
            error=AgentError("ToolError", error) if error else None,
        )

    def set_meta(self, **kwargs) -> None:
        self._metadata.update(kwargs)

    def _build(self) -> AgentStep:
        elapsed = (time.perf_counter() - self._start) * 1000
        if self._model_call:
            self._model_call.latency_ms = elapsed
        return AgentStep(
            step_index=self._index,
            step_type=self._step_type,
            timestamp=self._timestamp,
            latency_ms=round(elapsed, 2),
            inputs=self._inputs,
            output=self._output,
            tool=self._tool,
            tool_call=self._tool_call,
            model_call=self._model_call,
            error=self._error,
            tokens=self._tokens,
            metadata=self._metadata,
        )


# ── Trace context ──────────────────────────────────────────────────────────────

class TraceContext:
    """Context manager that accumulates steps and builds a finished AgentTrace."""

    def __init__(self, run_id: str | None = None, task_id: str | None = None):
        self.run_id  = run_id or str(uuid.uuid4())[:12]
        self.task_id = task_id or str(uuid.uuid4())[:8]
        self._steps: list[AgentStep] = []
        self._started_at = _now()

    def __enter__(self) -> "TraceContext":
        return self

    def __exit__(self, *_) -> None:
        pass

    @contextmanager
    def step(
        self,
        step_type: StepType | str,
        *,
        tool: str | None = None,
        inputs: dict | None = None,
    ) -> Generator[StepRecorder, None, None]:
        if isinstance(step_type, str):
            step_type = StepType(step_type)
        rec = StepRecorder(
            index=len(self._steps),
            step_type=step_type,
            tool=tool,
            inputs=inputs or {},
        )
        try:
            yield rec
        except Exception as exc:
            rec.set_error(type(exc).__name__, str(exc))
            raise
        finally:
            self._steps.append(rec._build())

    def build_trace(
        self,
        *,
        task_type: TaskType,
        task_description: str,
        expected_output: Any,
        final_output: Any,
        success: bool,
        fault_type: str | None = None,
        fault_step: int | None = None,
        meta: dict | None = None,
    ) -> AgentTrace:
        return AgentTrace(
            run_id=self.run_id,
            task_id=self.task_id,
            task_type=task_type,
            task_description=task_description,
            steps=list(self._steps),
            final_output=final_output,
            expected_output=expected_output,
            success=success,
            started_at=self._started_at,
            ended_at=_now(),
            fault_type=fault_type,
            fault_step=fault_step,
            meta=meta or {},
        )


# ── @capture_tool decorator ────────────────────────────────────────────────────

def capture_tool(tool_name: str, ctx_attr: str = "_trace_ctx"):
    """
    Decorator that wraps a tool function and records its call into a TraceContext.
    The TraceContext must be attached to `self` (or the first arg) as `ctx_attr`.
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(self_or_ctx, *args, **kwargs):
            ctx: TraceContext | None = getattr(self_or_ctx, ctx_attr, None)
            if ctx is None:
                return fn(self_or_ctx, *args, **kwargs)
            inputs = {"args": args, "kwargs": kwargs}
            with ctx.step(StepType.TOOL_CALL, tool=tool_name, inputs=inputs) as rec:
                result = fn(self_or_ctx, *args, **kwargs)
                rec.set_output(result)
                rec.set_tool_call(tool_name, kwargs, result)
                return result
        return wrapper
    return decorator
