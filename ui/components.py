"""Reusable presentation components. No core imports or network requests."""

from __future__ import annotations

import re
from typing import Any

import streamlit as st

from .helpers import (
    EXAMPLES, clear_history, duration, fill_example, html_text, language,
    open_record, queue_question, remember_draft, reset_settings, save_settings,
    short_text, text_direction, tr,
)
from .layout import render_page_heading


def render_question_box() -> None:
    """Native textarea and callback-based submission inside a real container."""
    if "_qiso_question" not in st.session_state:
        st.session_state._qiso_question = st.session_state.qiso_draft
    with st.container(key="qiso_composer"):
        busy = bool(st.session_state.get("qiso_busy", False))
        st.text_area(
            tr("question"), placeholder=tr("placeholder"), height=115,
            key="_qiso_question", label_visibility="collapsed",
            on_change=remember_draft, max_chars=8000, disabled=busy,
        )
        note, action = st.columns([4, 1.25], vertical_alignment="center")
        with note:
            st.caption(tr("input_hint"))
        with action:
            st.button(
                tr("send"), icon=":material/send:", type="primary",
                key="qiso_send", on_click=queue_question, width="stretch",
                disabled=busy,
            )


def render_examples() -> None:
    """Clickable examples fill the input only; they do not call the model."""
    with st.container(key="qiso_examples"):
        st.subheader(tr("examples"), anchor=False)
        index = 0
        for row_size in (3, 2):
            for column in st.columns(row_size, gap="small"):
                arabic, english, icon = EXAMPLES[index]
                question = english if language() == "en" else arabic
                with column:
                    st.button(
                        question, icon=f":material/{icon}:",
                        key=f"qiso_example_{index}",
                        on_click=fill_example, args=(question,), width="stretch",
                    )
                index += 1
        # A single persistent hint replaces five overlapping hover tooltips.
        st.caption(tr("example_help"))


def render_markdown(text: str, context_key: str) -> None:
    """Render safe Markdown with an independent, stable direction/key."""
    direction = text_direction(text)
    with st.container(key=f"qiso_{direction}_{context_key}"):
        # Do not enable unsafe_allow_html for model output or document text.
        st.markdown(text, unsafe_allow_html=False)


def render_sources(sources: list[dict[str, Any]], *, context_key: str) -> None:
    """Preserve source numbering and duplicate-page chunks from the backend."""
    if not sources:
        st.info(tr("no_sources"))
        return
    for index, source in enumerate(sources):
        number = source.get("number", index + 1)
        filename = str(source.get("source") or "Unknown source")
        page = source.get("page", "?")
        title = f"[{number}] {short_text(filename, 84)} | {tr('page')} {page}"
        anchor = _citation_anchor(context_key, number)
        st.html(f'<span id="{anchor}" class="qiso-source-anchor" aria-hidden="true"></span>')
        with st.expander(title, expanded=False):
            source_direction = text_direction(filename)
            st.html(
                f'<div class="qiso-source-heading" dir="{source_direction}">' 
                f'{html_text(filename)}<small>{html_text(tr("page"))}: '
                f'<bdi>{html_text(page)}</bdi></small></div>'
            )
            passage = str(source.get("text") or "").strip()
            if passage:
                render_markdown(passage, f"source_{context_key}_{index}")
            else:
                st.caption(tr("passage_missing"))



def _citation_anchor(context_key: str, number: object) -> str:
    """Return a stable local anchor id for an answer source."""
    safe_context = re.sub(r"[^a-zA-Z0-9_-]", "-", str(context_key))
    safe_number = re.sub(r"[^0-9]", "", str(number)) or "0"
    return f"qiso-source-{safe_context}-{safe_number}"


def _link_answer_citations(
    text: str,
    sources: list[dict[str, Any]],
    context_key: str,
) -> str:
    """Link valid single and grouped citations to their source cards.

    Supported examples include ``[1]``, ``[1, 4]`` and ``[1,2,3]``.
    Each citation number becomes an independent local Markdown link.
    Existing Markdown links are left unchanged.
    """

    valid = {
        str(source.get("number", index + 1))
        for index, source in enumerate(sources)
    }

    def replace_group(match: re.Match[str]) -> str:
        raw_group = match.group(1)
        numbers = [
            part.strip()
            for part in raw_group.split(",")
        ]

        # Leave the original text untouched if any referenced source is invalid.
        if not numbers or any(number not in valid for number in numbers):
            return match.group(0)

        linked = []
        for number in numbers:
            anchor = _citation_anchor(
                context_key,
                number,
            )
            linked.append(
                f"[[{number}]](#{anchor})"
            )

        return " ".join(linked)

    # Match citation groups only when they are not already Markdown links.
    # Examples: [1], [1, 4], [1,2,3].
    return re.sub(
        r"\[((?:\d{1,3})(?:\s*,\s*\d{1,3})*)\](?!\()",
        replace_group,
        text,
    )

def render_answer(record: dict[str, Any]) -> None:
    """Stage 2.1 chat layout: user message + QISO answer + compact metadata."""
    question = str(record["question"])
    question_direction = text_direction(question)
    answer_text = str(record.get("answer") or "")
    sources = record.get("sources") or []

    with st.container(key="qiso_chat_thread"):
        # User turn
        with st.container(key="qiso_user_turn"):
            st.html(
                f'<div class="qiso-chat-role qiso-chat-role-user" dir="{question_direction}">'
                f'<span class="qiso-chat-avatar qiso-chat-avatar-user">U</span>'
                f'<span>{html_text(tr("you"))}</span></div>'
            )
            st.html(
                f'<div class="qiso-user-bubble" dir="{question_direction}">'
                f'{html_text(question)}</div>'
            )

        # Assistant turn
        with st.container(key="qiso_assistant_turn"):
            st.html(
                '<div class="qiso-chat-role qiso-chat-role-assistant" dir="ltr">'
                '<span class="qiso-chat-avatar qiso-chat-avatar-qiso">Q</span>'
                '<span>QISO</span></div>'
            )
            with st.container(key="qiso_answer_card"):
                answer_context = f"answer_{record['id']}"
                cited_answer = _link_answer_citations(answer_text, sources, answer_context)
                render_markdown(cited_answer, answer_context)
                meta = [
                    f"{len(sources)} {tr('source_count')}",
                    duration(record.get("total_seconds")),
                ]
                st.html(
                    '<div class="qiso-answer-meta">'
                    + '<span> • </span>'.join(html_text(value) for value in meta if value)
                    + '</div>'
                )
                st.caption(tr("review_notice"))

            # Stage 2.2 - evidence used for this answer.
            with st.container(key="qiso_inline_sources"):
                st.subheader(tr("sources"), anchor=False)
                st.caption(tr("evidence_note"))
                render_sources(
                    sources,
                    context_key=answer_context,
                )



def render_error() -> None:
    error = st.session_state.qiso_error
    if not error:
        return
    if error.get("code") == "empty_question":
        st.warning(tr("empty_question"))
        return
    st.error(tr("error"))
    st.caption(tr("error_hint"))
    if error.get("type"):
        st.caption(f"{tr('error_type')}: {error['type']}")


def render_history_page() -> None:
    render_page_heading(tr("history"), tr("history_note"))
    history = st.session_state.qiso_history
    if not history:
        st.info(tr("empty_history"))
        return
    query = st.text_input(tr("history_search"), key="qiso_history_filter").strip().casefold()
    matches = [record for record in history if query in record["question"].casefold()]
    if not matches:
        st.info(tr("no_match"))
    with st.container(key="qiso_history_list"):
        for record in matches:
            with st.container(border=True, key=f"qiso_history_card_{record['id']}"):
                render_markdown(record["question"], f"history_question_{record['id']}")
                st.caption(short_text(record["answer"], 190))
                st.button(
                    tr("open_answer"), icon=":material/arrow_outward:",
                    key=f"qiso_open_{record['id']}", on_click=open_record,
                    args=(record["id"],),
                )


def render_sources_page() -> None:
    render_page_heading(tr("sources_page"), tr("source_page_note"))
    history = st.session_state.qiso_history
    if not history:
        st.info(tr("empty_history"))
        return
    records = {record["id"]: record for record in history}
    if st.session_state.get("_qiso_source_record") not in records:
        st.session_state._qiso_source_record = next(iter(records))
    record_id = st.selectbox(
        tr("choose_question"), list(records), key="_qiso_source_record",
        format_func=lambda value: short_text(records[value]["question"], 100),
    )
    query = st.text_input(tr("source_search"), key="qiso_source_filter").strip().casefold()
    sources = records[record_id].get("sources") or []
    matches = [
        source for source in sources
        if query in f"{source.get('source', '')} {source.get('text', '')}".casefold()
    ]
    if query and not matches:
        st.info(tr("no_match"))
        return
    st.caption(tr("evidence_note"))
    render_sources(matches, context_key=f"library_{record_id}")


def render_settings() -> None:
    render_page_heading(tr("settings"), tr("settings_note"))
    for widget, setting in (
        ("_qiso_top_k", "qiso_top_k"), ("_qiso_candidate_k", "qiso_candidate_k"),
    ):
        if widget not in st.session_state:
            st.session_state[widget] = st.session_state[setting]
    with st.container(border=True, key="qiso_settings"):
        st.subheader(tr("advanced"), anchor=False)
        st.slider(
            tr("top_k"), min_value=3, max_value=10, key="_qiso_top_k",
            help=tr("top_help"), on_change=save_settings,
        )
        st.slider(
            tr("candidate_k"), min_value=10, max_value=40, step=5,
            key="_qiso_candidate_k", help=tr("candidate_help"), on_change=save_settings,
        )
        st.button(tr("reset_settings"), key="qiso_reset_settings", on_click=reset_settings)
    with st.expander(tr("about"), expanded=False):
        st.write(tr("about_text"))
        st.caption("Hybrid Search + Reranking + Generation")
    st.subheader(tr("session"), anchor=False)
    st.caption(tr("history_note"))
    st.button(
        tr("clear_history"), icon=":material/delete_outline:",
        key="qiso_clear_history", on_click=clear_history,
        disabled=not bool(st.session_state.qiso_history),
    )
