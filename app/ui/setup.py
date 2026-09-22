"""
Setup Page UI Component.
Phase 2: Advanced Interview Configuration Console.
Presents 10 configuration sections, topic matrix, persona guidance,
and pre-flight interview summary preview.
"""

import streamlit as st
from app.schemas.interview import (
    InterviewConfig,
    InterviewType,
    ExperienceLevel,
    Difficulty,
    InterviewMode,
    InterviewerPersona,
)
from app.services.config_service import get_config_service
from app.core.interviewer import InterviewEngine
from app.ai.factory import create_llm_service, set_global_llm_service
from app.config.settings import get_settings


def render_setup_page() -> None:
    """Render the Advanced Interview Configuration page."""
    settings = get_settings()
    config_service = get_config_service()

    st.markdown(
        """
        <div style="margin-bottom: 1.5rem;">
            <h2 style="margin-bottom: 0.2rem; color: #f8fafc;">⚙️ Advanced Interview Configuration</h2>
            <p style="color: #94a3b8; font-size: 0.95rem;">
                Configure every dimension of the interview engine: topics matrix, persona tone, adaptive difficulty, and session timing.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------
    # 1. Candidate Profile & Role
    # -------------------------------------------------------------
    st.markdown("#### 👤 1. Candidate Profile")
    col_c1, col_c2, col_c3 = st.columns([2, 2, 1.5])

    with col_c1:
        candidate_name = st.text_input(
            "Candidate Full Name *",
            value=st.session_state.get("setup_candidate_name", "Alex Developer"),
            placeholder="e.g., Sarah Chen",
            help="Name used for personalization and historical records.",
        )

    with col_c2:
        role = st.text_input(
            "Target Role / Position",
            value=st.session_state.get("setup_role", "Senior Python Engineer"),
            placeholder="e.g., Full Stack Engineer, ML Engineer, Backend Lead",
            help="Specific job title the interview will calibrate toward.",
        )

    with col_c3:
        experience_options = [e.value for e in ExperienceLevel]
        selected_exp = st.selectbox(
            "Experience Tier",
            options=experience_options,
            index=experience_options.index(ExperienceLevel.TWO_TO_FIVE.value),
            help="Calibrates base technical depth.",
        )

    st.markdown("---")

    # -------------------------------------------------------------
    # 2. Interview Structure & Delivery Mode
    # -------------------------------------------------------------
    st.markdown("#### 🎯 2. Interview Structure & Delivery Mode")
    col_s1, col_s2, col_s3 = st.columns(3)

    with col_s1:
        type_options = [t.value for t in InterviewType]
        selected_type = st.selectbox(
            "Interview Category",
            options=type_options,
            index=type_options.index(InterviewType.TECHNICAL.value),
            help="Select the overall interview focus.",
        )

    with col_s2:
        difficulty_options = [d.value for d in Difficulty]
        selected_diff = st.selectbox(
            "Difficulty Mode",
            options=difficulty_options,
            index=difficulty_options.index(Difficulty.ADAPTIVE.value),
            help="Adaptive dynamically adjusts difficulty question-by-question based on your score!",
        )

    with col_s3:
        modes_dict = config_service.get_supported_modes()
        mode_labels = [
            f"{m.value} {'✅ (Active)' if active else '🔒 (Phase 3+)'}"
            for m, active in modes_dict.items()
        ]
        selected_mode_label = st.selectbox(
            "Delivery Mode",
            options=mode_labels,
            index=0,
            help="TEXT is currently active. Voice, Video, Coding, and SQL modes are prepared for upcoming phases.",
        )
        # Parse selected mode enum
        selected_mode_str = selected_mode_label.split(" ")[0]
        selected_mode = InterviewMode(selected_mode_str)

    st.markdown("---")

    # -------------------------------------------------------------
    # 3. Focus Topics Matrix
    # -------------------------------------------------------------
    st.markdown("#### 🛠️ 3. Focus Topics Matrix")
    st.caption("Select technical or behavioral topics. Questions will be systematically generated across these areas.")

    all_catalog_topics = config_service.get_all_topics()
    default_topics = ["Python", "Data Structures", "APIs", "System Design", "Databases"]

    selected_topics = st.multiselect(
        "Select Topics (or type custom topics below)",
        options=all_catalog_topics,
        default=[t for t in default_topics if t in all_catalog_topics],
        help="Choose one or more topics from our extensible catalog.",
    )

    custom_topics_input = st.text_input(
        "Add Custom Topics (Comma-separated)",
        placeholder="e.g., PyTorch, Redis, Kubernetes, GraphQL, Payment Systems",
        help="Enter any niche or custom frameworks to include.",
    )

    # Merge topics
    final_topics = list(selected_topics)
    if custom_topics_input.strip():
        for ct in custom_topics_input.split(","):
            clean_t = ct.strip()
            if clean_t and clean_t not in final_topics:
                final_topics.append(clean_t)

    st.markdown("---")

    # -------------------------------------------------------------
    # 4. Sizing & Duration
    # -------------------------------------------------------------
    st.markdown("#### ⏱️ 4. Sizing & Session Timing")
    col_t1, col_t2 = st.columns(2)

    with col_t1:
        num_questions = st.slider(
            "Total Number of Questions",
            min_value=1,
            max_value=15,
            value=5,
            help="Standard full interview: 5 questions. Quick screening: 3 questions.",
        )

    # Compute recommended duration automatically
    chosen_diff_enum = Difficulty(selected_diff)
    recommended_duration = config_service.calculate_recommended_duration(num_questions, chosen_diff_enum)

    with col_t2:
        estimated_duration = st.number_input(
            f"Estimated Duration (Minutes) — Recommended: {recommended_duration}m",
            min_value=5,
            max_value=180,
            value=recommended_duration,
            step=5,
            help="Paces interview timing and session estimation.",
        )

    st.markdown("---")

    # -------------------------------------------------------------
    # 5. Interviewer Persona & Language
    # -------------------------------------------------------------
    st.markdown("#### 🎭 5. Interviewer Persona & Language")
    col_p1, col_p2 = st.columns(2)

    personas_dict = config_service.get_personas()
    persona_options = [p.value for p in personas_dict.keys()]

    with col_p1:
        selected_persona_str = st.selectbox(
            "Interviewer Persona & Coaching Tone",
            options=persona_options,
            index=persona_options.index(InterviewerPersona.PROFESSIONAL.value),
            help="Controls AI evaluation strictness, interview tone, and communication style.",
        )
        selected_persona = InterviewerPersona(selected_persona_str)

        # Show persona description card
        st.info(f"💡 **Tone Style:** {personas_dict[selected_persona]}")

    with col_p2:
        supported_langs = config_service.get_supported_languages()
        selected_lang = st.selectbox(
            "Interview Language",
            options=supported_langs,
            index=0,
            help="Language in which questions, answers, and feedback are conducted.",
        )

    st.markdown("---")

    # -------------------------------------------------------------
    # 6. AI Provider & Inference Engine
    # -------------------------------------------------------------
    st.markdown("#### ⚡ 6. AI Engine Configuration")
    prov_col1, prov_col2 = st.columns(2)

    with prov_col1:
        provider_display_map = {
            "Google Gemini API (Cloud)": "gemini",
            "NVIDIA Nemotron NIM (Cloud)": "nvidia",
            "Local Ollama (Offline / Local)": "ollama",
            "Offline Simulator (No API Key Required)": "mock",
        }
        provider_labels = list(provider_display_map.keys())

        default_prov_idx = 0
        if settings.llm_provider == "nvidia":
            default_prov_idx = 1
        elif settings.llm_provider == "ollama":
            default_prov_idx = 2
        elif settings.llm_provider == "mock":
            default_prov_idx = 3

        selected_provider_label = st.selectbox(
            "AI Provider",
            options=provider_labels,
            index=default_prov_idx,
        )
        selected_provider_key = provider_display_map[selected_provider_label]

    with prov_col2:
        if selected_provider_key == "gemini":
            model_choices = ["gemini-3.6-flash", "gemini-2.5-pro", "gemini-flash-latest"]
            selected_model = st.selectbox("Gemini Model", options=model_choices, index=0)
        elif selected_provider_key == "nvidia":
            model_choices = [
                "nvidia/llama-3.1-nemotron-70b-instruct",
                "nvidia/nemotron-4-340b-instruct",
                "nvidia/nemotron-3-ultra-550b-a55b",
                "meta/llama-3.1-70b-instruct",
            ]
            selected_model = st.selectbox("Nemotron Model", options=model_choices, index=0)
        elif selected_provider_key == "ollama":
            model_choices = [
                settings.ollama_model,
                "nemotron-3-ultra-550b-a55b",
                "qwen2.5:7b",
                "nemotron-mini:latest",
            ]
            selected_model = st.selectbox("Ollama Model", options=list(dict.fromkeys(model_choices)), index=0)
        else:
            selected_model = "mock-simulator-v1"
            st.text_input("Model", value="Simulation Engine", disabled=True)

    # API key input if needed
    api_key_input = ""
    if selected_provider_key == "gemini":
        api_key_input = st.text_input(
            "Google Gemini API Key (leave blank to use .env key)",
            value=settings.gemini_api_key or "",
            type="password",
            placeholder="AIzaSy...",
        )
    elif selected_provider_key == "nvidia":
        api_key_input = st.text_input(
            "NVIDIA API Key (leave blank to use .env key)",
            value=settings.nvidia_api_key or "",
            type="password",
            placeholder="nvapi-...",
        )

    st.markdown("---")

    # -------------------------------------------------------------
    # 7. Pre-Flight Summary Preview Card
    # -------------------------------------------------------------
    st.markdown("#### 📋 7. Pre-Flight Interview Summary")

    summary_topics_str = ", ".join(final_topics) if final_topics else (role or "Software Engineering")
    diff_badge_color = "#3b82f6" if selected_diff == "Adaptive" else ("#22c55e" if selected_diff == "Easy" else "#f59e0b")

    st.markdown(
        f"""
        <div style="background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px; padding: 1.35rem; margin-bottom: 1.5rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                <div>
                    <span style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">Candidate</span>
                    <div style="font-size: 1.1rem; font-weight: 700; color: #f8fafc;">{candidate_name or "Not Specified"}</div>
                </div>
                <div>
                    <span style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">Role</span>
                    <div style="font-size: 1.1rem; font-weight: 700; color: #f8fafc;">{role or "Software Engineer"}</div>
                </div>
                <div>
                    <span style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">Experience Tier</span>
                    <div style="font-size: 1.1rem; font-weight: 700; color: #f8fafc;">{selected_exp}</div>
                </div>
                <div>
                    <span style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">Category & Mode</span>
                    <div style="font-size: 1.1rem; font-weight: 700; color: #38bdf8;">{selected_type} ({selected_mode.value})</div>
                </div>
                <div>
                    <span style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">Difficulty</span>
                    <div style="font-size: 1.1rem; font-weight: 700; color: {diff_badge_color};">{selected_diff}</div>
                </div>
                <div>
                    <span style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">Length & Timing</span>
                    <div style="font-size: 1.1rem; font-weight: 700; color: #f8fafc;">{num_questions} Questions (~{estimated_duration} mins)</div>
                </div>
                <div>
                    <span style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">Persona & Tone</span>
                    <div style="font-size: 1.1rem; font-weight: 700; color: #c4b5fd;">{selected_persona_str}</div>
                </div>
                <div>
                    <span style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">Language</span>
                    <div style="font-size: 1.1rem; font-weight: 700; color: #f8fafc;">{selected_lang}</div>
                </div>
            </div>
            <hr style="border: none; border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 1rem 0;">
            <div>
                <span style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">Focus Topics Matrix:</span>
                <div style="font-size: 0.95rem; color: #cbd5e1; margin-top: 0.25rem; line-height: 1.4;">
                    <b>{summary_topics_str}</b>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------
    # Launch Actions & Submission
    # -------------------------------------------------------------
    col_btn1, col_btn2, col_back = st.columns([2, 1, 1])

    with col_btn1:
        if st.button("🚀 Launch Customized Interview", type="primary", use_container_width=True):
            if not candidate_name.strip():
                st.error("Please enter a valid candidate name.")
                return

            if selected_mode != InterviewMode.TEXT:
                st.error(f"{selected_mode.value} mode is scheduled for a future phase. Please select TEXT mode to run.")
                return

            try:
                # Build InterviewConfig using Pydantic validation
                config_data = {
                    "candidate_name": candidate_name.strip(),
                    "role": role.strip() if role.strip() else "Software Engineer",
                    "experience_level": selected_exp,
                    "interview_type": selected_type,
                    "difficulty": selected_diff,
                    "num_questions": num_questions,
                    "estimated_duration_minutes": int(estimated_duration),
                    "language": selected_lang,
                    "interviewer_persona": selected_persona_str,
                    "topics": final_topics,
                    "mode": selected_mode.value,
                }

                config = config_service.validate_and_build(config_data)

                # Store defaults for next session
                st.session_state["setup_candidate_name"] = candidate_name
                st.session_state["setup_role"] = role

                # Initialize AI Provider
                active_api_key = api_key_input.strip() if api_key_input.strip() else None
                llm_service = create_llm_service(
                    provider=selected_provider_key,
                    api_key=active_api_key,
                    model=selected_model,
                )

                # Pre-flight health check
                is_healthy, msg = llm_service.health_check()
                if not is_healthy and selected_provider_key != "mock":
                    st.error(f"Cannot connect to {selected_provider_label}: {msg}")
                    return

                set_global_llm_service(llm_service)

                # Initialize and start interview engine
                with st.spinner("Initializing advanced interview session and generating first question..."):
                    engine = InterviewEngine(llm_service=llm_service)
                    first_question = engine.start_interview(config)

                    st.session_state.engine = engine
                    st.session_state.current_question = first_question
                    st.session_state.submitted_current = False
                    st.session_state.page = "interview"
                    st.rerun()

            except Exception as e:
                st.error(f"Configuration Validation Error: {str(e)}")

    with col_back:
        if st.button("⬅️ Home", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()
