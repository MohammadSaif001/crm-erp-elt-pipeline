"""Shared editorial shell for the ELT operational report."""

from __future__ import annotations

from html import escape

import streamlit as st

from config import APP_SETTINGS


def apply_report_styles() -> None:
    """Load the one visual system used by every Streamlit page."""
    with open(APP_SETTINGS.styles_path, encoding="utf-8") as styles:
        st.markdown(f"<style>{styles.read()}</style>", unsafe_allow_html=True)


def render_site_header(section: str) -> None:
    st.markdown(
        f"""
        <header class="site-header">
          <span class="site-header__code">ELT / {escape(section.split(' / ')[0])}</span>
          <span class="site-header__title">PIPELINE HEALTH</span>
          <span class="site-header__meta">DATA ENGINEERING</span>
          <span aria-hidden="true">&#8599;</span>
        </header>
        """,
        unsafe_allow_html=True,
    )


def render_page_intro(number: str, title: str, description: str) -> None:
    """Render a consistent numbered page masthead."""
    st.markdown(
        f"""
        <section class="page-intro">
          <div class="eyebrow">{escape(number)} / {escape(title)}</div>
          <h1>{escape(title)}</h1>
          <p>{escape(description)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_section_title(number: str, title: str, description: str | None = None) -> None:
    detail = f'<p class="section-note">{escape(description)}</p>' if description else ""
    st.markdown(
        f'<div class="section-heading"><span>{escape(number)} / {escape(title)}</span>{detail}</div>',
        unsafe_allow_html=True,
    )


def status_markup(status: str) -> str:
    """Use symbol plus text for every status, never color alone."""
    normalized = status.upper()
    if normalized in {"HEALTHY", "PASS", "SUCCESS", "AVAILABLE"}:
        return '<span class="status status--pass">&#10003; PASS</span>'
    if normalized in {"WARNING", "WARN"}:
        return '<span class="status status--warning">! WARNING</span>'
    return '<span class="status status--fail">&#215; FAILED</span>'


def render_footer() -> None:
    st.markdown(
        '<footer class="report-footer">ELT PIPELINE HEALTH REPORT <span>•</span> INTERNAL OPERATIONS <span>•</span> BRONZE → SILVER → GOLD</footer>',
        unsafe_allow_html=True,
    )
