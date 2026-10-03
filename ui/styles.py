import streamlit as st

def apply_custom_styles():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        
        * {
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        .main-header {
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(90deg, #1E3A8A 0%, #2563EB 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.2rem;
        }
        
        .sub-header {
            font-size: 1.0rem;
            color: #64748B;
            margin-bottom: 1.6rem;
            font-weight: 500;
        }

        .kpi-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 1.2rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            text-align: center;
        }

        .kpi-value {
            font-size: 1.8rem;
            font-weight: 800;
            color: #1E3A8A;
        }

        .kpi-label {
            font-size: 0.85rem;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
        }

        .stButton>button {
            background: linear-gradient(90deg, #2563EB 0%, #1D4ED8 100%);
            color: white;
            border-radius: 8px;
            font-weight: 600;
            border: none;
            padding: 0.55rem 1.4rem;
            transition: all 0.2s ease-in-out;
        }

        .stButton>button:hover {
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
            color: white;
            transform: translateY(-1px);
        }
        </style>
    """, unsafe_allow_html=True)
