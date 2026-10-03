# Scripts Reference

This document provides detailed documentation for the CLI automation scripts in the `scripts/` directory.

## Table of Contents

- [Overview](#overview)
- [Generate Traces](#generate-traces)
- [Train Local Model](#train-local-model)
- [Run Analysis](#run-analysis)
- [Run Evaluation](#run-evaluation)
- [Export Report](#export-report)

---

## Overview

The scripts directory contains CLI tools for common operations:

- **generate_traces.py**: Generate synthetic benchmark traces
- **train_local.py**: Train the local attribution ML model
- **run_analysis.py**: Analyze an individual trace
- **run_eval.py**: Run full benchmark evaluation
- **export_report.py**: Export diagnostic reports

All scripts follow a consistent pattern:
1. Add root directory to `sys.path`
2. Use `argparse` for CLI argument parsing
3. Load data from TraceStore
4. Execute core blackbox library functions
5. Print formatted results to console

---

## Generate Traces

**File**: `scripts/generate_traces.py`

Generates synthetic execution traces across Math, QA, and Text2SQL tasks with controlled fault injection.

### Usage

```bash
python scripts/generate_traces.py [-n NUM_TRACES] [-f FAULT_RATIO] [-o OUTPUT_DIR] [-s SEED]
```

### Arguments

- `-n, --num-traces`: Number of traces to generate (default: 50)
- `-f, --fault-ratio`: Ratio of faulty traces (default: 0.6)
- `-o, --out`: Output traces directory (default: `data/traces`)
- `-s, --seed`: Random seed for reproducibility (default: 42)

### Implementation Details

```python
def generate(n: int = 50, fault_ratio: float = 0.6, 
             output_dir: Path = Path("data/traces"), seed: int = 42):
    rng = random.Random(seed)
    store = TraceStore(output_dir)
    labels = LabelStore(Path("data/artifacts/labels.json"))

    task_types = ["math", "qa", "text2sql"]
    fault_types = ["bad_args", "fake_output", "poisoned_context", "truncation"]

    for i in range(n):
        # Randomly select task type
        task_type = rng.choice(task_types)
        run_id = f"trace-{task_type}-{i:04d}"

        # Sample task based on type
        if task_type == "math":
            task = math_tasks.sample(rng)
        elif task_type == "qa":
            task = qa_tasks.sample(rng)
        else:
            task = sql_tasks.sample(rng)

        # Decide whether to inject fault
        inject = (rng.random() < fault_ratio)
        injector = None
        if inject:
            ftype = rng.choice(fault_types)
            fstep = rng.randint(1, 4)
            injector = FaultInjector(ftype, fstep, rng)

        # Run task with optional fault injection
        trace = run(task_type, task, run_id=run_id, injector=injector)
        store.save(trace)

        # Store ground truth labels if fault injected
        if trace.fault_step is not None:
            labels.set(trace.run_id, trace.fault_step, trace.fault_type)
            fault_count += 1
        else:
            success_count += 1

    labels.save()
```

### Process Flow

1. **Initialize**: Set up random generator, trace store, and label store
2. **Loop**: For each trace:
   - Randomly select task type (Math, QA, Text2SQL)
   - Sample a specific task from that domain
   - Decide whether to inject fault (based on fault_ratio)
   - If injecting: randomly select fault type and step (1-4)
   - Execute task with optional fault injection
   - Save trace to store
   - Store ground truth labels if fault injected
3. **Finalize**: Save labels and print summary

### Output

```
==================================================
Generated Traces Summary:
  • Total Traces:     50
  • Successful Runs:  20
  • Faulty Runs:      30
  • Storage Path:     /path/to/data/traces
==================================================
```

### Example

```bash
# Generate 100 traces with 70% fault injection
python scripts/generate_traces.py -n 100 -f 0.7 -s 123
```

---

## Train Local Model

**File**: `scripts/train_local.py`

Trains the LocalAttributionModel on stored traces and ground-truth labels.

### Usage

```bash
python scripts/train_local.py [-t TRACES_DIR] [-l LABELS_FILE] [-o OUTPUT_MODEL]
```

### Arguments

- `-t, --traces`: Traces directory (default: `data/traces`)
- `-l, --labels`: Labels JSON file (default: `data/artifacts/labels.json`)
- `-o, --out`: Model output path (default: `data/artifacts/model.pkl`)

### Implementation Details

```python
def train(traces_dir: Path = Path("data/traces"), 
          labels_file: Path = Path("data/artifacts/labels.json"), 
          output_model: Path = Path("data/artifacts/model.pkl")):
    store = TraceStore(traces_dir)
    traces = store.load_all()
    
    if not traces:
        print(f"Error: No traces found in {traces_dir}.")
        sys.exit(1)

    labels = LabelStore(labels_file)
    
    # If labels file doesn't exist, extract from traces
    if not labels_file.exists():
        for t in traces:
            if t.fault_step is not None:
                labels.set(t.run_id, t.fault_step, t.fault_type)

    print(f"Training LocalAttributionModel on {len(traces)} traces...")
    t0 = time.perf_counter()

    model = LocalAttributionModel()
    model.fit(traces, labels)
    model.save(output_model)
    elapsed = (time.perf_counter() - t0) * 1000

    # Evaluate model performance
    metrics = eval_localization(traces, model)
```

### Process Flow

1. **Load Traces**: Load all traces from traces directory
2. **Load Labels**: Load ground truth labels from JSON file
3. **Fallback**: If labels file doesn't exist, extract from trace metadata
4. **Train**: Fit LocalAttributionModel on traces and labels
5. **Save**: Serialize model to pickle file
6. **Evaluate**: Compute localization accuracy metrics
7. **Report**: Print training results and metrics

### Output

```
==================================================
Model Training Results:
  • Training Samples: 50
  • Training Latency: 34.2 ms
  • Top-1 Accuracy:   85.0%
  • Top-3 Accuracy:   95.0%
  • MRR:              0.892
  • Saved Model to:   /path/to/data/artifacts/model.pkl
==================================================
```

### Example

```bash
# Train model on custom traces directory
python scripts/train_local.py -t /custom/traces -o /custom/model.pkl
```

---

## Run Analysis

**File**: `scripts/run_analysis.py`

Analyzes an individual trace file and prints diagnosis results.

### Usage

```bash
python scripts/run_analysis.py RUN_ID [-t TRACES_DIR] [-m MODEL_PATH] [-c]
```

### Arguments

- `run_id`: Trace run ID to analyze (required)
- `-t, --traces`: Traces directory (default: `data/traces`)
- `-m, --model`: Model path (default: `data/artifacts/model.pkl`)
- `-c, --cloud`: Run cloud LLM verification (flag)

### Implementation Details

```python
def analyze(run_id: str, traces_dir: Path = Path("data/traces"), 
           model_path: Path = Path("data/artifacts/model.pkl"), 
           with_cloud: bool = False):
    store = TraceStore(traces_dir)
    trace = store.load(run_id)

    model = LocalAttributionModel()
    if model_path.exists():
        model.load(model_path)

    # Run local analysis
    local_res = analyze_local(trace, model)
    consensus = ConsensusResult(
        scores=local_res.scores,
        top_step=local_res.top_step,
        agreement=True,
        final_confidence=local_res.confidence
    )
    diagnosis = create_diagnosis(trace, consensus)

    # Print step suspicion attribution
    for i, s in enumerate(trace.steps):
        score = local_res.scores.get(i, 0.0)
        is_top = (i == local_res.top_step)
        flag = " [CULPRIT]" if is_top else ""
        print(f"  Step {i:02d} | {s.name:<18} | Suspicion: {score:.3f}{flag:<10}")

    # Print diagnosis verdict
    print(f"  • Primary Culprit: Step {diagnosis.likely_source}")
    print(f"  • Confidence:      {diagnosis.confidence.upper()}")
    print(f"  • Rationale:       {diagnosis.rationale}")

    # Generate and print suggestions
    sugs = generate_suggestions(trace, diagnosis.likely_source)
    if sugs:
        for s in sugs:
            print(f"  • [{s.action_type.upper()}] {s.title}: {s.description}")

    # Optional cloud verification
    if with_cloud:
        cloud_res = analyze_cloud(trace)
        print(f"  • Cloud Suspect: Step {cloud_res.top_step}")
        print(f"  • Cloud Reasoning: {cloud_res.reasoning}")
```

### Process Flow

1. **Load Trace**: Load specific trace by run_id
2. **Load Model**: Load trained model if available
3. **Local Analysis**: Run local ML analysis (<50ms)
4. **Diagnosis**: Create human-readable diagnosis
5. **Attribution**: Print step-by-step suspicion scores
6. **Verdict**: Print primary culprit and rationale
7. **Suggestions**: Generate and print remediation suggestions
8. **Cloud (Optional)**: Run LLM judge for verification

### Output

```
Analyzing Run: trace-math-0001 (MATH)
Task: Solve 2+2
Outcome: FAILED

============================================================
STEP SUSPICION ATTRIBUTION:
============================================================
  Step 00 | llm_call          | Suspicion: 0.120         | Out: I need to calculate 2+2
  Step 01 | calculator()      | Suspicion: 0.950 [CULPRIT]| Out: 5
  Step 02 | llm_call          | Suspicion: 0.080         | Out: The answer is 5

============================================================
DIAGNOSIS VERDICT:
============================================================
  • Primary Culprit: Step 1 (calculator())
  • Confidence:      HIGH
  • Rationale: Step 1 has a high suspicion score (0.950) and produced an incorrect calculation result (5 instead of 4).

Actionable Remediation Suggestions:
  • [OVERRIDE] Correct Calculation: Override the calculator output with the correct value 4.

Running Cloud Verifier...
  • Cloud Suspect: Step 1
  • Cloud Reasoning: The calculator step produced an incorrect result (5) for the expression 2+2, which should be 4.
```

### Example

```bash
# Analyze a specific trace with cloud verification
python scripts/run_analysis.py trace-math-0001 -c
```

---

## Run Evaluation

**File**: `scripts/run_eval.py`

Runs the full benchmark evaluation suite across localization accuracy, generalization, confidence calibration, latency, and replay savings.

### Usage

```bash
python scripts/run_eval.py [-t TRACES_DIR] [-m MODEL_PATH]
```

### Arguments

- `-t, --traces`: Traces directory (default: `data/traces`)
- `-m, --model`: Model path (default: `data/artifacts/model.pkl`)

### Implementation Details

```python
def evaluate(traces_dir: Path = Path("data/traces"), 
             model_path: Path = Path("data/artifacts/model.pkl")):
    store = TraceStore(traces_dir)
    traces = store.load_all()
    
    if not traces:
        print(f"Error: No traces found in {traces_dir}.")
        sys.exit(1)

    model = LocalAttributionModel()
    if model_path.exists():
        model.load(model_path)
    else:
        print("Warning: Model weights not found. Evaluating with calibrated heuristic baseline.")

    # Run evaluation metrics
    loc_metrics = eval_localization(traces, model)
    conf_metrics = eval_confidence(traces, model)
    lat_metrics = eval_latency(traces, model)
    cf_metrics = eval_counterfactual_repairs([t for t in traces if not t.success])
```

### Process Flow

1. **Load Traces**: Load all traces from directory
2. **Load Model**: Load trained model if available (fallback to heuristic)
3. **Localization**: Compute Top-1, Top-3 accuracy, and MRR
4. **Confidence**: Compute calibration metrics per tier
5. **Latency**: Compute diagnosis latency statistics
6. **Counterfactual**: Compute repair success rate
7. **Report**: Print comprehensive evaluation results

### Output

```
Evaluating Black Box Diagnostic System on 50 traces...

============================================================
1. LOCALIZATION ACCURACY & CALIBRATION
============================================================
  • Total Evaluated Traces:       50
  • Faulty Traces Analyzed:       30
  • Top-1 Fault Localization Acc: 85.0%
  • Top-3 Fault Localization Acc: 95.0%
  • Mean Reciprocal Rank (MRR):   0.892
  • High-Confidence Accuracy:     92.0%
  • Medium-Confidence Accuracy:   78.0%

============================================================
2. PERFORMANCE & REPLAY SAVINGS
============================================================
  • Mean Diagnosis Latency:       42.3 ms
  • P95 Diagnosis Latency:        48.7 ms
  • Sub-50ms SLA Met:             YES
  • Counterfactual Repair Success: 80.0%
============================================================
```

### Metrics Explained

**Localization Accuracy:**
- **Top-1 Accuracy**: Percentage of traces where model correctly identifies exact fault step
- **Top-3 Accuracy**: Percentage where fault step is in top 3 suspected steps
- **MRR (Mean Reciprocal Rank)**: Average of 1/rank across all traces (higher is better)

**Confidence Calibration:**
- **High-Confidence Accuracy**: Accuracy when confidence tier is "high"
- **Medium-Confidence Accuracy**: Accuracy when confidence tier is "medium"

**Performance:**
- **Mean Diagnosis Latency**: Average time for local analysis
- **P95 Diagnosis Latency**: 95th percentile latency
- **Sub-50ms SLA Met**: Whether P95 latency is under 50ms target

**Counterfactual:**
- **Repair Success Rate**: Percentage of failed runs that succeeded after applying suggested patch

### Example

```bash
# Evaluate on custom traces with custom model
python scripts/run_eval.py -t /custom/traces -m /custom/model.pkl
```

---

## Export Report

**File**: `scripts/export_report.py`

Exports diagnostic reports in Markdown format for audit and post-mortems.

### Usage

```bash
python scripts/export_report.py RUN_ID [-t TRACES_DIR] [-o OUTPUT_FILE]
```

### Arguments

- `run_id`: Trace run ID to export (required)
- `-t, --traces`: Traces directory (default: `data/traces`)
- `-o, --out`: Report output file (default: `data/reports/report.md`)

### Implementation Details

```python
def export(run_id: str, traces_dir: Path = Path("data/traces"), 
           output_file: Path = Path("data/reports/report.md")):
    store = TraceStore(traces_dir)
    trace = store.load(run_id)

    model = LocalAttributionModel()
    model_p = Path("data/artifacts/model.pkl")
    if model_p.exists():
        model.load(model_p)

    # Run analysis
    local_res = analyze_local(trace, model)
    consensus = ConsensusResult(...)
    diag = create_diagnosis(trace, consensus)
    sugs = generate_suggestions(trace, diag.likely_source)

    # Build markdown report
    lines = [
        f"# Black Box Root-Cause Post-Mortem Report",
        f"**Run ID:** `{trace.run_id}`",
        f"**Task Domain:** `{trace.task_type.value.upper()}`",
        f"**Status:** `{'SUCCESS' if trace.success else 'FAILED'}`",
        f"**Task Description:** {trace.task_description}",
        f"**Expected Output:** `{trace.expected_output}`",
        f"**Actual Output:** `{trace.final_output}`",
        "",
        f"## 1. Executive Summary & Root Cause Diagnosis",
        f"- **Primary Suspect:** Step {diag.likely_source}",
        f"- **Confidence Level:** `{diag.confidence.upper()}`",
        f"- **Rationale:** {diag.rationale}",
        "",
        f"## 2. Step Execution Timeline & Suspicion Scores",
        # ... table rows ...
        "",
        f"## 3. Actionable Remediation Suggestions",
        # ... suggestions ...
    ]

    content = "\n".join(lines)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
```

### Process Flow

1. **Load Trace**: Load specific trace by run_id
2. **Load Model**: Load trained model if available
3. **Analyze**: Run local analysis and create diagnosis
4. **Generate Suggestions**: Create remediation suggestions
5. **Build Report**: Construct markdown document with:
   - Executive summary
   - Step timeline table with suspicion scores
   - Remediation suggestions
6. **Save**: Write report to output file

### Output (Markdown)

```markdown
# Black Box Root-Cause Post-Mortem Report
**Run ID:** `trace-math-0001` | **Task Domain:** `MATH` | **Status:** `FAILED`
**Task Description:** Solve 2+2
**Expected Output:** `4` | **Actual Output:** `5`

## 1. Executive Summary & Root Cause Diagnosis
- **Primary Suspect:** Step 1 (`calculator()`)
- **Confidence Level:** `HIGH` (Suspicion Score: 0.950)
- **Rationale:** Step 1 has a high suspicion score (0.950) and produced an incorrect calculation result (5 instead of 4).

## 2. Step Execution Timeline & Suspicion Scores
| Step | Name | Type | Latency (ms) | Suspicion | Output Summary |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | `llm_call` | llm_call | 50.0 | 0.120 | `I need to calculate 2+2` |
| 1 | `calculator()` | tool_call | 5.0 | 0.950 ⚠️ **[CULPRIT]** | `5` |
| 2 | `llm_call` | llm_call | 30.0 | 0.080 | `The answer is 5` |

## 3. Actionable Remediation Suggestions
### • Correct Calculation (OVERRIDE)
- **Description:** Override the calculator output with the correct value 4.
- **Patch Payload:** `{"output": 4}`
```

### Example

```bash
# Export report to custom location
python scripts/export_report.py trace-math-0001 -o /custom/reports/postmortem.md
```

---

## Summary

The scripts provide a complete CLI workflow for the Black Box system:

1. **generate_traces.py**: Create synthetic benchmark data
2. **train_local.py**: Train ML model on traces
3. **run_analysis.py**: Debug individual traces
4. **run_eval.py**: Benchmark system performance
5. **export_report.py**: Generate audit reports

All scripts are designed to be:
- **Reproducible**: Use random seeds for consistent results
- **Configurable**: Support custom paths via CLI arguments
- **Informative**: Print detailed progress and results
- **Self-contained**: Handle missing data gracefully with fallbacks
