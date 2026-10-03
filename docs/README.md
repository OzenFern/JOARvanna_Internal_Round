# Black Box Documentation

Welcome to the comprehensive documentation for **Black Box**, an AI-powered fault localization and time-travel debugging system for multi-step AI agents.

## Table of Contents

- [Overview](#overview)
- [Core Concepts](#core-concepts)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Module Documentation](#module-documentation)
- [API Reference](#api-reference)

---

## Overview

Black Box is a debugging workbench designed to identify root-cause failures in complex multi-step AI agent executions. Traditional logging systems cannot pinpoint which intermediate decision caused downstream failures in long execution graphs. Black Box solves this through:

1. **Intelligent Fault Localization** - ML-based suspicion scoring across execution graphs
2. **Dual-Layer Verification** - Fast local ML (<50ms) + optional LLM judge consensus
3. **Actionable Remediation** - Tailored patch recommendations
4. **Time-Travel Replay** - Resume execution from any checkpoint without re-running unaffected steps
5. **Trace Diff Analysis** - Side-by-side comparison to locate earliest divergence
6. **Quantitative Evaluation** - Benchmarks for accuracy, latency, and computational savings

### Problem Statement

AI agents solve complex tasks across long execution graphs involving:
- Model calls (LLM interactions)
- Tool executions (calculators, databases, search)
- Retrieved documents
- State mutations

A 20-step execution may appear normal throughout but fail at the end due to a single subtle error at Step 2 (e.g., wrong tool arguments, poisoned document context, unit conversion mistake, or SQL schema drift).

### Solution Approach

Black Box provides a complete debugging pipeline:

```
Agent Execution → Trace Capture → Local ML Analysis → Cloud Verification → Remediation → Replay
```

---

## Core Concepts

### AgentTrace

The fundamental data structure representing a complete agent execution. Contains:
- **Steps**: Sequential list of AgentStep objects
- **Task metadata**: Domain (Math, QA, Text2SQL), description, expected vs actual output
- **Execution telemetry**: Total latency, token consumption, timestamps
- **Fault information**: Ground truth fault type and step (for training)

### AgentStep

A single atomic operation in the agent's execution graph:
- **Step types**: LLM_CALL, TOOL_CALL, OBSERVATION, DECISION, RETRIEVAL
- **Inputs/Outputs**: Arguments passed and results returned
- **Telemetry**: Latency, token usage, error states
- **Tool/Model calls**: Detailed telemetry for external interactions

### Checkpoint

A snapshot of agent state at a specific step, enabling:
- **State reconstruction**: Restore agent memory at any point
- **Branch execution**: Fork new execution paths from checkpoints
- **Computational savings**: Skip re-executing steps 0 to k-1

### Attribution Model

The ML model that assigns suspicion scores to each step:
- **Local model**: Gradient Boosting or pure Python statistical anomaly classifier
- **Features**: Position, latency, error flags, token usage, text embeddings
- **Output**: Suspicion score (0.0 to 1.0) per step
- **Target latency**: <50ms for local analysis

### Consensus

Combines local ML analysis with optional cloud LLM verification:
- **Local**: Fast, deterministic, always available
- **Cloud**: Deep semantic critique, optional, requires API key
- **Agreement**: When both agree on culprit step → high confidence
- **Refinement**: When they disagree → cloud overrides with reasoning

---

## Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent Execution                          │
│  (Multi-step task: LLM calls, tools, retrievals, decisions) │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Trace Capture Layer                        │
│  • TraceContext: Decorator-based instrumentation            │
│  • @capture_tool: Automatic tool call recording            │
│  • TraceStore: JSON persistence to data/traces/             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Feature Extraction Layer                    │
│  • Step features: Position, latency, errors, tokens          │
│  • Text embeddings: TF-IDF / n-gram bag-of-words             │
│  • Dataset builder: ML-ready matrix construction            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 Attribution Model Layer                       │
│  • LocalAttributionModel: GBM or pure Python classifier      │
│  • Confidence calculator: High/Medium/Low tiers              │
│  • Baselines: FirstError, CloudJudge for comparison          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Analysis & Consensus                        │
│  • Local analyzer: <50ms fault localization                  │
│  • Cloud verifier: Optional LLM judge (OpenAI/Gemini)       │
│  • Consensus merger: Combine local + cloud results          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Debugging & Remediation                      │
│  • Diagnosis: Human-readable failure explanation             │
│  • Suggestions: Actionable patch recommendations             │
│  • Exception categorization: ZeroDivision, ToolError, etc.   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                Checkpointed Replay Engine                     │
│  • Checkpoint: State snapshot at any step                    │
│  • Resume: Forward execution from checkpoint                 │
│  • Branch: Fork new execution with patched parameters       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Trace Diff & Divergence                      │
│  • Alignment: Step sequence alignment algorithm              │
│  • Divergence: Earliest point of execution difference        │
│  • Contrastive explanation: Why executions deviated           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Streamlit Web UI                           │
│  • 6 interactive pages for complete debugging workflow        │
│  • Real-time visualization and interactive controls          │
└─────────────────────────────────────────────────────────────┘
```

### Module Organization

```
blackbox/
├── capture/          # Data structures and instrumentation
├── attribution/      # ML models and confidence scoring
├── analysis/         # Local/cloud analysis coordination
├── features/         # Feature extraction and embeddings
├── agents/           # Multi-domain agent implementations
├── faults/           # Fault injection library
├── replay/           # Checkpointing and resumption
├── intervene/        # Counterfactual branch testing
├── compare/          # Trace diff and divergence
├── debug/            # Diagnosis and suggestions
├── explain/          # Explainability and saliency
└── evaluate/        # Benchmark evaluation suite
```

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/OzenFern/JOARvanna_Internal_Round.git
cd JOARvanna_Internal_Round

# Install dependencies
pip install -e .
```

### Generate Traces

```bash
python scripts/generate_traces.py -n 50 -f 0.6
```

This creates 50 synthetic traces across Math, QA, and Text2SQL tasks with 60% fault injection rate.

### Train Model

```bash
python scripts/train_local.py
```

Trains the local attribution model on generated traces.

### Launch Web UI

```bash
python -m streamlit run app/main.py
```

Opens the interactive debugging workbench at `http://localhost:8501`.

---

## Module Documentation

Detailed documentation for each module:

- [Blackbox Core Module](./blackbox_module.md) - Core library implementation
- [Streamlit App Module](./app_module.md) - Web interface implementation
- [Scripts Reference](./scripts.md) - CLI automation scripts
- [Configuration Guide](./configuration.md) - YAML configuration files

---

## API Reference

### Core Classes

#### AgentTrace
```python
@dataclass
class AgentTrace:
    run_id: str
    task_type: TaskType
    task_description: str
    steps: list[AgentStep]
    final_output: Any
    expected_output: Any
    success: bool
    # ... additional fields
```

#### AgentStep
```python
@dataclass
class AgentStep:
    step_index: int
    step_type: StepType
    inputs: dict[str, Any]
    output: Any
    latency_ms: float
    error: AgentError | None = None
    # ... additional fields
```

#### LocalAttributionModel
```python
class LocalAttributionModel:
    def fit(self, traces: list[AgentTrace], labels: LabelStore) -> None
    def predict_trace(self, trace: AgentTrace) -> dict[int, float]
    def save(self, path: Path) -> None
    def load(self, path: Path) -> None
```

### Key Functions

#### TraceContext
```python
with TraceContext(run_id="run-01", task_id="math-42") as ctx:
    with ctx.step("llm_call", tool=None) as step:
        response = llm.call(prompt)
        step.set_output(response)
    trace = ctx.build_trace(task_type, task_description, expected, final, success)
```

#### @capture_tool Decorator
```python
@capture_tool("calculator")
def calculate(self, expression: str) -> float:
    return eval(expression)
```

---

## Evaluation Metrics

The system evaluates performance across multiple dimensions:

### Localization Accuracy
- **Top-1 Accuracy**: Percentage of traces where model correctly identifies exact fault step
- **Top-3 Accuracy**: Percentage where fault step is in top 3 suspected steps
- **Mean Reciprocal Rank (MRR)**: Average of 1/rank across all traces

### Latency SLA
- **Local Analysis Target**: <50ms per trace
- **Cloud Verification**: Typically 2-5 seconds (depends on LLM API)

### Confidence Calibration
- **High Confidence**: Top score > 2× second score
- **Medium Confidence**: Top score > 1.3× second score
- **Low Confidence**: Otherwise

### Computational Savings
- **Replay Savings**: Percentage of steps skipped via checkpointed replay
- **Token Savings**: Tokens saved by not re-executing LLM calls

---

## Contributing

When adding new features:

1. Update relevant module documentation
2. Add fault types to `blackbox/faults/library/`
3. Add task types to `blackbox/agents/tasks/`
4. Update evaluation metrics in `blackbox/evaluate/`
5. Test with both local ML and cloud verification

---

## License

See LICENSE file for details.
