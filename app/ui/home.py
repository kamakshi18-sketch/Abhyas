"""
Home Page UI Component.
Phase 4: Luxury Aurora Landing Experience.
Provides application overview, AI provider diagnostics, and quick launch actions.
"""

import streamlit as st
from app.ai.factory import get_llm_service
from app.config.settings import get_settings


def render_home_page() -> None:
    """Render the Home landing page."""
    settings = get_settings()
    llm_service = get_llm_service()

    # Hero Banner with Gradient Header & AI Glow Orb
    st.markdown(
        """
        <div style="text-align: center; padding: 1.5rem 0 2rem 0;">
            <div style="display: inline-flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem;">
                <span class="badge-pill badge-pill-cyan">
                    <span class="status-dot"></span> Next-Gen AI Interview Coaching
                </span>
                <span class="badge-pill badge-pill-purple">
                    Phases 1-4 Active
                </span>
            </div>
            
            <h1 style="font-size: 3.2rem; font-weight: 800; letter-spacing: -0.03em; margin: 0 0 0.75rem 0; line-height: 1.15; background: linear-gradient(135deg, #ffffff 30%, #38bdf8 70%, #c084fc 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Master Your Interviews with Abhyas
            </h1>
            
            <p style="font-size: 1.15rem; color: #94a3b8; max-width: 720px; margin: 0 auto 1.5rem auto; line-height: 1.6;">
                Stateful, adaptive simulation powered by <b style="color: #38bdf8;">Google Gemini</b>, <b style="color: #38bdf8;">NVIDIA Nemotron</b>, and <b style="color: #38bdf8;">Local Ollama</b>.
                Practice realistic Technical, Behavioral (STAR), and HR rounds with rubric-grounded feedback.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Central Mini Orb Callout
    st.markdown(
        """
        <div class="orb-wrapper" style="margin: 0.5rem 0 2rem 0;">
            <div class="orb-halo"></div>
            <div class="orb-sphere" style="width: 100px; height: 100px;">
                <div class="soundwave" style="height: 25px;">
                    <div class="soundwave-bar"></div>
                    <div class="soundwave-bar"></div>
                    <div class="soundwave-bar"></div>
                    <div class="soundwave-bar"></div>
                    <div class="soundwave-bar"></div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Diagnostic & Connectivity HUD Cards
    is_healthy, status_msg = llm_service.health_check()
    status_col1, status_col2 = st.columns([1, 1], gap="medium")

    with status_col1:
        if is_healthy:
            st.markdown(
                f"""
                <div class="glass-panel" style="padding: 1.25rem; height: 100%; border-color: rgba(34, 197, 94, 0.3) !important;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span style="font-weight: 700; color: #4ade80; font-size: 1rem;">🔌 AI Service Status</span>
                        <span style="color: #22c55e; font-size: 0.8rem; font-weight: 700;">READY ●</span>
                    </div>
                    <p style="font-size: 0.88rem; color: #cbd5e1; margin: 0; line-height: 1.5;">{status_msg}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="glass-panel" style="padding: 1.25rem; height: 100%; border-color: rgba(245, 158, 11, 0.4) !important;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span style="font-weight: 700; color: #fbbf24; font-size: 1rem;">🔌 AI Service Status</span>
                        <span style="color: #f59e0b; font-size: 0.8rem; font-weight: 700;">CONFIG NEEDED ⚠️</span>
                    </div>
                    <p style="font-size: 0.88rem; color: #cbd5e1; margin: 0; line-height: 1.5;">{status_msg}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with status_col2:
        provider_name = getattr(llm_service, "__class__", type(llm_service)).__name__.replace("Service", "")
        active_model = getattr(llm_service, "model", "default")

        st.markdown(
            f"""
            <div class="glass-panel" style="padding: 1.25rem; height: 100%;">
                <div style="font-weight: 700; font-size: 1rem; margin-bottom: 0.5rem; color: #f8fafc;">Configuration Profile</div>
                <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.3rem;"><b>Active Provider:</b> <span style="color: #38bdf8;">{provider_name}</span></div>
                <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.3rem;"><b>Active Model:</b> <span style="color: #e2e8f0;">{active_model}</span></div>
                <div style="font-size: 0.85rem; color: #94a3b8;"><b>Storage:</b> <span style="color: #c084fc;">SQLite (data/interviews.db)</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Feature Highlights Grid
    col1, col2, col3 = st.columns(3, gap="medium")

    with col1:
        st.markdown(
            """
            <div class="glass-panel" style="padding: 1.35rem; height: 100%;">
                <div style="width: 42px; height: 42px; border-radius: 10px; background: rgba(56, 189, 248, 0.15); display: flex; align-items: center; justify-content: center; font-size: 1.4rem; margin-bottom: 0.75rem; border: 1px solid rgba(56, 189, 248, 0.3);">
                    🎯
                </div>
                <h4 style="margin: 0 0 0.5rem 0; color: #f8fafc; font-weight: 700; font-size: 1.1rem;">Adaptive Questioning</h4>
                <p style="font-size: 0.88rem; color: #94a3b8; margin: 0; line-height: 1.5;">
                    Calibrated progression planning across 8 question categories and topic matrices.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div class="glass-panel" style="padding: 1.35rem; height: 100%;">
                <div style="width: 42px; height: 42px; border-radius: 10px; background: rgba(168, 85, 247, 0.15); display: flex; align-items: center; justify-content: center; font-size: 1.4rem; margin-bottom: 0.75rem; border: 1px solid rgba(168, 85, 247, 0.3);">
                    📊
                </div>
                <h4 style="margin: 0 0 0.5rem 0; color: #f8fafc; font-weight: 700; font-size: 1.1rem;">Type-Specific Rubrics</h4>
                <p style="font-size: 0.88rem; color: #94a3b8; margin: 0; line-height: 1.5;">
                    Dedicated rubrics with grounded evidence extraction for Technical, STAR, and HR rounds.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
            <div class="glass-panel" style="padding: 1.35rem; height: 100%;">
                <div style="width: 42px; height: 42px; border-radius: 10px; background: rgba(34, 197, 94, 0.15); display: flex; align-items: center; justify-content: center; font-size: 1.4rem; margin-bottom: 0.75rem; border: 1px solid rgba(34, 197, 94, 0.3);">
                    ⚡
                </div>
                <h4 style="margin: 0 0 0.5rem 0; color: #f8fafc; font-weight: 700; font-size: 1.1rem;">Multi-Provider Engine</h4>
                <p style="font-size: 0.88rem; color: #94a3b8; margin: 0; line-height: 1.5;">
                    Seamlessly switch between Google Gemini API, NVIDIA Nemotron NIM, and local Ollama.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Call to Action Button
    cta_col1, cta_col2, cta_col3 = st.columns([1, 2, 1])
    with cta_col2:
        if st.button("🚀  Configure & Start Interview", use_container_width=True, type="primary"):
            st.session_state.page = "setup"
            st.rerun()
