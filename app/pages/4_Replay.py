"""
app/pages/4_Replay.py
─────────────────────
Checkpointed Replay Studio & Counterfactual Time-Travel Execution.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import json
from blackbox.capture.store import TraceStore
from blackbox.replay.resume import resume_from_step
from blackbox.replay.checkpoint import CheckpointManager

st.set_page_config(page_title="Replay Studio · Black Box", page_icon="⏪", layout="wide")
st.title("⏪ Checkpointed Time-Travel Replay Studio")

store = TraceStore(Path("data/traces"))
run_ids = store.list_runs()

if not run_ids:
    st.warning("No traces available.")
    st.stop()

selected_run_id = st.selectbox("Select Baseline Run to Replay / Fork:", run_ids, index=0)
trace = store.load(selected_run_id)

st.markdown(f"**Task:** {trace.task_description}")
st.markdown(f"**Baseline Status:** {'✅ SUCCESS' if trace.success else '❌ FAILED'}")

st.markdown("---")

# Checkpoint Step Selector
st.subheader("1. Select Checkpoint Step to Fork From")
step_options = [f"Step {s.step_index}: {s.name} (Output: {str(s.output)[:30]})" for s in trace.steps]
selected_step_str = st.selectbox("Choose Checkpoint Step:", step_options, index=1 if len(trace.steps) > 1 else 0)
fork_step_idx = int(selected_step_str.split(":")[0].replace("Step", "").strip())
fork_step = trace.steps[fork_step_idx]

# Checkpoint State Inspector
with st.expander(f"📦 Inspect Checkpoint State at Step {fork_step_idx}", expanded=False):
    state_snap = CheckpointManager.extract_state_at_step(trace, fork_step_idx)
    st.json(state_snap)

st.markdown("---")

# Intervention & Patch Editor
st.subheader("2. Configure Step Intervention / Patch")
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

# Execution Button
st.markdown("---")
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

# Replay Result View
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
