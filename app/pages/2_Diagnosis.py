"""
app/pages/2_Diagnosis.py
────────────────────────
Root-Cause Failure Diagnosis & Step Suspicion Attribution.
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
from blackbox.attribution.model import LocalAttributionModel
from blackbox.analysis.local import analyze_local
from blackbox.analysis.cloud import analyze_cloud
from blackbox.debug.diagnose import create_diagnosis
from blackbox.analysis.consensus import ConsensusResult
from blackbox.explain.saliency import compute_step_saliency

st.set_page_config(page_title="Diagnosis · Black Box", page_icon="🩺", layout="wide")
st.title("🩺 Intelligent Fault Diagnosis & Attribution")

store = TraceStore(Path("data/traces"))
run_ids = store.list_runs()

if not run_ids:
    st.warning("No traces available. Return to the Home page to generate traces.")
    st.stop()

# Filter selector to prefer failed runs
selected_run_id = st.selectbox("Select Agent Run to Diagnose:", run_ids, index=0)
trace = store.load(selected_run_id)

model = LocalAttributionModel()
model_path = Path("data/artifacts/model.pkl")
if model_path.exists():
    model.load(model_path)

# Run Local Analysis
local_res = analyze_local(trace, model)
consensus = ConsensusResult(
    scores=local_res.scores,
    top_step=local_res.top_step,
    agreement=True,
    final_confidence=local_res.confidence
)
diagnosis = create_diagnosis(trace, consensus)

# Status & Verdict Banner
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

st.markdown("---")

# Suspicion Ranking Chart
st.subheader("🎯 Step Suspicion Distribution (Attribution Weights)")
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

# Diagnostic Rationale & Evidence
st.subheader("📖 Evidence & Rationale Breakdown")
r_col1, r_col2 = st.columns([3, 2])

with r_col1:
    st.markdown("#### 🔍 Failure Explanation")
    st.info(diagnosis.rationale)

    # Feature saliency for the culprit step
    saliency = compute_step_saliency(trace, diagnosis.likely_source)
    st.markdown("#### 🔬 Step Feature Saliency")
    st.write(saliency.summary)
    
    sal_df = pd.DataFrame(saliency.top_contributing_features, columns=["Feature Signal", "Weight"])
    st.dataframe(sal_df, use_container_width=True, hide_index=True)

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

st.markdown("---")

# Cloud Verifier Section (Multi-Layer Verification)
st.subheader("☁️ Cloud LLM Verifier (Optional Deep Critique)")
st.write("Cross-validate the fast local ML attribution using an LLM Judge (OpenAI / Gemini / Heuristic Critique).")

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
