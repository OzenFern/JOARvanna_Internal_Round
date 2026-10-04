"""
app/pages/1_Trace_Viewer.py
───────────────────────────
Interactive Step-by-Step Trace Viewer & DAG Inspector.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import plotly.express as px
from blackbox.capture.store import TraceStore
from app.paths import TRACES_DIR
from app.styles import inject_styles

st.set_page_config(page_title="Trace Viewer · Black Box", layout="wide")
st.title("Execution Trace Viewer")

inject_styles()

store = TraceStore(TRACES_DIR)
run_ids = store.list_runs()

if not run_ids:
    st.warning("No traces found. Return to the Home page to generate or load traces.")
    st.stop()

# Run Selector
selected_run_id = st.selectbox("Select Agent Run to Inspect:", run_ids, index=0)
trace = store.load(selected_run_id)

# Overview Banner
b_col1, b_col2, b_col3, b_col4, b_col5 = st.columns(5)
with b_col1:
    st.markdown(f"**Task Domain:** `{trace.task_type.value.upper()}`")
with b_col2:
    st.markdown(f"**Status:** {'SUCCESS' if trace.success else 'FAILED'}")
with b_col3:
    st.markdown(f"**Total Steps:** `{len(trace.steps)}`")
with b_col4:
    st.markdown(f"**Total Latency:** `{trace.total_latency_ms:.1f} ms`")
with b_col5:
    st.markdown(f"**Total Tokens:** `{trace.total_tokens}`")

st.info(f"**Task Goal:** {trace.task_description}")

# Summary of Expected vs Actual Output
out_col1, out_col2 = st.columns(2)
with out_col1:
    st.markdown("#### Expected Output")
    st.code(str(trace.expected_output), language="json")
with out_col2:
    st.markdown("#### Final Agent Output")
    st.code(str(trace.final_output), language="json")

st.divider()

# Execution Timeline & Charts
st.subheader("Step Latency & Token Breakdown")
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

st.divider()

# Step Scrubber / Detail View
st.subheader("Step-by-Step Execution Sequence")
step_indices = [f"Step {s.step_index}: {s.name}" for s in trace.steps]
selected_step_str = st.radio("Select Step to Inspect:", step_indices, horizontal=True)
selected_idx = int(selected_step_str.split(":")[0].replace("Step", "").strip())
step = trace.steps[selected_idx]

# Step Card
st.markdown(f"### Step {step.step_index}: `{step.name}` ({step.step_type.value})")

scol1, scol2, scol3 = st.columns(3)
with scol1:
    st.metric("Step Latency", f"{step.latency_ms:.1f} ms")
with scol2:
    st.metric("Step Tokens", step.tokens.total_tokens if step.tokens else 0)
with scol3:
    st.metric("Error State", "ERROR" if step.has_error else "NORMAL")

if step.has_error and step.error:
    st.error(f"**Runtime Exception:** [{step.error.error_type}] {step.error.message}")

d_col1, d_col2 = st.columns(2)
with d_col1:
    st.markdown("**Inputs / Arguments:**")
    st.json(step.inputs)
with d_col2:
    st.markdown("**Step Output / Observation:**")
    if isinstance(step.output, (dict, list)):
        st.json(step.output)
    else:
        st.code(str(step.output))

if step.tool_call:
    with st.expander("Tool Call Telemetry", expanded=False):
        st.write(f"**Tool:** `{step.tool_call.tool_name}`")
        st.write("**Arguments:**", step.tool_call.arguments)
        st.write(f"**Latency:** {step.tool_call.latency_ms:.1f} ms")

if step.model_call:
    with st.expander("Model Call Telemetry", expanded=False):
        st.write(f"**Model:** `{step.model_call.model}`")
        st.write(f"**Prompt:** {step.model_call.prompt}")
        st.write(f"**Response:** {step.model_call.response}")
