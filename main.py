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

# Custom CSS for Luxury Dark & Aurora Borealis Aesthetic
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

        /* Global Theme Foundation - Sleek Dark Charcoal / Grey */
        html, body, [class*="css"], .stApp {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
            background-color: #0c0d11 !important;
            color: #f1f5f9 !important;
        }

        .stApp {
            background: radial-gradient(circle at 50% -20%, rgba(255, 255, 255, 0.03) 0%, transparent 60%),
                        radial-gradient(circle at 80% 30%, rgba(255, 255, 255, 0.015) 0%, transparent 50%),
                        #0c0d11 !important;
            min-height: 100vh;
        }

        /* Container Layout */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 7rem !important;
            max-width: 1280px !important;
            position: relative;
            z-index: 1;
        }

        /* Ambient Aurora Horizon Glow at the Bottom */
        .aurora-horizon {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: 200px;
            pointer-events: none;
            z-index: 0;
            overflow: hidden;
        }

        .aurora-wave {
            position: absolute;
            bottom: -50px;
            left: -20%;
            width: 140%;
            height: 180px;
            background: radial-gradient(ellipse at 30% 90%, rgba(0, 242, 254, 0.28) 0%, transparent 60%),
                        radial-gradient(ellipse at 50% 95%, rgba(79, 172, 254, 0.25) 0%, transparent 65%),
                        radial-gradient(ellipse at 75% 90%, rgba(168, 85, 247, 0.28) 0%, transparent 60%),
                        radial-gradient(ellipse at 90% 85%, rgba(236, 72, 153, 0.22) 0%, transparent 55%);
            filter: blur(40px);
            opacity: 0.85;
            animation: aurora-flow 12s ease-in-out infinite alternate;
        }

        .aurora-line {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, 
                transparent 0%, 
                rgba(0, 242, 254, 0.6) 20%, 
                rgba(79, 172, 254, 0.9) 40%, 
                rgba(168, 85, 247, 0.9) 70%, 
                rgba(236, 72, 153, 0.6) 90%, 
                transparent 100%
            );
            box-shadow: 0 0 25px 3px rgba(0, 242, 254, 0.5), 0 0 45px 8px rgba(168, 85, 247, 0.4);
        }

        @keyframes aurora-flow {
            0% {
                transform: scaleY(0.9) translateX(-3%) rotate(-0.5deg);
                filter: blur(40px) hue-rotate(0deg);
            }
            50% {
                transform: scaleY(1.15) translateX(3%) rotate(0.5deg);
                filter: blur(48px) hue-rotate(15deg);
            }
            100% {
                transform: scaleY(0.9) translateX(-3%) rotate(-0.5deg);
                filter: blur(40px) hue-rotate(0deg);
            }
        }

        /* Sleek Neutral Dark Grey Glassmorphic Panels */
        .glass-panel {
            background: rgba(20, 21, 27, 0.78) !important;
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 16px !important;
            box-shadow: 0 12px 36px 0 rgba(0, 0, 0, 0.55) !important;
            transition: all 0.25s ease-in-out;
        }

        .glass-panel:hover {
            border-color: rgba(56, 189, 248, 0.3) !important;
            box-shadow: 0 16px 42px 0 rgba(0, 0, 0, 0.7), 0 0 20px 0 rgba(56, 189, 248, 0.12) !important;
        }

        /* Glass Pill Badges */
        .badge-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(12px);
            padding: 0.35rem 0.85rem;
            border-radius: 9999px;
            font-size: 0.82rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            color: #e2e8f0;
        }

        .badge-pill-cyan {
            background: rgba(6, 182, 212, 0.12);
            border-color: rgba(6, 182, 212, 0.35);
            color: #38bdf8;
            box-shadow: 0 0 15px rgba(6, 182, 212, 0.15);
        }

        .badge-pill-purple {
            background: rgba(168, 85, 247, 0.12);
            border-color: rgba(168, 85, 247, 0.35);
            color: #c084fc;
            box-shadow: 0 0 15px rgba(168, 85, 247, 0.15);
        }

        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background-color: #38bdf8;
            box-shadow: 0 0 10px #38bdf8;
            display: inline-block;
            animation: pulse-dot 2s infinite;
        }

        @keyframes pulse-dot {
            0% { transform: scale(0.9); opacity: 0.7; }
            50% { transform: scale(1.3); opacity: 1; }
            100% { transform: scale(0.9); opacity: 0.7; }
        }

        /* Glowing AI Orb Component */
        .orb-wrapper {
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 1.5rem 0;
            position: relative;
        }

        .orb-sphere {
            width: 140px;
            height: 140px;
            border-radius: 50%;
            background: radial-gradient(circle at 35% 30%, #38bdf8 0%, #3b82f6 30%, #8b5cf6 65%, #181920 95%);
            box-shadow: 0 0 45px 12px rgba(56, 189, 248, 0.35),
                        0 0 80px 24px rgba(139, 92, 246, 0.25),
                        inset 0 0 25px rgba(255, 255, 255, 0.4);
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            animation: orb-breathe 4s ease-in-out infinite alternate;
        }

        .orb-halo {
            position: absolute;
            width: 180px;
            height: 180px;
            border-radius: 50%;
            border: 1px dashed rgba(56, 189, 248, 0.25);
            animation: orb-spin 18s linear infinite;
        }

        .orb-halo-outer {
            position: absolute;
            width: 215px;
            height: 215px;
            border-radius: 50%;
            border: 1px solid rgba(168, 85, 247, 0.15);
            animation: orb-spin 26s linear infinite reverse;
        }


        @keyframes orb-breathe {
            0% { transform: scale(0.96); box-shadow: 0 0 35px 8px rgba(56, 189, 248, 0.3), 0 0 70px 18px rgba(139, 92, 246, 0.2); }
            100% { transform: scale(1.04); box-shadow: 0 0 55px 16px rgba(56, 189, 248, 0.45), 0 0 95px 30px rgba(139, 92, 246, 0.35); }
        }

        @keyframes orb-spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        /* Soundwave frequency visualizer inside Orb */
        .soundwave {
            display: flex;
            align-items: center;
            gap: 4px;
            height: 35px;
            z-index: 2;
        }

        .soundwave-bar {
            width: 3px;
            background: #ffffff;
            border-radius: 99px;
            box-shadow: 0 0 6px rgba(255, 255, 255, 0.8);
            animation: soundwave-anim 1.2s ease-in-out infinite alternate;
        }

        .soundwave-bar:nth-child(1) { height: 12px; animation-delay: 0.1s; }
        .soundwave-bar:nth-child(2) { height: 24px; animation-delay: 0.3s; }
        .soundwave-bar:nth-child(3) { height: 32px; animation-delay: 0.5s; }
        .soundwave-bar:nth-child(4) { height: 20px; animation-delay: 0.2s; }
        .soundwave-bar:nth-child(5) { height: 14px; animation-delay: 0.4s; }

        @keyframes soundwave-anim {
            0% { transform: scaleY(0.4); opacity: 0.7; }
            100% { transform: scaleY(1.1); opacity: 1; }
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #111217 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        }

        [data-testid="stSidebar"] [class*="stMarkdown"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4,
        [data-testid="stSidebar"] h5,
        [data-testid="stSidebar"] h6,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] b,
        [data-testid="stSidebar"] strong {
            color: #f1f5f9 !important;
        }

        /* Buttons Styling */
        .stButton button {
            border-radius: 12px !important;
            font-weight: 600 !important;
            letter-spacing: 0.01em !important;
            padding: 0.55rem 1.2rem !important;
            transition: all 0.2s ease !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }

        .stButton button[kind="primary"] {
            background: linear-gradient(135deg, #0284c7 0%, #2563eb 50%, #7c3aed 100%) !important;
            color: #ffffff !important;
            border: 1px solid rgba(56, 189, 248, 0.4) !important;
            box-shadow: 0 4px 18px 0 rgba(37, 99, 235, 0.45) !important;
        }

        .stButton button[kind="primary"]:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 24px 0 rgba(37, 99, 235, 0.65), 0 0 15px rgba(56, 189, 248, 0.5) !important;
            border-color: rgba(56, 189, 248, 0.8) !important;
        }

        .stButton button[kind="secondary"] {
            background: rgba(26, 27, 34, 0.8) !important;
            color: #cbd5e1 !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
        }

        .stButton button[kind="secondary"]:hover {
            background: rgba(38, 40, 50, 0.95) !important;
            color: #ffffff !important;
            border-color: rgba(56, 189, 248, 0.35) !important;
            transform: translateY(-1px) !important;
        }

        /* Input Elements */
        .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] {
            background-color: rgba(18, 19, 25, 0.9) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 12px !important;
            color: #f8fafc !important;
            backdrop-filter: blur(12px) !important;
        }

        .stTextInput input:focus, .stTextArea textarea:focus {
            border-color: #38bdf8 !important;
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.25) !important;
        }

        /* Progress Bar */
        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #00f2fe 0%, #4facfe 50%, #a855f7 100%) !important;
            box-shadow: 0 0 12px rgba(56, 189, 248, 0.5) !important;
            border-radius: 9999px !important;
        }

        .stProgress > div > div > div {
            background-color: rgba(255, 255, 255, 0.07) !important;
            border-radius: 9999px !important;
        }

        /* Expanders */
        .streamlit-expanderHeader {
            background-color: rgba(22, 23, 30, 0.85) !important;
            border-radius: 10px !important;
            color: #f8fafc !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
        }

        /* Hide Streamlit top decoration */
        header[data-testid="stHeader"] {
            background: transparent !important;
        }
    </style>

    <!-- Animated Aurora Horizon Backdrop -->
    <div class="aurora-horizon">
        <div class="aurora-wave"></div>
        <div class="aurora-line"></div>
    </div>
    """,
    unsafe_allow_html=True,
)


def render_sidebar() -> None:
    """Render application sidebar with session metadata and sleek glassmorphic navigation."""
    with st.sidebar:
        # App Logo & Branding Header
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 0.75rem; padding: 0.5rem 0 1.25rem 0;">
                <div style="width: 38px; height: 38px; border-radius: 10px; background: linear-gradient(135deg, #00f2fe 0%, #7c3aed 100%); display: flex; align-items: center; justify-content: center; box-shadow: 0 0 16px rgba(0, 242, 254, 0.4);">
                    <span style="font-size: 1.2rem;">✨</span>
                </div>
                <div>
                    <h2 style="margin: 0; font-size: 1.25rem; font-weight: 800; background: linear-gradient(90deg, #ffffff 0%, #38bdf8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -0.02em;">Abhyas</h2>
                    <span style="font-size: 0.72rem; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em;">AI Interviewer & Coach</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 0.5rem 0 1.25rem 0;'>", unsafe_allow_html=True)

        # Navigation
        current_page = st.session_state.get("page", "home")
        engine = st.session_state.get("engine")

        st.markdown("<div style='font-size: 0.72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.6rem;'>Menu</div>", unsafe_allow_html=True)

        if st.button("🎙️  Interview Console", use_container_width=True, type="primary" if current_page == "interview" else "secondary"):
            if engine and engine.current_question:
                st.session_state.page = "interview"
            else:
                st.session_state.page = "setup"
            st.rerun()

        if st.button("⚙️  Configuration & Setup", use_container_width=True, type="primary" if current_page == "setup" else "secondary"):
            st.session_state.page = "setup"
            st.rerun()

        if st.button("📊  Insights & Reports", use_container_width=True, type="primary" if current_page == "results" else "secondary"):
            if st.session_state.get("result"):
                st.session_state.page = "results"
            else:
                st.session_state.page = "home"
            st.rerun()

        if st.button("🏠  Dashboard Home", use_container_width=True, type="primary" if current_page == "home" else "secondary"):
            st.session_state.page = "home"
            st.rerun()

        # Active Session HUD Card if in progress
        if engine and engine.config and engine.status.value == "IN_PROGRESS":
            st.markdown("<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 1.25rem 0;'>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style="background: rgba(22, 23, 30, 0.85); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 12px; padding: 0.9rem; box-shadow: 0 4px 14px rgba(0,0,0,0.4);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.4rem;">
                        <span style="font-size: 0.72rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.05em;">Active Session</span>
                        <span class="status-dot"></span>
                    </div>
                    <div style="font-size: 0.92rem; font-weight: 700; color: #f8fafc;">{engine.config.candidate_name}</div>
                    <div style="font-size: 0.78rem; color: #94a3b8; margin-bottom: 0.5rem;">{engine.config.role}</div>
                    <div style="font-size: 0.76rem; color: #cbd5e1; display: flex; justify-content: space-between;">
                        <span>Question {engine.current_question_number}/{engine.config.num_questions}</span>
                        <span style="color: #38bdf8; font-weight: 600;">{engine.config.difficulty.value}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 1.25rem 0;'>", unsafe_allow_html=True)

        # AI Provider Badge
        active_model = settings.gemini_model if settings.llm_provider == "gemini" else (settings.nvidia_model if settings.llm_provider == "nvidia" else settings.ollama_model)
        st.markdown(
            f"""
            <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 10px; padding: 0.75rem 0.85rem; font-size: 0.75rem; line-height: 1.5; color: #94a3b8;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.25rem;">
                    <span style="color: #cbd5e1; font-weight: 600;">Engine Status</span>
                    <span style="color: #22c55e; font-weight: 700;">ONLINE ●</span>
                </div>
                <div><b>Provider:</b> <span style="color: #38bdf8;">{settings.llm_provider.upper()}</span></div>
                <div><b>Model:</b> <span style="color: #e2e8f0;">{active_model}</span></div>
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

