"""
Interview Session UI Component.
Renders real-time question display, answer submission, immediate feedback, and state progression.
Phase 5: Displays adaptive decision badges, topic progression, and difficulty scaling indicators.
"""

import streamlit as st
from app.core.interviewer import InterviewEngine
from app.schemas.interview import DecisionAction, Difficulty


def _render_decision_badge(decision) -> str:
    """Render a styled badge representing the active Phase 5 adaptive decision action."""
    if not decision:
        return ""
    
    action_val = decision.action.value if hasattr(decision.action, "value") else str(decision.action)
    action_map = {
        "FOLLOW_UP": ("🎯 Follow-Up", "rgba(59, 130, 246, 0.25)", "#60a5fa", "rgba(59, 130, 246, 0.4)"),
        "DEEP_DIVE": ("🚀 Deep-Dive", "rgba(168, 85, 247, 0.25)", "#c084fc", "rgba(168, 85, 247, 0.4)"),
        "CLARIFY": ("🔍 Clarification", "rgba(234, 179, 8, 0.25)", "#facc15", "rgba(234, 179, 8, 0.4)"),
        "NEW_TOPIC": ("🏷️ New Topic", "rgba(16, 185, 129, 0.25)", "#34d399", "rgba(16, 185, 129, 0.4)"),
        "INCREASE_DIFFICULTY": ("📈 Stepping Up Difficulty", "rgba(249, 115, 22, 0.25)", "#fb923c", "rgba(249, 115, 22, 0.4)"),
        "DECREASE_DIFFICULTY": ("📉 Calibrating Difficulty", "rgba(239, 68, 68, 0.25)", "#f87171", "rgba(239, 68, 68, 0.4)"),
        "REPHRASE": ("🔄 Scaffolding & Rephrase", "rgba(244, 63, 94, 0.25)", "#fb7185", "rgba(244, 63, 94, 0.4)"),
        "MOVE_ON": ("➡️ Next Step", "rgba(100, 116, 139, 0.25)", "#cbd5e1", "rgba(100, 116, 139, 0.4)"),
        "FINAL_QUESTION": ("🏁 Final Wrap-Up", "rgba(236, 72, 153, 0.25)", "#f472b6", "rgba(236, 72, 153, 0.4)"),
    }
    label, bg, color, border = action_map.get(
        action_val,
        ("🎯 Adaptive Step", "rgba(59, 130, 246, 0.25)", "#60a5fa", "rgba(59, 130, 246, 0.4)")
    )
    return f"""<span style="background: {bg}; color: {color}; border: 1px solid {border}; padding: 0.25rem 0.65rem; border-radius: 6px; font-size: 0.82rem; font-weight: 600; margin-right: 0.35rem;">
{label}
</span>"""


def render_interview_page() -> None:
    """Render the active interview session console."""
    engine: InterviewEngine = st.session_state.get("engine")

    if not engine or not engine.config or not engine.current_question:
        st.warning("No active interview session found. Please configure an interview first.")
        if st.button("Go to Setup"):
            st.session_state.page = "setup"
            st.rerun()
        return

    config = engine.config
    current_q = engine.current_question
    q_num = engine.current_question_number
    total_q = config.num_questions
    has_submitted = st.session_state.get("submitted_current", False)
    state = engine.state
    decision = getattr(engine, "current_decision", None)

    # Session Header
    st.markdown(
        f"""<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.5rem;">
<div>
<h3 style="margin: 0; font-size: 1.4rem; color: #f8fafc;">💬 Live Interview Session</h3>
<span style="color: #94a3b8; font-size: 0.9rem;">
Candidate: <b style="color: #f8fafc;">{config.candidate_name}</b> | Role: <b style="color: #f8fafc;">{config.role}</b>
</span>
</div>
<div>
<span style="background: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.85rem; font-weight: 600; margin-right: 0.4rem;">
🎭 {config.interviewer_persona.value}
</span>
<span style="background: rgba(3, 105, 161, 0.25); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.85rem; font-weight: 600; margin-right: 0.4rem;">
{config.interview_type.value}
</span>
<span style="background: rgba(100, 116, 139, 0.25); color: #cbd5e1; border: 1px solid rgba(203, 213, 225, 0.2); padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.85rem; font-weight: 600;">
{config.difficulty.value}
</span>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    # Progress Indicator
    progress_val = engine.get_progress_percentage()
    st.progress(progress_val, text=f"Progress: Question {q_num} of {total_q} ({int(progress_val * 100)}% completed)")

    # Adaptive Topic Status Bar (Phase 5)
    if state and (state.topics_covered or state.topics_remaining):
        covered_str = ", ".join(state.topics_covered) if state.topics_covered else "None yet"
        rem_str = ", ".join(state.topics_remaining) if state.topics_remaining else "All addressed"
        st.markdown(
            f"""<div style="font-size: 0.82rem; color: #94a3b8; background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 6px; padding: 0.35rem 0.75rem; margin-top: -0.5rem; margin-bottom: 0.85rem;">
🗺️ <b>Topic Tracking:</b> Covered: <span style="color: #34d399;">{covered_str}</span> | Remaining: <span style="color: #cbd5e1;">{rem_str}</span>
</div>""",
            unsafe_allow_html=True,
        )

    # Question Display Card
    topic_display = current_q.topic if hasattr(current_q, "topic") and current_q.topic else current_q.category
    type_display = current_q.question_type.value if hasattr(current_q, "question_type") and hasattr(current_q.question_type, "value") else "Technical"
    q_text_display = current_q.text or current_q.question_text
    decision_badge_html = _render_decision_badge(decision)

    follow_up_banner = ""
    if getattr(current_q, "is_follow_up", False) or getattr(current_q, "anchor_reference", None):
        ft_label = current_q.follow_up_type.value if getattr(current_q, "follow_up_type", None) and hasattr(current_q.follow_up_type, "value") else "Contextual Follow-Up"
        anchor_txt = getattr(current_q, "anchor_reference", "")
        follow_up_banner = f"""<div style="font-size: 0.83rem; color: #38bdf8; background: rgba(56, 189, 248, 0.12); border-left: 3px solid #38bdf8; padding: 0.35rem 0.75rem; border-radius: 4px; margin-bottom: 0.75rem;">
🔗 <b>{ft_label}:</b> Grounded on your mention of <i>"{anchor_txt}"</i>
</div>"""

    st.markdown(
        f"""<div style="background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(59, 130, 246, 0.4); border-left: 5px solid #3b82f6; border-radius: 10px; padding: 1.35rem 1.6rem; margin-bottom: 1.25rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem; flex-wrap: wrap; gap: 0.4rem;">
<span style="font-weight: 700; color: #60a5fa; font-size: 1rem; text-transform: uppercase; letter-spacing: 0.05em;">
Question {q_num}
</span>
<div>
{decision_badge_html}
<span style="background: rgba(14, 165, 233, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.82rem; font-weight: 600; margin-right: 0.3rem;">
🎯 {type_display}
</span>
<span style="background: rgba(139, 92, 246, 0.25); color: #c4b5fd; border: 1px solid rgba(196, 181, 253, 0.3); padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.82rem; font-weight: 600;">
🏷️ {topic_display}
</span>
</div>
</div>
{follow_up_banner}
<div style="font-size: 1.15rem; font-weight: 500; color: #f8fafc; line-height: 1.6;">
{q_text_display}
</div>
</div>""",
        unsafe_allow_html=True,
    )

    # Answer Input Section
    input_key = f"answer_input_q_{q_num}"
    if not has_submitted:
        answer_text = st.text_area(
            "Your Written Response:",
            key=input_key,
            height=180,
            placeholder="Type your structured answer here (thought process, architectural reasoning, or STAR framework)...",
            help="Be thorough and specific. AI evaluation will assess against calibrated rubrics and extract grounding quotes.",
        )

        # Word counter
        words = len(answer_text.strip().split()) if answer_text.strip() else 0
        st.caption(f"Word count: {words} words | Characters: {len(answer_text)}")

        btn_col1, btn_col2, btn_col3 = st.columns([2, 1, 1])
        with btn_col1:
            if st.button("📤 Submit Answer", type="primary", use_container_width=True):
                if not answer_text.strip():
                    st.error("Please provide your answer before submitting.")
                else:
                    with st.spinner("Analyzing and evaluating your response with AI..."):
                        evaluation = engine.submit_answer(answer_text)
                        st.session_state.submitted_current = True
                        st.session_state.latest_evaluation = evaluation
                        st.rerun()

        with btn_col3:
            if st.button("⏹️ Conclude Early", use_container_width=True, help="Conclude early and view results"):
                with st.spinner("Compiling final assessment report..."):
                    result = engine.finish_interview()
                    st.session_state.result = result
                    st.session_state.page = "results"
                    st.rerun()

    else:
        # Candidate has submitted current answer — show evaluation preview & next action
        evaluation = st.session_state.get("latest_evaluation") or engine.current_evaluation

        if evaluation:
            # Score badge color
            score = evaluation.score
            score_color = "#22c55e" if score >= 7.0 else ("#f59e0b" if score >= 5.0 else "#ef4444")

            st.markdown(
                f"""<div style="background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px; padding: 1.35rem; margin-bottom: 1.5rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);">
<div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 0.75rem; margin-bottom: 0.75rem;">
<span style="font-weight: 700; font-size: 1.15rem; color: #f8fafc;">📋 Question {q_num} Evaluation</span>
<span style="font-size: 1.25rem; font-weight: 800; color: {score_color}; background: rgba(0,0,0,0.3); padding: 0.25rem 0.85rem; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.1);">
Score: {score:.1f} / 10
</span>
</div>""",
                unsafe_allow_html=True,
            )

            # Type-Specific Rubric Criteria Breakdown
            if evaluation.criteria_scores:
                crit_cols = st.columns(len(evaluation.criteria_scores))
                for idx, c in enumerate(evaluation.criteria_scores):
                    with crit_cols[idx]:
                        st.metric(c.name, f"{c.score:.1f}/10")
            else:
                m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
                metrics = evaluation.metrics
                with m_col1:
                    st.metric("Relevance", f"{metrics.relevance}/10")
                with m_col2:
                    st.metric("Correctness", f"{metrics.correctness}/10")
                with m_col3:
                    st.metric("Completeness", f"{metrics.completeness}/10")
                with m_col4:
                    st.metric("Clarity", f"{metrics.clarity}/10")
                with m_col5:
                    st.metric("Depth", f"{metrics.depth}/10")

            # Grounded Evidence Quotes
            if evaluation.evidence:
                with st.expander("🔍 Grounding Evidence from Your Response", expanded=False):
                    for ev in evaluation.evidence:
                        icon = "🟢" if ev.is_positive else "🔴"
                        st.markdown(f"{icon} **[{ev.criterion_name}]** *\"{ev.quote_or_reference}\"* — {ev.assessment}")

            # Strengths & Weaknesses
            feed_col1, feed_col2 = st.columns(2)
            with feed_col1:
                st.markdown("**✅ Strengths Identified:**")
                if evaluation.strengths:
                    for s in evaluation.strengths:
                        st.markdown(f"- {s}")
                else:
                    st.markdown("- *No notable strengths captured.*")

            with feed_col2:
                st.markdown("**⚠️ Areas for Improvement:**")
                if evaluation.weaknesses:
                    for w in evaluation.weaknesses:
                        st.markdown(f"- {w}")
                else:
                    st.markdown("- *None flagged.*")

            # Feedback & Suggested Improvement
            st.markdown(f"**💬 Detailed Feedback:**\n\n{evaluation.feedback}")
            st.info(f"💡 **Suggested Model Approach / Improvement:**\n\n{evaluation.suggested_improvement}")
            
            # Pedagogical Disclaimer
            st.caption(f"ℹ️ *{evaluation.assessment_disclaimer}*")
            st.markdown("</div>", unsafe_allow_html=True)

        # Navigation Controls after evaluation
        st.markdown("<br>", unsafe_allow_html=True)
        nav_col1, nav_col2 = st.columns([3, 1])

        with nav_col1:
            if engine.has_more_questions:
                if st.button("➡️ Next Question", type="primary", use_container_width=True):
                    with st.spinner("Generating next interview question..."):
                        next_q = engine.generate_next_question()
                        st.session_state.current_question = next_q
                        st.session_state.submitted_current = False
                        st.session_state.latest_evaluation = None
                        st.rerun()
            else:
                if st.button("🏁 View Final Assessment", type="primary", use_container_width=True):
                    with st.spinner("Synthesizing comprehensive interview report..."):
                        result = engine.finish_interview()
                        st.session_state.result = result
                        st.session_state.page = "results"
                        st.rerun()

        with nav_col2:
            if st.button("⏹️ Conclude Now", use_container_width=True):
                with st.spinner("Compiling final assessment report..."):
                    result = engine.finish_interview()
                    st.session_state.result = result
                    st.session_state.page = "results"
                    st.rerun()
