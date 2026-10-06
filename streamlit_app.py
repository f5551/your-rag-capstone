"""QISO entry point: UI orchestration and the existing core.generator adapter.

Launch with Streamlit. This file has no CLI parser and does not re-index data.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import streamlit as st

st.set_page_config(
    page_title="QISO | Quality Intelligence",
    page_icon=":material/fact_check:",
    layout="wide",
    # Explicit on first load; users can still collapse/reopen the native panel.
    initial_sidebar_state="expanded",
)

from ui.components import (
    render_answer, render_error, render_examples, render_history_page,
    render_question_box, render_settings, render_sources_page,
)
from ui.helpers import (
    display_error, initialize_state, language, store_result, text_direction, tr,
)
from ui.layout import render_footer, render_header, render_welcome, workspace
from ui.sidebar import render_sidebar
from ui.styles import apply_styles

logger = logging.getLogger("qiso.ui")


def request_answer(question: str) -> dict[str, Any]:
    """The only boundary between presentation and the user's existing RAG."""
    # Lazy import: the welcome page opens without creating clients or calling APIs.
    from core.generator import Generator, answer_question

    # One engine per browser session, not a mutable engine shared between users.
    if "qiso_engine" not in st.session_state:
        st.session_state.qiso_engine = Generator()
    return answer_question(
        question=question,
        top_k=st.session_state.qiso_top_k,
        candidate_k=st.session_state.qiso_candidate_k,
        generator=st.session_state.qiso_engine,
    )


def render_assistant() -> None:
    # Consume the request BEFORE calling the provider: ordinary reruns cannot
    # accidentally replay the previous question and charge another API call.
    pending = st.session_state.pop("qiso_pending", None)
    if pending:
        st.session_state.qiso_busy = True
        try:
            with st.spinner(tr("working"), show_time=True):
                st.caption(tr("working_hint"))
                result = request_answer(pending)
                store_result(pending, result)
        except Exception as error:
            st.session_state.qiso_error = display_error(error)
            st.session_state.qiso_busy = False
            # No raw exception message: it can contain credentials/provider data.
            logger.error("QISO request failed (%s)", type(error).__name__)
        finally:
            st.session_state.qiso_busy = False
        st.rerun()

    record = st.session_state.qiso_current
    if record is None:
        render_welcome()
    else:
        render_answer(record)
    render_error()
    render_question_box()
    if record is None:
        render_examples()


def render_app() -> None:
    match = re.match(r"(\d+)\.(\d+)", st.__version__)
    if match and tuple(map(int, match.groups())) < (1, 50):
        st.error("This UI requires Streamlit 1.50 or newer. See requirements-ui.txt.")
        st.stop()
    initialize_state()
    input_direction = text_direction(
        st.session_state.qiso_draft, fallback="rtl" if language() == "ar" else "ltr",
    )
    apply_styles(language(), input_direction)
    render_sidebar()
    with st.container(key="qiso_root"):
        render_header(st.session_state.qiso_page)
        with workspace():
            page = st.session_state.qiso_page
            if page == "assistant":
                render_assistant()
            elif page == "history":
                render_history_page()
            elif page == "sources":
                render_sources_page()
            else:
                render_settings()
            render_footer()


render_app()
