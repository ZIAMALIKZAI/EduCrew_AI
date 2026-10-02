import streamlit as st

def apply_custom_styles():
    css = """<style>
        .main-header { font-size: 2.2rem; font-weight: 700; color: #1E3A8A; margin-bottom: 0.2rem; }
        .sub-header { font-size: 1.05rem; color: #475569; margin-bottom: 1.5rem; }
        .stButton>button { background-color: #2563EB; color: white; border-radius: 8px; font-weight: 600; border: none; padding: 0.5rem 1rem; }
        .stButton>button:hover { background-color: #1D4ED8; color: white; }
    </style>"""
    st.markdown(css, unsafe_allow_html=True)
