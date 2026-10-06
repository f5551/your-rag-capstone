"""Branding, page headings, welcome state, and the main page shell."""

from __future__ import annotations

from typing import Any

import streamlit as st

from .helpers import html_text, language, tr


def brand_html(*, sidebar: bool = False) -> str:
    """A lightweight Q-shaped mark, inspired by the supplied visual reference."""
    extra = " qiso-sidebar-brand" if sidebar else ""
    return (
        f'<div class="qiso-brand{extra}" aria-label="QISO">'
        '<span class="qiso-symbol" aria-hidden="true"></span>'
        '<strong>QISO</strong></div>'
    )


def render_header(page: str = "assistant") -> None:
    label = {"assistant": "assistant", "history": "history", "sources": "sources_page", "settings": "settings"}[page]
    with st.container(key="qiso_topbar"):
        title, controls = st.columns([1, 1], gap="small", vertical_alignment="center")
        with title:
            with st.container(key="qiso_header_title"):
                st.markdown(f"**{tr(label)}**")
        with controls:
            with st.container(key="qiso_language_controls"):
                st.radio(
                    tr("ui_language"), ["ar", "en"],
                    format_func=lambda code: "العربية" if code == "ar" else "English",
                    horizontal=True, key="qiso_language", label_visibility="collapsed",
                )


def workspace() -> Any:
    """Actual keyed container: never try to wrap Streamlit widgets with div tags."""
    return st.container(key="qiso_workspace")


def render_welcome() -> None:
    direction = "rtl" if language() == "ar" else "ltr"
    st.html(
        '<section class="qiso-hero">'
        f'{brand_html()}'
        f'<h1 dir="{direction}">{html_text(tr("welcome"))}</h1>'
        f'<p dir="{direction}">{html_text(tr("description"))}</p>'
        f'<div class="qiso-eyebrow">{html_text(tr("eyebrow"))}</div>'
        '</section>'
    )


def render_page_heading(title: str, description: str = "") -> None:
    st.html(
        '<section class="qiso-page-heading">'
        f'<h1>{html_text(title)}</h1><p>{html_text(description)}</p>'
        '</section>'
    )


def render_footer() -> None:
    st.html(
        '<footer class="qiso-footer">'
        'QISO &nbsp; &middot; &nbsp; Quality Management &nbsp; &middot; &nbsp; '
        'ISO Standards &nbsp; &middot; &nbsp; Internal Auditing'
        '</footer>'
    )
