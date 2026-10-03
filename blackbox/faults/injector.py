"""
blackbox/faults/injector.py
────────────────────────────
FaultInjector: selects a step and corrupts it during agent execution.

Normal:   Step 0 → Step 1 → Step 2 → Step 3 → Step 4
Injected: Step 0 → Step 1 → Step 2* → Step 3 → Step 4
                                   ↑
                              faulty step (index=2)

The injector is passed to the runner, which calls should_inject(i)
before each step and corrupt(i, true_output, step_plan) to get the
corrupted value.
"""
from __future__ import annotations

import random
from typing import Any


class FaultInjector:
    def __init__(self, fault_type: str, fault_step: int, rng: random.Random):
        self.fault_type = fault_type
        self.fault_step = fault_step
        self._rng       = rng
        self._impl      = _REGISTRY.get(fault_type)
        if self._impl is None:
            raise ValueError(f"Unknown fault type: {fault_type!r}. "
                             f"Known: {list(_REGISTRY)}")

    def should_inject(self, step_index: int) -> bool:
        return step_index == self.fault_step

    def corrupt(self, step_index: int, true_output: Any,
                step_plan: dict[str, Any]) -> Any:
        return self._impl(true_output, step_plan, self._rng)


# ── Registry ───────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, Any] = {}

def register_fault(name: str):
    def decorator(fn):
        _REGISTRY[name] = fn
        return fn
    return decorator


# ── Fault implementations ──────────────────────────────────────────────────────

@register_fault("bad_args")
def _bad_args(true_output: Any, step_plan: dict, rng: random.Random) -> Any:
    from blackbox.faults.library.bad_args import inject
    return inject(true_output, step_plan, rng)


@register_fault("poisoned_context")
def _poisoned_context(true_output: Any, step_plan: dict, rng: random.Random) -> Any:
    from blackbox.faults.library.poisoned_context import inject
    return inject(true_output, step_plan, rng)


@register_fault("truncation")
def _truncation(true_output: Any, step_plan: dict, rng: random.Random) -> Any:
    from blackbox.faults.library.truncation import inject
    return inject(true_output, step_plan, rng)


@register_fault("fake_output")
def _fake_output(true_output: Any, step_plan: dict, rng: random.Random) -> Any:
    from blackbox.faults.library.fake_output import inject
    return inject(true_output, step_plan, rng)


KNOWN_FAULTS = list(_REGISTRY.keys())


def make_injector(fault_type: str, fault_step: int,
                  rng: random.Random | None = None) -> FaultInjector:
    return FaultInjector(fault_type, fault_step, rng or random.Random())
