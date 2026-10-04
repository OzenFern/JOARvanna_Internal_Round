"""
app/pages/3_Debugging.py
────────────────────────
Interactive Debugging, Exception Analyzer, and Actionable Remediation Cards.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import json
from blackbox.capture.store import TraceStore
from blackbox.attribution.model import LocalAttributionModel
from blackbox.analysis.local import analyze_local
from blackbox.debug.exceptions import analyze_exceptions
from blackbox.debug.suggestions import generate_suggestions
from blackbox.intervene.patch import StepPatch
from blackbox.intervene.branch import create_branch
from app.styles import inject_styles

st.set_page_config(page_title="Debugging · Black Box", layout="wide")
st.title("Interactive Debugging & Remediation Studio")

inject_styles()

store = TraceStore(Path("data/traces"))
run_ids = store.list_runs()

if not run_ids:
    st.warning("No traces available.")
    st.stop()

selected_run_id = st.selectbox("Select Failed Run to Debug:", run_ids, index=0)
trace = store.load(selected_run_id)

model = LocalAttributionModel()
model_path = Path("data/artifacts/model.pkl")
if model_path.exists():
    model.load(model_path)

local_res = analyze_local(trace, model)
suspect_step_idx = local_res.top_step
suspect_step = trace.steps[suspect_step_idx] if suspect_step_idx < len(trace.steps) else None

# Section 1: Exception Analysis
st.subheader("1. Exception & Runtime Signal Analyzer")
exc_analysis = analyze_exceptions(trace)

if exc_analysis.has_exception:
    st.error(f"**Root Exception Category:** `{exc_analysis.category.upper()}` ({exc_analysis.exception_type})")
    st.write(f"**Originating Step:** Step {exc_analysis.origin_step_index} (`{exc_analysis.origin_step_name}`)")
    st.write(f"**Error Message:** `{exc_analysis.exception_message}`")
    st.info(f"**Root Cause Diagnosis:** {exc_analysis.root_cause_summary}")
else:
    st.success("No explicit uncaught exceptions: silent semantic or computational failure detected.")
    st.info(f"The failure was caused by an erroneous intermediate calculation or retrieved fact at Step {suspect_step_idx} ({suspect_step.name if suspect_step else ''}).")

st.divider()

# Section 2: Actionable Remediation Suggestions
st.subheader(f"2. Actionable Fix Suggestions for Step {suspect_step_idx} (`{suspect_step.name if suspect_step else ''}`)")

suggestions = generate_suggestions(trace, suspect_step_idx)

if not suggestions:
    st.info("No automatic rule-based suggestions generated. You can manually configure a patch in the Replay tab.")
else:
    for i, sug in enumerate(suggestions):
        with st.container():
            st.markdown(f"### Suggestion #{i+1}: {sug.title}")
            st.write(sug.description)

            sc1, sc2 = st.columns([3, 1])
            with sc1:
                st.markdown("**Proposed Patch Payload:**")
                st.json(sug.patch_payload)
            with sc2:
                st.metric("Patch Confidence", f"{sug.confidence:.0%}")

                if st.button(f"Apply Patch & Replay Branch", key=f"btn_patch_{i}", type="primary"):
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
                        st.success(f"Branch `{repaired_trace.run_id}` created and executed.")

        st.divider()

# Display Result of Repaired Run if available
if "last_repaired_run" in st.session_state:
    rep = st.session_state["last_repaired_run"]
    st.subheader(f"Repaired Execution Result: `{rep.run_id}`")

    r_res_col1, r_res_col2, r_res_col3 = st.columns(3)
    with r_res_col1:
        st.metric("Repaired Outcome", "SUCCESS" if rep.success else "FAILED")
    with r_res_col2:
        st.metric("Target Output", str(rep.expected_output))
    with r_res_col3:
        st.metric("Recomputed Final Output", str(rep.final_output))

    st.info(f"**Replay Savings:** Checkpoint resumption bypassed re-executing steps 0 to {suspect_step_idx-1}, saving {rep.meta.get('replay_savings_pct', 0)}% of runtime computation.")
