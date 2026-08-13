"""
components/navbar.py
==============================================================================
Top-of-page header: title, subtitle, and optional right-aligned status badges
(e.g. "Live", "Last Run: ..."). Used at the top of every page for a
consistent enterprise-BI look.
"""

from __future__ import annotations

import streamlit as st


def render_page_header(title: str, subtitle: str = "", badges: list[tuple[str, str]] | None = None) -> None:
    """
    Render a consistent page header.

    Args:
        title: Main page title.
        subtitle: One-line description shown under the title.
        badges: List of (label, style) tuples, style in
            {"success", "warning", "danger", "neutral"}, rendered top-right.
    """
    header_col, badge_col = st.columns([4, 2])
    with header_col:
        st.markdown(f"## {title}")
        if subtitle:
            st.caption(subtitle)
    with badge_col:
        if badges:
            badge_html = " ".join(
                f'<span class="badge badge-{style}">{label}</span>' for label, style in badges
            )
            st.markdown(
                f'<div style="display:flex; justify-content:flex-end; gap:8px; margin-top:14px;">{badge_html}</div>',
                unsafe_allow_html=True,
            )
    st.divider()
