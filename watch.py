"""EFG Training · visualización de sesiones Apple Watch por fecha."""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


PURPLE = "#A855F7"
PINK = "#F472B6"
CYAN = "#22D3EE"
MINT = "#4ADE80"
MUTED = "#B9ABCD"


def _duration(seconds: int | float) -> str:
    seconds = max(0, int(seconds or 0))
    hours, rem = divmod(seconds, 3600)
    mins, sec = divmod(rem, 60)
    return f"{hours}:{mins:02d}:{sec:02d}" if hours else f"{mins:02d}:{sec:02d}"


def _summary_rows(workouts: list[dict]) -> list[dict]:
    rows = []
    for item in workouts:
        if not isinstance(item, dict):
            continue
        try:
            session_day = date.fromisoformat(str(item.get("date", "")))
            duration = max(0, int(item["duration_seconds"]))
            active = max(0, int(item["active_kcal"]))
            total = max(0, int(item["total_kcal"]))
            heart = max(0, int(item["avg_hr_bpm"]))
        except (TypeError, ValueError, KeyError):
            continue
        if duration > 86400 or active > 10000 or total > 10000 or heart > 250:
            continue
        rows.append({
            "Fecha": session_day,
            "Hora": str(item.get("start_time", "")),
            "Actividad": str(item.get("activity", "Entrenamiento")),
            "Duración (min)": round(duration / 60, 2),
            "Duración": _duration(duration),
            "Calorías activas": active,
            "Calorías totales": total,
            "FC media": heart,
            "Zonas": item.get("hr_zones_seconds", {}),
        })
    return sorted(rows, key=lambda row: (row["Fecha"], row["Hora"]))


def render_watch_dashboard(
    workouts: list[dict],
    *,
    offline: bool = False,
    plot_layout=None,
) -> None:
    st.markdown("### ⌚ Apple Watch · Rendimiento por fecha")
    st.caption(
        "Entrenamientos registrados desde las capturas de Apple Fitness. "
        "Se ordenan por la fecha real de cada sesión."
    )
    if offline:
        st.warning("No se pudo actualizar el historial de Apple Watch desde GitHub.")
    rows = _summary_rows(workouts)
    if not rows:
        st.info("Todavía no hay sesiones de Apple Watch confirmadas para mostrar.")
        return

    df = pd.DataFrame(rows)
    latest = rows[-1]
    a, b, c, d = st.columns(4)
    a.metric("Sesiones", str(len(rows)))
    b.metric("Tiempo acumulado", _duration(round(df["Duración (min)"].sum() * 60)))
    c.metric("Kcal activas estimadas", f"{df['Calorías activas'].sum():,}".replace(",", "."))
    d.metric("FC media · última sesión", f"{latest['FC media']} lpm")

    st.markdown("#### 📈 Evolución entre entrenamientos")
    selected = st.radio(
        "Indicador",
        ["Calorías activas", "Frecuencia cardíaca", "Duración"],
        horizontal=True, key="apple_watch_plot_metric",
    )
    choices = {
        "Calorías activas": ("Calorías activas", "kcal activas (estimadas)", PINK),
        "Frecuencia cardíaca": ("FC media", "FC promedio (lpm)", CYAN),
        "Duración": ("Duración (min)", "Duración del entrenamiento (min)", PURPLE),
    }
    column, unit, color = choices[selected]
    ordered = df.sort_values(["Fecha", "Hora"])
    fig = go.Figure(go.Scatter(
        x=ordered["Fecha"],
        y=ordered[column],
        mode="lines+markers",
        line=dict(color=color, width=3),
        marker=dict(size=12, color=color, line=dict(color="#FFFFFF", width=1)),
        hovertemplate=f"%{{x|%d/%m/%Y}}<br>%{{y:.1f}} {unit}<extra></extra>",
    ))
    fig.update_layout(
        xaxis=dict(title="Fecha", type="date", tickformat="%d/%m/%Y"),
        yaxis_title=unit,
        margin=dict(l=10, r=15, t=25, b=32),
    )
    if plot_layout is not None:
        fig = plot_layout(fig, 350)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("#### ❤️ Zonas cardíacas · última sesión")
    st.caption(
        f"{latest['Fecha'].strftime('%d/%m/%Y')} · {latest['Actividad']} "
        f"· {latest['Duración']} · {latest['Calorías activas']} kcal activas"
    )
    zones = latest["Zonas"] if isinstance(latest["Zonas"], dict) else {}
    colors = ["#60A5FA", "#5EEAD4", "#BEF264", "#FB923C", "#F472B6"]
    labels = ["Zona 1", "Zona 2", "Zona 3", "Zona 4", "Zona 5"]
    seconds = [max(0, int(zones.get(f"z{i}", 0))) for i in range(1, 6)]
    if any(seconds):
        fig_zone = go.Figure(go.Bar(
            x=[s / 60 for s in seconds], y=labels, orientation="h",
            marker_color=colors,
            text=[_duration(s) for s in seconds],
            textposition="outside",
            hovertemplate="%{y}: %{text}<extra></extra>",
        ))
        fig_zone.update_layout(
            xaxis_title="Minutos por zona",
            yaxis=dict(autorange="reversed"),
            margin=dict(l=10, r=25, t=15, b=35),
        )
        if plot_layout is not None:
            fig_zone = plot_layout(fig_zone, 300)
        st.plotly_chart(
            fig_zone, use_container_width=True,
            config={"displayModeBar": False},
        )
    else:
        st.info("Esta sesión no tiene tiempo por zona registrado.")

    st.markdown("#### 📅 Historial cronológico")
    visible = df.drop(columns=["Zonas", "Duración (min)"]).sort_values(
        ["Fecha", "Hora"], ascending=[False, False]
    ).rename(columns={
        "Calorías activas": "Kcal activas",
        "Calorías totales": "Kcal totales",
        "FC media": "FC media (lpm)",
    })
    st.dataframe(
        visible, use_container_width=True, hide_index=True,
        column_config={"Fecha": st.column_config.DateColumn(format="DD/MM/YYYY")},
    )
    st.caption(
        "Las calorías son estimaciones del Apple Watch, no una medición directa. "
        "Los datos de actividad se presentan separados de las estadísticas de fuerza."
    )
