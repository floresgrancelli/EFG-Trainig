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


def render_day_watch_summary(
    workouts: list[dict], plan_week: int, plan_day: int
) -> None:
    """Resumen Apple Watch asociado a la semana y al día de entrenamiento.

    Los datos de Apple Watch se muestran separados de las cargas y series.
    No se inventa una sesión de fuerza si aún no se registraron sus ejercicios.
    """
    day_items = []
    for record in workouts:
        if not isinstance(record, dict):
            continue
        try:
            if (int(record.get("plan_week", -1)) == plan_week
                    and int(record.get("plan_day", -1)) == plan_day
                    and int(record.get("duration_seconds", 0)) > 0):
                date.fromisoformat(str(record.get("date", "")))
                day_items.append(record)
        except (TypeError, ValueError):
            continue
    if not day_items:
        return
    day_items.sort(key=lambda record: (str(record.get("date", "")),
                                      str(record.get("start_time", ""))))
    for item in day_items:
        day = date.fromisoformat(str(item["date"]))
        start = str(item.get("start_time", ""))
        end = str(item.get("end_time", ""))
        hour_label = f"{start}–{end}" if end else start
        st.markdown("#### ⌚ Apple Fitness · Captura registrada")
        st.caption(
            f"{day.strftime('%d/%m/%Y')} · {hour_label} · "
            f"{item.get('activity', 'Entrenamiento')} · Datos de Apple Fitness"
        )
        a, b = st.columns(2)
        a.metric("Duración", _duration(item.get("duration_seconds", 0)))
        b.metric("FC media", f"{int(item.get('avg_hr_bpm', 0))} lpm")
        c, d = st.columns(2)
        c.metric("Kcal activas (estimadas)", str(item.get("active_kcal", "—")))
        d.metric("Kcal totales (estimadas)", str(item.get("total_kcal", "—")))
        zones = item.get("hr_zones_seconds", {})
        if isinstance(zones, dict) and zones:
            st.caption(
                f"Zonas cardíacas: Z1 {_duration(zones.get('z1', 0))} · "
                f"Z2 {_duration(zones.get('z2', 0))} · "
                f"Z3–Z5: {_duration(sum(int(zones.get(f'z{i}', 0)) for i in (3, 4, 5)))}."
            )
        recovery = item.get("post_workout_hr_bpm")
        if isinstance(recovery, dict):
            st.caption(
                f"Recuperación de FC: al terminar {recovery.get('at_end', '—')} lpm "
                f"· al minuto {recovery.get('minute_1', '—')} lpm "
                f"· a los 2 minutos {recovery.get('minute_2', '—')} lpm."
            )
        st.caption(
            "Datos cargados manualmente desde tus capturas de Apple Fitness, "
            "sin conexión con el reloj. Las series, repeticiones y cargas "
            "se guardan por separado en el registro de entrenamiento."
        )


def render_watch_dashboard(
    workouts: list[dict],
    *,
    offline: bool = False,
    plot_layout=None,
) -> None:
    st.markdown("### ⌚ Apple Fitness · Datos de capturas")
    st.caption(
        "Datos transcritos manualmente de las capturas que compartiste. "
        "EFG Training NO está conectada al Apple Watch ni sincroniza datos en tiempo real. "
        "Se ordenan por la fecha real de cada entrenamiento."
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

    latest_recovery = next(
        (record.get("post_workout_hr_bpm") for record in workouts
         if isinstance(record, dict)
         and record.get("date") == latest["Fecha"].isoformat()
         and record.get("start_time") == latest["Hora"]),
        None,
    )
    if isinstance(latest_recovery, dict):
        st.markdown("#### ❤️ FC tras finalizar · última sesión")
        e, f, g = st.columns(3)
        e.metric("Al finalizar", f"{latest_recovery.get('at_end', '—')} lpm")
        f.metric("Al minuto", f"{latest_recovery.get('minute_1', '—')} lpm")
        g.metric("A los 2 minutos", f"{latest_recovery.get('minute_2', '—')} lpm")
        st.caption("Lecturas de Apple Fitness; no constituyen una prueba de recuperación estandarizada.")

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
