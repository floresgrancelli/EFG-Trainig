"""EFG Training · seguimiento público de fuerza, edición protegida por PIN.

Datos del plan: data/plan.json, migrados de la planilla original.
Entrenamientos: data/history.json, persistidos mediante GitHub Contents API.
Credenciales: Streamlit Community Cloud > App settings > Secrets.
"""
from __future__ import annotations

import base64
import csv
import hmac
import io
import json
import math
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import requests

st.set_page_config(
    page_title="EFG Training | Strength & Progress",
    page_icon="💜",
    layout="wide",
    initial_sidebar_state="collapsed",
)

REPO = "floresgrancelli/EFG-Trainig"
BRANCH = "main"
API = f"https://api.github.com/repos/{REPO}/contents"
PURPLE = "#A855F7"
VIOLET = "#7C3AED"
PINK = "#F472B6"
CYAN = "#22D3EE"
MINT = "#4ADE80"
TEXT = "#F3EDFF"
MUTED = "#AA9FBF"
BG = "#080714"
CARD = "#171328"
DAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&display=swap');
    html, body, [data-testid="stApp"], p, label, button, input {font-family:'Outfit',sans-serif}
    [data-testid="stAppViewContainer"] {
       background: radial-gradient(ellipse 50% 24% at 84% 3%,rgba(124,58,237,.20),transparent),
                   radial-gradient(ellipse 42% 25% at 10% 32%,rgba(219,39,119,.075),transparent),
                   #080714;
    }
    [data-testid="stHeader"] {background:transparent}
    .block-container {max-width:1180px; padding-top:1.35rem; padding-bottom:3rem}
    h1,h2,h3,h4 {color:#F5F1FF; letter-spacing:-.045em}
    h2 {padding-top:1rem}
    [data-testid="stMetric"] {
        background:linear-gradient(140deg,rgba(88,37,156,.24),rgba(29,24,53,.90));
        border:1px solid rgba(181,126,255,.22);
        border-radius:18px; padding:18px 18px 14px; min-height:100px;
    }
    [data-testid="stMetricLabel"] {color:#B4A8C6}
    [data-testid="stMetricValue"] {color:#F5ECFF; font-size:1.62rem}
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] {line-height:1.5}
    div[data-testid="stExpander"] {border:1px solid rgba(164,101,249,.27);
      background:rgba(22,17,40,.73); border-radius:15px; margin-bottom:.32rem}
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {gap:5px; background:rgba(13,9,26,.7);
      border:1px solid rgba(164,101,249,.16); border-radius:18px; padding:6px}
    div[data-testid="stTabs"] button {border-radius:12px; font-weight:700; color:#C3B4DC}
    div[data-testid="stTabs"] button[aria-selected="true"] {
       color:#F8F3FF; background:linear-gradient(105deg,#5A189A,#7C3AED);
    }
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {display:none}
    button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
      background:linear-gradient(110deg,#7C3AED,#C026D3)!important;
      border:1px solid rgba(250,180,255,.35)!important;
      color:white!important; font-weight:750!important;
      border-radius:12px!important;
    }
    button[kind="secondary"] {border-radius:12px!important}
    .hero {border:1px solid rgba(187,121,255,.34); border-radius:25px;
       padding:35px 39px 31px; margin-bottom:22px;
       background:radial-gradient(circle at 93% 7%,rgba(242,73,195,.24),transparent 31%),
              linear-gradient(110deg,rgba(74,29,118,.75),rgba(20,13,40,.98) 67%);
       box-shadow:0 17px 55px rgba(4,1,16,.22)}
    .hero-kicker {font-size:.72rem; letter-spacing:.23em; color:#E7BAFF;
        font-weight:850; margin-bottom:10px}
    .hero h1 {font-size:clamp(2.3rem,6vw,4.5rem)!important; margin:0!important;
       line-height:1.05; font-weight:900;
       background:linear-gradient(92deg,#FFF 2%,#E7C4FF 46%,#D99AFF 78%,#FF9EDB);
       -webkit-background-clip:text; -webkit-text-fill-color:transparent}
    .hero-sub {font-size:1.07rem;color:#D8CAE9;margin:13px 0 0}
    .pill {display:inline-block;background:rgba(124,58,237,.22);
       color:#D8B6FF; border:1px solid rgba(186,114,253,.32);
       font-size:.72rem;font-weight:800;letter-spacing:.04em;
       padding:5px 10px;border-radius:100px;margin-right:7px}
    .muted {color:#AA9FBF; font-size:.91rem}
    .status {border-radius:15px; padding:13px 16px; background:rgba(65,35,94,.24);
       border:1px solid rgba(175,119,245,.22); font-size:.87rem;color:#D6C7E8}
    .mini-title {font-size:.72rem;letter-spacing:.15em;text-transform:uppercase;
      color:#E6B3FF;font-weight:850}
    .finish {background:linear-gradient(115deg,rgba(79,46,141,.38),rgba(15,16,35,.8));
      border:1px solid rgba(184,125,254,.24);padding:19px 23px;border-radius:17px}
    @media(max-width:640px) {
      .block-container {padding:1rem .85rem 2.5rem}
      .hero {padding:24px 22px;border-radius:19px}
      .hero-sub {font-size:.92rem}
      [data-testid="stMetricValue"] {font-size:1.37rem}
      div[data-testid="stTabs"] button {font-size:.79rem;padding:0 7px}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def secret(name: str) -> str:
    try:
        return str(st.secrets.get(name, "")).strip()
    except (FileNotFoundError, KeyError, AttributeError, RuntimeError):
        return ""


def fetch_remote(path: str, token: str = "") -> tuple[dict, str]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(
        f"{API}/{path}",
        headers=headers,
        params={"ref": BRANCH},
        timeout=13,
    )
    response.raise_for_status()
    body = response.json()
    raw = base64.b64decode(body["content"]).decode("utf-8")
    return json.loads(raw), body["sha"]


@st.cache_data(ttl=45, show_spinner=False)
def public_history() -> dict:
    try:
        result, _ = fetch_remote("data/history.json")
        return result if isinstance(result.get("sessions"), list) else {"sessions": []}
    except (requests.RequestException, ValueError, KeyError, TypeError):
        # Nunca inventamos registros: si no es posible leerlos, lo indicamos.
        return {"sessions": [], "_offline": True}


def persist_remote(path: str, payload: dict, token: str, message: str) -> None:
    if not token:
        raise ValueError("Falta configurar GITHUB_TOKEN en los Secrets de Streamlit.")
    _, sha = fetch_remote(path, token)
    content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    response = requests.put(
        f"{API}/{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={
            "message": message,
            "content": base64.b64encode(content).decode("ascii"),
            "sha": sha,
            "branch": BRANCH,
        },
        timeout=18,
    )
    if response.status_code not in (200, 201):
        if response.status_code in (401, 403):
            raise ValueError("El token no autoriza la escritura. Revisá permisos de Contents.")
        if response.status_code in (409, 422):
            raise ValueError("Hubo otro cambio en el repositorio. Actualizá y volvé a guardar.")
        raise ValueError(f"GitHub no guardó el cambio (HTTP {response.status_code}).")


@st.cache_data
def load_plan_local() -> list[dict]:
    path = Path(__file__).resolve().parent / "data" / "plan.json"
    return json.loads(path.read_text(encoding="utf-8"))["entries"]


def parse_count(value: str, fallback: int = 3) -> int:
    found = re.search(r"\d+", str(value))
    return max(1, min(12, int(found.group()) if found else fallback))


def suggested_reps(value: str, n: int) -> list[int]:
    # "12-10-8-8" = valores por serie; "10/12" = rango, no dos series.
    raw = str(value)
    nums = [int(x) for x in re.findall(r"\d+", raw)]
    if len(nums) == n and "-" in raw:
        return nums
    return [nums[0] if nums else 8] * n


def fmt(v, decimal: int = 2) -> str:
    if v is None:
        return "—"
    return f"{float(v):,.{decimal}f}".replace(",", "·").replace(".", ",").replace("·", ".")


def plot_layout(fig, height=370):
    fig.update_layout(
        height=height,
        margin=dict(l=5, r=10, t=24, b=35),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial", color=TEXT, size=13),
        xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(color=MUTED)),
        yaxis=dict(gridcolor="rgba(180,140,233,.12)", zeroline=False,
                   tickfont=dict(color=MUTED)),
        hoverlabel=dict(bgcolor="#25163F", font_color="#FFFFFF"),
        showlegend=False,
    )
    return fig


def series_rows(sessions):
    all_rows = []
    for session in sessions:
        if not isinstance(session, dict):
            continue
        try:
            event_date = date.fromisoformat(str(session.get("date", "")))
        except ValueError:
            continue
        for pos, item in enumerate(session.get("sets", []), start=1):
            try:
                weight = float(item.get("kg", 0))
                reps = int(item.get("reps", 0))
            except (ValueError, TypeError):
                continue
            if not math.isfinite(weight) or weight < 0 or weight > 1500 or reps < 0 or reps > 10000:
                continue
            all_rows.append({
                "Fecha": event_date,
                "Semana del plan": int(session.get("week", 0)),
                "Día": DAY_NAMES[max(0, min(4, int(session.get("day", 1))-1))],
                "Ejercicio": str(session.get("exercise", "Sin nombre")),
                "Serie": pos,
                "Carga (kg)": round(weight, 3),
                "Repeticiones": reps,
                "Volumen": round(weight * reps, 2),
                "RIR": session.get("rir"),
                "Notas": session.get("notes", ""),
            })
    return pd.DataFrame(all_rows)


def announce(kicker, title, sub):
    st.markdown(
        f'<div class="hero"><div class="hero-kicker">{kicker}</div>'
        f'<h1>{title}</h1><div class="hero-sub">{sub}</div>'
        f'<div style="margin-top:18px"><span class="pill">5 DÍAS</span>'
        f'<span class="pill">4 SEMANAS</span>'
        f'<span class="pill">FUERZA + DATOS</span></div></div>',
        unsafe_allow_html=True,
    )


PLAN = load_plan_local()
HISTORY = public_history()
SESSIONS = HISTORY.get("sessions", [])
DF = series_rows(SESSIONS)
TOKEN = secret("GITHUB_TOKEN")
ADMIN_PIN = secret("ADMIN_PIN")

announce(
    "EFG  /  PERSONAL TRAINING SYSTEM  ·  V1.0",
    "TRAIN HARD.<br>TRACK SMART.",
    "Tu rutina, tus marcas, tu evolución. Seguimiento real con diseño premium.",
)

tabs = st.tabs(["⚡ MI RUTINA", "📊 PROGRESO", "📚 HISTORIAL", "🔐 ADMIN"])

with tabs[0]:
    st.markdown("### ⚡ Plan de entrenamiento")
    a, b, c = st.columns(3)
    a.metric("Días de entrenamiento", "05")
    b.metric("Semanas planificadas", "04")
    c.metric("Ejercicios programados", len(PLAN))
    st.markdown("")
    left, right = st.columns([1, 1])
    with left:
        week = st.selectbox("SEMANA", [1, 2, 3, 4], format_func=lambda x: f"Semana {x}")
    with right:
        day = st.selectbox("DÍA", [1, 2, 3, 4, 5],
                          format_func=lambda x: f"Día {x} · {DAY_NAMES[x-1]}")
    chosen = [r for r in PLAN if int(r["week"]) == week and int(r["day"]) == day]
    week_one_references = {
        r["exercise"].strip().casefold(): r
        for r in PLAN if r["week"] == 1 and (r.get("reference_weight_lb") is not None
                                              or r.get("reference_series_kg"))
    }
    st.markdown(
        f'<div class="finish"><div class="mini-title">TU SESIÓN</div>'
        f'<h3 style="margin:3px 0 4px">SEMANA {week} · {DAY_NAMES[day-1].upper()}</h3>'
        f'<div class="muted">{len(chosen)} ejercicios · desplegá cualquiera para ver sus indicaciones</div></div>',
        unsafe_allow_html=True,
    )
    st.write("")
    for index, ex in enumerate(chosen, 1):
        with st.expander(f"{index:02}. {ex['exercise']}  ·  {ex['series']} × {ex['repetitions']}"):
            x, y, z = st.columns(3)
            x.metric("Series", ex["series"] or "—")
            y.metric("Repeticiones", ex["repetitions"] or "—")
            z.metric("Esfuerzo", ex["intensity"] or "—")
            if ex.get("pattern"):
                st.caption(f"**Grupo / patrón:** {ex['pattern']}")
            if ex.get("block"):
                st.caption(f"**Bloque:** {ex['block']}")
            if ex.get("notes"):
                st.write(f"**Indicaciones:** {ex['notes']}")
            ref = ex if week == 1 else week_one_references.get(ex["exercise"].strip().casefold())
            if ref:
                if ref.get("reference_series_kg"):
                    string = " · ".join(f"{fmt(w)} kg" for w in ref["reference_series_kg"])
                    st.info(f"Referencia Excel (semana 1, por serie): {string}")
                elif ref.get("reference_weight_lb") is not None:
                    st.info(
                        f"Referencia Excel (semana 1): "
                        f"{fmt(ref.get('reference_weight_lb'))} lb "
                        f"≈ {fmt(ref.get('reference_weight_kg'))} kg. "
                        "No constituye un entrenamiento registrado."
                    )
            recorded = [
                r for r in SESSIONS if r.get("exercise_id") == ex["id"]
            ]
            if recorded:
                newest = sorted(recorded, key=lambda d: d.get("date", ""), reverse=True)[0]
                st.caption(
                    "Última sesión real cargada: "
                    f"{newest.get('date')} · "
                    f"{len(newest.get('sets', []))} series"
                )

    st.markdown("")
    st.caption(
        "Transcripción fiel del plan de cuatro semanas. Cargas de la planilla = referencias "
        "sin fecha, no avances semanales. Los espacios sin datos permanecen vacíos."
    )

with tabs[1]:
    st.markdown("### 📊 Tu evolución, en números")
    if HISTORY.get("_offline"):
        st.warning("No se pudo consultar el historial online. Los registros pueden no estar actualizados.")
    if DF.empty:
        st.markdown(
            '<div class="status">Todavía no hay sesiones reales guardadas. '
            'Los gráficos de progreso aparecerán al cargar los primeros entrenamientos. '
            'Mientras tanto, estas son las referencias originales de la rutina.</div>',
            unsafe_allow_html=True,
        )
        x, y, z = st.columns(3)
        x.metric("Sesiones registradas", 0)
        y.metric("Series realizadas", 0)
        z.metric("Volumen acumulado", "—")
        refs = [
            r for r in PLAN if r["week"] == 1 and
            isinstance(r.get("reference_weight_kg"), (int, float)) and
            r["reference_weight_kg"] > 0
        ]
        if refs:
            refs = sorted(refs, key=lambda r: r["reference_weight_kg"], reverse=True)[:12]
            fig = go.Figure(go.Bar(
                x=[x["reference_weight_kg"] for x in refs],
                y=[x["exercise"] for x in refs],
                orientation="h",
                marker=dict(color=[PURPLE if i % 2 == 0 else PINK for i in range(len(refs))],
                            line=dict(color="#D9B9FF", width=.35)),
                text=[f"{fmt(x['reference_weight_kg'])} kg" for x in refs],
                textposition="outside",
            ))
            fig.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="kg")
            st.markdown("#### Cargas de referencia de tu Excel · Semana 1")
            st.plotly_chart(plot_layout(fig, max(450, 30 * len(refs))), use_container_width=True,
                            config={"displayModeBar": False})
            st.caption("Estos pesos NO son estadísticas de entrenamientos realizados.")
    else:
        dates = pd.to_datetime(DF["Fecha"])
        week_start = (dates - pd.to_timedelta(dates.dt.weekday, unit="D")).dt.date
        DF["Semana calendario"] = week_start.astype(str)
        sessions_count = len({r.get("date") for r in SESSIONS})
        sets_count = len(DF)
        vol = DF["Volumen"].sum()
        a, b, c, d = st.columns(4)
        a.metric("Días entrenados", sessions_count)
        b.metric("Series realizadas", sets_count)
        c.metric("Volumen total", f"{fmt(vol, 0)} kg·rep")
        d.metric("Ejercicios realizados", DF["Ejercicio"].nunique())

        by_week = DF.groupby("Semana calendario").agg(
            Volumen=("Volumen", "sum"),
            Series=("Serie", "count"),
            Reps=("Repeticiones", "sum"),
        ).reset_index().sort_values("Semana calendario")
        st.markdown("#### 📈 Volumen por semana")
        fig = go.Figure(go.Bar(
            x=by_week["Semana calendario"],
            y=by_week["Volumen"],
            marker=dict(color=[PURPLE, PINK, CYAN, VIOLET] * (len(by_week)//4+1),
                        line=dict(width=0)),
            text=[fmt(v,0) for v in by_week["Volumen"]],
            textposition="outside",
        ))
        fig.update_layout(yaxis_title="kg × repeticiones")
        st.plotly_chart(plot_layout(fig), use_container_width=True, config={"displayModeBar":False})

        st.markdown("#### 💪 Evolución por ejercicio")
        picked = st.selectbox("Elegí el movimiento", sorted(DF["Ejercicio"].unique()),
                              key="stats_exercise")
        filtered = DF[DF["Ejercicio"] == picked]
        by_date = filtered.groupby("Fecha")["Carga (kg)"].max().reset_index()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=by_date["Fecha"], y=by_date["Carga (kg)"], mode="lines+markers",
            line=dict(color=PINK, width=4),
            marker=dict(size=12, color=PURPLE, line=dict(color="#FFFFFF",width=2)),
            fill="tozeroy", fillcolor="rgba(168,85,247,.12)",
            hovertemplate="%{x}<br>%{y:.2f} kg<extra></extra>",
        ))
        fig.update_layout(yaxis_title="Carga máxima registrada (kg)")
        st.plotly_chart(plot_layout(fig), use_container_width=True, config={"displayModeBar":False})
        st.markdown("#### Resumen semanal")
        show = by_week.rename(columns={
            "Semana calendario":"Semana (lunes)", "Volumen":"Volumen (kg·rep)"
        })
        st.dataframe(show, use_container_width=True, hide_index=True)
        st.caption(
            "Volumen = carga externa × repeticiones. No representa fuerza máxima ni incorpora "
            "peso corporal, cargas bilaterales/unilaterales equivalentes o isométricos. "
            "Compará el mismo ejercicio y condiciones."
        )

with tabs[2]:
    st.markdown("### 📚 Registro público de sesiones")
    st.caption("Cada sesión guardada por el administrador aparece para todos.")
    if DF.empty:
        st.info("Aún no se cargaron entrenamientos realizados. La rutina y sus pesos de referencia están en Mi rutina.")
    else:
        ordered = DF.sort_values(["Fecha","Día","Ejercicio","Serie"],
                                 ascending=[False,True,True,True])
        if st.checkbox("Mostrar únicamente un ejercicio"):
            wanted = st.selectbox("Ejercicio", sorted(ordered["Ejercicio"].unique()),
                                  key="filter_history_ex")
            ordered = ordered[ordered["Ejercicio"] == wanted]
        st.dataframe(
            ordered.drop(columns=["Volumen","Semana calendario"], errors="ignore"),
            hide_index=True, use_container_width=True,
            column_config={"Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY")}
        )
        csv_file = ordered.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Descargar historial CSV",
                           csv_file, "efg_training_historial.csv", "text/csv")

    plan_rows = pd.DataFrame(PLAN)
    included = ["week","day","pattern","block","exercise","series","repetitions",
                "intensity","notes","reference_weight_lb","reference_weight_kg",
                "reference_weight_lb_text"]
    st.download_button(
        "⬇️ Descargar plan completo (4 semanas) en CSV",
        plan_rows[included].to_csv(index=False).encode("utf-8-sig"),
        "efg_training_plan_completo.csv", "text/csv",
        help="Incluye los ejercicios y pesos de referencia que existían en el Excel original."
    )

with tabs[3]:
    st.markdown("### 🔐 Panel de administración")
    st.caption("La aplicación es pública. Este panel requiere tu PIN para guardar o modificar.")

    if not (TOKEN and ADMIN_PIN):
        st.warning(
            "El acceso de edición todavía no está habilitado. Falta configurar "
            "ADMIN_PIN y GITHUB_TOKEN en los Secrets de Streamlit Cloud. "
            "Hasta entonces, toda la aplicación es de solo lectura."
        )
    else:
        st.session_state.setdefault("efg_admin_ok", False)
        st.session_state.setdefault("efg_failed", 0)
        st.session_state.setdefault("efg_locked_until", 0.0)
        if not st.session_state["efg_admin_ok"]:
            now = time.time()
            if now < st.session_state["efg_locked_until"]:
                st.error("Demasiados intentos. Volvé a intentar dentro de unos minutos.")
            else:
                entered = st.text_input("PIN de administrador", type="password",
                                        max_chars=40, key="efg_pin_input")
                if st.button("🔓 Desbloquear edición", type="primary"):
                    if hmac.compare_digest(entered, ADMIN_PIN):
                        st.session_state["efg_admin_ok"] = True
                        st.session_state["efg_failed"] = 0
                        st.rerun()
                    else:
                        st.session_state["efg_failed"] += 1
                        if st.session_state["efg_failed"] >= 5:
                            st.session_state["efg_locked_until"] = time.time() + 300
                            st.session_state["efg_failed"] = 0
                            st.error("Cinco intentos fallidos. Acceso bloqueado 5 minutos en esta sesión.")
                        else:
                            st.error("PIN incorrecto.")
        else:
            left, right = st.columns([3, 1])
            left.success("Acceso de administrador activo en esta sesión.")
            with right:
                if st.button("Cerrar sesión", use_container_width=True):
                    st.session_state["efg_admin_ok"] = False
                    st.rerun()

            edit_tabs = st.tabs(["🏋️ Cargar entrenamiento", "✏️ Editar rutina"])
            with edit_tabs[0]:
                col1, col2, col3 = st.columns(3)
                with col1:
                    edit_week = st.selectbox("Semana del plan", [1,2,3,4],
                                             key="edit_week")
                with col2:
                    edit_day = st.selectbox("Día", [1,2,3,4,5],
                                            format_func=lambda x:DAY_NAMES[x-1],
                                            key="edit_day")
                with col3:
                    edit_date = st.date_input("Fecha", date.today(),
                                              format="DD/MM/YYYY", key="edit_date")
                choices = [
                    x for x in PLAN if x["week"]==edit_week and x["day"]==edit_day
                ]
                selected = st.selectbox(
                    "Ejercicio a registrar", range(len(choices)),
                    format_func=lambda i:f"{i+1:02}. {choices[i]['exercise']}",
                    key="register_exercise",
                )
                ex = choices[selected]
                ident = f"{edit_date.isoformat()}|{ex['id']}"
                previous = next((s for s in SESSIONS if s.get("id")==ident), None)
                series_count = parse_count(ex["series"])
                reps_plan = suggested_reps(ex["repetitions"], series_count)
                st.caption(
                    f"Objetivo: {ex['series']} series · {ex['repetitions']} repeticiones "
                    f"· {ex['intensity'] or 'sin RIR indicado'}"
                )
                units = st.radio("Unidad de carga", ["kg", "lb"], horizontal=True, key="register_units")
                with st.form("register_session_form", clear_on_submit=False):
                    new_sets = []
                    for i in range(series_count):
                        oldset = (previous.get("sets", [])[i]
                                  if previous and i < len(previous.get("sets", []))
                                  else None)
                        weight = float(oldset.get("kg",0)) if oldset else 0.0
                        if units == "lb":
                            weight /= 0.45359237
                        a, b, c = st.columns([.5,1.35,1.35])
                        a.markdown(f"**S{i+1}**")
                        with b:
                            loaded = st.number_input(
                                f"Carga ({units}) · S{i+1}", 0.0, 1500.0,
                                value=round(weight,2), step=2.5, key=f"weight_{i}",
                            )
                        with c:
                            rep = st.number_input(
                                f"Reps · S{i+1}", 0, 10000,
                                value=int(oldset.get("reps",0)) if oldset else reps_plan[i],
                                step=1, key=f"reps_{i}",
                            )
                        new_sets.append({
                            "kg":round(loaded * (0.45359237 if units=="lb" else 1.0), 3),
                            "reps":int(rep),
                        })
                    effort = st.selectbox(
                        "RIR real (opcional)", ["No registrado",0,1,2,3,4,5],
                        index=0, key="register_rir",
                    )
                    note = st.text_area(
                        "Observaciones (opcional)",
                        value=previous.get("notes","") if previous else "",
                        key="register_notes",
                    )
                    submitted = st.form_submit_button(
                        "💾 GUARDAR ENTRENAMIENTO", type="primary",
                        use_container_width=True,
                    )

                if submitted:
                    if not new_sets:
                        st.error("No hay series para guardar.")
                    else:
                        try:
                            latest, _ = fetch_remote("data/history.json", TOKEN)
                            other = [s for s in latest.get("sessions", [])
                                     if s.get("id") != ident]
                            other.append({
                                "id":ident,
                                "date":edit_date.isoformat(),
                                "week":edit_week,
                                "day":edit_day,
                                "exercise_id":ex["id"],
                                "exercise":ex["exercise"],
                                "sets":new_sets,
                                "rir":None if effort=="No registrado" else int(effort),
                                "notes":note[:900],
                                "saved_at":datetime.now(timezone.utc).isoformat(),
                            })
                            persist_remote(
                                "data/history.json",
                                {"schema_version":1,"sessions":other},
                                TOKEN,
                                f"EFG Training: registrar {ex['exercise']} {edit_date.isoformat()}",
                            )
                            public_history.clear()
                            st.success("¡Sesión guardada online! Se verá públicamente en breve.")
                            st.rerun()
                        except (requests.RequestException, ValueError, KeyError, TypeError) as error:
                            st.error(f"No se pudo guardar: {error}")

            with edit_tabs[1]:
                st.caption(
                    "Permite corregir la planificación publicada. Guardar provoca una "
                    "actualización automática de la app; puede tardar unos minutos."
                )
                modify_week = st.selectbox("Semana", [1,2,3,4], key="modify_week")
                modify_day = st.selectbox(
                    "Día", [1,2,3,4,5], format_func=lambda x:DAY_NAMES[x-1],
                    key="modify_day",
                )
                modify_options = [
                    x for x in PLAN if x["week"]==modify_week and x["day"]==modify_day
                ]
                modify_index = st.selectbox(
                    "Ejercicio", range(len(modify_options)),
                    format_func=lambda i: modify_options[i]["exercise"], key="modify_select"
                )
                target = modify_options[modify_index]
                with st.form("modify_plan_form"):
                    e_name = st.text_input("Nombre del ejercicio", value=target["exercise"])
                    e_sets = st.text_input("Series", value=target["series"])
                    e_reps = st.text_input("Repeticiones", value=target["repetitions"])
                    e_rir = st.text_input("Intensidad / RIR", value=target["intensity"])
                    e_pattern = st.text_input("Patrón muscular", value=target["pattern"])
                    e_block = st.text_input("Bloque / orden", value=target["block"])
                    e_notes = st.text_area("Observaciones técnicas", value=target["notes"])
                    update_plan = st.form_submit_button(
                        "💜 PUBLICAR CAMBIOS DE RUTINA", type="primary",
                        use_container_width=True
                    )
                if update_plan:
                    if not e_name.strip() or not e_sets.strip():
                        st.error("El nombre y las series son obligatorios.")
                    else:
                        try:
                            current, _ = fetch_remote("data/plan.json", TOKEN)
                            current_rows = current["entries"]
                            original = next((e for e in current_rows if e["id"]==target["id"]), None)
                            if not original:
                                raise ValueError("No se encontró el ejercicio en el plan online.")
                            original.update({
                                "exercise":e_name.strip()[:180],
                                "series":e_sets.strip()[:40],
                                "repetitions":e_reps.strip()[:40],
                                "intensity":e_rir.strip()[:100],
                                "pattern":e_pattern.strip()[:100],
                                "block":e_block.strip()[:100],
                                "notes":e_notes.strip()[:1600],
                            })
                            persist_remote(
                                "data/plan.json", current, TOKEN,
                                f"EFG Training: actualizar semana {modify_week} día {modify_day}",
                            )
                            st.success(
                                "Plan actualizado en GitHub. La app mostrará los cambios "
                                "después del redepliegue automático."
                            )
                        except (requests.RequestException, ValueError, KeyError, TypeError) as error:
                            st.error(f"No se pudo actualizar el plan: {error}")

st.divider()
st.markdown(
    '<div class="mini-title">EFG TRAINING / STRENGTH IN NUMBERS</div>'
    '<p class="muted">Rutina pública · Modificaciones protegidas · Datos almacenados en GitHub. '
    'Los indicadores son de entrenamiento, no evaluaciones médicas.</p>',
    unsafe_allow_html=True,
)
