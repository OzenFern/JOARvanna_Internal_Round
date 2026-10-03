"""
app/pages/5_Trace_Diff.py
─────────────────────────
Side-by-Side Trace Comparison & Earliest Divergence Detector.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from blackbox.capture.store import TraceStore
from blackbox.compare.divergence import find_divergence
from blackbox.explain.contrast import generate_contrastive_explanation

st.set_page_config(page_title="Trace Diff · Black Box", page_icon="🔀", layout="wide")
st.title("🔀 Side-by-Side Execution Trace Diff & Divergence")

store = TraceStore(Path("data/traces"))
run_ids = store.list_runs()

if len(run_ids) < 2:
    st.warning("Need at least two traces to perform side-by-side comparison.")
    st.stop()

col_left_sel, col_right_sel = st.columns(2)
with col_left_sel:
    left_id = st.selectbox("Select Baseline / Failed Trace (Left):", run_ids, index=0)
with col_right_sel:
    right_id = st.selectbox("Select Comparison / Fixed Trace (Right):", run_ids, index=1 if len(run_ids) > 1 else 0)

t_left = store.load(left_id)
t_right = store.load(right_id)

st.markdown("---")

# Divergence Verdict Banner
div_res = find_divergence(t_left, t_right)

if div_res.has_divergence:
    st.error(f"⚠️ **Divergence Detected:** {div_res.explanation}")
    st.markdown(f"**Earliest Divergence Point:** `Step {div_res.earliest_step_index}` | **Category:** `{div_res.divergence_type}`")
else:
    st.success("✅ **Zero Divergence:** Both traces executed identically.")

# Contrastive Summary Card
contrast = generate_contrastive_explanation(t_left, t_right)
st.info(f"💡 **Contrastive Explanation:** {contrast.explanation}")

st.markdown("---")

# Outcome Comparison Table
st.subheader("🏁 Final Outcome Comparison")
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

st.markdown("---")

# Step-by-Step Alignment Matrix
st.subheader("📊 Step-by-Step Trajectory Alignment")

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
