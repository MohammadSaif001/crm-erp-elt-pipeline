from __future__ import annotations
import streamlit as st
from utils.helpers import format_currency, format_number, format_percent


def render_metric_card(
    label: str,
    value: str,
    delta: float | None = None,
    delta_suffix: str = "%",
) -> None:
    """Render a single KPI card. `delta` is a signed percentage change."""
    delta_html = ""
    if delta is not None:
        css_class = "metric-delta-positive" if delta >= 0 else "metric-delta-negative"
        arrow = "▲" if delta >= 0 else "▼"
        delta_html = f'<div class="{css_class}">{arrow} {abs(delta):.1f}{delta_suffix} vs prior period</div>'

    st.markdown(
        f"""
        <div class="metric-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div class="metric-label">{label}</div>
                <div class="metric-icon"></div>
            </div>
            <div class="metric-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_row(kpis: list[dict]) -> None:
    """
    Render a row of KPI cards evenly spaced.

    Each dict in `kpis`: {"label": str, "value": str, "icon": str, "delta": float | None}
    """
    cols = st.columns(len(kpis))
    for col, kpi in zip(cols, kpis):
        with col:
            render_metric_card(
                label=kpi["label"],
                value=kpi["value"],
                delta=kpi.get("delta"),
            )


def render_executive_kpi_row(kpi_data: dict) -> None:
    """Convenience wrapper: build the standard Executive Dashboard KPI row."""
    render_kpi_row([
        {"label": "Total Revenue", "value": format_currency(kpi_data.get("total_revenue", 0))},
        {"label": "Total Orders", "value": format_number(kpi_data.get("total_orders", 0))},
        {"label": "Total Customers", "value": format_number(kpi_data.get("total_customers", 0))},
        {"label": "Total Products", "value": format_number(kpi_data.get("total_products", 0))},
        {"label": "Avg Order Value", "value": format_currency(kpi_data.get("avg_order_value", 0))},
    ])
