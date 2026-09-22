"""
AI Interviewer - Main Application Entrypoint.
Streamlit orchestration, session router, styling, and database auto-initialization.
"""

import logging
import streamlit as st

from app.config.settings import get_settings
from app.database.database import init_db
from app.ui.home import render_home_page
from app.ui.setup import render_setup_page
from app.ui.interview import render_interview_page
from app.ui.results import render_results_page

# Configure Logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai_interviewer")

# Initialize Database Schema
try:
    init_db()
except Exception as e:
    logger.error(f"Database initialization failed: {e}")

# Page Configuration
st.set_page_config(
    page_title="Abhyas — AI Interviewer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Premium Design Aesthetic
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        /* Card and Container Styling */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1000px;
        }

        /* Button Styling */
        .stButton button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.2s ease;
        }

        .stButton button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        /* Card Hover Animations */
        div[style*="border-radius: 12px"] {
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        div[style*="border-radius: 12px"]:hover {
            transform: translateY(-2px);
        }

        /* Sidebar Styling & High-Contrast Typography */
        [data-testid="stSidebar"] {
            background-color: #f8fafc !important;
            border-right: 1px solid #e2e8f0;
        }


        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4,
        [data-testid="stSidebar"] h5,
        [data-testid="stSidebar"] h6,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] b,
        [data-testid="stSidebar"] strong,
        [data-testid="stSidebar"] .stMarkdown {
            color: #0f172a !important;
        }

        /* Keep button text contrast correct */
        [data-testid="stSidebar"] .stButton button p,
        [data-testid="stSidebar"] .stButton button span {
            color: inherit !important;
        }

        /* Form Inputs */
        .stTextInput input, .stTextArea textarea, .stSelectbox select {
            border-radius: 8px;
        }

        /* Metric Styling */
        [data-testid="stMetricValue"] {
            font-size: 1.6rem !important;
            font-weight: 700 !important;
        }

        /* Alert Styling */
        .stAlert {
            border-radius: 8px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_sidebar() -> None:
    """Render application sidebar with session metadata and quick actions."""
    with st.sidebar:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 1rem;">
                <span style="font-size: 2rem;">🎯</span>
                <div>
                    <h2 style="margin: 0; font-size: 1.35rem; font-weight: 800; color: #0f172a !important; letter-spacing: -0.02em;">Abhyas</h2>
                    <span style="font-size: 0.76rem; color: #475569 !important; font-weight: 600;">AI Interviewer & Coach</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Current Session Info if active
        engine = st.session_state.get("engine")
        if engine and engine.config and engine.status.value == "IN_PROGRESS":
            st.markdown("##### 📍 Active Session")
            st.markdown(f"**Candidate:** {engine.config.candidate_name}")
            st.markdown(f"**Role:** {engine.config.role}")
            st.markdown(f"**Progress:** Q{engine.current_question_number} / {engine.config.num_questions}")
            st.markdown(f"**Type:** {engine.config.interview_type.value}")
            st.markdown(f"**Difficulty:** {engine.config.difficulty.value}")
            st.markdown("---")

        # Quick Navigation
        st.markdown("##### 🧭 Navigation")
        current_page = st.session_state.get("page", "home")

        if st.button("🏠 Home", use_container_width=True, type="secondary" if current_page != "home" else "primary"):
            st.session_state.page = "home"
            st.rerun()

        if st.button("⚙️ Setup Interview", use_container_width=True, type="secondary" if current_page != "setup" else "primary"):
            st.session_state.page = "setup"
            st.rerun()

        if engine and engine.current_question:
            if st.button("🎙️ Active Interview", use_container_width=True, type="secondary" if current_page != "interview" else "primary"):
                st.session_state.page = "interview"
                st.rerun()

        if st.session_state.get("result"):
            if st.button("📊 Assessment Report", use_container_width=True, type="secondary" if current_page != "results" else "primary"):
                st.session_state.page = "results"
                st.rerun()

        st.markdown("---")
        active_model = settings.gemini_model if settings.llm_provider == "gemini" else (settings.nvidia_model if settings.llm_provider == "nvidia" else settings.ollama_model)
        st.markdown(
            f"""
            <div style="font-size: 0.78rem; color: #334155 !important; line-height: 1.5; font-weight: 500;">
                <b>Provider:</b> {settings.llm_provider.upper()}<br>
                <b>Model:</b> {active_model}<br>
                <b>Storage:</b> SQLite Active
            </div>
            """,
            unsafe_allow_html=True,
        )



def main() -> None:
    """Main application controller and page router."""
    # Initialize Session State Variables
    if "page" not in st.session_state:
        st.session_state.page = "home"
    if "engine" not in st.session_state:
        st.session_state.engine = None
    if "current_question" not in st.session_state:
        st.session_state.current_question = None
    if "submitted_current" not in st.session_state:
        st.session_state.submitted_current = False
    if "latest_evaluation" not in st.session_state:
        st.session_state.latest_evaluation = None
    if "result" not in st.session_state:
        st.session_state.result = None

    render_sidebar()

    # Route to appropriate page
    page = st.session_state.page

    try:
        if page == "home":
            render_home_page()
        elif page == "setup":
            render_setup_page()
        elif page == "interview":
            render_interview_page()
        elif page == "results":
            render_results_page()
        else:
            st.session_state.page = "home"
            render_home_page()
    except Exception as e:
        logger.exception("Unhandled error in page rendering")
        st.error(f"An unexpected error occurred: {str(e)}")
        if st.button("Return to Home"):
            st.session_state.page = "home"
            st.rerun()


if __name__ == "__main__":
    main()
