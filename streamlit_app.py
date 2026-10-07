"""QISO Streamlit UI."""

from __future__ import annotations

import hmac
import logging
import re
from typing import Any

import streamlit as st

st.set_page_config(
    page_title="QISO | Quality Intelligence",
    page_icon=":material/fact_check:",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui.components import (
    render_answer, render_error, render_examples, render_history_page,
    render_question_box, render_settings, render_sources_page,
)
from ui.helpers import (
    display_error, initialize_state, language, store_result,
    text_direction, tr,
)
from ui.layout import (
    brand_html, render_footer, render_header, render_welcome, workspace,
)
from ui.sidebar import render_sidebar
from ui.styles import apply_styles

logger = logging.getLogger("qiso.ui")


# ============================================================
# LOGIN
# ============================================================

def get_credentials() -> tuple[str, str] | None:
    try:
        return (
            str(st.secrets["LOGIN_USERNAME"]).strip(),
            str(st.secrets["LOGIN_PASSWORD"]),
        )
    except (KeyError, FileNotFoundError):
        return None


def check_login(username: str, password: str) -> bool:
    """Unicode-safe login check."""
    credentials = get_credentials()

    if not credentials:
        return False

    saved_user, saved_password = credentials

    return (
        hmac.compare_digest(
            username.strip().encode("utf-8"),
            saved_user.encode("utf-8"),
        )
        and hmac.compare_digest(
            password.encode("utf-8"),
            saved_password.encode("utf-8"),
        )
    )


def logout() -> None:
    """Clear session and return to login."""
    lang = st.session_state.get("qiso_language", "ar")
    st.session_state.clear()
    st.session_state.qiso_language = lang
    st.session_state.qiso_logged_in = False


def render_login() -> None:
    english = language() == "en"
    direction = "ltr" if english else "rtl"

    text = {
        "title": "Welcome to QISO" if english else "مرحبًا بك في QISO",
        "subtitle": (
            "Sign in to continue to QISO."
            if english
            else "سجّل الدخول للمتابعة إلى نظام QISO."
        ),
        "about": (
            "<strong>QISO</strong> is an intelligent assistant specialized "
            "in quality management systems and internal auditing. It helps "
            "you access reliable information with supporting sources and pages."
            if english
            else
            "<strong>QISO</strong> مساعد ذكي متخصص في أنظمة إدارة الجودة "
            "والتدقيق الداخلي، يساعدك على الوصول إلى المعلومات الموثوقة "
            "مع إظهار المصادر والصفحات الداعمة للإجابة."
        ),
        "user": "Username" if english else "اسم المستخدم",
        "user_ph": "Enter your username" if english else "أدخل اسم المستخدم",
        "pass": "Password" if english else "كلمة المرور",
        "pass_ph": "Enter your password" if english else "أدخل كلمة المرور",
        "button": "Sign in" if english else "تسجيل الدخول",
        "empty": (
            "Please enter your username and password."
            if english else
            "يرجى إدخال اسم المستخدم وكلمة المرور."
        ),
        "wrong": (
            "Incorrect username or password."
            if english else
            "اسم المستخدم أو كلمة المرور غير صحيحة."
        ),
        "secure": (
            "Private and secure session"
            if english else
            "جلسة دخول خاصة وآمنة"
        ),
    }

    st.html(
        """
        <style>
        section[data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"] {
            display:none !important;
        }

        header[data-testid="stHeader"] {
            background:transparent !important;
        }

        .stApp {
            background:
                radial-gradient(circle at 15% 20%,
                rgba(13,148,136,.09), transparent 30%),
                radial-gradient(circle at 85% 80%,
                rgba(14,116,144,.07), transparent 30%),
                #f7fafc;
        }

        .block-container {
            padding-top:.5rem;
        }

        .st-key-login_shell {
            max-width:470px;
            margin:4vh auto;
            padding:16px;
        }

        .st-key-login_card {
            background:white;
            padding:34px;
            border:1px solid #e2e8f0;
            border-radius:22px;
            box-shadow:0 20px 55px rgba(15,23,42,.10);
        }

        .st-key-login_card div[data-testid="stForm"] {
            border:0 !important;
            padding:0 !important;
        }

        .login-brand {
            display:flex;
            justify-content:center;
            margin-bottom:15px;
        }

        .login-title {
            text-align:center;
            margin:0;
            color:#0f172a;
            font-size:1.65rem;
            font-weight:800;
        }

        .login-subtitle {
            text-align:center;
            color:#64748b;
            margin:8px 0 20px;
        }

        .login-about {
            background:#f8fafc;
            border:1px solid #e2e8f0;
            border-radius:13px;
            padding:15px 17px;
            margin-bottom:22px;
            color:#475569;
            font-size:.88rem;
            line-height:1.8;
        }

        .login-about strong {
            color:#0f9488;
        }

        .st-key-login_card input {
            min-height:48px;
            border-radius:10px;
        }

        .st-key-login_card
        [data-testid="stFormSubmitButton"] button {
            min-height:48px;
            border-radius:10px;
            font-weight:700;
            margin-top:10px;
        }

        .login-secure {
            text-align:center;
            color:#94a3b8;
            font-size:.78rem;
            margin-top:18px;
        }

        @media(max-width:600px) {
            .st-key-login_shell {
                margin:1vh auto;
                padding:10px;
            }

            .st-key-login_card {
                padding:25px 18px;
                border-radius:18px;
            }

            .login-title {
                font-size:1.4rem;
            }

            .login-about {
                font-size:.83rem;
            }
        }
        </style>
        """
    )

    with st.container(key="login_shell"):
        with st.container(key="login_card"):

            st.html(
                '<div class="login-brand">'
                f'{brand_html()}'
                '</div>'
            )

            st.radio(
                "Language",
                ["ar", "en"],
                format_func=lambda x: "العربية" if x == "ar" else "English",
                horizontal=True,
                key="qiso_language",
                label_visibility="collapsed",
            )

            # إعادة التشغيل التلقائية تغير اللغة.
            english = language() == "en"
            direction = "ltr" if english else "rtl"

            # تحديث النص بعد تغيير اللغة.
            if english:
                text.update({
                    "title": "Welcome to QISO",
                    "subtitle": "Sign in to continue to QISO.",
                    "about": (
                        "<strong>QISO</strong> is an intelligent assistant "
                        "specialized in quality management systems and internal "
                        "auditing. It helps you access reliable information "
                        "with supporting sources and pages."
                    ),
                    "user": "Username",
                    "user_ph": "Enter your username",
                    "pass": "Password",
                    "pass_ph": "Enter your password",
                    "button": "Sign in",
                    "empty": "Please enter your username and password.",
                    "wrong": "Incorrect username or password.",
                    "secure": "Private and secure session",
                })

            st.html(
                f"""
                <div dir="{direction}">
                    <h1 class="login-title">{text["title"]}</h1>
                    <p class="login-subtitle">{text["subtitle"]}</p>

                    <div class="login-about">
                        {text["about"]}
                    </div>
                </div>
                """
            )

            if not get_credentials():
                st.error("Login credentials are not configured.")
                st.stop()

            with st.form("login_form"):
                username = st.text_input(
                    text["user"],
                    placeholder=text["user_ph"],
                )

                password = st.text_input(
                    text["pass"],
                    type="password",
                    placeholder=text["pass_ph"],
                )

                submitted = st.form_submit_button(
                    text["button"],
                    type="primary",
                    width="stretch",
                )

            if submitted:
                if not username.strip() or not password:
                    st.warning(text["empty"])

                elif check_login(username, password):
                    st.session_state.qiso_logged_in = True
                    st.rerun()

                else:
                    st.error(text["wrong"])

            st.html(
                f'<div class="login-secure">🔒 {text["secure"]}</div>'
            )


# ============================================================
# RAG
# ============================================================

def request_answer(question: str) -> dict[str, Any]:
    from core.generator import Generator, answer_question

    if "qiso_engine" not in st.session_state:
        st.session_state.qiso_engine = Generator()

    return answer_question(
        question=question,
        top_k=st.session_state.qiso_top_k,
        candidate_k=st.session_state.qiso_candidate_k,
        generator=st.session_state.qiso_engine,
    )


def render_assistant() -> None:
    pending = st.session_state.pop("qiso_pending", None)

    if pending:
        try:
            with st.spinner(tr("working")):
                result = request_answer(pending)
                store_result(pending, result)

        except Exception as error:
            st.session_state.qiso_error = display_error(error)
            logger.error(
                "QISO request failed (%s)",
                type(error).__name__,
            )

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


# ============================================================
# APP
# ============================================================

def render_app() -> None:
    match = re.match(r"(\d+)\.(\d+)", st.__version__)

    if match and tuple(map(int, match.groups())) < (1, 50):
        st.error("Streamlit 1.50 or newer is required.")
        st.stop()

    initialize_state()

    if "qiso_logged_in" not in st.session_state:
        st.session_state.qiso_logged_in = False

    input_direction = text_direction(
        st.session_state.qiso_draft,
        fallback="rtl" if language() == "ar" else "ltr",
    )

    apply_styles(language(), input_direction)

    # Login
    if not st.session_state.qiso_logged_in:
        render_login()
        st.stop()

    # Main QISO
    render_sidebar()

    # Logout button
    with st.sidebar:
        st.divider()

        if st.button(
            "Sign out" if language() == "en" else "تسجيل الخروج",
            icon=":material/logout:",
            width="stretch",
        ):
            logout()
            st.rerun()

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