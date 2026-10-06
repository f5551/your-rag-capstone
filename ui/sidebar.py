"""Functional navigation and session history; no placeholder account details."""

from __future__ import annotations

import streamlit as st

from .helpers import html_text, navigate, new_question, open_record, short_text, tr
from .layout import brand_html


NAV_ITEMS = (
    ("assistant", "assistant", "forum"),
    ("history", "history", "history"),
    ("sources", "sources_page", "description"),
    ("settings", "settings", "settings"),
)


def render_sidebar() -> None:
    with st.sidebar:
        with st.container(key="qiso_sidebar"):
            st.html(brand_html(sidebar=True))
            with st.container(key="qiso_new"):
                st.button(
                    tr("new"), icon=":material/add:", key="qiso_new_button",
                    on_click=new_question, width="stretch",
                )
            st.html(f'<div class="qiso-sidebar-label">{html_text(tr("workspace"))}</div>')
            for page, label, icon in NAV_ITEMS:
                st.button(
                    tr(label), icon=f":material/{icon}:", key=f"qiso_nav_{page}",
                    type="primary" if st.session_state.qiso_page == page else "secondary",
                    on_click=navigate, args=(page,), width="stretch",
                )
            if st.session_state.qiso_history:
                st.divider()
                st.html(f'<div class="qiso-sidebar-label">{html_text(tr("recent"))}</div>')
                with st.container(key="qiso_recent"):
                    for record in st.session_state.qiso_history:
                        st.button(
                            short_text(record["question"], 40),
                            key=f"qiso_recent_{record['id']}", help=record["question"],
                            on_click=open_record, args=(record["id"],), width="stretch",
                        )
            st.html(
                '<div class="qiso-session">'
                f'{html_text(tr("session"))}'
                f'<small>{html_text(tr("temporary"))}</small></div>'
            )
