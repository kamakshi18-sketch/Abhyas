"""
Home Page UI Component.
Provides application overview, system diagnostics, provider status, and entry point.
"""

import streamlit as st
from app.ai.factory import get_llm_service
from app.config.settings import get_settings


def render_home_page() -> None:
    """Render the Home landing page."""
    settings = get_settings()
    llm_service = get_llm_service()

    st.markdown(
        """
        <div style="text-align: center; padding: 1.5rem 0 2rem 0;">
            <h1 style="font-size: 2.8rem; margin-bottom: 0.5rem; font-weight: 800; letter-spacing: -0.02em;">
                🎯 Abhyas — AI Interviewer
            </h1>
            <p style="font-size: 1.15rem; color: #94a3b8; max-width: 650px; margin: 0 auto; line-height: 1.6;">
                Intelligent, rubric-driven interview preparation and coaching powered by <b style="color: #38bdf8;">Google Gemini</b>, <b style="color: #38bdf8;">NVIDIA Nemotron</b>, and <b style="color: #38bdf8;">Local Ollama</b>.
                Practice realistic technical, behavioral STAR, and HR sessions with grounded, actionable feedback.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Diagnostic & System Status Card
    st.markdown("### 🔌 AI Provider Connectivity")
    is_healthy, status_msg = llm_service.health_check()

    status_col1, status_col2 = st.columns([1, 1])
    with status_col1:
        if is_healthy:
            st.success(f"**AI Service Status:** Ready\n\n{status_msg}")
        else:
            st.warning(f"**AI Service Status:** Configuration Required\n\n{status_msg}")
            st.info("💡 *Tip:* Go to **⚙️ Setup Interview** to select your provider (Gemini, NVIDIA Nemotron, or Ollama) and enter your API key.")

    with status_col2:
        provider_name = getattr(llm_service, "__class__", type(llm_service)).__name__.replace("Service", "")
        active_model = getattr(llm_service, "model", "default")

        st.markdown(
            f"""
            <div style="background: rgba(30, 41, 59, 0.7); padding: 1.1rem; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.12); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);">
                <div style="font-weight: 700; font-size: 1rem; margin-bottom: 0.5rem; color: #f8fafc !important;">Configuration Profile</div>
                <div style="font-size: 0.88rem; color: #cbd5e1 !important; margin-bottom: 0.3rem;"><b>Active Provider:</b> <code style="color: #38bdf8; background: rgba(0,0,0,0.3);">{provider_name}</code></div>
                <div style="font-size: 0.88rem; color: #cbd5e1 !important; margin-bottom: 0.3rem;"><b>Active Model:</b> <code style="color: #38bdf8; background: rgba(0,0,0,0.3);">{active_model}</code></div>
                <div style="font-size: 0.88rem; color: #cbd5e1 !important;"><b>Storage:</b> <code style="color: #38bdf8; background: rgba(0,0,0,0.3);">SQLite (data/interviews.db)</code></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Feature Highlights Grid
    st.markdown("### 🌟 Key Capabilities")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div style="padding: 1.25rem; background: rgba(30, 41, 59, 0.75); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px; height: 100%; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);">
                <div style="font-size: 1.6rem; margin-bottom: 0.5rem;">🤖</div>
                <h4 style="margin: 0 0 0.5rem 0; color: #f8fafc !important; font-weight: 700; font-size: 1.15rem;">Adaptive Questions</h4>
                <p style="font-size: 0.9rem; color: #cbd5e1 !important; margin: 0; line-height: 1.5;">
                    Questions dynamically generated according to role, seniority, category, and session progression.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div style="padding: 1.25rem; background: rgba(30, 41, 59, 0.75); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px; height: 100%; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);">
                <div style="font-size: 1.6rem; margin-bottom: 0.5rem;">📊</div>
                <h4 style="margin: 0 0 0.5rem 0; color: #f8fafc !important; font-weight: 700; font-size: 1.15rem;">5-Metric Evaluation</h4>
                <p style="font-size: 0.9rem; color: #cbd5e1 !important; margin: 0; line-height: 1.5;">
                    Detailed score breakdown across Relevance, Correctness, Completeness, Clarity, and Depth.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
            <div style="padding: 1.25rem; background: rgba(30, 41, 59, 0.75); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px; height: 100%; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);">
                <div style="font-size: 1.6rem; margin-bottom: 0.5rem;">⚡</div>
                <h4 style="margin: 0 0 0.5rem 0; color: #f8fafc !important; font-weight: 700; font-size: 1.15rem;">Multi-Model & Cloud</h4>
                <p style="font-size: 0.9rem; color: #cbd5e1 !important; margin: 0; line-height: 1.5;">
                    Use Google Gemini API, NVIDIA Nemotron, local Ollama, or offline simulation with zero hassle.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Call to Action
    cta_col1, cta_col2, cta_col3 = st.columns([1, 2, 1])
    with cta_col2:
        if st.button("🚀 Start New Interview", use_container_width=True, type="primary"):
            st.session_state.page = "setup"
            st.rerun()
