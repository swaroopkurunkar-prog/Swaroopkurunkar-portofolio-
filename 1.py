import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from scipy import stats
import urllib.request
import json
import os

# ── Mumbai Real Weather via Open-Meteo (free, no API key) ────────────────────
CACHE_FILE = "mumbai_weather_2024.csv"

def fetch_mumbai_weather():
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        "?latitude=19.0760&longitude=72.8777"
        "&start_date=2024-01-01&end_date=2024-12-31"
        "&daily=temperature_2m_mean,precipitation_sum"
        "&timezone=Asia%2FKolkata"
    )
    print("🌦  Fetching real Mumbai weather from Open-Meteo...")
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read())
        daily = data["daily"]
        df_w = pd.DataFrame({
            "date":        pd.to_datetime(daily["time"]),
            "temperature": [t if t is not None else np.nan for t in daily["temperature_2m_mean"]],
            "rainfall":    [p if p is not None else 0.0    for p in daily["precipitation_sum"]],
        })
        df_w["temperature"] = df_w["temperature"].interpolate()
        df_w.to_csv(CACHE_FILE, index=False)
        print(f"✅  Got {len(df_w)} days of real Mumbai weather.")
        return df_w
    except Exception as e:
        print(f"⚠️  Live fetch failed ({e}). Using Mumbai-pattern fallback.")
        return None

# Load cached → fresh fetch → fallback
if os.path.exists(CACHE_FILE):
    print("📂  Loading cached Mumbai weather...")
    df_weather = pd.read_csv(CACHE_FILE, parse_dates=["date"])
else:
    df_weather = fetch_mumbai_weather()

if df_weather is None:
    print("🔄  Generating Mumbai-pattern synthetic data...")
    np.random.seed(42)
    dates_fb = pd.date_range("2024-01-01", periods=365, freq="D")
    temp_fb  = 28 + 4 * np.sin((np.arange(365) - 60) * 2 * np.pi / 365) + np.random.normal(0, 1.5, 365)
    monsoon  = np.zeros(365)
    monsoon[152:273] = 1
    rain_fb  = np.clip(np.random.exponential(2, 365) + 20 * monsoon * np.random.exponential(1, 365), 0, 80)
    df_weather = pd.DataFrame({"date": dates_fb, "temperature": temp_fb.round(1), "rainfall": rain_fb.round(1)})

# ── Generate Mumbai-realistic sales & traffic from real weather ───────────────
np.random.seed(7)
temp  = df_weather["temperature"].values
rain  = df_weather["rainfall"].values
N     = len(temp)
dates = pd.to_datetime(df_weather["date"])

is_weekend = (dates.dt.dayofweek >= 5).astype(float)

sales = (
    45000
    - 400  * np.clip(temp - 30, 0, None)
    - 500  * rain
    + np.random.normal(0, 2500, N)
    + 8000 * is_weekend
)

traffic = (
    120000
    + 800  * np.clip(rain, 0, 5)
    - 1500 * np.clip(rain - 5, 0, None)
    - 500  * np.clip(temp - 35, 0, None)
    + np.random.normal(0, 5000, N)
    + 15000 * is_weekend
)

seasons = pd.cut(dates.dt.month, bins=[0,3,6,9,12], labels=["Winter","Spring","Summer","Monsoon"])

df = pd.DataFrame({
    "date":        dates.values,
    "temperature": temp.round(1),
    "rainfall":    rain.round(1),
    "sales":       np.clip(sales, 5000, None).round(0),
    "traffic":     np.clip(traffic, 10000, None).round(0),
    "month":       dates.dt.month,
    "month_name":  dates.dt.strftime("%b"),
    "season":      seasons,
    "day_of_week": dates.dt.day_name(),
    "week":        dates.dt.isocalendar().week.astype(int),
})

# ── Correlation helpers ───────────────────────────────────────────────────────
def pearson(x, y):
    r, p = stats.pearsonr(x, y)
    return r, p

r_temp_sales,  p1 = pearson(df.temperature, df.sales)
r_rain_traffic, p2 = pearson(df.rainfall,   df.traffic)

# ── Colour palette ────────────────────────────────────────────────────────────
BG       = "#0D1117"
SURFACE  = "#161B22"
SURFACE2 = "#1C2128"
ACCENT1  = "#58A6FF"
ACCENT2  = "#F78166"
ACCENT3  = "#3FB950"
ACCENT4  = "#D2A8FF"
TEXT     = "#E6EDF3"
MUTED    = "#8B949E"
BORDER   = "#30363D"

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor ="rgba(0,0,0,0)",
    font=dict(family="'DM Sans', sans-serif", color=TEXT, size=12),
    margin=dict(l=40, r=20, t=40, b=40),
    colorway=[ACCENT1, ACCENT2, ACCENT3, ACCENT4],
    xaxis=dict(gridcolor=BORDER, linecolor=BORDER, showgrid=True, zeroline=False),
    yaxis=dict(gridcolor=BORDER, linecolor=BORDER, showgrid=True, zeroline=False),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=BORDER),
    hoverlabel=dict(bgcolor=SURFACE2, bordercolor=BORDER, font_color=TEXT),
)

# ── KPI Cards ─────────────────────────────────────────────────────────────────
def kpi_card(title, value, sub, color=ACCENT1, icon=""):
    return html.Div([
        html.Div(icon, style={"fontSize":"1.6rem","marginBottom":"4px"}),
        html.Div(title, style={"color":MUTED,"fontSize":"0.72rem","letterSpacing":"0.08em","textTransform":"uppercase","marginBottom":"4px"}),
        html.Div(value, style={"color":color,"fontSize":"1.65rem","fontWeight":"700","fontFamily":"'DM Serif Display', serif","lineHeight":"1"}),
        html.Div(sub,   style={"color":MUTED,"fontSize":"0.78rem","marginTop":"6px"}),
    ], style={
        "background":SURFACE2, "border":f"1px solid {BORDER}",
        "borderRadius":"14px", "padding":"20px 22px",
        "flex":"1", "minWidth":"180px",
    })

# ── Figures ───────────────────────────────────────────────────────────────────
def fig_temp_sales():
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.temperature, y=df.sales, mode="markers",
        marker=dict(color=df.rainfall, colorscale="Blues", size=5, opacity=0.65,
                    colorbar=dict(title="Rainfall mm", thickness=8, len=0.6, tickfont=dict(color=MUTED, size=10))),
        name="Daily", hovertemplate="Temp: %{x}°C<br>Sales: ₹%{y:,.0f}<extra></extra>",
    ))
    m, b, *_ = stats.linregress(df.temperature, df.sales)
    xr = np.linspace(df.temperature.min(), df.temperature.max(), 100)
    fig.add_trace(go.Scatter(x=xr, y=m*xr+b, mode="lines",
        line=dict(color=ACCENT2, width=2.5, dash="dot"),
        name=f"Trend (r={r_temp_sales:.2f})", hoverinfo="skip"))
    fig.update_layout(**PLOTLY_LAYOUT, title=dict(text="Temperature × Sales — Mumbai 2024", font=dict(size=14)))
    fig.update_xaxes(title="Temperature (°C)")
    fig.update_yaxes(title="Daily Sales (₹)")
    return fig

def fig_rain_traffic():
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.rainfall, y=df.traffic, mode="markers",
        marker=dict(color=df.temperature, colorscale="RdYlGn", size=5, opacity=0.65,
                    colorbar=dict(title="Temp °C", thickness=8, len=0.6, tickfont=dict(color=MUTED, size=10))),
        name="Daily", hovertemplate="Rain: %{x}mm<br>Traffic: %{y:,.0f}<extra></extra>",
    ))
    m, b, *_ = stats.linregress(df.rainfall, df.traffic)
    xr = np.linspace(0, df.rainfall.max(), 100)
    fig.add_trace(go.Scatter(x=xr, y=m*xr+b, mode="lines",
        line=dict(color=ACCENT1, width=2.5, dash="dot"),
        name=f"Trend (r={r_rain_traffic:.2f})", hoverinfo="skip"))
    fig.update_layout(**PLOTLY_LAYOUT, title=dict(text="Rainfall × Traffic Volume — Mumbai 2024", font=dict(size=14)))
    fig.update_xaxes(title="Rainfall (mm)")
    fig.update_yaxes(title="Traffic Count")
    return fig

def fig_seasonal_heatmap(metric="sales"):
    pivot = df.groupby(["season","month_name"])[metric].mean().unstack()
    month_order = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    pivot = pivot.reindex(columns=[m for m in month_order if m in pivot.columns])
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
        colorscale="Thermal" if metric=="sales" else "Blues",
        hoverongaps=False,
        hovertemplate="%{y} – %{x}<br>Avg: %{z:,.0f}<extra></extra>",
        colorbar=dict(thickness=10, len=0.85, tickfont=dict(color=MUTED, size=10)),
    ))
    fig.update_layout(**PLOTLY_LAYOUT, title=dict(text=f"Seasonal Heatmap — Avg {metric.title()} (Mumbai)", font=dict(size=14)))
    return fig

def fig_monthly_bars():
    grp = df.groupby("month_name").agg(sales=("sales","mean"), traffic=("traffic","mean")).reindex(
        ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"])
    fig = go.Figure()
    fig.add_trace(go.Bar(x=grp.index, y=grp.sales,         name="Avg Sales",            marker_color=ACCENT2, opacity=0.88))
    fig.add_trace(go.Bar(x=grp.index, y=grp.traffic*0.35,  name="Avg Traffic (scaled)", marker_color=ACCENT1, opacity=0.88))
    fig.update_layout(**PLOTLY_LAYOUT, barmode="group", title=dict(text="Monthly Averages — Mumbai 2024", font=dict(size=14)))
    return fig

def fig_rain_buckets():
    df2 = df.copy()
    df2["rain_bucket"] = pd.cut(df2.rainfall,
        bins=[-0.1,1,5,15,30,100],
        labels=["Dry (0-1mm)","Light (1-5mm)","Moderate (5-15mm)","Heavy (15-30mm)","Very Heavy (30+mm)"])
    grp = df2.groupby("rain_bucket", observed=True).agg(
        sales_pct=  ("sales",   lambda x: (x.mean()/df.sales.mean()-1)*100),
        traffic_pct=("traffic", lambda x: (x.mean()/df.traffic.mean()-1)*100),
    ).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=grp.rain_bucket, y=grp.sales_pct,   name="Sales Δ%",   marker_color=ACCENT2))
    fig.add_trace(go.Bar(x=grp.rain_bucket, y=grp.traffic_pct, name="Traffic Δ%", marker_color=ACCENT1))
    fig.add_hline(y=0, line_color=MUTED, line_dash="dot")
    fig.update_layout(**PLOTLY_LAYOUT, barmode="group",
        title=dict(text="% Change vs Average by Rain Intensity (Mumbai)", font=dict(size=14)))
    fig.update_yaxes(title="% vs baseline")
    return fig

def fig_weekly_heatmap(metric="sales"):
    dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    pivot = df.pivot_table(values=metric, index="day_of_week", columns="week", aggfunc="mean")
    pivot = pivot.reindex(dow_order)
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
        colorscale="Magma", hoverongaps=False,
        hovertemplate="Week %{x} / %{y}<br>Avg: %{z:,.0f}<extra></extra>",
        colorbar=dict(thickness=10, len=0.85, tickfont=dict(color=MUTED, size=10)),
    ))
    fig.update_layout(**PLOTLY_LAYOUT, title=dict(text=f"Day × Week Heatmap — {metric.title()} (Mumbai)", font=dict(size=14)))
    return fig

# ── App layout ────────────────────────────────────────────────────────────────
FONTS = html.Link(rel="stylesheet",
    href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap")

app = dash.Dash(__name__, title="WeatherLens Mumbai",
    meta_tags=[{"name":"viewport","content":"width=device-width,initial-scale=1"}])
server = app.server

heavy_rain_rows = df[df.rainfall > 15]
heavy_traffic_delta = (
    f"−{abs(int(round((heavy_rain_rows.traffic.mean()/df.traffic.mean()-1)*100)))}% traffic"
    if len(heavy_rain_rows) > 0 else "N/A"
)

app.layout = html.Div([
    FONTS,

    # HEADER
    html.Div([
        html.Div([
            html.Span("🌧️", style={"fontSize":"2rem","verticalAlign":"middle","marginRight":"10px"}),
            html.Span("WeatherLens", style={"fontFamily":"'DM Serif Display',serif","fontSize":"1.8rem","color":TEXT}),
            html.Span(" Mumbai · 2024", style={"color":MUTED,"fontSize":"1rem","fontWeight":"300","marginLeft":"6px"}),
        ]),
        html.Div("Real weather data · How monsoon, heat & seasons shape Mumbai's sales and traffic.",
            style={"color":MUTED,"fontSize":"0.85rem","marginTop":"4px"}),
    ], style={"padding":"28px 40px 20px","borderBottom":f"1px solid {BORDER}",
              "background":f"linear-gradient(135deg, {SURFACE} 0%, {BG} 100%)"}),

    # KPI ROW
    html.Div([
        kpi_card("Temp → Sales",         f"r = {r_temp_sales:.2f}",  "Correlation coefficient", ACCENT3, "🌡️"),
        kpi_card("Rain → Traffic",        f"r = {r_rain_traffic:.2f}", "Correlation coefficient", ACCENT2, "🌧️"),
        kpi_card("Peak Sales Month",      df.groupby("month_name")["sales"].mean().idxmax(),
                 "Highest avg daily revenue", ACCENT1, "📈"),
        kpi_card("Heavy Rain Impact",     heavy_traffic_delta, "Traffic during 15+ mm days", ACCENT4, "⛈️"),
    ], style={"display":"flex","flexWrap":"wrap","gap":"16px","padding":"24px 40px","background":BG}),

    # CONTROLS
    html.Div([
        html.Div([
            html.Label("Heatmap Metric", style={"color":MUTED,"fontSize":"0.75rem","letterSpacing":"0.07em","textTransform":"uppercase"}),
            dcc.Dropdown(id="heatmap-metric",
                options=[{"label":"Sales","value":"sales"},{"label":"Traffic","value":"traffic"}],
                value="sales", clearable=False,
                style={"backgroundColor":SURFACE2,"color":TEXT,"border":f"1px solid {BORDER}","borderRadius":"8px","width":"160px"}),
        ]),
        html.Div([
            html.Label("Season Filter", style={"color":MUTED,"fontSize":"0.75rem","letterSpacing":"0.07em","textTransform":"uppercase"}),
            dcc.Checklist(id="season-filter",
                options=[{"label":s,"value":s} for s in ["Winter","Spring","Summer","Monsoon"]],
                value=["Winter","Spring","Summer","Monsoon"],
                inline=True,
                labelStyle={"marginRight":"14px","color":TEXT,"fontSize":"0.85rem"}),
        ]),
    ], style={"display":"flex","flexWrap":"wrap","gap":"28px","alignItems":"flex-end",
              "padding":"0 40px 20px","background":BG}),

    # CHARTS
    html.Div([
        html.Div([
            html.Div(dcc.Graph(id="fig-temp-sales",   figure=fig_temp_sales(),   config={"displayModeBar":False}),
                style={"flex":"1","minWidth":"300px","background":SURFACE,"borderRadius":"16px","border":f"1px solid {BORDER}","padding":"8px"}),
            html.Div(dcc.Graph(id="fig-rain-traffic", figure=fig_rain_traffic(), config={"displayModeBar":False}),
                style={"flex":"1","minWidth":"300px","background":SURFACE,"borderRadius":"16px","border":f"1px solid {BORDER}","padding":"8px"}),
        ], style={"display":"flex","flexWrap":"wrap","gap":"16px","marginBottom":"16px"}),

        html.Div([
            html.Div(dcc.Graph(id="fig-seasonal-heatmap", config={"displayModeBar":False}),
                style={"flex":"1.2","minWidth":"300px","background":SURFACE,"borderRadius":"16px","border":f"1px solid {BORDER}","padding":"8px"}),
            html.Div(dcc.Graph(id="fig-monthly-bars", figure=fig_monthly_bars(), config={"displayModeBar":False}),
                style={"flex":"1","minWidth":"300px","background":SURFACE,"borderRadius":"16px","border":f"1px solid {BORDER}","padding":"8px"}),
        ], style={"display":"flex","flexWrap":"wrap","gap":"16px","marginBottom":"16px"}),

        html.Div([
            html.Div(dcc.Graph(id="fig-rain-buckets",  config={"displayModeBar":False}),
                style={"flex":"1","minWidth":"300px","background":SURFACE,"borderRadius":"16px","border":f"1px solid {BORDER}","padding":"8px"}),
            html.Div(dcc.Graph(id="fig-weekly-heatmap",config={"displayModeBar":False}),
                style={"flex":"1","minWidth":"300px","background":SURFACE,"borderRadius":"16px","border":f"1px solid {BORDER}","padding":"8px"}),
        ], style={"display":"flex","flexWrap":"wrap","gap":"16px"}),

    ], style={"padding":"0 40px 40px","background":BG}),

    # FOOTER
    html.Div("WeatherLens · Mumbai 2024 · Weather: Open-Meteo · Built with Python, Dash & Plotly",
        style={"textAlign":"center","color":MUTED,"fontSize":"0.78rem","padding":"18px",
               "borderTop":f"1px solid {BORDER}","background":SURFACE}),

], style={"fontFamily":"'DM Sans', sans-serif","background":BG,"minHeight":"100vh","color":TEXT})

# ── Callbacks ─────────────────────────────────────────────────────────────────
@callback(
    Output("fig-seasonal-heatmap","figure"),
    Output("fig-rain-buckets",    "figure"),
    Output("fig-weekly-heatmap",  "figure"),
    Output("fig-temp-sales",      "figure"),
    Output("fig-rain-traffic",    "figure"),
    Input("heatmap-metric", "value"),
    Input("season-filter",  "value"),
)
def update_charts(metric, seasons_selected):
    return (
        fig_seasonal_heatmap(metric),
        fig_rain_buckets(),
        fig_weekly_heatmap(metric),
        fig_temp_sales(),
        fig_rain_traffic(),
    )

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)