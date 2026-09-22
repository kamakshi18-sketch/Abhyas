"""
Results Page UI Component.
Renders comprehensive interview performance reports, score metrics, question breakdowns, and export utilities.
"""

import json
import streamlit as st
from app.schemas.interview import InterviewResult


def render_results_page() -> None:
    """Render the Final Interview Assessment Report."""
    result: InterviewResult = st.session_state.get("result")

    if not result:
        st.warning("No completed interview assessment found.")
        if st.button("Start New Interview"):
            st.session_state.page = "setup"
            st.rerun()
        return

    config = result.config
    summary = result.summary
    score = summary.overall_score

    # Score styling
    score_color = "#22c55e" if score >= 7.0 else ("#f59e0b" if score >= 5.0 else "#ef4444")
    performance_tier = "Exceeds Expectations" if score >= 8.0 else ("Proficient" if score >= 6.5 else ("Developing" if score >= 5.0 else "Needs Improvement"))

    st.markdown(
        """
        <div style="margin-bottom: 1.5rem;">
            <h2 style="margin-bottom: 0.2rem; color: #f8fafc;">📊 Final Interview Assessment</h2>
            <p style="color: #94a3b8; font-size: 0.95rem;">
                Comprehensive evaluation summary, score breakdowns, and developmental feedback.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Executive Score & Overview Card
    st.markdown(
        f"""
        <div class="glass-panel" style="padding: 1.75rem; margin-bottom: 1.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 1rem;">
                <div>
                    <h3 style="margin: 0 0 0.25rem 0; font-size: 1.5rem; color: #ffffff; font-weight: 700;">{config.candidate_name}</h3>
                    <div style="color: #cbd5e1; font-size: 0.95rem;">
                        Target Role: <b style="color: #38bdf8;">{config.role}</b> | Experience: <b style="color: #f8fafc;">{config.experience_level.value}</b>
                    </div>
                    <div style="color: #94a3b8; font-size: 0.9rem; margin-top: 0.25rem;">
                        Format: <b style="color: #c084fc;">{config.interview_type.value}</b> | Difficulty: <b style="color: #f8fafc;">{config.difficulty.value}</b>
                    </div>
                </div>
                <div style="text-align: right; background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(255, 255, 255, 0.1); padding: 0.85rem 1.5rem; border-radius: 14px; box-shadow: 0 0 20px rgba(0,0,0,0.5);">
                    <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; font-weight: 700; letter-spacing: 0.08em;">Overall Score</div>
                    <div style="font-size: 2.4rem; font-weight: 800; color: {score_color}; line-height: 1.1;">
                        {score:.1f}<span style="font-size: 1.1rem; font-weight: 500; color: #94a3b8;"> / 10</span>
                    </div>
                    <div style="font-size: 0.85rem; font-weight: 700; color: {score_color}; margin-top: 0.2rem;">
                        {performance_tier}
                    </div>
                </div>
            </div>
            <hr style="border: none; border-top: 1px solid rgba(255, 255, 255, 0.08); margin: 1.25rem 0;">
            <div>
                <h4 style="margin: 0 0 0.5rem 0; color: #f8fafc; font-size: 1.1rem;">Executive Assessment Summary</h4>
                <p style="color: #cbd5e1; line-height: 1.6; margin: 0; font-size: 0.96rem;">
                    {summary.overall_feedback}
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Key Strengths & Recommendations Grid
    col_str, col_rec = st.columns(2, gap="medium")

    with col_str:
        st.markdown(
            """
            <div class="glass-panel" style="padding: 1.4rem; height: 100%; border-color: rgba(34, 197, 94, 0.3) !important;">
                <h4 style="color: #4ade80; margin: 0 0 0.75rem 0; font-size: 1.05rem; font-weight: 700;">
                    🌟 Top Candidate Strengths
                </h4>
            """,
            unsafe_allow_html=True,
        )
        if summary.strengths_summary:
            for item in summary.strengths_summary:
                st.markdown(f"✅ {item}")
        else:
            st.markdown("*None recorded.*")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_rec:
        st.markdown(
            """
            <div class="glass-panel" style="padding: 1.4rem; height: 100%; border-color: rgba(56, 189, 248, 0.3) !important;">
                <h4 style="color: #38bdf8; margin: 0 0 0.75rem 0; font-size: 1.05rem; font-weight: 700;">
                    🎯 Recommended Growth Areas
                </h4>
            """,
            unsafe_allow_html=True,
        )
        if summary.areas_to_improve:
            for item in summary.areas_to_improve:
                st.markdown(f"📌 {item}")
        elif summary.weaknesses_summary:
            for item in summary.weaknesses_summary:
                st.markdown(f"📌 {item}")
        else:
            st.markdown("*None recorded.*")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Question-by-Question Detailed Breakdown
    st.markdown("### 📝 Question Breakdown & Detailed Feedback")

    if not result.pairs:
        st.info("No individual questions were recorded in this session.")
    else:
        for idx, pair in enumerate(result.pairs, 1):
            q = pair.question
            ans = pair.answer
            ev = pair.evaluation
            q_score = ev.score

            with st.expander(f"Question {idx}: {q.category} — Score: {q_score:.1f}/10", expanded=(idx == 1)):
                st.markdown(f"**Question:**\n> {q.question_text}")
                st.markdown(f"**Your Answer:**\n```\n{ans.answer_text}\n```")

                # Metrics
                st.markdown("**Metric Ratings (1-10 scale):**")
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Relevance", f"{ev.metrics.relevance}/10")
                m2.metric("Correctness", f"{ev.metrics.correctness}/10")
                m3.metric("Completeness", f"{ev.metrics.completeness}/10")
                m4.metric("Clarity", f"{ev.metrics.clarity}/10")
                m5.metric("Depth", f"{ev.metrics.depth}/10")

                sub_c1, sub_c2 = st.columns(2)
                with sub_c1:
                    st.markdown("**Strengths:**")
                    for s in ev.strengths:
                        st.markdown(f"- {s}")
                with sub_c2:
                    st.markdown("**Weaknesses / Gaps:**")
                    for w in ev.weaknesses:
                        st.markdown(f"- {w}")

                st.markdown(f"**Feedback:**\n{ev.feedback}")
                st.info(f"💡 **Suggested Ideal Approach:**\n\n{ev.suggested_improvement}")

    st.markdown("---")

    # Bottom Actions & Export
    b_col1, b_col2, b_col3 = st.columns([1, 1, 1])

    with b_col1:
        # Download JSON
        result_json = result.model_dump_json(indent=2)
        st.download_button(
            label="💾 Export Results (JSON)",
            data=result_json,
            file_name=f"interview_result_{config.candidate_name.replace(' ', '_').lower()}.json",
            mime="application/json",
            use_container_width=True,
        )

    with b_col2:
        if st.button("🔄 Start New Interview", type="primary", use_container_width=True):
            st.session_state.engine = None
            st.session_state.result = None
            st.session_state.latest_evaluation = None
            st.session_state.submitted_current = False
            st.session_state.current_question = None
            st.session_state.page = "setup"
            st.rerun()

    with b_col3:
        if st.button("🏠 Back to Home", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

    # Coaching Disclaimer
    st.markdown(
        """
        <div style="text-align: center; margin-top: 2rem; color: #94a3b8; font-size: 0.82rem;">
            ℹ️ <i>Disclaimer: Abhyas provides AI-assisted coaching feedback generated by language models for preparation and practice.
            Evaluations represent simulated pedagogical perspectives and should not be treated as absolute hiring measurements.</i>
        </div>
        """,
        unsafe_allow_html=True,
    )
