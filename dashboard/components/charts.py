"""
components/charts.py
==============================================================================
Reusable Plotly chart builders, all themed for the dark enterprise-BI look
defined in config.AppSettings. Every function returns a `go.Figure` — pages
are responsible for `st.plotly_chart(fig, use_container_width=True)`.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import APP_SETTINGS

_PALETTE = ["#6366F1", "#8B5CF6", "#22C55E", "#F59E0B", "#EF4444", "#06B6D4", "#EC4899", "#84CC16"]

_LAYOUT_DEFAULTS = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=APP_SETTINGS.text_primary, family="Segoe UI, sans-serif", size=12),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hoverlabel=dict(bgcolor=APP_SETTINGS.bg_card, font_color=APP_SETTINGS.text_primary),
)


def _apply_theme(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(**_LAYOUT_DEFAULTS, title=dict(text=title, font=dict(size=15)))
    fig.update_xaxes(gridcolor=APP_SETTINGS.border_color, zerolinecolor=APP_SETTINGS.border_color)
    fig.update_yaxes(gridcolor=APP_SETTINGS.border_color, zerolinecolor=APP_SETTINGS.border_color)
    return fig


def line_chart(df: pd.DataFrame, x: str, y: str, title: str = "", color: str | None = None) -> go.Figure:
    """Line/trend chart — used for monthly/daily sales, customer growth."""
    fig = px.line(df, x=x, y=y, color=color, markers=True, color_discrete_sequence=_PALETTE)
    fig.update_traces(line=dict(width=3), marker=dict(size=6))
    return _apply_theme(fig, title)


def area_chart(df: pd.DataFrame, x: str, y: str, title: str = "") -> go.Figure:
    """Filled area chart — used for revenue trend with visual weight."""
    fig = px.area(df, x=x, y=y, color_discrete_sequence=_PALETTE)
    fig.update_traces(line=dict(width=2), fillcolor="rgba(99, 102, 241, 0.25)")
    return _apply_theme(fig, title)


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str = "", horizontal: bool = False, color: str | None = None) -> go.Figure:
    """Vertical or horizontal bar chart."""
    if horizontal:
        fig = px.bar(df, x=y, y=x, orientation="h", color=color, color_discrete_sequence=_PALETTE)
        fig.update_yaxes(categoryorder="total ascending")
    else:
        fig = px.bar(df, x=x, y=y, color=color, color_discrete_sequence=_PALETTE)
    fig.update_traces(marker_line_width=0)
    return _apply_theme(fig, title)


def donut_chart(df: pd.DataFrame, names: str, values: str, title: str = "") -> go.Figure:
    """Donut chart — used for category/gender/product-line breakdowns."""
    fig = px.pie(df, names=names, values=values, hole=0.55, color_discrete_sequence=_PALETTE)
    fig.update_traces(textposition="outside", textinfo="percent+label")
    return _apply_theme(fig, title)


def treemap_chart(df: pd.DataFrame, path: list[str], values: str, title: str = "") -> go.Figure:
    """Treemap — used for category > subcategory revenue contribution."""
    fig = px.treemap(df, path=path, values=values, color_discrete_sequence=_PALETTE)
    fig.update_traces(marker=dict(line=dict(color=APP_SETTINGS.bg_primary, width=2)))
    return _apply_theme(fig, title)


def scatter_chart(df: pd.DataFrame, x: str, y: str, size: str | None = None, color: str | None = None, title: str = "") -> go.Figure:
    """Scatter plot — used for quantity vs revenue analysis."""
    fig = px.scatter(df, x=x, y=y, size=size, color=color, color_discrete_sequence=_PALETTE)
    return _apply_theme(fig, title)


def heatmap_chart(df: pd.DataFrame, x: str, y: str, z: str, title: str = "") -> go.Figure:
    """Calendar/matrix heatmap — used for revenue-by-day-of-week x month."""
    pivot = df.pivot(index=y, columns=x, values=z)
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index,
        colorscale=[[0, APP_SETTINGS.bg_card], [1, APP_SETTINGS.accent_color]],
        hoverongaps=False,
    ))
    return _apply_theme(fig, title)


def gauge_chart(value: float, title: str = "", max_value: float = 100) -> go.Figure:
    """Gauge chart — used for the Data Quality Score."""
    if value >= 90:
        bar_color = APP_SETTINGS.success_color
    elif value >= 70:
        bar_color = APP_SETTINGS.warning_color
    else:
        bar_color = APP_SETTINGS.danger_color

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": "%", "font": {"size": 36, "color": APP_SETTINGS.text_primary}},
        gauge={
            "axis": {"range": [0, max_value], "tickcolor": APP_SETTINGS.text_secondary},
            "bar": {"color": bar_color},
            "bgcolor": APP_SETTINGS.bg_card,
            "borderwidth": 0,
            "steps": [
                {"range": [0, 70], "color": "rgba(239,68,68,0.12)"},
                {"range": [70, 90], "color": "rgba(245,158,11,0.12)"},
                {"range": [90, 100], "color": "rgba(34,197,94,0.12)"},
            ],
        },
        title={"text": title, "font": {"size": 14, "color": APP_SETTINGS.text_secondary}},
    ))
    fig.update_layout(**{**_LAYOUT_DEFAULTS, "margin": dict(l=20, r=20, t=50, b=10), "height": 260})
    return fig


def funnel_or_pipeline_chart(stages: list[str], values: list[int], title: str = "") -> go.Figure:
    """Horizontal funnel — used for Bronze -> Silver -> Gold row-count flow."""
    fig = go.Figure(go.Funnel(
        y=stages,
        x=values,
        marker={"color": ["#CD7F32", "#C0C0C0", "#FFD700"][: len(stages)]},
        textinfo="value+percent initial",
    ))
    return _apply_theme(fig, title)
