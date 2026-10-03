"""
scripts/generate_traces.py
──────────────────────────
CLI tool to generate synthetic execution traces across Math, QA, and Text2SQL tasks,
injecting controlled faults to build benchmark datasets.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

# Ensure package root is in path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackbox.capture.store import TraceStore
from blackbox.faults.injector import FaultInjector
from blackbox.faults.labels import LabelStore
from blackbox.agents.runner import run
from blackbox.agents.tasks import math as math_tasks
from blackbox.agents.tasks import qa as qa_tasks
from blackbox.agents.tasks import text2sql as sql_tasks


def generate(n: int = 50, fault_ratio: float = 0.6, output_dir: Path = Path("data/traces"), seed: int = 42):
    rng = random.Random(seed)
    store = TraceStore(output_dir)
    labels = LabelStore(Path("data/artifacts/labels.json"))

    print(f"Generating {n} agent execution traces into {output_dir}...")
    task_types = ["math", "qa", "text2sql"]
    fault_types = ["bad_args", "fake_output", "poisoned_context", "truncation"]

    success_count = 0
    fault_count = 0

    for i in range(n):
        task_type = rng.choice(task_types)
        run_id = f"trace-{task_type}-{i:04d}"

        if task_type == "math":
            task = math_tasks.sample(rng)
        elif task_type == "qa":
            task = qa_tasks.sample(rng)
        else:
            task = sql_tasks.sample(rng)

        inject = (rng.random() < fault_ratio)
        injector = None
        if inject:
            ftype = rng.choice(fault_types)
            fstep = rng.randint(1, 4)
            injector = FaultInjector(ftype, fstep, rng)

        trace = run(task_type, task, run_id=run_id, injector=injector)
        store.save(trace)

        if trace.fault_step is not None:
            labels.set(trace.run_id, trace.fault_step, trace.fault_type)
            fault_count += 1
        else:
            success_count += 1

    labels.save()
    print("=" * 50)
    print(f"Generated Traces Summary:")
    print(f"  • Total Traces:     {n}")
    print(f"  • Successful Runs:  {success_count}")
    print(f"  • Faulty Runs:      {fault_count}")
    print(f"  • Storage Path:     {output_dir.resolve()}")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic agent execution traces.")
    parser.add_argument("-n", "--num-traces", type=int, default=50, help="Number of traces to generate")
    parser.add_argument("-f", "--fault-ratio", type=float, default=0.6, help="Ratio of faulty traces")
    parser.add_argument("-o", "--out", type=Path, default=Path("data/traces"), help="Output traces dir")
    parser.add_argument("-s", "--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()
    generate(args.num_traces, args.fault_ratio, args.out, args.seed)
