"""Gráficos premium de EFG Training: planificación, adherencia y peso corporal."""
from collections import Counter
from datetime import date, timedelta
import math
import unicodedata

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PURPLE = "#A855F7"
PINK = "#F472B6"
CYAN = "#22D3EE"
MINT = "#4ADE80"
GOLD = "#FBBF24"
VIOLET = "#7C3AED"
TEXT = "#F3EDFF"
MUTED = "#B3A5C8"


def _fmt(number, decimals=1):
    return f"{number:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _style(fig, height=340, legend=False):
    fig.update_layout(
        height=height, margin=dict(l=7, r=12, t=35, b=25),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="Arial", size=12),
        showlegend=legend,
        legend=dict(orientation="h", y=-.16, font=dict(color=MUTED)),
        hoverlabel=dict(bgcolor="#241637", font_color="#FFFFFF"),
        xaxis=dict(showgrid=False, tickfont=dict(color=MUTED), zeroline=False),
        yaxis=dict(gridcolor="rgba(174,128,229,.14)",
                   tickfont=dict(color=MUTED), zeroline=False),
    )
    return fig


def _normalized(text):
    source = unicodedata.normalize("NFKD", str(text).casefold())
    return "".join(ch for ch in source if not unicodedata.combining(ch))


def _category(text):
    t = _normalized(text)
    if any(x in t for x in ("core", "abdom", "oblic", "recto", "espinal")):
        return "Core"
    if "movilidad" in t:
        return "Movilidad"
    if any(x in t for x in (
        "rodilla", "cadera", "femor", "cuadri", "aductor", "glute",
        "gemelo", "pierna",
    )):
        return "Piernas"
    if any(x in t for x in ("empuje", "triceps", "pecho", "deltoides")):
        return "Empuje"
    if any(x in t for x in ("traccion", "biceps", "dorsal")):
        return "Tracción"
    return "Otros"


def render_plan_charts(plan):
    """Información programada del Excel (no confundir con actividad realizada)."""
    st.markdown("### 🟣 Radiografía de la rutina")
    week = st.selectbox(
        "Elegí la semana para analizar la planificación",
        options=sorted({int(x["week"]) for x in plan}),
        format_func=lambda number: f"Semana {number}",
        key="efg_plan_charts_week",
    )
    selected = [x for x in plan if int(x["week"]) == week]
    count_by_area = Counter(_category(x.get("pattern", "")) for x in selected)
    colors = {"Empuje": PURPLE, "Tracción": CYAN, "Piernas": PINK,
              "Core": GOLD, "Movilidad": MINT, "Otros": "#8572AA"}

    left, right = st.columns(2)
    with left:
        st.markdown("**Distribución de ejercicios por área**")
        names = [k for k in colors if count_by_area.get(k, 0)]
        fig = go.Figure(go.Pie(
            labels=names,
            values=[count_by_area[k] for k in names],
            hole=.72,
            sort=False,
            marker=dict(colors=[colors[k] for k in names],
                        line=dict(color="#0B0917", width=3)),
            textinfo="none",
            hovertemplate="%{label}: %{value} ejercicios<extra></extra>",
        ))
        fig.update_layout(
            annotations=[dict(text=f"<b>{len(selected)}</b><br><span style='font-size:11px'>EJERCICIOS</span>",
                              x=.5, y=.5, font=dict(size=26, color=TEXT), showarrow=False)]
        )
        st.plotly_chart(_style(fig, 340, True), use_container_width=True,
                        config={"displayModeBar": False})
    with right:
        st.markdown("**Series programadas por día**")
        totals = {}
        for d in range(1, 6):
            items = [x for x in selected if int(x["day"]) == d]
            series = 0
            for item in items:
                import re
                match = re.search(r"\d+", str(item.get("series", "")))
                series += int(match.group()) if match else 0
            totals[d] = series
        labels = ["Lun", "Mar", "Mié", "Jue", "Vie"]
        fig = go.Figure(go.Bar(
            x=labels, y=list(totals.values()),
            marker=dict(color=[PURPLE, PINK, CYAN, VIOLET, MINT],
                        line=dict(color="#FFFFFF", width=.3)),
            text=[str(n) for n in totals.values()], textposition="outside",
            hovertemplate="%{x}: %{y} series planificadas<extra></extra>",
        ))
        fig.update_layout(yaxis_title="Series")
        st.plotly_chart(_style(fig), use_container_width=True,
                        config={"displayModeBar": False})
    st.caption(
        "Programa ampliado a 12 semanas con tres ciclos de cuatro semanas. "
        "Las categorías son agrupaciones descriptivas "
        "según el patrón de la planilla; no equivalen al trabajo muscular efectivo."
    )


def render_calendar(sessions):
    """Mapa de sesiones cargadas realmente, sin contar datos de referencia."""
    st.markdown("#### 🗓️ Constancia: últimos 56 días")
    today = date.today()
    start = today - timedelta(days=today.weekday()) - timedelta(weeks=7)
    counts = Counter()
    for item in sessions:
        try:
            d = date.fromisoformat(str(item["date"]))
        except (KeyError, ValueError, TypeError):
            continue
        # Cada ejercicio puede tener registro propio: contar solo días distintos
        counts[d] = 1

    z = []
    y_days = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    x_week = [(start + timedelta(weeks=w)).strftime("%d/%m") for w in range(8)]
    for weekday in range(7):
        z.append([counts[start + timedelta(days=w*7+weekday)] for w in range(8)])
    fig = go.Figure(go.Heatmap(
        x=x_week, y=y_days, z=z,
        zmin=0, zmax=1, showscale=False,
        colorscale=[[0, "#211832"], [.49, "#211832"], [.5, "#8B5CF6"], [1, "#E879F9"]],
        xgap=8, ygap=8,
        hovertemplate="Semana %{x} · %{y}<br>%{z} día registrado<extra></extra>",
    ))
    fig.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(_style(fig, 270), use_container_width=True,
                    config={"displayModeBar": False})
    st.caption("Un día iluminado significa que existe al menos una sesión guardada con esa fecha.")


def render_weight_chart(measurements):
    """Última medición de cada semana calendario; otras fechas permanecen visibles en tabla."""
    rows = []
    for item in measurements:
        try:
            d = date.fromisoformat(str(item["date"]))
            kg = float(item["kg"])
            if not math.isfinite(kg) or not (20 <= kg <= 350):
                continue
            rows.append({"Fecha": d, "Peso (kg)": kg, "Notas": str(item.get("notes", ""))})
        except (KeyError, ValueError, TypeError):
            continue

    if not rows:
        st.info(
            "Aún no hay mediciones confirmadas. Cuando el administrador cargue "
            "el peso corporal, aparecerá aquí un gráfico púrpura con la evolución semanal."
        )
        return

    df = pd.DataFrame(rows).sort_values("Fecha")
    df["Semana"] = df["Fecha"].apply(
        lambda d: d - timedelta(days=d.weekday())
    )
    weekly = df.groupby("Semana", as_index=False).tail(1).sort_values("Semana")
    first = weekly.iloc[0]
    last = weekly.iloc[-1]
    change = float(last["Peso (kg)"] - first["Peso (kg)"])

    a, b, c = st.columns(3)
    a.metric("Peso inicial", f"{_fmt(float(first['Peso (kg)']))} kg")
    b.metric("Último peso", f"{_fmt(float(last['Peso (kg)']))} kg")
    c.metric("Variación desde inicio", f"{change:+.1f} kg".replace(".", ","))

    fig = go.Figure(go.Scatter(
        x=[d.isoformat() for d in weekly["Fecha"]],
        y=weekly["Peso (kg)"],
        mode="lines+markers+text",
        text=[f"{_fmt(v)} kg" for v in weekly["Peso (kg)"]],
        textposition="top center",
        textfont=dict(color="#EACBFF", size=13),
        line=dict(color=PURPLE, width=4, shape="spline"),
        marker=dict(color=PINK, size=13, line=dict(color="#FFFFFF", width=2)),
        fill="tozeroy",
        fillcolor="rgba(168,85,247,.09)",
        hovertemplate="%{x}<br><b>%{y:.2f} kg</b><extra></extra>",
    ))
    ymin, ymax = float(weekly["Peso (kg)"].min()), float(weekly["Peso (kg)"].max())
    fig.update_layout(
        yaxis=dict(range=[max(0, ymin - 3), ymax + 3], title="kg"),
        xaxis=dict(title="Fecha de pesaje"),
    )
    st.plotly_chart(_style(fig, 380), use_container_width=True,
                    config={"displayModeBar": False})

    if len(weekly) >= 2:
        st.markdown("#### Variación respecto de la semana anterior")
        diffs = weekly["Peso (kg)"].diff().iloc[1:]
        fig2 = go.Figure(go.Bar(
            x=[d.isoformat() for d in weekly["Semana"].iloc[1:]],
            y=diffs,
            marker=dict(color=[CYAN if delta <= 0 else PINK for delta in diffs]),
            text=[f"{float(v):+.2f} kg".replace(".", ",") for v in diffs],
            textposition="outside",
            hovertemplate="%{x}: %{y:+.2f} kg<extra></extra>",
        ))
        fig2.add_hline(y=0, line=dict(color="#E2D5F4", width=.8))
        fig2.update_layout(yaxis_title="kg / semana")
        st.plotly_chart(_style(fig2, 275), use_container_width=True,
                        config={"displayModeBar": False})

    st.caption(
        "Para el gráfico se utiliza la última medición disponible de cada semana "
        "calendario (lunes a domingo). La tabla conserva todos los pesajes."
    )
    st.dataframe(df[["Fecha", "Peso (kg)", "Notas"]].sort_values("Fecha", ascending=False),
                 use_container_width=True, hide_index=True)
