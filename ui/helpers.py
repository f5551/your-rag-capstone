"""UI text, session actions, display formatting, and the result contract."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
from html import escape
import math
import re
import unicodedata
from typing import Any
from uuid import uuid4

import streamlit as st

MAX_HISTORY = 5
DEFAULT_TOP_K = 5
DEFAULT_CANDIDATE_K = 20

# Arabic is the default UI language. Source passages retain their own direction.
TEXT: dict[str, tuple[str, str]] = {
    "assistant": ("المساعد الذكي", "Assistant"),
    "new": ("سؤال جديد", "New question"),
    "history": ("سجل الأسئلة", "Question history"),
    "sources_page": ("المصادر المسترجعة", "Retrieved sources"),
    "settings": ("الإعدادات", "Settings"),
    "workspace": ("مساحة العمل", "WORKSPACE"),
    "recent": ("الأسئلة الأخيرة", "RECENT QUESTIONS"),
    "welcome": ("مرحبًا بك في QISO", "Welcome to QISO"),
    "description": (
        "ابحث في معايير ISO وإدارة الجودة. اطرح سؤالك، ثم راجع الإجابة ومقاطع المصادر.",
        "Explore ISO standards and quality management. Ask a question, then review the answer and its retrieved evidence.",
    ),
    "eyebrow": ("معرفة موثقة. جودة أوضح.", "Trusted knowledge. Clearer quality."),
    "question": ("سؤالك", "Your question"),
    "placeholder": ("اكتب سؤالك هنا...", "Type your question here..."),
    "send": ("إرسال", "Ask QISO"),
    "input_hint": ("العربية والإنجليزية • أسئلة مستقلة", "Arabic & English | Independent questions"),
    "examples": ("أمثلة على الأسئلة", "A few places to start"),
    "example_help": ("اضغط لنسخ السؤال إلى حقل الكتابة، دون إرساله.", "Fill the question box without sending an API request."),
    "answer": ("إجابة QISO", "QISO answer"),
    "you": ("سؤالك", "You asked"),
    "sources": ("المقاطع المسترجعة", "Retrieved passages"),
    "source_count": ("مقاطع مسترجعة", "retrieved passages"),
    "page": ("صفحة PDF", "PDF page"),
    "passage_missing": ("لم يرجع المولد نص المقطع.", "The generator did not return the passage text."),
    "no_sources": ("لا توجد مقاطع مسترجعة لهذه الإجابة.", "No passages were returned for this answer."),
    "evidence_note": (
        "هذه المقاطع أُرسلت للنموذج. ظهورها لا يعني أن كل مقطع يدعم الإجابة؛ راجع الاستشهادات.",
        "These passages were supplied to the model. Retrieval alone does not establish support for a claim; check the citations.",
    ),
    "diagnostics": ("تفاصيل تقنية", "Technical details"),
    "retrieval": ("استرجاع وإعادة ترتيب", "Retrieval + reranking"),
    "generation": ("توليد الإجابة", "Generation"),
    "total": ("الزمن الكلي", "Total time"),
    "seconds": ("ث", "s"),
    "model": ("النموذج", "Model"),
    "working": ("جارٍ البحث في المصادر وإعداد الإجابة...", "Searching the sources and preparing your answer..."),
    "working_hint": ("قد يستغرق ذلك بضع ثوانٍ. لا تغلق الصفحة أثناء المعالجة.", "This may take a few seconds. Keep this page open while QISO works."),
    "empty_question": ("اكتب سؤالًا قبل الإرسال.", "Enter a question before sending."),
    "error": ("تعذر إكمال الطلب. حاول مرة أخرى.", "The request could not be completed. Please try again."),
    "error_hint": ("تحقق من الاتصال وإعدادات Cohere وملفات core. لا ترسل مفتاح API.", "Check your connection, Cohere settings, and core modules. Do not share your API key."),
    "error_type": ("نوع الخطأ", "Error type"),
    "empty_history": ("لم تطرح أسئلة بعد.", "No questions yet."),
    "history_note": ("آخر خمسة أسئلة في الجلسة الحالية. السجل مؤقت وليس ذاكرة للنموذج.", "The last five questions in this browser session. This is temporary UI history, not model conversation memory."),
    "history_search": ("ابحث في أسئلة الجلسة", "Search session questions"),
    "open_answer": ("عرض الإجابة", "Open answer"),
    "no_match": ("لا توجد نتائج مطابقة.", "No matching results."),
    "source_page_note": ("مقاطع أعادها النظام لأسئلتك، وليست قائمة بكل الوثائق في Chroma.", "Passages returned for your questions, not an inventory of all documents in Chroma."),
    "choose_question": ("اختر السؤال", "Choose a question"),
    "source_search": ("ابحث باسم الملف أو نص المقطع", "Search filenames or passage text"),
    "advanced": ("إعدادات الاسترجاع", "Retrieval settings"),
    "top_k": ("عدد المقاطع النهائية", "Final passages"),
    "top_help": ("المقاطع المرسلة إلى المولد بعد إعادة الترتيب.", "Passages supplied to generation after reranking."),
    "candidate_k": ("عدد المرشحين", "Retrieval candidates"),
    "candidate_help": ("عدد المرشحين قبل إعادة الترتيب.", "Candidate passages considered before reranking."),
    "settings_note": ("تُطبق التغييرات على السؤال التالي فقط، دون إعادة الفهرسة.", "Changes apply to the next question only. They do not re-index documents."),
    "reset_settings": ("استعادة الافتراضي", "Restore defaults"),
    "session": ("جلسة محلية", "Local session"),
    "temporary": ("السجل مؤقت في هذه الجلسة", "History is temporary in this session"),
    "clear_history": ("مسح سجل الجلسة", "Clear session history"),
    "review_notice": ("راجع نص المصدر قبل اعتماد الإجابة.", "Review the source text before relying on an answer."),
    "ui_language": ("لغة الواجهة", "Interface language"),
    "about": ("عن QISO", "About QISO"),
    "about_text": ("واجهة للبحث الهجين وإعادة الترتيب وتوليد الإجابات من مصادر QISO. لا تتضمن هذه النسخة حسابات مستخدمين أو رفع ملفات.", "A presentation layer for QISO hybrid retrieval, reranking, and answer generation. User accounts and document uploads are not included in this version."),
}

EXAMPLES = (
    ("ما الهدف من التدقيق الداخلي؟", "What is the purpose of an internal audit?", "fact_check"),
    ("ما متطلبات البند 9.2 في ISO 9001؟", "What does ISO 9001 clause 9.2 require?", "rule"),
    ("كيف أعد قائمة تحقق للتدقيق؟", "How do I prepare an audit checklist?", "checklist"),
    ("كيف أتعامل مع حالات عدم المطابقة؟", "How should nonconformities be handled?", "manage_search"),
    ("ما الأدلة التي ينبغي جمعها أثناء التدقيق؟", "What evidence should be collected during an audit?", "search"),
)


def language() -> str:
    return "en" if st.session_state.get("qiso_language") == "en" else "ar"


def tr(key: str) -> str:
    """Look up a UI label without translating user or document content."""
    return TEXT[key][1 if language() == "en" else 0]


def html_text(value: object) -> str:
    """Escape dynamic values used inside controlled decorative HTML."""
    return escape(str(value), quote=True)


def text_direction(text: str, fallback: str = "ltr") -> str:
    """Use the first strong Unicode character, like HTML dir=auto."""
    for character in str(text):
        bidi = unicodedata.bidirectional(character)
        if bidi in {"AL", "R"}:
            return "rtl"
        if bidi == "L":
            return "ltr"
    return fallback


def short_text(value: object, limit: int = 62) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def finite_number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def duration(value: object) -> str:
    number = finite_number(value)
    return "—" if number is None else f"{number:.2f} {tr('seconds')}"


def score(value: object) -> str:
    number = finite_number(value)
    return "—" if number is None else f"{number:.4f}"


def initialize_state() -> None:
    """Namespaced state; independent of keys from earlier app versions."""
    defaults: dict[str, Any] = {
        "qiso_language": "ar",
        "qiso_page": "assistant",
        "qiso_current": None,
        "qiso_history": [],
        "qiso_draft": "",
        "qiso_pending": None,
        "qiso_error": None,
        "qiso_busy": False,
        "qiso_top_k": DEFAULT_TOP_K,
        "qiso_candidate_k": DEFAULT_CANDIDATE_K,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = deepcopy(value)


def navigate(page: str) -> None:
    if page not in {"assistant", "history", "sources", "settings"}:
        raise ValueError("Unknown UI page.")
    st.session_state.qiso_page = page


def new_question() -> None:
    """Start a new independent question, retaining session history."""
    st.session_state.update({
        "qiso_page": "assistant", "qiso_current": None, "qiso_error": None,
        "qiso_pending": None, "qiso_draft": "", "_qiso_question": "",
        "qiso_busy": False,
    })


def remember_draft() -> None:
    st.session_state.qiso_draft = st.session_state.get("_qiso_question", "")


def fill_example(question: str) -> None:
    """Callback: populate the widget before its next render, never auto-send."""
    st.session_state.update({
        "qiso_draft": question, "_qiso_question": question,
        "qiso_page": "assistant", "qiso_error": None,
    })


def queue_question() -> None:
    """Callback: queue exactly one request; the entry point consumes it."""
    question = str(st.session_state.get("_qiso_question", "")).strip()
    st.session_state.qiso_draft = question
    if not question:
        st.session_state.qiso_error = {"code": "empty_question"}
        return
    st.session_state.update({
        "qiso_pending": question, "qiso_current": None, "qiso_error": None,
        "qiso_busy": True,
    })


def store_result(question: str, result: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the UI contract without changing retrieval or source numbering."""
    if not isinstance(result, Mapping):
        raise TypeError("Generator output must be a mapping.")
    answer = result.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Generator output must include non-empty answer text.")
    raw_sources = result.get("sources") or []
    if not isinstance(raw_sources, (list, tuple)):
        raise TypeError("Generator sources must be a sequence of mappings.")
    sources: list[dict[str, Any]] = []
    for index, source in enumerate(raw_sources, 1):
        if not isinstance(source, Mapping):
            raise TypeError("Every source must be a mapping.")
        clean = dict(source)
        clean.setdefault("number", index)
        clean["source"] = str(clean.get("source") or "Unknown source")
        clean["text"] = str(clean.get("text") or "")
        clean["page"] = clean.get("page") if clean.get("page") is not None else "?"
        sources.append(clean)

    record = dict(result)
    record.update({
        "id": uuid4().hex,
        "question": question,
        "answer": answer,
        "sources": sources,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "request_settings": {
            "top_k": st.session_state.qiso_top_k,
            "candidate_k": st.session_state.qiso_candidate_k,
        },
    })
    history = [record, *st.session_state.qiso_history][:MAX_HISTORY]
    st.session_state.update({
        "qiso_current": record, "qiso_history": history,
        "qiso_error": None, "qiso_draft": "", "_qiso_question": "",
        "qiso_busy": False,
    })
    return record


def open_record(record_id: str) -> None:
    """Reopen a stored answer without another retrieval/generation request."""
    for record in st.session_state.qiso_history:
        if record["id"] == record_id:
            st.session_state.update({
                "qiso_current": record, "qiso_page": "assistant",
                "qiso_error": None, "qiso_draft": "", "_qiso_question": "",
                "qiso_busy": False,
            })
            return


def clear_history() -> None:
    st.session_state.qiso_history = []
    st.session_state.qiso_current = None


def save_settings() -> None:
    top_k = int(st.session_state.get("_qiso_top_k", DEFAULT_TOP_K))
    candidates = int(st.session_state.get("_qiso_candidate_k", DEFAULT_CANDIDATE_K))
    if not 3 <= top_k <= 10 or not 10 <= candidates <= 40 or candidates < top_k:
        raise ValueError("Invalid retrieval settings.")
    st.session_state.qiso_top_k = top_k
    st.session_state.qiso_candidate_k = candidates


def reset_settings() -> None:
    st.session_state.update({
        "qiso_top_k": DEFAULT_TOP_K, "qiso_candidate_k": DEFAULT_CANDIDATE_K,
        "_qiso_top_k": DEFAULT_TOP_K, "_qiso_candidate_k": DEFAULT_CANDIDATE_K,
    })


def display_error(error: Exception) -> dict[str, str]:
    """Do not expose raw provider messages, environment values, or credentials."""
    name = re.sub(r"[^A-Za-z0-9_]", "", type(error).__name__)
    return {"code": "error", "type": name or "RequestError"}
