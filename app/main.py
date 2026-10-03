"""
app/main.py
───────────
Streamlit app entry point.
"""
import streamlit as st

st.set_page_config(page_title="Black Box", page_icon="⬛", layout="wide")
st.title("Black Box Debugger")
st.write("Select a page from the sidebar to inspect traces, view diagnoses, or debug failures.")
