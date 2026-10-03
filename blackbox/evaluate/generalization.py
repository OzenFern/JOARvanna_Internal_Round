"""
blackbox/evaluate/generalization.py
───────────────────────────────────
Evaluates model generalization across unseen tasks and unseen fault classes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from blackbox.capture.schema import AgentTrace, TaskType
from blackbox.attribution.model import LocalAttributionModel
from blackbox.evaluate.localization import eval_localization, LocalizationMetrics


@dataclass
class GeneralizationReport:
    in_distribution_acc: float
    cross_task_metrics: dict[str, float]
    cross_fault_metrics: dict[str, float]
    overall_generalization_score: float


def eval_generalization(
    train_traces: list[AgentTrace],
    test_traces: list[AgentTrace],
    model: LocalAttributionModel
) -> GeneralizationReport:
    """
    Measures performance when testing on tasks and fault types held out during training.
    """
    # Breakdown by task type
    task_groups: dict[str, list[AgentTrace]] = {}
    fault_groups: dict[str, list[AgentTrace]] = {}

    for t in test_traces:
        tt = t.task_type.value
        task_groups.setdefault(tt, []).append(t)

        ft = t.fault_type or "none"
        fault_groups.setdefault(ft, []).append(t)

    task_results: dict[str, float] = {}
    for task_name, grp in task_groups.items():
        metrics = eval_localization(grp, model)
        task_results[task_name] = metrics.top1_accuracy

    fault_results: dict[str, float] = {}
    for f_name, grp in fault_groups.items():
        metrics = eval_localization(grp, model)
        fault_results[f_name] = metrics.top1_accuracy

    overall_metrics = eval_localization(test_traces, model)

    return GeneralizationReport(
        in_distribution_acc=overall_metrics.top1_accuracy,
        cross_task_metrics=task_results,
        cross_fault_metrics=fault_results,
        overall_generalization_score=round(sum(task_results.values()) / max(1, len(task_results)), 4)
    )
