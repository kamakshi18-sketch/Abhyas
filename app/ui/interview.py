"""
Interview Session UI Component.
Phase 4: Luxury Aurora Interview Console.
Renders central animated voice orb, hero question typography, floating glassmorphic
answer controls, live persona HUD, and grounded rubric evaluation scorecard.
"""

import streamlit as st
from app.core.interviewer import InterviewEngine


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

    # Top Status Bar & Tags
    type_display = current_q.question_type.value if hasattr(current_q, "question_type") and hasattr(current_q.question_type, "value") else config.interview_type.value
    topic_display = current_q.topic if hasattr(current_q, "topic") and current_q.topic else (current_q.category or "General")
    q_text_display = current_q.text or current_q.question_text

    # 2-Column Luxury Layout: Main Stage (left) & Live HUD (right)
    col_stage, col_hud = st.columns([2.0, 1.0], gap="large")

    with col_stage:
        # Top Stage Header
        st.markdown(
            f"""
            <div style="text-align: center; padding: 0.5rem 0 1rem 0;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #64748b; letter-spacing: 0.2em; text-transform: uppercase; margin-bottom: 0.75rem;">
                    QUESTION {q_num:02d} / {total_q:02d}
                </div>
                <h2 style="font-size: 1.85rem; font-weight: 600; color: #ffffff; line-height: 1.45; max-width: 780px; margin: 0 auto; letter-spacing: -0.01em;">
                    "{q_text_display}"
                </h2>
                <div style="margin-top: 1.1rem; display: flex; justify-content: center; gap: 0.6rem; flex-wrap: wrap;">
                    <span class="badge-pill badge-pill-cyan">
                        <span class="status-dot"></span> The AI is listening...
                    </span>
                    <span class="badge-pill">
                        🎯 {type_display}
                    </span>
                    <span class="badge-pill">
                        🏷️ {topic_display}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Central Glowing Aurora Orb & Waveform
        st.markdown(
            """
            <div class="orb-wrapper">
                <div class="orb-halo"></div>
                <div class="orb-halo-outer"></div>
                <div class="orb-sphere">
                    <div class="soundwave">
                        <div class="soundwave-bar"></div>
                        <div class="soundwave-bar"></div>
                        <div class="soundwave-bar"></div>
                        <div class="soundwave-bar"></div>
                        <div class="soundwave-bar"></div>
                    </div>
                </div>
            </div>
            <div style="text-align: center; margin-bottom: 1.25rem;">
                <div style="font-size: 1rem; font-weight: 600; color: #f1f5f9; letter-spacing: -0.01em;">Speak naturally or type your response</div>
                <div style="font-size: 0.8rem; color: #64748b; margin-top: 0.25rem;">Your response helps Abhyas evaluate conceptual depth, structure & reasoning</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Q&A Input Console & Controls
        input_key = f"answer_input_q_{q_num}"

        if not has_submitted:
            answer_text = st.text_area(
                "Candidate Response:",
                key=input_key,
                height=150,
                placeholder="Type your response here. Articulate your architecture, thought process, or structured STAR response...",
                label_visibility="collapsed",
            )

            # Word counter & controls
            words = len(answer_text.strip().split()) if answer_text.strip() else 0
            
            # Bottom Glassmorphic Action Bar
            st.markdown(
                f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.25rem; margin-bottom: 0.75rem; font-size: 0.78rem; color: #64748b;">
                    <span>📝 Response length: <b style="color: #cbd5e1;">{words} words</b> ({len(answer_text)} chars)</span>
                    <span style="color: #38bdf8;">Press Submit when ready</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1, 2, 1])

            with ctrl_col1:
                if st.button("✕ Reset", use_container_width=True, help="Clear current input"):
                    st.session_state[input_key] = ""
                    st.rerun()

            with ctrl_col2:
                if st.button("🎙️ Submit Answer", type="primary", use_container_width=True):
                    if not answer_text.strip():
                        st.error("Please provide your answer before submitting.")
                    else:
                        with st.spinner("Analyzing and evaluating your response with AI..."):
                            evaluation = engine.submit_answer(answer_text)
                            st.session_state.submitted_current = True
                            st.session_state.latest_evaluation = evaluation
                            st.rerun()

            with ctrl_col3:
                if st.button("⏹️ Conclude", use_container_width=True, help="End session early and view report"):
                    with st.spinner("Compiling final assessment report..."):
                        result = engine.finish_interview()
                        st.session_state.result = result
                        st.session_state.page = "results"
                        st.rerun()

            # Floating Bottom Status Pills
            st.markdown(
                """
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1.5rem; flex-wrap: wrap; gap: 0.5rem;">
                    <div class="badge-pill" style="font-size: 0.75rem; color: #94a3b8;">
                        <span>〰️ Live Analysis</span>
                        <span style="color: #64748b;">• Available after submission</span>
                    </div>
                    <div class="badge-pill badge-pill-cyan" style="font-size: 0.75rem;">
                        <span>🔆 AI Engine Active</span>
                        <span class="status-dot"></span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        else:
            # Candidate has submitted current answer — show evaluation preview & next action
            evaluation = st.session_state.get("latest_evaluation") or engine.current_evaluation

            if evaluation:
                score = evaluation.score
                score_color = "#22c55e" if score >= 7.0 else ("#f59e0b" if score >= 5.0 else "#ef4444")

                st.markdown(
                    f"""
                    <div class="glass-panel" style="padding: 1.4rem; margin-top: 1rem; border-color: rgba(56, 189, 248, 0.3) !important;">
                        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 0.75rem; margin-bottom: 1rem;">
                            <div>
                                <span style="font-weight: 700; font-size: 1.15rem; color: #f8fafc;">📋 Assessment for Question {q_num}</span>
                                <div style="font-size: 0.78rem; color: #94a3b8; margin-top: 0.2rem;">Rubric-grounded pedagogical feedback</div>
                            </div>
                            <div style="font-size: 1.35rem; font-weight: 800; color: {score_color}; background: rgba(0,0,0,0.4); padding: 0.3rem 1rem; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.1);">
                                {score:.1f} <span style="font-size: 0.85rem; color: #94a3b8;">/ 10</span>
                            </div>
                        </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Criteria Scores
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

                # Detailed Feedback & Suggested Model Approach
                st.markdown(f"**💬 Detailed Feedback:**\n\n{evaluation.feedback}")
                st.info(f"💡 **Suggested Model Approach / Key Points:**\n\n{evaluation.suggested_improvement}")
                st.caption(f"ℹ️ *{evaluation.assessment_disclaimer}*")
                st.markdown("</div>", unsafe_allow_html=True)

            # Navigation Controls after evaluation
            st.markdown("<br>", unsafe_allow_html=True)
            nav_col1, nav_col2 = st.columns([3, 1])

            with nav_col1:
                if engine.has_more_questions:
                    if st.button("➡️ Next Question", type="primary", use_container_width=True):
                        with st.spinner("Generating next calibrated question..."):
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

    # -----------------------------------------------------------------
    # Right-Hand HUD: Persona & Progress Stepper
    # -----------------------------------------------------------------
    with col_hud:
        persona_name = config.interviewer_persona if hasattr(config, "interviewer_persona") and config.interviewer_persona else "The Architect"
        
        # Persona Card
        st.markdown(
            f"""
            <div class="glass-panel" style="padding: 1.25rem; margin-bottom: 1.25rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.9rem;">
                    <span class="badge-pill badge-pill-cyan" style="font-size: 0.75rem;">
                        🎙️ {config.interview_type.value}
                    </span>
                    <span style="font-size: 0.72rem; color: #64748b;">Active AI</span>
                </div>
                
                <div style="display: flex; flex-direction: column; align-items: center; text-align: center; padding: 0.5rem 0;">
                    <div style="width: 72px; height: 72px; border-radius: 50%; background: radial-gradient(circle at 35% 30%, #38bdf8 0%, #3b82f6 40%, #8b5cf6 75%, #1e1b4b 100%); box-shadow: 0 0 25px rgba(56, 189, 248, 0.4); margin-bottom: 0.75rem; border: 1px solid rgba(255,255,255,0.2);"></div>
                    <div style="font-size: 0.72rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em;">Your AI Interviewer</div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #ffffff; margin-top: 0.15rem;">{persona_name}</div>
                    <div style="font-size: 0.75rem; color: #38bdf8; margin-top: 0.2rem;">Analytical • Focused • Supportive</div>
                </div>

                <div style="background: rgba(22, 23, 30, 0.8); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 0.75rem 0.9rem; margin-top: 0.9rem; display: flex; gap: 0.6rem; align-items: flex-start;">
                    <span style="font-size: 1.1rem; line-height: 1;">💬</span>
                    <div style="font-size: 0.78rem; color: #cbd5e1; line-height: 1.45;">
                        <i>"Take your time. I'm listening closely to your reasoning, structure, and approach."</i>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Progress Stepper Card
        progress_pct = int(engine.get_progress_percentage() * 100)
        st.markdown(
            f"""
            <div class="glass-panel" style="padding: 1.25rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem;">
                    <span style="font-size: 0.85rem; font-weight: 700; color: #ffffff;">Interview Progress</span>
                    <span style="font-size: 0.85rem; font-weight: 700; color: #38bdf8;">{q_num} / {total_q}</span>
                </div>
            """,
            unsafe_allow_html=True,
        )

        st.progress(engine.get_progress_percentage())

        # Dynamic Stage Steps
        steps = [
            ("Core Technical & Fundamentals", 1),
            ("Architecture & System Design", 2),
            ("Problem Solving & Execution", 3),
            ("Behavioral & Collaboration", 4),
            ("Advanced Deep-Dive & Wrap-Up", 5),
        ]

        st.markdown("<div style='margin-top: 1rem; display: flex; flex-direction: column; gap: 0.65rem;'>", unsafe_allow_html=True)
        for label, step_idx in steps:
            if q_num > step_idx:
                status_icon = "<span style='color: #22c55e; font-size: 0.85rem;'>●</span>"
                text_style = "color: #94a3b8; font-size: 0.8rem; text-decoration: line-through;"
            elif q_num == step_idx:
                status_icon = "<span class='status-dot'></span>"
                text_style = "color: #38bdf8; font-size: 0.82rem; font-weight: 700;"
            else:
                status_icon = "<span style='color: #475569; font-size: 0.85rem;'>○</span>"
                text_style = "color: #64748b; font-size: 0.8rem;"

            st.markdown(
                f"""
                <div style="display: flex; align-items: center; gap: 0.6rem;">
                    {status_icon}
                    <span style="{text_style}">{label}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.06); margin: 1rem 0;'>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="font-size: 0.74rem; color: #64748b; line-height: 1.5;">
                <div><b>Candidate:</b> <span style="color: #cbd5e1;">{config.candidate_name}</span></div>
                <div><b>Role:</b> <span style="color: #cbd5e1;">{config.role}</span></div>
                <div><b>Difficulty:</b> <span style="color: #38bdf8;">{config.difficulty.value}</span></div>
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

