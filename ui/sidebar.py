"""Functional QISO navigation and session controls."""

from __future__ import annotations

import streamlit as st

from .helpers import (
    html_text,
    language,
    navigate,
    new_question,
    open_record,
    short_text,
    tr,
)
from .layout import brand_html


NAV_ITEMS = (
    (
        "assistant",
        "assistant",
        "forum",
    ),
    (
        "history",
        "history",
        "history",
    ),
    (
        "sources",
        "sources_page",
        "description",
    ),
    (
        "settings",
        "settings",
        "settings",
    ),
)


def logout() -> None:
    """End the current QISO session."""

    # Clear questions, engine and login state
    # so another person using the device
    # cannot see the previous session.
    st.session_state.clear()


def render_sidebar() -> None:

    with st.sidebar:

        with st.container(
            key="qiso_sidebar"
        ):

            st.html(
                brand_html(
                    sidebar=True
                )
            )

            # ----------------------
            # New question
            # ----------------------

            with st.container(
                key="qiso_new"
            ):

                st.button(
                    tr("new"),
                    icon=":material/add:",
                    key="qiso_new_button",
                    on_click=new_question,
                    width="stretch",
                )

            st.html(
                '<div class="qiso-sidebar-label">'
                f'{html_text(tr("workspace"))}'
                '</div>'
            )

            # ----------------------
            # Navigation
            # ----------------------

            for (
                page,
                label,
                icon,
            ) in NAV_ITEMS:

                st.button(
                    tr(label),
                    icon=(
                        f":material/{icon}:"
                    ),
                    key=(
                        f"qiso_nav_{page}"
                    ),
                    type=(
                        "primary"
                        if (
                            st.session_state.qiso_page
                            == page
                        )
                        else "secondary"
                    ),
                    on_click=navigate,
                    args=(page,),
                    width="stretch",
                )

            # ----------------------
            # Recent questions
            # ----------------------

            if (
                st.session_state.qiso_history
            ):

                st.divider()

                st.html(
                    '<div '
                    'class="qiso-sidebar-label">'
                    f'{html_text(tr("recent"))}'
                    '</div>'
                )

                with st.container(
                    key="qiso_recent"
                ):

                    for record in (
                        st.session_state.qiso_history
                    ):

                        st.button(
                            short_text(
                                record[
                                    "question"
                                ],
                                40,
                            ),
                            key=(
                                "qiso_recent_"
                                f"{record['id']}"
                            ),
                            help=record[
                                "question"
                            ],
                            on_click=(
                                open_record
                            ),
                            args=(
                                record["id"],
                            ),
                            width="stretch",
                        )

            # ----------------------
            # Session / Logout
            # ----------------------

            st.divider()

            logout_text = (
                "Sign out"
                if language() == "en"
                else "تسجيل الخروج"
            )

            st.button(
                logout_text,
                icon=":material/logout:",
                key="qiso_logout_button",
                on_click=logout,
                width="stretch",
            )