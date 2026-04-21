
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

COLORS = {
    "positive":   "#2ecc71",
    "negative":   "#e74c3c",
    "neutral":    "#95a5a6",
    "highlight":  "#2980b9",
    "background": "#0f1117",
    "surface":    "#1a1d27",
    "border":     "#2d2f3e",
    "text":       "#e8e8f0",
    "subtext":    "#9a9ab0",
    "sig_strong": "#f39c12",
    "sig_weak":   "#f1c40f",
}

MONTH_LABELS = ["Jan","Feb","Mar","Apr","May","Jun",
                "Jul","Aug","Sep","Oct","Nov","Dec"]

def format_return(val, as_pct=True):
    if pd.isna(val): return "—"
    if as_pct: return f"{val*100:+.2f}%"
    return f"{val:+.4f}"

def color_return(val):
    if pd.isna(val): return COLORS["neutral"]
    return COLORS["positive"] if val >= 0 else COLORS["negative"]

def make_heatmap(pivot_df, title="Seasonality Heatmap", fmt="pct"):
    """
    Build a Plotly heatmap from a pivot table.
    pivot_df: rows = series names, cols = month numbers 1-12
    fmt: "pct" multiplies by 100 for display, "bp" for basis points

    Uses robust colour scaling (5th/95th percentile of non-zero values)
    so that outliers do not wash out all other cells to grey.
    """
    if fmt == "pct":
        z = pivot_df.values * 100
        text = [[f"{v:+.1f}%" if not np.isnan(v) else "—"
                 for v in row] for row in z]
        colorbar_title = "Return (%)"
    else:
        z = pivot_df.values
        text = [[f"{v:+.0f}bp" if not np.isnan(v) else "—"
                 for v in row] for row in z]
        colorbar_title = "Change (bp)"

    # Robust colour scale: use 5th/95th percentile instead of min/max
    # This prevents a single extreme value from collapsing all others to grey.
    flat = z[~np.isnan(z)]
    if len(flat) > 0:
        vmin = np.percentile(flat, 5)
        vmax = np.percentile(flat, 95)
        # Ensure the scale is symmetric around zero
        abs_max = max(abs(vmin), abs(vmax))
        if abs_max == 0:
            abs_max = 1
        zmin, zmax = -abs_max, abs_max
    else:
        zmin, zmax = -1, 1

    fig = go.Figure(go.Heatmap(
        z=z,
        x=MONTH_LABELS,
        y=pivot_df.index.tolist(),
        text=text,
        texttemplate="%{text}",
        textfont={"size": 10},
        colorscale=[
            [0.0,  "#c0392b"],
            [0.35, "#922b21"],
            [0.5,  "#2d2f3e"],
            [0.65, "#1e8449"],
            [1.0,  "#27ae60"],
        ],
        zmin=zmin,
        zmax=zmax,
        zmid=0,
        showscale=True,
        colorbar=dict(title=colorbar_title, tickfont=dict(color="#e8e8f0")),
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(color="#e8e8f0", size=16)),
        paper_bgcolor="#0f1117",
        plot_bgcolor="#0f1117",
        font=dict(color="#e8e8f0"),
        xaxis=dict(tickfont=dict(color="#e8e8f0")),
        yaxis=dict(tickfont=dict(color="#e8e8f0", size=9), autorange="reversed"),
        margin=dict(l=200, r=40, t=60, b=40),
        height=max(400, len(pivot_df) * 22 + 100),
    )
    return fig

def make_bar_chart(months, values, title="Monthly Average Returns", fmt="pct"):
    colors = [COLORS["positive"] if v >= 0 else COLORS["negative"] for v in values]
    if fmt == "pct":
        y_vals = [v * 100 for v in values]
        y_label = "Average Return (%)"
        text = [f"{v*100:+.2f}%" for v in values]
    else:
        y_vals = values
        y_label = "Change (bp)"
        text = [f"{v:+.1f}bp" for v in values]

    fig = go.Figure(go.Bar(
        x=months,
        y=y_vals,
        marker_color=colors,
        text=text,
        textposition="outside",
        textfont=dict(size=11, color="#e8e8f0"),
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(color="#e8e8f0", size=15)),
        paper_bgcolor="#0f1117",
        plot_bgcolor="#0f1117",
        font=dict(color="#e8e8f0"),
        xaxis=dict(tickfont=dict(color="#e8e8f0")),
        yaxis=dict(title=y_label, tickfont=dict(color="#e8e8f0"),
                   zeroline=True, zerolinecolor="#2d2f3e"),
        margin=dict(l=60, r=40, t=60, b=40),
        height=400,
    )
    return fig
