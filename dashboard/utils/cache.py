"""
utils/cache.py
==============================================================================
Small caching utilities layered on top of Streamlit's native cache decorators.
Kept separate from database/queries.py so cache-clearing / cache-key logic
isn't tangled with SQL.
"""

from __future__ import annotations

import streamlit as st


def clear_all_caches() -> None:
    """Clear both data and resource caches — used by the sidebar 'Refresh' button."""
    st.cache_data.clear()
    st.cache_resource.clear()


def get_last_refresh_key() -> str:
    """Session-scoped timestamp key so components can show 'last refreshed at'."""
    if "last_refresh" not in st.session_state:
        import datetime as dt
        st.session_state["last_refresh"] = dt.datetime.now().strftime("%H:%M:%S")
    return st.session_state["last_refresh"]


def bump_last_refresh() -> None:
    """Update the last-refresh marker; call after clear_all_caches()."""
    import datetime as dt
    st.session_state["last_refresh"] = dt.datetime.now().strftime("%H:%M:%S")
