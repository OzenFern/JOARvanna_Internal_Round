# ⬛ Black Box · AI Agent Fault Localization & Time-Travel Debugger

> **An AI-powered debugging workbench that learns from agent execution traces to localize root-cause failures, explain culpability, and test counterfactual fixes via checkpointed replay without re-running unaffected steps.**

---

## 📌 The Problem
AI agents solve complex multi-step tasks across long execution graphs involving model calls, tool executions, retrieved documents, and state mutations. A 20-step execution may appear normal throughout, but fail at the end due to a single subtle error at Step 2 (e.g., wrong tool arguments, poisoned document context, unit conversion mistake, or SQL schema drift). 

Traditional log dumpers cannot pinpoint which intermediate decision caused the downstream failure. **Black Box** solves this by providing:
1. **Intelligent Fault Localization:** ML-based suspicion scoring and root cause attribution across multi-step execution graphs.
2. **Confidence & Cloud Verification:** Dual-layer diagnostic consensus (sub-50ms local ML + optional LLM judge).
3. **1-Click Actionable Remediation:** Tailored patch recommendations (override calculations, repair tool arguments, filter poisoned context).
4. **Time-Travel Checkpointed Replay:** Resume execution from any intermediate step $k$ with patched parameters, avoiding redundant re-execution of steps $0 \dots k-1$.
5. **Trace Diff & Divergence Analysis:** Side-by-side execution graph alignment highlighting the exact earliest point of divergence.
6. **Quantitative Evaluation Suite:** Benchmarks for Top-1/Top-3 localization accuracy, MRR, latency SLAs, and computational replay savings.

---

## 🏗️ Architecture Overview

```
Agent Execution / Benchmark Traces
                │
                ▼
      ┌──────────────────┐
      │Trace Store (JSON)│
      └─────────┬────────┘
                │
        ┌───────┴───────┐
        ▼               ▼
┌──────────────┐  ┌────────────────────────┐
│   LOCAL ML   │  │ CHECKPOINT & REPLAY    │
│  ANALYZER    │  │        ENGINE          │
│ (<50ms target│  │ (State reconstruction  │
│  attribution)│  │  & Branch Execution)   │
└───────┬──────┘  └───────────┬────────────┘
        │                     │
        ▼                     ▼
┌──────────────┐  ┌────────────────────────┐
│  CLOUD LLM   │  │   TRACE DIFF ENGINE    │
│   VERIFIER   │  │ (Earliest Divergence   │
│  (LLM Judge) │  │  & Alignment Matrix)   │
└───────┬──────┘  └───────────┬────────────┘
        │                     │
        └──────────┬──────────┘
                   ▼
       ┌──────────────────────┐
       │ STREAMLIT WORKBENCH  │
       │  (Interactive UI)    │
       └──────────────────────┘
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites & Installation

Ensure you have Python 3.10+ installed:

```bash
# Clone and checkout dev branch
git clone -b dev https://github.com/OzenFern/JOARvanna_Internal_Round.git "JOARVANNA Dev"
cd "JOARVANNA Dev"

# Optional: Set OpenAI or Gemini API key for live Cloud Verifier calls
export OPENAI_API_KEY="sk-..."       # Linux/macOS
set OPENAI_API_KEY="sk-..."          # Windows CMD
$env:OPENAI_API_KEY="sk-..."         # Windows PowerShell
```

*(Note: If no API key is provided, the Cloud Verifier automatically uses an intelligent semantic critique model so all features work offline without crashing!)*

---

### 2. Launch the Streamlit Web Application

Run the single command below to open the complete interactive UI:

```bash
python -m streamlit run app/main.py
```

The app will launch at `http://localhost:8501`.

---

## 🖥️ Streamlit Web Interface Walkthrough

| Page | Features & Purpose |
| :--- | :--- |
| **🏠 Home (`main.py`)** | • High-level dashboard with total traces, success/failure counts, and model status.<br>• **Quick Action Buttons:** 1-click **Generate Benchmark Traces**, **Train Local ML Model**, and **Reset Traces**.<br>• Searchable table of recent agent trajectories. |
| **🔍 1. Trace Viewer** | • Scrubber to inspect every step in the agent's trajectory.<br>• Step inputs, outputs, observations, and telemetry.<br>• Interactive Plotly charts for per-step latency (ms) and token consumption.<br>• Detailed inspection drawers for tool calls and LLM prompts/responses. |
| **🩺 2. Diagnosis** | • Real-time fault localization identifying the primary culprit step.<br>• Interactive **Step Suspicion Distribution** bar chart (Attribution scores 0.0 to 1.0).<br>• High / Medium / Low confidence ratings and human-readable rationale.<br>• Step feature saliency breakdown.<br>• **Cloud LLM Verifier:** 1-click trigger to cross-validate local attribution with an LLM judge. |
| **🛠️ 3. Debugging** | • Runtime exception categorization (ZeroDivision, SyntaxError, DatabaseError, ToolError, or Silent Failure).<br>• **Actionable Remediation Cards:** Tailored fix suggestions.<br>• **1-Click Apply Patch & Replay:** Applies the proposed patch, forks a new execution branch from the checkpoint, and displays whether the run flipped from FAILED to SUCCESS. |
| **⏪ 4. Replay Studio** | • Time-travel debugging workbench: choose any historical checkpoint step.<br>• Interactive input/output override editor.<br>• Forward branch execution from checkpoint.<br>• Displays computational time and token savings achieved by avoiding step re-execution. |
| **🔀 5. Trace Diff** | • Side-by-side comparison between any two traces (e.g. baseline failed run vs repaired child run).<br>• Automated detection of the **Earliest Point of Divergence**.<br>• Step sequence alignment matrix highlighting modified and diverged outputs.<br>• Contrastive explanation of why execution deviated. |
| **📈 6. Evaluation** | • Benchmark metrics dashboard for hackathon evaluation:<br>&nbsp;&nbsp;• **Top-1 Exact Step Localization Accuracy**<br>&nbsp;&nbsp;• **Top-3 Step Accuracy & Mean Reciprocal Rank (MRR)**<br>&nbsp;&nbsp;• **Diagnosis Latency SLA (< 50ms benchmark)**<br>&nbsp;&nbsp;• **Confidence Calibration Tiers** (High vs Medium vs Low)<br>&nbsp;&nbsp;• **Cross-Domain Generalization** (Math, QA, Text2SQL)<br>&nbsp;&nbsp;• **Counterfactual Repair Success Rate**. |

---

## 💻 CLI Commands Reference

You can also run all diagnostic, training, and evaluation operations directly from the terminal using standard library scripts:

### 1. Generate Synthetic Benchmark Traces
Generates 50 balanced clean and faulted traces across Math, QA, and Text2SQL tasks:
```bash
python scripts/generate_traces.py -n 50 -f 0.6
```

### 2. Train Local Attribution ML Model
Trains the gradient boosting and statistical anomaly ranker (< 35ms training latency):
```bash
python scripts/train_local.py
```

### 3. Run Individual Trace Analysis & Diagnosis
Inspects a specific trace, prints step suspicion attribution, diagnosis rationale, remediation cards, and optional cloud verification:
```bash
python scripts/run_analysis.py trace-math-0001 --cloud
```

### 4. Run Full Evaluation Benchmarks
Computes Top-1/Top-3 localization accuracy, MRR, latency benchmarks, and counterfactual repair efficacy:
```bash
python scripts/run_eval.py
```

### 5. Export Post-Mortem Audit Report
Exports a Markdown report summarizing root causes, step timeline, and proposed patches:
```bash
python scripts/export_report.py trace-math-0001 -o data/reports/postmortem.md
```

---

## 📂 Repository Structure

```text
JOARVANNA Dev/
├── app/                              # Streamlit Web UI Application
│   ├── main.py                       # Main landing dashboard
│   └── pages/
│       ├── 1_Trace_Viewer.py         # Step scrubber & telemetry inspector
│       ├── 2_Diagnosis.py            # Fault localization & cloud verifier
│       ├── 3_Debugging.py            # Exception analysis & 1-click remediation
│       ├── 4_Replay.py               # Checkpointed time-travel replay studio
│       ├── 5_Trace_Diff.py           # Side-by-side trace diff & divergence
│       └── 6_Evaluation.py           # Quantitative benchmark dashboard
│
├── blackbox/                         # Core Python Library
│   ├── capture/                      # Schemas, instrumentation, & persistence
│   │   ├── schema.py                 # AgentTrace, AgentStep, Checkpoint dataclasses
│   │   ├── instrument.py             # TraceContext & @capture_tool decorators
│   │   └── store.py                  # JSON trace persistence & serialization
│   ├── attribution/                  # Fault localization & suspicion scoring
│   │   ├── model.py                  # LocalAttributionModel (GBM + Pure-Python)
│   │   ├── confidence.py             # Confidence calibration calculator
│   │   └── baselines/                # FirstError, GBM, & CloudJudge baselines
│   ├── analysis/                     # Analysis coordination & consensus
│   │   ├── local.py                  # Local analyzer (<50ms target)
│   │   ├── cloud.py                  # Cloud LLM verifier (OpenAI/Gemini/Mock)
│   │   ├── consensus.py              # Local + Cloud consensus merger
│   │   └── router.py                 # Confidence-based routing policy
│   ├── replay/                       # Checkpointing & resumption
│   │   ├── checkpoint.py             # Memory state reconstruction & snapshotting
│   │   ├── resume.py                 # Checkpointed forward execution engine
│   │   └── cache.py                  # Deterministic tool result cache
│   ├── intervene/                    # Counterfactual branch testing
│   │   ├── patch.py                  # StepPatch specification
│   │   └── branch.py                 # Branch runner with parent linkage
│   ├── compare/                      # Sequence alignment & diffing
│   │   ├── align.py                  # Step sequence alignment algorithm
│   │   └── divergence.py             # Earliest divergence point detector
│   ├── debug/                        # Diagnosis, exceptions & suggestions
│   │   ├── diagnose.py               # Diagnosis constructor
│   │   ├── suggestions.py            # Actionable remediation generator
│   │   ├── suspicion.py              # Step suspicion ranking
│   │   └── exceptions.py             # Exception categorization
│   ├── explain/                      # Explainability & saliency
│   │   ├── contrast.py               # Contrastive reference comparison
│   │   ├── rationale.py              # Human-readable rationale builder
│   │   └── saliency.py               # Step feature saliency weights
│   ├── evaluate/                     # Benchmark evaluation suite
│   │   ├── localization.py           # Top-1/Top-3/Top-5 accuracy & MRR
│   │   ├── confidence.py             # Calibration metrics
│   │   ├── generalization.py         # Cross-domain & cross-fault metrics
│   │   ├── latency.py                # SLA latency benchmarks
│   │   ├── replay_savings.py         # Computation & token savings
│   │   └── counterfactual.py         # Repair success rate
│   ├── faults/                       # Fault injection library
│   │   ├── injector.py               # Fault injector orchestrator
│   │   ├── labels.py                 # Ground truth label store
│   │   └── library/                  # bad_args, fake_output, poisoned_context, truncation
│   ├── features/                     # Step feature extraction & embeddings
│   │   ├── step_features.py          # Dense feature extraction (latency, entropy, etc.)
│   │   ├── embeddings.py             # Text TF-IDF / n-gram embedder
│   │   └── dataset.py                # ML dataset matrix builder
│   └── agents/                       # Multi-domain agent implementations
│       ├── runner.py                 # Scripted task execution loop
│       ├── tasks/                    # math.py, qa.py, text2sql.py
│       └── tools/                    # calculator.py, database.py, search.py
│
├── configs/                          # Experiment & task YAML configurations
├── scripts/                          # CLI automation scripts
└── README.md                         # Project documentation
```