from __future__ import annotations
import datetime as dt
import streamlit as st
from database.queries import get_filter_options


def render_filter_bar(show: tuple[str, ...] = ("date", "country", "category", "gender", "marital_status")) -> dict:
    """
    Render the filter widgets requested in `show` and return the current
    selections as a dict ready to unpack into query functions.

    Returns:
        {
            "date_range": (start_date, end_date) | None,
            "country": list[str] | None,
            "category": list[str] | None,
            "gender": list[str] | None,
            "marital_status": list[str] | None,
        }
    """
    options = get_filter_options()
    selections: dict = {"date_range": None, "country": None, "category": None, "gender": None, "marital_status": None}

    with st.container():
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        cols = st.columns(len(show))

        for col, key in zip(cols, show):
            with col:
                if key == "date" and options.get("min_date") and options.get("max_date"):
                    min_d, max_d = options["min_date"], options["max_date"]
                    if isinstance(min_d, dt.datetime):
                        min_d = min_d.date()
                    if isinstance(max_d, dt.datetime):
                        max_d = max_d.date()
                    date_val = st.date_input("Date Range", value=(min_d, max_d), min_value=min_d, max_value=max_d, key="filter_date")
                    if isinstance(date_val, tuple) and len(date_val) == 2:
                        selections["date_range"] = date_val

                elif key == "country":
                    selections["country"] = st.multiselect("Country", options.get("countries", []), key="filter_country") or None

                elif key == "category":
                    selections["category"] = st.multiselect("Category", options.get("categories", []), key="filter_category") or None

                elif key == "gender":
                    selections["gender"] = st.multiselect("Gender", options.get("genders", []), key="filter_gender") or None

                elif key == "marital_status":
                    selections["marital_status"] = st.multiselect("Marital Status", options.get("marital_statuses", []), key="filter_marital") or None

        st.markdown('</div>', unsafe_allow_html=True)

    return selections
