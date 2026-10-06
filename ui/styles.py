"""QISO design tokens and scoped styles. No layout or RAG logic."""

from __future__ import annotations

import streamlit as st

PALETTE = {
    "navy": "#0F2D4A",
    "navy_deep": "#092139",
    "teal": "#14B8A6",
    "action": "#087F75",
    "canvas": "#F3F6F9",
    "ice": "#E8F6F7",
    "border": "#D8E5EE",
    "muted": "#526D82",
}

CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --qiso-navy: #0F2D4A;
    --qiso-navy-deep: #092139;
    --qiso-teal: #14B8A6;
    --qiso-action: #087F75;
    --qiso-canvas: #F3F6F9;
    --qiso-ice: #E8F6F7;
    --qiso-border: #D8E5EE;
    --qiso-muted: #526D82;
    --qiso-font: "Inter", "Cairo", "Segoe UI", Tahoma, sans-serif;
    --qiso-arabic: "Cairo", "Inter", "Segoe UI", Tahoma, sans-serif;
}

/* Scope typography: do not overwrite the Material Symbols icon font. */
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse at 88% 32%, #E8F6F7 0, transparent 50%),
        linear-gradient(155deg, #FAFCFF 0%, #F3F8FC 57%, #EDF5FA 100%);
    color: var(--qiso-navy);
    font-family: var(--qiso-font);
}
/* FIX-01: the native toolbar contains the sidebar REOPEN button.
   Never hide stHeader/stToolbar, even when the sidebar is collapsed.
   Keep Streamlit's display/layout logic; only hide the decorative stripe. */
[data-testid="stHeader"] { background: rgba(248,252,255,.96); }
[data-testid="stDecoration"] { display: none; }

/* These selectors affect existing controls only; they do not fabricate a
   second control or force an otherwise closed sidebar to remain open. */
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
}
[data-testid="stExpandSidebarButton"],
[data-testid="stExpandSidebarButton"] button {
    min-width: 44px;
    min-height: 44px;
    border-radius: 10px;
    color: #0F2D4A !important;
    background: #E8F6F7 !important;
}
[data-testid="stSidebarCollapseButton"] button,
button[data-testid="stSidebarCollapseButton"] {
    min-width: 40px;
    min-height: 40px;
    border-radius: 9px;
    color: #EAF3FB !important;
    background: rgba(255,255,255,.10) !important;
}
[data-testid="stExpandSidebarButton"]:focus-visible,
[data-testid="stSidebarCollapseButton"] button:focus-visible {
    outline: 3px solid #20AFA1 !important;
    outline-offset: 2px;
}
/* Main content starts below Streamlit's native toolbar. */
[data-testid="stMain"] .block-container {
    max-width: 1380px;
    width: 100%;
    padding: 4.25rem clamp(1rem, 3.2vw, 3.2rem) 1.75rem;
}
.st-key-qiso_root { color: var(--qiso-navy); }
.st-key-qiso_root h1, .st-key-qiso_root h2, .st-key-qiso_root h3,
.st-key-qiso_root p, .st-key-qiso_root li, .st-key-qiso_root label,
.st-key-qiso_root button, .st-key-qiso_root textarea,
.st-key-qiso_root input, .st-key-qiso_root summary {
    font-family: __BODY_FONT__;
}
.st-key-qiso_root h2 { font-size: 1.5rem; font-weight: 750; }
.st-key-qiso_root h3 { font-size: 1.13rem; font-weight: 700; }
.st-key-qiso_root p, .st-key-qiso_root li { line-height: 1.9; }
.st-key-qiso_root [data-testid="stCaptionContainer"] p {
    color: var(--qiso-muted); font-size: .875rem; line-height: 1.7;
}
.st-key-qiso_root [data-testid="stWidgetLabel"],
.st-key-qiso_root h2, .st-key-qiso_root h3,
.st-key-qiso_root [data-testid="stCaptionContainer"] {
    direction: __DIR__; text-align: __ALIGN__;
}
.st-key-qiso_root hr { border-color: var(--qiso-border); }

/* Sidebar: native panel, not a fixed custom overlay. */
@media (min-width: 769px) {
    section[data-testid="stSidebar"][aria-expanded="true"] {
        width: 252px !important; min-width: 252px !important; max-width: 252px !important;
    }
}
section[data-testid="stSidebar"] {
    background: linear-gradient(170deg, #0F2D4A 0%, #092139 100%);
    border-right: 1px solid rgba(255,255,255,.06);
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    background: transparent;
}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    padding: 1.2rem .85rem 1rem;
}
.st-key-qiso_sidebar { color: #EAF3FB; }
.st-key-qiso_sidebar p, .st-key-qiso_sidebar button,
.st-key-qiso_sidebar label { font-family: __BODY_FONT__; }
.st-key-qiso_sidebar [data-testid="stCaptionContainer"] p {
    color: #C0D2E0; font-size: .76rem; line-height: 1.7;
    direction: __DIR__; text-align: __ALIGN__;
}
.st-key-qiso_sidebar hr { border-color: rgba(255,255,255,.13); margin: .7rem 0; }
.st-key-qiso_sidebar [data-testid="stButton"] button {
    min-height: 43px; border-radius: 9px;
    border: 1px solid transparent; background: transparent;
    color: #DCE9F5; padding: .55rem .75rem;
    justify-content: flex-start; text-align: __ALIGN__;
    direction: __DIR__; box-shadow: none;
}
.st-key-qiso_sidebar [data-testid="stButton"] button p {
    color: inherit; font-size: .9rem; line-height: 1.5;
}
.st-key-qiso_sidebar [data-testid="stButton"] button:hover {
    background: rgba(255,255,255,.08); border-color: rgba(255,255,255,.10);
}
.st-key-qiso_sidebar [data-testid="stButton"] button[kind="primary"] {
    background: var(--qiso-action); color: #FFF;
    border-color: var(--qiso-action); font-weight: 700;
}
.st-key-qiso_sidebar [data-testid="stButton"] button[kind="primary"]:hover {
    background: #096D66;
}
.st-key-qiso_new [data-testid="stButton"] button {
    background: #087F75 !important; border-color: #19B3A5 !important;
    color: white !important; min-height: 46px;
    box-shadow: 0 6px 16px rgba(0,0,0,.11);
}
.st-key-qiso_recent [data-testid="stButton"] button {
    border-inline-start: 2px solid rgba(123,174,198,.26);
    border-radius: 0 7px 7px 0; min-height: 36px;
}
.st-key-qiso_recent [data-testid="stButton"] button p {
    font-size: .77rem; font-weight: 400;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.qiso-sidebar-label {
    color: #91AEC3; font-family: __BODY_FONT__; font-size: .70rem;
    letter-spacing: .04em; margin: .8rem .65rem .2rem;
    direction: __DIR__; text-align: __ALIGN__;
}
.qiso-session {
    border-top: 1px solid rgba(255,255,255,.12);
    padding: 1rem .45rem .2rem; margin-top: 1.2rem;
    color: #DCEAF3; direction: __DIR__; font-family: __BODY_FONT__;
    font-size: .8rem;
}
.qiso-session small { display: block; color: #ABC2D3; font-size: .7rem; margin-top: .35rem; }

/* Q-shaped mark drawn in CSS, no external logo asset is required. */
.qiso-brand { display:flex; align-items:center; gap:.65rem; direction:ltr; }
.qiso-symbol {
    --mark: 40px; flex-shrink:0; position:relative; display:inline-block;
    width:var(--mark); height:var(--mark); border-radius:50%;
    background: conic-gradient(from 120deg, #13C0AC, #0F2D4A 33%, #105776 68%, #13C0AC);
}
.qiso-symbol::before {
    content:""; position:absolute; inset:24%; border-radius:50%; background:var(--qiso-symbol-hole, #F7FBFD);
}
.qiso-symbol::after {
    content:""; position:absolute; width:52%; height:23%; right:-8%; bottom:5%;
    transform:rotate(44deg); border-radius:1px;
    background:linear-gradient(90deg, #10B8AC, #16D3C0);
}
.qiso-brand strong { font-family:var(--qiso-font); font-size:1.65rem; letter-spacing:-.07em; }
.qiso-sidebar-brand { padding:.35rem .5rem 1.25rem; color:white; --qiso-symbol-hole:#0E2B47; }
.qiso-sidebar-brand .qiso-symbol { --mark:36px; }

/* Main top bar, real controls stay inside real Streamlit containers. */
.st-key-qiso_topbar {
    padding: .3rem .25rem .8rem;
    border-bottom: 1px solid var(--qiso-border);
    margin-bottom: .3rem;
}
.st-key-qiso_header_title [data-testid="stMarkdownContainer"] {
    color:var(--qiso-navy); font-weight:700; font-size:1rem;
    font-family:__BODY_FONT__; direction:__DIR__; text-align:left;
}
.st-key-qiso_header_title p { margin:0; }
.st-key-qiso_language_controls [role="radiogroup"] {
    justify-content:flex-end; gap:.75rem; direction:ltr;
}
.st-key-qiso_language_controls [data-testid="stMarkdownContainer"] p { font-size:.9rem; }
.st-key-qiso_workspace { max-width:920px; width:100%; margin-inline:auto; }

/* Empty/welcome state. No nested empty columns shrinking the content. */
.qiso-hero { text-align:center; padding:2.25rem 1rem 1.45rem; color:var(--qiso-navy); }
.qiso-hero .qiso-brand { justify-content:center; gap:1rem; margin-bottom:.9rem; }
.qiso-hero .qiso-symbol { --mark:66px; --qiso-symbol-hole:#F7FBFD; }
.qiso-hero .qiso-brand strong { font-size:3.1rem; font-weight:800; letter-spacing:-.065em; }
.qiso-hero h1 {
    margin:.2rem 0 .45rem; font-size:1.58rem !important; line-height:1.65;
    font-family:__BODY_FONT__; font-weight:750; direction:__DIR__;
}
.qiso-hero p {
    margin:0 auto; max-width:620px; color:#365872;
    font-size:.98rem; line-height:1.9; direction:__DIR__;
}
.qiso-eyebrow { font-size:.8rem; color:#177E7A; letter-spacing:.035em; margin-top:.8rem; }

/* Question composer: key targets the actual Streamlit container. */
.st-key-qiso_composer {
    background:#FFF; border:1px solid #C9DDEB; border-radius:17px;
    box-shadow:0 10px 35px rgba(15,45,74,.055); padding:.55rem .9rem .7rem;
    margin-top:.3rem;
}
.st-key-qiso_composer:focus-within {
    border-color:#168F84; box-shadow:0 0 0 3px rgba(20,184,166,.10);
}
.st-key-qiso_composer [data-testid="stTextArea"] [data-baseweb="textarea"] {
    background:transparent; border:0; box-shadow:none;
}
.st-key-qiso_composer textarea {
    background:transparent; border:0; box-shadow:none;
    font-size:1rem; line-height:1.9; padding:.45rem .25rem;
    direction:__INPUT_DIR__; text-align:__INPUT_ALIGN__;
    unicode-bidi:plaintext; resize:vertical;
}
.st-key-qiso_composer textarea::placeholder { color:#68849B; opacity:1; }
.st-key-qiso_composer [data-testid="stButton"] button {
    min-height:43px; background:var(--qiso-action); color:#FFF;
    border:1px solid var(--qiso-action); border-radius:11px; font-weight:700;
}
.st-key-qiso_composer [data-testid="stButton"] button:hover { background:#096D66; }
.st-key-qiso_composer [data-testid="stCaptionContainer"] p { font-size:.85rem; padding:.25rem; }

/* Example cards are actual buttons. */
.st-key-qiso_examples { margin-top:1.15rem; }
.st-key-qiso_examples h3 { font-size:.91rem; margin-bottom:.1rem; }
.st-key-qiso_examples [data-testid="stButton"] button {
    width:100%; min-height:73px; background:rgba(255,255,255,.87);
    border:1px solid var(--qiso-border); border-radius:11px;
    color:#244A66; text-align:__ALIGN__; direction:__DIR__;
    justify-content:flex-start; padding:.85rem;
    box-shadow:0 3px 10px rgba(15,45,74,.018);
    transition:border-color .15s ease, background .15s ease;
}
.st-key-qiso_examples [data-testid="stButton"] button p { font-size:.9rem; line-height:1.7; }
.st-key-qiso_examples [data-testid="stButton"] button:hover {
    background:#F0FBFA; border-color:#4CAEA4;
}

/* Stage 2.1 - conversational question / answer layout. */
.st-key-qiso_chat_thread {
    margin-top:1.15rem;
    display:flex;
    flex-direction:column;
    gap:1.1rem;
}
.st-key-qiso_user_turn {
    width:min(78%, 720px);
    margin-inline-start:auto;
}
.st-key-qiso_assistant_turn {
    width:min(92%, 820px);
    margin-inline-end:auto;
}
.qiso-chat-role {
    display:flex;
    align-items:center;
    gap:.5rem;
    margin:0 0 .42rem;
    color:#365872;
    font-family:__BODY_FONT__;
    font-size:.79rem;
    font-weight:700;
}
.qiso-chat-role-user { justify-content:flex-end; }
.qiso-chat-role-assistant { justify-content:flex-start; }
.qiso-chat-avatar {
    display:inline-flex;
    align-items:center;
    justify-content:center;
    width:28px;
    height:28px;
    border-radius:50%;
    flex:0 0 28px;
    font-family:var(--qiso-font);
    font-size:.75rem;
    font-weight:800;
}
.qiso-chat-avatar-user {
    background:#DCECF4;
    color:#17445E;
    border:1px solid #C6DFEA;
}
.qiso-chat-avatar-qiso {
    color:white;
    background:linear-gradient(145deg, #0F2D4A 10%, #14B8A6 92%);
    box-shadow:0 3px 9px rgba(15,45,74,.12);
}
.qiso-user-bubble {
    background:#E8F6F7;
    border:1px solid #CFE7EA;
    border-radius:17px 17px 5px 17px;
    padding:.9rem 1.05rem;
    color:#163E57;
    font-family:var(--qiso-arabic);
    font-size:.96rem;
    line-height:1.85;
    white-space:pre-wrap;
    overflow-wrap:anywhere;
    box-shadow:0 4px 14px rgba(15,45,74,.025);
}
.st-key-qiso_answer_card {
    margin:0;
    background:#FFF;
    padding:1.2rem 1.3rem .95rem;
    border:1px solid var(--qiso-border);
    border-radius:5px 17px 17px 17px;
    box-shadow:0 7px 24px rgba(15,45,74,.04);
}
.st-key-qiso_answer_card [data-testid="stMarkdownContainer"] p:first-child {
    margin-top:0;
}
.qiso-answer-meta {
    display:flex;
    flex-wrap:wrap;
    gap:.35rem;
    align-items:center;
    margin-top:.9rem;
    padding-top:.65rem;
    border-top:1px solid #E7EEF3;
    color:#68849B;
    font-family:var(--qiso-font);
    font-size:.74rem;
    direction:ltr;
    text-align:left;
}
.qiso-answer-meta span { color:#9AB0C0; }

/* Answer citations: valid [n] markers become local links to their source card. */
.st-key-qiso_answer_card [data-testid="stMarkdownContainer"] a[href^="#qiso-source-"] {
    display:inline-flex;
    align-items:center;
    justify-content:center;
    min-width:1.7rem;
    height:1.45rem;
    margin-inline:.12rem;
    padding:0 .38rem;
    border:1px solid #B9DDD9;
    border-radius:999px;
    background:#EAF8F6;
    color:#087F75 !important;
    font-family:var(--qiso-font);
    font-size:.76rem;
    font-weight:800;
    line-height:1;
    text-decoration:none !important;
    vertical-align:middle;
}
.st-key-qiso_answer_card [data-testid="stMarkdownContainer"] a[href^="#qiso-source-"]:hover {
    background:#DDF3F0;
    border-color:#66BDB4;
}
.qiso-source-anchor {
    display:block;
    position:relative;
    top:-5rem;
    visibility:hidden;
}

/* Stage 2.2 - inline evidence cards under the answer. */
.st-key-qiso_inline_sources {
    margin-top:.15rem;
    padding:.15rem .15rem .1rem;
}
.st-key-qiso_inline_sources h3 {
    margin:.2rem 0 .1rem;
    font-size:.98rem !important;
    color:var(--qiso-navy);
}
.st-key-qiso_inline_sources [data-testid="stCaptionContainer"] p {
    margin-bottom:.35rem;
    color:#6A8396;
}
.st-key-qiso_inline_sources [data-testid="stExpander"] details {
    background:rgba(255,255,255,.96);
    border:1px solid #D8E5EE;
    border-radius:12px;
    box-shadow:0 3px 11px rgba(15,45,74,.025);
}
.st-key-qiso_inline_sources [data-testid="stExpander"] summary {
    min-height:50px;
    padding-inline:.2rem;
}
.st-key-qiso_inline_sources [data-testid="stExpander"] summary p {
    font-size:.84rem;
    font-weight:600;
    color:#244A66;
}
.st-key-qiso_inline_sources .qiso-source-heading {
    padding:.15rem 0 .35rem;
    font-weight:700;
}

/* Stage 2.3 - diagnostics intentionally secondary and collapsed. */
.st-key-qiso_inline_diagnostics {
    margin-top:.45rem;
}
.st-key-qiso_inline_diagnostics [data-testid="stExpander"] details {
    background:rgba(247,250,252,.86);
    border:1px dashed #C9D9E5;
    border-radius:11px;
    box-shadow:none;
}
.st-key-qiso_inline_diagnostics [data-testid="stExpander"] summary p {
    font-size:.8rem;
    font-weight:600;
    color:#5E788C;
}
.st-key-qiso_inline_diagnostics [data-testid="stMetric"] {
    background:#FFFFFF;
}

/* Readable question/answer content and source cards. */
[class*="st-key-qiso_rtl_"] [data-testid="stMarkdownContainer"] {
    direction:rtl; text-align:right; font-family:var(--qiso-arabic);
}
[class*="st-key-qiso_ltr_"] [data-testid="stMarkdownContainer"] {
    direction:ltr; text-align:left; font-family:var(--qiso-font);
}
[class*="st-key-qiso_rtl_"] p, [class*="st-key-qiso_rtl_"] li { font-family:var(--qiso-arabic); }
[class*="st-key-qiso_ltr_"] p, [class*="st-key-qiso_ltr_"] li { font-family:var(--qiso-font); }
[class*="st-key-qiso_rtl_"] ol, [class*="st-key-qiso_rtl_"] ul { padding-inline-start:1.5rem; padding-inline-end:0; }
.st-key-qiso_root pre, .st-key-qiso_root code {
    direction:ltr; text-align:left; unicode-bidi:plaintext;
    font-family:Consolas, "Courier New", monospace;
}
.st-key-qiso_root pre { overflow-x:auto; max-width:100%; }
.st-key-qiso_root [data-testid="stExpander"] details {
    background:rgba(255,255,255,.94); border-color:var(--qiso-border);
    border-radius:11px;
}
.st-key-qiso_root [data-testid="stExpander"] summary {
    color:var(--qiso-navy); min-height:48px; line-height:1.6;
}
.st-key-qiso_root [data-testid="stExpander"] summary p { font-size:.86rem; }
.qiso-source-heading { font-family:var(--qiso-font); overflow-wrap:anywhere; color:#214862; }
.qiso-source-heading small { color:var(--qiso-muted); display:block; margin-top:.35rem; }
.st-key-qiso_root [data-testid="stMetric"] {
    background:#F7FAFC; border:1px solid var(--qiso-border);
    padding:.7rem; border-radius:10px;
}
.st-key-qiso_root [data-testid="stMetricValue"] { font-size:1.2rem; }
.st-key-qiso_root [data-testid="stAlert"] { border-radius:12px; }
.st-key-qiso_history_list [data-testid="stVerticalBlock"] [data-testid="stButton"] button {
    border-radius:9px; color:var(--qiso-action); border-color:#B7D9D5;
}
.st-key-qiso_settings, .st-key-qiso_history_list { margin-top:1rem; }
.qiso-page-heading { direction:__DIR__; text-align:__ALIGN__; padding:1.5rem 0 .5rem; }
.qiso-page-heading h1 { font-size:1.55rem; font-family:__BODY_FONT__; color:var(--qiso-navy); }
.qiso-page-heading p { font-size:.87rem; color:var(--qiso-muted); line-height:1.8; }
.qiso-footer {
    padding:1.5rem .3rem .3rem; margin-top:1.3rem; text-align:center;
    color:#4D7089; font-size:.78rem; letter-spacing:.01em;
    font-family:var(--qiso-font);
}

/* Keyboard focus and mobile layout; never force a desktop sidebar on phones. */
.st-key-qiso_root button:focus-visible, .st-key-qiso_sidebar button:focus-visible {
    outline:3px solid #20AFA1 !important; outline-offset:3px;
}
@media (max-width: 768px) {
    [data-testid="stMain"] .block-container { padding:4.1rem 1rem 1.5rem; }
    .qiso-hero { padding:1.3rem .2rem 1rem; }
    .qiso-hero .qiso-brand strong { font-size:2.4rem; }
    .qiso-hero .qiso-symbol { --mark:53px; }
    .qiso-hero h1 { font-size:1.3rem !important; }
    .qiso-hero p { font-size:.9rem; }
    .st-key-qiso_topbar [data-testid="stHorizontalBlock"] {
        flex-wrap:nowrap; align-items:center;
    }
    .st-key-qiso_topbar [data-testid="stColumn"] { min-width:0; }
    .st-key-qiso_composer [data-testid="stHorizontalBlock"] { flex-wrap:nowrap; align-items:center; }
    .st-key-qiso_composer [data-testid="stColumn"] { min-width:0; }
    .st-key-qiso_composer { padding:.45rem .65rem .6rem; }
    .st-key-qiso_composer [data-testid="stCaptionContainer"] p { font-size:.8rem; }
    .st-key-qiso_answer_card { padding:1rem; }
    .st-key-qiso_examples [data-testid="stButton"] button { min-height:64px; }
}
@media (max-width: 768px) {
    .st-key-qiso_user_turn, .st-key-qiso_assistant_turn { width:100%; }
    .qiso-user-bubble { border-radius:15px 15px 5px 15px; }
    .st-key-qiso_answer_card { border-radius:5px 15px 15px 15px; }
}

/* ==========================================================
   User UI production polish: language, responsive, UX, cleanup
   ========================================================== */

/* User-visible evidence is content, not diagnostics. */
.st-key-qiso_inline_sources {
    margin-top:1rem;
    padding-top:.9rem;
    border-top:1px solid #E5EDF3;
}
.st-key-qiso_inline_sources h3 {
    font-size:1rem;
    margin:0 0 .15rem;
}
.st-key-qiso_inline_sources [data-testid="stCaptionContainer"] p {
    font-size:.78rem;
    color:#60798D;
}
.qiso-source-heading {
    unicode-bidi:plaintext;
    line-height:1.65;
}

/* Keep all interactive surfaces visually consistent. */
.st-key-qiso_root [data-testid="stButton"] button,
.st-key-qiso_sidebar [data-testid="stButton"] button,
.st-key-qiso_root input,
.st-key-qiso_root textarea {
    transition:border-color .15s ease, background-color .15s ease, box-shadow .15s ease;
}
.st-key-qiso_root [data-testid="stAlert"] {
    border:1px solid var(--qiso-border);
    box-shadow:none;
}

/* Laptop / medium desktop. */
@media (max-width: 1180px) and (min-width: 769px) {
    [data-testid="stMain"] .block-container {
        padding-inline:1.65rem;
    }
    .st-key-qiso_workspace {
        max-width:860px;
    }
    section[data-testid="stSidebar"][aria-expanded="true"] {
        width:238px !important;
        min-width:238px !important;
        max-width:238px !important;
    }
}

/* Phones and narrow tablets. */
@media (max-width: 768px) {
    [data-testid="stMain"] .block-container {
        padding:3.9rem .85rem 1.25rem;
    }
    .st-key-qiso_workspace { max-width:100%; }
    .st-key-qiso_topbar {
        padding-bottom:.55rem;
        margin-bottom:0;
    }
    .st-key-qiso_topbar [data-testid="stHorizontalBlock"] {
        gap:.45rem;
    }
    .st-key-qiso_language_controls [role="radiogroup"] {
        gap:.35rem;
    }
    .qiso-hero {
        padding:1.15rem .15rem .85rem;
    }
    .qiso-hero .qiso-brand {
        gap:.7rem;
        margin-bottom:.55rem;
    }
    .qiso-hero .qiso-brand strong { font-size:2.15rem; }
    .qiso-hero .qiso-symbol { --mark:48px; }
    .qiso-hero h1 { font-size:1.18rem !important; }
    .qiso-hero p { font-size:.88rem; line-height:1.75; }
    .st-key-qiso_composer {
        border-radius:14px;
        padding:.45rem .55rem .55rem;
    }
    .st-key-qiso_composer textarea {
        font-size:.96rem;
        line-height:1.75;
        min-height:96px;
    }
    .st-key-qiso_composer [data-testid="stHorizontalBlock"] {
        gap:.45rem;
    }
    .st-key-qiso_composer [data-testid="stButton"] button {
        min-height:42px;
    }
    .st-key-qiso_examples [data-testid="stHorizontalBlock"] {
        flex-wrap:wrap;
    }
    .st-key-qiso_examples [data-testid="stColumn"] {
        min-width:100% !important;
        width:100% !important;
    }
    .st-key-qiso_examples [data-testid="stButton"] button {
        min-height:54px;
    }
    .st-key-qiso_user_turn,
    .st-key-qiso_assistant_turn {
        width:100%;
    }
    .qiso-user-bubble {
        padding:.8rem .9rem;
        font-size:.94rem;
    }
    .st-key-qiso_answer_card {
        padding:1rem .9rem .85rem;
    }
    .st-key-qiso_inline_sources {
        margin-top:.75rem;
        padding-top:.7rem;
    }
    .st-key-qiso_root [data-testid="stExpander"] summary {
        min-height:44px;
    }
    .st-key-qiso_root [data-testid="stExpander"] summary p {
        font-size:.8rem;
        overflow-wrap:anywhere;
    }
    .qiso-footer {
        font-size:.7rem;
        padding-top:1rem;
    }
}

/* Small phones. */
@media (max-width: 480px) {
    [data-testid="stMain"] .block-container {
        padding-inline:.65rem;
    }
    .qiso-page-label { font-size:.8rem; }
    .st-key-qiso_language_controls [data-testid="stMarkdownContainer"] p {
        font-size:.71rem;
    }
    .qiso-chat-role { font-size:.74rem; }
    .qiso-chat-avatar {
        width:25px;
        height:25px;
        flex-basis:25px;
    }
    .qiso-answer-meta { font-size:.68rem; }
}
@media (prefers-reduced-motion: reduce) {
    .st-key-qiso_root *, .st-key-qiso_sidebar * { transition:none !important; }
}
"""


def apply_styles(language: str = "ar", input_direction: str | None = None) -> None:
    """Inject only controlled CSS via st.html, never through Markdown parsing."""
    arabic = language == "ar"
    if input_direction not in {"rtl", "ltr"}:
        input_direction = "rtl" if arabic else "ltr"
    css = (CSS.replace("__DIR__", "rtl" if arabic else "ltr")
           .replace("__ALIGN__", "right" if arabic else "left")
           .replace("__INPUT_DIR__", input_direction)
           .replace("__INPUT_ALIGN__", "right" if input_direction == "rtl" else "left")
           .replace("__BODY_FONT__", "var(--qiso-arabic)" if arabic else "var(--qiso-font)"))
    st.html(f"<style>{css}</style>")
