"""
blackbox/faults/labels.py
──────────────────────────
Ground-truth label records for training runs.

Every generated training trace has:
  run_id     → unique identifier
  fault_type → which fault was injected
  fault_step → which step index was corrupted
  run_failed → whether the final answer was wrong (should be True for training)

These are stored alongside traces and loaded during dataset construction.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

LABELS_PATH = Path("data/artifacts/labels.json")


@dataclass
class FaultLabel:
    run_id:     str
    fault_type: str
    fault_step: int
    run_failed: bool
    task_type:  str
    n_steps:    int


class LabelStore:
    def __init__(self, path: Path = LABELS_PATH):
        self.path   = Path(path)
        self._labels: dict[str, FaultLabel] = {}
        if self.path.exists():
            self._load()

    def add(self, label: FaultLabel) -> None:
        self._labels[label.run_id] = label

    def get(self, run_id: str) -> FaultLabel | None:
        return self._labels.get(run_id)

    def all(self) -> list[FaultLabel]:
        return list(self._labels.values())

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump([asdict(lb) for lb in self._labels.values()], f, indent=2)

    def _load(self) -> None:
        with open(self.path) as f:
            for d in json.load(f):
                lb = FaultLabel(**d)
                self._labels[lb.run_id] = lb

    def __len__(self) -> int:
        return len(self._labels)
