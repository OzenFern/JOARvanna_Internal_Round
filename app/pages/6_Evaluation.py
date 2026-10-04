"""
app/pages/6_Evaluation.py
─────────────────────────
Benchmark Evaluation Suite & Quantitative Metrics Dashboard.
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
from blackbox.evaluate.localization import eval_localization
from blackbox.evaluate.confidence import eval_confidence
from blackbox.evaluate.latency import eval_latency
from blackbox.evaluate.generalization import eval_generalization
from blackbox.evaluate.counterfactual import eval_counterfactual_repairs
from app.paths import ARTIFACTS_DIR, TRACES_DIR
from app.styles import inject_styles

st.set_page_config(page_title="Evaluation · Black Box", layout="wide")
st.title("Model Evaluation & Diagnostic Benchmark Suite")

inject_styles()

store = TraceStore(TRACES_DIR)
traces = store.load_all()

if not traces:
    st.warning("No traces available for evaluation. Generate traces on the Home page.")
    st.stop()

model = LocalAttributionModel()
model_path = ARTIFACTS_DIR / "model.pkl"
if model_path.exists():
    model.load(model_path)

loc_metrics = eval_localization(traces, model)
conf_metrics = eval_confidence(traces, model)
lat_metrics = eval_latency(traces, model)
gen_report = eval_generalization(traces, traces, model)
cf_metrics = eval_counterfactual_repairs([t for t in traces if not t.success])

# Top Metrics Row
st.subheader("1. Primary Fault Localization Accuracy")
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Top-1 Exact Step Accuracy", f"{loc_metrics.top1_accuracy:.1%}")
with m2:
    st.metric("Top-3 Step Accuracy", f"{loc_metrics.top3_accuracy:.1%}")
with m3:
    st.metric("Mean Reciprocal Rank (MRR)", f"{loc_metrics.mrr:.3f}")
with m4:
    st.metric("Diagnosis Latency (Mean)", f"{lat_metrics.mean_local_latency_ms:.2f} ms")

st.divider()

# Chart 1: Per-Fault Type Accuracy Breakdown
st.subheader("2. Fault Localization Accuracy by Injected Category")
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
    else:
        st.info("No fault breakdowns recorded yet.")

with c_col2:
    st.markdown("#### Confidence Calibration Tiers")
    conf_df = pd.DataFrame([
        {"Tier": "High Confidence", "Total Predictions": conf_metrics.high_tier.total_predictions, "Accuracy": f"{conf_metrics.high_tier.accuracy:.1%}"},
        {"Tier": "Medium Confidence", "Total Predictions": conf_metrics.medium_tier.total_predictions, "Accuracy": f"{conf_metrics.medium_tier.accuracy:.1%}"},
        {"Tier": "Low Confidence", "Total Predictions": conf_metrics.low_tier.total_predictions, "Accuracy": f"{conf_metrics.low_tier.accuracy:.1%}"}
    ])
    st.dataframe(conf_df, use_container_width=True, hide_index=True)

st.divider()

# Generalization & Replay Metrics
st.subheader("3. Domain Generalization & Counterfactual Repair Efficacy")
g1, g2 = st.columns(2)

with g1:
    st.markdown("#### Cross-Domain Performance")
    task_df = pd.DataFrame([
        {"Task Domain": k.upper(), "Accuracy": v}
        for k, v in gen_report.cross_task_metrics.items()
    ])
    if not task_df.empty:
        fig_task = px.bar(task_df, x="Task Domain", y="Accuracy", title="Performance by Task Domain")
        fig_task.update_layout(yaxis_range=[0, 1.05])
        st.plotly_chart(fig_task, use_container_width=True)

with g2:
    st.markdown("#### Time-Travel Counterfactual Repair Efficacy")
    st.metric("1-Click Patch Success Rate", f"{cf_metrics.repair_success_rate:.1f}%")
    st.write(f"Tested on **{cf_metrics.total_tested}** faulty trajectories.")
    st.write(f"Successfully repaired **{cf_metrics.successful_repairs}** runs by patching suspected root-cause step.")
    st.success("This demonstrates that learned fault localizations are actionable and verifiable via replay.")
