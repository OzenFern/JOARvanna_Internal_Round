"""Shared visual styling for the Streamlit application."""

import streamlit as st


def inject_styles() -> None:
    """Apply the shared visual system used across all app pages."""
    st.markdown(
        """
<style>
    :root {
        --bb-bg: #0b1220;
        --bb-panel: #111c2f;
        --bb-panel-soft: #16243a;
        --bb-border: rgba(148, 163, 184, 0.18);
        --bb-text-muted: #94a3b8;
        --bb-accent: #38bdf8;
    }

    .stApp {
        background:
            radial-gradient(circle at 8% 0%, rgba(14, 165, 233, 0.09), transparent 28rem),
            linear-gradient(180deg, var(--bb-bg) 0%, #0f172a 100%);
    }

    .block-container {
        max-width: 1500px;
        padding-top: 2.5rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3, h4 {
        letter-spacing: -0.03em;
    }

    h1 {
        font-weight: 750;
        margin-bottom: 0.35rem;
    }

    h2, h3 {
        margin-top: 1.25rem;
    }

    [data-testid="stMetric"] {
        background: rgba(17, 28, 47, 0.82);
        border: 1px solid var(--bb-border);
        border-radius: 14px;
        padding: 0.85rem 1rem;
        box-shadow: 0 12px 30px rgba(2, 6, 23, 0.16);
    }

    [data-testid="stMetricLabel"] {
        color: var(--bb-text-muted);
    }

    [data-testid="stMetricValue"] {
        color: #f8fafc;
    }

    [data-testid="stDataFrame"],
    [data-testid="stExpander"] {
        border: 1px solid var(--bb-border);
        border-radius: 14px;
        overflow: hidden;
    }

    [data-testid="stExpander"] details {
        background: rgba(17, 28, 47, 0.5);
    }

    .stButton > button {
        border-radius: 9px;
        border: 1px solid rgba(56, 189, 248, 0.28);
        transition: border-color 120ms ease, background 120ms ease, transform 120ms ease;
    }

    .stButton > button:hover {
        border-color: var(--bb-accent);
        transform: translateY(-1px);
    }

    hr {
        border-color: var(--bb-border);
        margin: 1.75rem 0;
    }

    [data-testid="stCaptionContainer"] {
        color: var(--bb-text-muted);
    }
</style>
        """,
        unsafe_allow_html=True,
    )
