"""
app/main.py
───────────
Black Box: AI-Powered Agentic Fault Localization & Time-Travel Debugger
Main Dashboard and Landing Page.
"""
import os
import sys
from pathlib import Path

# Ensure root package is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from blackbox.capture.store import TraceStore
from blackbox.attribution.model import LocalAttributionModel
from app.styles import inject_styles

st.set_page_config(
    page_title="Black Box · Agent Debugger",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_styles()

store = TraceStore(Path("data/traces"))
traces = store.load_all()

st.title("Black Box")
st.caption("AI agent debugging workspace  /  fault localization  /  checkpointed replay  /  branch testing")

st.markdown(
    "Inspect failures, verify likely causes, and replay corrected trajectories from one workspace."
)

# Top Metrics Row
col1, col2, col3, col4, col5 = st.columns(5)
total_traces = len(traces)
failed_traces = sum(1 for t in traces if not t.success)
success_traces = total_traces - failed_traces
model_path = Path("data/artifacts/model.pkl")
model_trained = model_path.exists()

with col1:
    st.metric("Total Execution Traces", total_traces)
with col2:
    st.metric("Successful Runs", success_traces)
with col3:
    st.metric("Failed Runs (Diagnostic Target)", failed_traces)
with col4:
    st.metric("Attribution Model Status", "Trained (GBM)" if model_trained else "Heuristic Ready")
with col5:
    st.metric("Local Diagnosis Target Latency", "< 50 ms")

st.divider()

# Quick Actions Bar
st.subheader("Quick Control Actions")
qcol1, qcol2, qcol3 = st.columns(3)

with qcol1:
    if st.button("Generate Benchmark Traces (50 runs)", use_container_width=True):
        with st.spinner("Generating synthetic traces across Math, QA, Text2SQL..."):
            import random
            from blackbox.faults.injector import FaultInjector
            from blackbox.faults.labels import LabelStore
            from blackbox.agents.runner import run
            from blackbox.agents.tasks import math as math_tasks
            from blackbox.agents.tasks import qa as qa_tasks
            from blackbox.agents.tasks import text2sql as sql_tasks

            rng = random.Random(42)
            labels = LabelStore(Path("data/artifacts/labels.json"))
            task_types = ["math", "qa", "text2sql"]
            fault_types = ["bad_args", "fake_output", "poisoned_context", "truncation"]

            for i in range(50):
                tt = rng.choice(task_types)
                rid = f"trace-{tt}-{i:04d}"
                task = math_tasks.sample(rng) if tt == "math" else qa_tasks.sample(rng) if tt == "qa" else sql_tasks.sample(rng)
                inject = (rng.random() < 0.6)
                injector = FaultInjector(rng.choice(fault_types), rng.randint(1, 4), rng) if inject else None
                trace = run(tt, task, run_id=rid, injector=injector)
                store.save(trace)
                if trace.fault_step is not None:
                    labels.set(trace.run_id, trace.fault_step, trace.fault_type)
            labels.save()
            st.success("Generated 50 traces successfully!")
            st.rerun()

with qcol2:
    if st.button("Train Local ML Model (Gradient Boosting)", use_container_width=True):
        if not traces:
            st.error("Generate traces first before training.")
        else:
            with st.spinner("Extracting step embeddings & fitting Gradient Boosting model..."):
                from blackbox.faults.labels import LabelStore
                labels = LabelStore(Path("data/artifacts/labels.json"))
                model = LocalAttributionModel()
                model.fit(traces, labels)
                model.save(model_path)
                st.success("Trained and saved LocalAttributionModel to data/artifacts/model.pkl!")
                st.rerun()

with qcol3:
    if st.button("Reset All Traces", use_container_width=True):
        import shutil
        if Path("data/traces").exists():
            shutil.rmtree("data/traces")
        Path("data/traces").mkdir(parents=True, exist_ok=True)
        st.success("Cleared trace repository.")
        st.rerun()

st.divider()

# Recent Traces Table
st.subheader("Recent Agent Execution Traces")

if not traces:
    st.info("No traces currently loaded in `data/traces/`. Click 'Generate Benchmark Traces' above to create sample agent trajectories!")
else:
    table_data = []
    for t in traces[:30]:
        table_data.append({
            "Run ID": t.run_id,
            "Domain": t.task_type.value.upper(),
            "Task Description": t.task_description[:60] + "..." if len(t.task_description) > 60 else t.task_description,
            "Steps": len(t.steps),
            "Status": "SUCCESS" if t.success else "FAILED",
            "Injected Fault": t.fault_type.upper() if t.fault_type else "None",
            "Ground Truth Step": f"Step {t.fault_step}" if t.fault_step is not None else "N/A"
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
st.markdown("### Workflow Navigation Guide")
st.info("""
- **1. Trace Viewer**: Inspect step-by-step agent trajectory, tool arguments, outputs, model reasoning, and latency.
- **2. Diagnosis**: View ML-powered root cause step attribution, confidence ratings, and cloud LLM verification.
- **3. Debugging**: Analyze runtime exceptions and inspect 1-click actionable remediation suggestions.
- **4. Replay**: Select any intermediate checkpoint, patch parameters, and re-execute counterfactual branches.
- **5. Trace Diff**: Side-by-side comparison between original failed runs and repaired branches to locate earliest divergence.
- **6. Evaluation**: Benchmark accuracy (Top-1/Top-3, MRR), calibration, generalization, and computational savings.
""")
