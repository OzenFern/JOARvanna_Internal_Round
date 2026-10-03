# App Module Documentation

This document provides detailed implementation details for the Streamlit web application (`app/`), which provides an interactive interface for the Black Box debugging system.

## Table of Contents

- [Overview](#overview)
- [Main Dashboard](#main-dashboard)
- [Page 1: Trace Viewer](#page-1-trace-viewer)
- [Page 2: Diagnosis](#page-2-diagnosis)
- [Page 3: Debugging](#page-3-debugging)
- [Page 4: Replay Studio](#page-4-replay-studio)
- [Page 5: Trace Diff](#page-5-trace-diff)
- [Page 6: Evaluation](#page-6-evaluation)
- [UI Styling](#ui-styling)
- [Session State Management](#session-state-management)

---

## Overview

The app module is built with **Streamlit** and provides a 6-page interactive web interface for:

1. **Dashboard** - High-level overview and quick actions
2. **Trace Viewer** - Step-by-step execution inspection
3. **Diagnosis** - Fault localization and attribution
4. **Debugging** - Exception analysis and remediation
5. **Replay Studio** - Time-travel checkpointed execution
6. **Trace Diff** - Side-by-side trace comparison
7. **Evaluation** - Quantitative benchmark metrics

### Architecture

```
app/
├── main.py              # Main landing dashboard
└── pages/
    ├── 1_Trace_Viewer.py    # Step scrubber & telemetry
    ├── 2_Diagnosis.py       # Fault localization
    ├── 3_Debugging.py       # Remediation suggestions
    ├── 4_Replay.py          # Checkpointed replay
    ├── 5_Trace_Diff.py      # Trace comparison
    └── 6_Evaluation.py      # Benchmark metrics
```

### Common Pattern

All pages follow a consistent pattern:

1. **Path Setup**: Add root directory to `sys.path`
2. **Page Config**: Set page title, icon, and layout
3. **Data Loading**: Load traces from TraceStore
4. **User Selection**: Select trace/run to analyze
5. **Core Logic**: Execute blackbox library functions
6. **Visualization**: Display results with Streamlit components
7. **Interactivity**: Provide buttons for actions (replay, patch, etc.)

---

## Main Dashboard

**File**: `app/main.py`

The main landing page provides a high-level overview of the system and quick control actions.

### Key Components

#### 1. Page Configuration

```python
st.set_page_config(
    page_title="Black Box · Agent Debugger",
    page_icon="⬛",
    layout="wide",
    initial_sidebar_state="expanded"
)
```

#### 2. Custom CSS Styling

The dashboard includes custom CSS for visual components:

```python
st.markdown("""
<style>
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px;
        color: white;
    }
    .badge-success {
        background-color: #166534;
        color: #86efac;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-fail {
        background-color: #991b1b;
        color: #fca5a5;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-high {
        background-color: #1e3a8a;
        color: #93c5fd;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)
```

#### 3. Top Metrics Row

Displays key system metrics:

```python
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
```

#### 4. Quick Actions Bar

Three primary action buttons:

**Generate Benchmark Traces:**
```python
if st.button("🎲 Generate Benchmark Traces (50 runs)", use_container_width=True):
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
```

**Logic:**
- Uses seeded random generator for reproducibility
- Randomly selects task type (Math, QA, Text2SQL)
- 60% fault injection rate
- Randomly selects fault type and step (1-4)
- Saves traces and ground truth labels
- Reruns page to update metrics

**Train Local ML Model:**
```python
if st.button("🧠 Train Local ML Model (Gradient Boosting)", use_container_width=True):
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
```

**Logic:**
- Checks if traces exist
- Loads ground truth labels
- Fits LocalAttributionModel on traces
- Saves model to disk
- Reruns page to update model status

**Reset All Traces:**
```python
if st.button("🗑️ Reset All Traces", use_container_width=True):
    import shutil
    if Path("data/traces").exists():
        shutil.rmtree("data/traces")
    Path("data/traces").mkdir(parents=True, exist_ok=True)
    st.success("Cleared trace repository.")
    st.rerun()
```

#### 5. Recent Traces Table

Displays a searchable table of recent agent trajectories:

```python
table_data = []
for t in traces[:30]:
    table_data.append({
        "Run ID": t.run_id,
        "Domain": t.task_type.value.upper(),
        "Task Description": t.task_description[:60] + "..." if len(t.task_description) > 60 else t.task_description,
        "Steps": len(t.steps),
        "Status": "✅ SUCCESS" if t.success else "❌ FAILED",
        "Injected Fault": t.fault_type.upper() if t.fault_type else "None",
        "Ground Truth Step": f"Step {t.fault_step}" if t.fault_step is not None else "N/A"
    })

df = pd.DataFrame(table_data)
st.dataframe(df, use_container_width=True, hide_index=True)
```

#### 6. Workflow Navigation Guide

Provides guidance on how to use the 6 pages:

```python
st.info("""
- **1. Trace Viewer**: Inspect step-by-step agent trajectory, tool arguments, outputs, model reasoning, and latency.
- **2. Diagnosis**: View ML-powered root cause step attribution, confidence ratings, and cloud LLM verification.
- **3. Debugging**: Analyze runtime exceptions and inspect 1-click actionable remediation suggestions.
- **4. Replay**: Select any intermediate checkpoint, patch parameters, and re-execute counterfactual branches.
- **5. Trace Diff**: Side-by-side comparison between original failed runs and repaired branches to locate earliest divergence.
- **6. Evaluation**: Benchmark accuracy (Top-1/Top-3, MRR), calibration, generalization, and computational savings.
""")
```

---

## Page 1: Trace Viewer

**File**: `app/pages/1_Trace_Viewer.py`

Interactive step-by-step trace inspection with telemetry visualization.

### Key Components

#### 1. Run Selector

```python
selected_run_id = st.selectbox("Select Agent Run to Inspect:", run_ids, index=0)
trace = store.load(selected_run_id)
```

#### 2. Overview Banner

Displays key trace metadata:

```python
b_col1, b_col2, b_col3, b_col4, b_col5 = st.columns(5)
with b_col1:
    st.markdown(f"**Task Domain:** `{trace.task_type.value.upper()}`")
with b_col2:
    status_color = "green" if trace.success else "red"
    st.markdown(f"**Status:** :{status_color}[{'SUCCESS' if trace.success else 'FAILED'}]")
with b_col3:
    st.markdown(f"**Total Steps:** `{len(trace.steps)}`")
with b_col4:
    st.markdown(f"**Total Latency:** `{trace.total_latency_ms:.1f} ms`")
with b_col5:
    st.markdown(f"**Total Tokens:** `{trace.total_tokens}`")
```

#### 3. Expected vs Actual Output

Side-by-side comparison:

```python
out_col1, out_col2 = st.columns(2)
with out_col1:
    st.markdown("#### 🎯 Expected Output")
    st.code(str(trace.expected_output), language="json")
with out_col2:
    st.markdown("#### 🏁 Final Agent Output")
    st.code(str(trace.final_output), language="json")
```

#### 4. Step Latency & Token Charts

Interactive Plotly charts:

```python
step_data = []
for s in trace.steps:
    step_data.append({
        "Step": f"Step {s.step_index}: {s.name}",
        "Latency (ms)": s.latency_ms,
        "Tokens": s.tokens.total_tokens if s.tokens else 0,
        "Type": s.step_type.value,
        "Has Error": s.has_error
    })

df_steps = pd.DataFrame(step_data)
c_col1, c_col2 = st.columns(2)
with c_col1:
    fig_lat = px.bar(df_steps, x="Step", y="Latency (ms)", color="Type", title="Latency per Step")
    st.plotly_chart(fig_lat, use_container_width=True)
with c_col2:
    fig_tok = px.bar(df_steps, x="Step", y="Tokens", color="Type", title="Tokens per Step")
    st.plotly_chart(fig_tok, use_container_width=True)
```

#### 5. Step Scrubber

Radio button selector for step inspection:

```python
step_indices = [f"Step {s.step_index}: {s.name}" for s in trace.steps]
selected_step_str = st.radio("Select Step to Inspect:", step_indices, horizontal=True)
selected_idx = int(selected_step_str.split(":")[0].replace("Step", "").strip())
step = trace.steps[selected_idx]
```

#### 6. Step Detail Card

Displays detailed step information:

```python
st.markdown(f"### 📍 Step {step.step_index}: `{step.name}` ({step.step_type.value})")

scol1, scol2, scol3 = st.columns(3)
with scol1:
    st.metric("Step Latency", f"{step.latency_ms:.1f} ms")
with scol2:
    st.metric("Step Tokens", step.tokens.total_tokens if step.tokens else 0)
with scol3:
    st.metric("Error State", "⚠️ ERROR" if step.has_error else "NORMAL")

if step.has_error and step.error:
    st.error(f"**Runtime Exception:** [{step.error.error_type}] {step.error.message}")

d_col1, d_col2 = st.columns(2)
with d_col1:
    st.markdown("**📥 Inputs / Arguments:**")
    st.json(step.inputs)
with d_col2:
    st.markdown("**📤 Step Output / Observation:**")
    if isinstance(step.output, (dict, list)):
        st.json(step.output)
    else:
        st.code(str(step.output))
```

#### 7. Tool/Model Call Telemetry

Expandable sections for detailed telemetry:

```python
if step.tool_call:
    with st.expander("🛠️ Tool Call Telemetry", expanded=False):
        st.write(f"**Tool:** `{step.tool_call.tool_name}`")
        st.write("**Arguments:**", step.tool_call.arguments)
        st.write(f"**Latency:** {step.tool_call.latency_ms:.1f} ms")

if step.model_call:
    with st.expander("🤖 Model Call Telemetry", expanded=False):
        st.write(f"**Model:** `{step.model_call.model}`")
        st.write(f"**Prompt:** {step.model_call.prompt}")
        st.write(f"**Response:** {step.model_call.response}")
```

---

## Page 2: Diagnosis

**File**: `app/pages/2_Diagnosis.py`

Root-cause failure diagnosis with step suspicion attribution and cloud verification.

### Key Components

#### 1. Local Analysis Execution

```python
model = LocalAttributionModel()
model_path = Path("data/artifacts/model.pkl")
if model_path.exists():
    model.load(model_path)

local_res = analyze_local(trace, model)
consensus = ConsensusResult(
    scores=local_res.scores,
    top_step=local_res.top_step,
    agreement=True,
    final_confidence=local_res.confidence
)
diagnosis = create_diagnosis(trace, consensus)
```

#### 2. Status & Verdict Banner

```python
vcol1, vcol2, vcol3, vcol4 = st.columns(4)
with vcol1:
    status_label = "✅ SUCCESS" if trace.success else "❌ FAILED"
    st.metric("Run Status", status_label)
with vcol2:
    culprit_name = trace.steps[diagnosis.likely_source].name if diagnosis.likely_source < len(trace.steps) else 'Unknown'
    st.metric("Identified Culprit Step", f"Step {diagnosis.likely_source} ({culprit_name})")
with vcol3:
    st.metric("Local Model Confidence", diagnosis.confidence.upper())
with vcol4:
    st.metric("Diagnosis Latency", f"{local_res.latency_ms:.2f} ms")
```

#### 3. Suspicion Ranking Chart

Interactive bar chart showing attribution scores:

```python
chart_data = []
for i, s in enumerate(trace.steps):
    score = local_res.scores.get(i, 0.0)
    chart_data.append({
        "Step": f"Step {i}: {s.name}",
        "Suspicion Score": score,
        "Is Culprit": "🔴 Culprit Step" if i == diagnosis.likely_source else "⚪ Normal Step"
    })

df_susp = pd.DataFrame(chart_data)
fig_susp = px.bar(
    df_susp,
    x="Step",
    y="Suspicion Score",
    color="Is Culprit",
    color_discrete_map={"🔴 Culprit Step": "#ef4444", "⚪ Normal Step": "#3b82f6"},
    title="Attribution Suspicion Score (0.0 to 1.0)"
)
fig_susp.update_layout(yaxis_range=[0, 1.05])
st.plotly_chart(fig_susp, use_container_width=True)
```

#### 4. Evidence & Rationale

Human-readable explanation and feature saliency:

```python
with r_col1:
    st.markdown("#### 🔍 Failure Explanation")
    st.info(diagnosis.rationale)

    saliency = compute_step_saliency(trace, diagnosis.likely_source)
    st.markdown("#### 🔬 Step Feature Saliency")
    st.write(saliency.summary)
    
    sal_df = pd.DataFrame(saliency.top_contributing_features, columns=["Feature Signal", "Weight"])
    st.dataframe(sal_df, use_container_width=True, hide_index=True)
```

#### 5. Ground Truth Verification

Compares model prediction to injected fault:

```python
with r_col2:
    st.markdown("#### ⚖️ Ground Truth Verification")
    if trace.fault_step is not None:
        is_match = (diagnosis.likely_source == trace.fault_step)
        if is_match:
            st.success(f"🎯 **EXACT MATCH!** Model correctly localized injected ground-truth fault at **Step {trace.fault_step}** ({trace.fault_type.upper()}).")
        else:
            st.warning(f"⚠️ Model suspected **Step {diagnosis.likely_source}**, whereas injected fault was at **Step {trace.fault_step}**.")
    else:
        st.write("This run was clean (no artificial faults injected).")
```

#### 6. Cloud LLM Verifier

Optional deep critique using LLM judge:

```python
if st.button("🚀 Trigger Cloud Verification", type="primary"):
    with st.spinner("Executing Cloud LLM critique & multi-step trajectory evaluation..."):
        cloud_res = analyze_cloud(trace)
        st.session_state[f"cloud_{trace.run_id}"] = cloud_res

if f"cloud_{trace.run_id}" in st.session_state:
    c_res = st.session_state[f"cloud_{trace.run_id}"]
    agrees = (c_res.top_step == diagnosis.likely_source)
    
    st.markdown("### 📋 Cloud LLM Verification Verdict")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Consensus Agreement", "🤝 AGREE" if agrees else "⚡ REFINED")
    with c2:
        st.metric("Cloud Culprit Step", f"Step {c_res.top_step}")
    with c3:
        st.metric("Cloud Latency / Tokens", f"{c_res.latency_ms:.1f} ms ({c_res.token_usage.get('total', 0)} tok)")

    st.markdown("#### 🤖 LLM Reasoning:")
    st.success(c_res.reasoning)
```

---

## Page 3: Debugging

**File**: `app/pages/3_Debugging.py`

Interactive debugging with exception analysis and actionable remediation cards.

### Key Components

#### 1. Exception Analysis

```python
exc_analysis = analyze_exceptions(trace)

if exc_analysis.has_exception:
    st.error(f"**Root Exception Category:** `{exc_analysis.category.upper()}` ({exc_analysis.exception_type})")
    st.write(f"**Originating Step:** Step {exc_analysis.origin_step_index} (`{exc_analysis.origin_step_name}`)")
    st.write(f"**Error Message:** `{exc_analysis.exception_message}`")
    st.info(f"**Root Cause Diagnosis:** {exc_analysis.root_cause_summary}")
else:
    st.success("✅ **No Explicit Uncaught Exceptions**: Silent semantic or computational failure detected.")
    st.info(f"The failure was caused by an erroneous intermediate calculation or retrieved fact at Step {suspect_step_idx} ({suspect_step.name if suspect_step else ''}).")
```

#### 2. Actionable Remediation Suggestions

Generates and displays fix suggestions:

```python
suggestions = generate_suggestions(trace, suspect_step_idx)

if not suggestions:
    st.info("No automatic rule-based suggestions generated. You can manually configure a patch in the Replay tab.")
else:
    for i, sug in enumerate(suggestions):
        with st.container():
            st.markdown(f"### 💡 Suggestion #{i+1}: {sug.title}")
            st.write(sug.description)
            
            sc1, sc2 = st.columns([3, 1])
            with sc1:
                st.markdown("**Proposed Patch Payload:**")
                st.json(sug.patch_payload)
            with sc2:
                st.metric("Patch Confidence",f"{sug.confidence:.0%}")
```

#### 3. 1-Click Apply Patch & Replay

Applies patch and executes counterfactual branch:

```python
if st.button(f"⚡ Apply Patch & Replay Branch", key=f"btn_patch_{i}", type="primary"):
    with st.spinner("Forking state from checkpoint, applying patch, and resuming downstream steps..."):
        patch_val = sug.patch_payload.get("output")
        patch = StepPatch(
            step_index=suspect_step_idx,
            patch_kind="override_output" if sug.action_type == "override" else "retry",
            new_output=patch_val,
            new_inputs=sug.patch_payload,
            description=sug.title
        )
        repaired_trace = create_branch(trace, patch)
        store.save(repaired_trace)
        
        st.session_state["last_repaired_run"] = repaired_trace
        st.success(f"🎉 Branch `{repaired_trace.run_id}` created and executed!")
```

#### 4. Repaired Run Result

Displays outcome of repaired execution:

```python
if "last_repaired_run" in st.session_state:
    rep = st.session_state["last_repaired_run"]
    st.subheader(f"✨ Repaired Execution Result: `{rep.run_id}`")
    
    r_res_col1, r_res_col2, r_res_col3 = st.columns(3)
    with r_res_col1:
        st.metric("Repaired Outcome", "✅ SUCCESS" if rep.success else "❌ FAILED")
    with r_res_col2:
        st.metric("Target Output", str(rep.expected_output))
    with r_res_col3:
        st.metric("Recomputed Final Output", str(rep.final_output))
        
    st.info(f"⚡ **Replay Savings:** Checkpoint resumption bypassed re-executing steps 0 to {suspect_step_idx-1}, saving **{rep.meta.get('replay_savings_pct', 0)}%** of runtime computation.")
```

---

## Page 4: Replay Studio

**File**: `app/pages/4_Replay.py`

Checkpointed time-travel replay studio for counterfactual execution.

### Key Components

#### 1. Checkpoint Step Selector

```python
step_options = [f"Step {s.step_index}: {s.name} (Output: {str(s.output)[:30]})" for s in trace.steps]
selected_step_str = st.selectbox("Choose Checkpoint Step:", step_options, index=1 if len(trace.steps) > 1 else 0)
fork_step_idx = int(selected_step_str.split(":")[0].replace("Step", "").strip())
fork_step = trace.steps[fork_step_idx]
```

#### 2. Checkpoint State Inspector

View agent state at checkpoint:

```python
with st.expander(f"📦 Inspect Checkpoint State at Step {fork_step_idx}", expanded=False):
    state_snap = CheckpointManager.extract_state_at_step(trace, fork_step_idx)
    st.json(state_snap)
```

#### 3. Intervention & Patch Editor

Configure step intervention:

```python
p_col1, p_col2 = st.columns(2)

with p_col1:
    st.markdown("#### 📤 Current Step Output (Frozen in Checkpoint)")
    st.code(str(fork_step.output))
    
    patch_output_val = st.text_input(
        "Patched Output Value (Override):",
        value=str(fork_step.output),
        help="Enter the corrected mathematical or textual value you want this step to emit."
    )

with p_col2:
    st.markdown("#### 📥 Current Step Inputs")
    st.json(fork_step.inputs)
    patch_inputs_json = st.text_area(
        "Patched Inputs JSON (Optional):",
        value=json.dumps(fork_step.inputs, indent=2),
        height=120
    )
```

#### 4. Replay Execution

Execute forward from checkpoint with patches:

```python
if st.button("🚀 Replay Forward from Checkpoint", type="primary", use_container_width=True):
    with st.spinner(f"Resuming execution from Step {fork_step_idx} with patched parameters..."):
        # Convert numeric if possible
        try:
            if "." in patch_output_val:
                val = float(patch_output_val)
            else:
                val = int(patch_output_val)
        except ValueError:
            val = patch_output_val

        try:
            inputs_dict = json.loads(patch_inputs_json)
        except Exception:
            inputs_dict = None

        new_trace = resume_from_step(
            trace=trace,
            step_index=fork_step_idx,
            patched_output=val,
            patched_inputs=inputs_dict
        )
        store.save(new_trace)
        st.session_state["replay_result"] = new_trace
        st.success(f"Execution resumed! New Child Run ID: `{new_trace.run_id}`")
```

#### 5. Replay Result View

Displays outcome and savings:

```python
if "replay_result" in st.session_state:
    res_trace = st.session_state["replay_result"]
    st.markdown("### 📊 Replayed Trajectory Outcome")
    
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        st.metric("New Run ID", res_trace.run_id)
    with r2:
        st.metric("Final Status", "✅ SUCCESS" if res_trace.success else "❌ FAILED")
    with r3:
        st.metric("Expected Answer", str(res_trace.expected_output))
    with r4:
        st.metric("Replayed Final Output", str(res_trace.final_output))

    st.success(f"""
    ⚡ **Resource & Latency Savings:**
    - **Steps Reused (No re-computation):** {fork_step_idx} / {len(res_trace.steps)} steps
    - **Computational Time Saved:** ~{res_trace.meta.get('replay_savings_pct', 0)}%
    """)
```

---

## Page 5: Trace Diff

**File**: `app/pages/5_Trace_Diff.py`

Side-by-side trace comparison with earliest divergence detection.

### Key Components

#### 1. Dual Trace Selection

```python
col_left_sel, col_right_sel = st.columns(2)
with col_left_sel:
    left_id = st.selectbox("Select Baseline / Failed Trace (Left):", run_ids, index=0)
with col_right_sel:
    right_id = st.selectbox("Select Comparison / Fixed Trace (Right):", run_ids, index=1 if len(run_ids) > 1 else 0)

t_left = store.load(left_id)
t_right = store.load(right_id)
```

#### 2. Divergence Detection

```python
div_res = find_divergence(t_left, t_right)

if div_res.has_divergence:
    st.error(f"⚠️ **Divergence Detected:** {div_res.explanation}")
    st.markdown(f"**Earliest Divergence Point:** `Step {div_res.earliest_step_index}` | **Category:** `{div_res.divergence_type}`")
else:
    st.success("✅ **Zero Divergence:** Both traces executed identically.")
```

#### 3. Contrastive Explanation

```python
contrast = generate_contrastive_explanation(t_left, t_right)
st.info(f"💡 **Contrastive Explanation:** {contrast.explanation}")
```

#### 4. Outcome Comparison Table

```python
oc1, oc2 = st.columns(2)
with oc1:
    st.markdown(f"### Left Run: `{t_left.run_id}`")
    st.markdown(f"**Status:** {'✅ SUCCESS' if t_left.success else '❌ FAILED'}")
    st.markdown(f"**Final Output:** `{t_left.final_output}`")
    st.markdown(f"**Total Latency:** `{t_left.total_latency_ms:.1f} ms`")

with oc2:
    st.markdown(f"### Right Run: `{t_right.run_id}`")
    st.markdown(f"**Status:** {'✅ SUCCESS' if t_right.success else '❌ FAILED'}")
    st.markdown(f"**Final Output:** `{t_right.final_output}`")
    st.markdown(f"**Total Latency:** `{t_right.total_latency_ms:.1f} ms`")
```

#### 5. Step Alignment Matrix

```python
alignment_rows = []
for pair in div_res.alignment.pairs:
    s_left = pair.left_step
    s_right = pair.right_step
    
    is_earliest = (pair.index == div_res.earliest_step_index)
    status_icon = "🔴 DIVERGED (EARLIEST)" if is_earliest else ("⚠️ MODIFIED" if pair.status == "modified" else "🟢 MATCH")

    alignment_rows.append({
        "Step": pair.index,
        "Status": status_icon,
        "Left Step Name": s_left.name if s_left else "(none)",
        "Left Output": str(s_left.output)[:35] if s_left else "-",
        "Right Step Name": s_right.name if s_right else "(none)",
        "Right Output": str(s_right.output)[:35] if s_right else "-",
        "Divergence Reason": pair.divergence_reason or "-"
    })

df_align = pd.DataFrame(alignment_rows)
st.dataframe(df_align, use_container_width=True, hide_index=True)
```

---

## Page 6: Evaluation

**File**: `app/pages/6_Evaluation.py`

Benchmark evaluation suite with quantitative metrics dashboard.

### Key Components

#### 1. Metric Computation

```python
model = LocalAttributionModel()
model_path = Path("data/artifacts/model.pkl")
if model_path.exists():
    model.load(model_path)

loc_metrics = eval_localization(traces, model)
conf_metrics = eval_confidence(traces, model)
lat_metrics = eval_latency(traces, model)
gen_report = eval_generalization(traces, traces, model)
cf_metrics = eval_counterfactual_repairs([t for t in traces if not t.success])
```

#### 2. Primary Accuracy Metrics

```python
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Top-1 Exact Step Accuracy", f"{loc_metrics.top1_accuracy:.1%}")
with m2:
    st.metric("Top-3 Step Accuracy", f"{loc_metrics.top3_accuracy:.1%}")
with m3:
    st.metric("Mean Reciprocal Rank (MRR)", f"{loc_metrics.mrr:.3f}")
with m4:
    st.metric("Diagnosis Latency (Mean)", f"{lat_metrics.mean_local_latency_ms:.2f} ms")
```

#### 3. Fault Type Accuracy Breakdown

```python
fault_df = pd.DataFrame([
    {"Fault Type": k.upper(), "Top-1 Accuracy": v}
    for k, v in loc_metrics.per_fault_accuracy.items()
])

c_col1, c_col2 = st.columns(2)
with c_col1:
    if not fault_df.empty:
        fig_fault = px.bar(
            fault_df,
            x="Fault Type",
            y="Top-1 Accuracy",
            color="Fault Type",
            title="Localization Accuracy by Fault Class"
        )
        fig_fault.update_layout(yaxis_range=[0, 1.05])
        st.plotly_chart(fig_fault, use_container_width=True)
```

#### 4. Confidence Calibration Tiers

```python
with c_col2:
    st.markdown("#### 🎯 Confidence Calibration Tiers")
    conf_df = pd.DataFrame([
        {"Tier": "High Confidence", "Total Predictions": conf_metrics.high_tier.total_predictions, "Accuracy": f"{conf_metrics.high_tier.accuracy:.1%}"},
        {"Tier": "Medium Confidence", "Total Predictions": conf_metrics.medium_tier.total_predictions, "Accuracy": f"{conf_metrics.medium_tier.accuracy:.1%}"},
        {"Tier": "Low Confidence", "Total Predictions": conf_metrics.low_tier.total_predictions, "Accuracy": f"{conf_metrics.low_tier.accuracy:.1%}"}
    ])
    st.dataframe(conf_df, use_container_width=True, hide_index=True)
```

#### 5. Cross-Domain Performance

```python
with g1:
    st.markdown("#### 🌐 Cross-Domain Performance")
    task_df = pd.DataFrame([
        {"Task Domain": k.upper(), "Accuracy": v}
        for k, v in gen_report.cross_task_metrics.items()
    ])
    if not task_df.empty:
        fig_task = px.bar(task_df, x="Task Domain", y="Accuracy", title="Performance by Task Domain")
        fig_task.update_layout(yaxis_range=[0, 1.05])
        st.plotly_chart(fig_task, use_container_width=True)
```

#### 6. Counterfactual Repair Efficacy

```python
with g2:
    st.markdown("#### ⚡ Time-Travel Counterfactual Repair Efficacy")
    st.metric("1-Click Patch Success Rate", f"{cf_metrics.repair_success_rate:.1%}")
    st.write(f"Tested on **{cf_metrics.total_tested}** faulty trajectories.")
    st.write(f"Successfully repaired **{cf_metrics.successful_repairs}** runs by patching suspected root-cause step.")
    st.success("✅ Demonstrates that learned fault localizations are actionable and verifiable via replay.")
```

---

## UI Styling

The app uses consistent styling across all pages:

### Color Scheme

- **Success**: Green (#166534 background, #86efac text)
- **Error/Failure**: Red (#991b1b background, #fca5a5 text)
- **High Confidence**: Blue (#1e3a8a background, #93c5fd text)
- **Metric Cards**: Dark slate (#1e293b background, white text)

### Component Patterns

1. **Metrics**: Use `st.metric()` for key numbers
2. **Charts**: Use Plotly Express for interactive visualizations
3. **Data Tables**: Use `st.dataframe()` with `use_container_width=True`
4. **Code Display**: Use `st.code()` for JSON/code snippets
5. **Expandable Sections**: Use `st.expander()` for detailed information
6. **Status Indicators**: Use emojis (✅, ❌, ⚠️, 🔴, 🟢) for visual cues

### Layout Patterns

- **5-column layout**: For top metrics row
- **2-column layout**: For side-by-side comparisons
- **3-column layout**: For grouped metrics
- **Horizontal radio buttons**: For step selection
- **Container grouping**: For related controls

---

## Session State Management

Streamlit's session state is used to persist data across page navigations and interactions:

### Common Session State Keys

- `cloud_{run_id}`: Cloud verification results for a specific trace
- `last_repaired_run`: Most recently repaired trace from debugging page
- `replay_result`: Result of replayed execution

### Usage Pattern

```python
# Store result
st.session_state["last_repaired_run"] = repaired_trace

# Retrieve result
if "last_repaired_run" in st.session_state:
    rep = st.session_state["last_repaired_run"]
```

### Rerun Pattern

After state-changing operations (generating traces, training model, etc.):

```python
st.success("Operation completed!")
st.rerun()
```

This refreshes the page to reflect the new state.

---

## Summary

The app module provides a comprehensive 6-page Streamlit interface for the Black Box debugging system:

1. **Main Dashboard**: Overview and quick actions
2. **Trace Viewer**: Step-by-step inspection with telemetry
3. **Diagnosis**: ML-powered fault localization with cloud verification
4. **Debugging**: Exception analysis and 1-click remediation
5. **Replay Studio**: Checkpointed time-travel execution
6. **Trace Diff**: Side-by-side comparison and divergence detection
7. **Evaluation**: Quantitative benchmark metrics

All pages follow consistent patterns for data loading, user interaction, and visualization, providing a cohesive user experience for debugging AI agent executions.
