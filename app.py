"""EFG Training · seguimiento público de fuerza, edición protegida por PIN.

Datos del plan: data/plan.json, migrados de la planilla original.
Entrenamientos: data/history.json, persistidos mediante GitHub Contents API.
Credenciales: Streamlit Community Cloud > App settings > Secrets.
"""
from __future__ import annotations

import base64
import csv
import hmac
from html import escape as html_escape
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
from visuals import render_plan_charts, render_calendar, render_weight_chart
from timer import render_rest_timer
from watch import render_watch_dashboard
from session_detail import render_session_detail

st.set_page_config(
    page_title="EFG Training | Strength & Progress",
    page_icon="💜",
    layout="wide",
    initial_sidebar_state="collapsed",
)

REPO = "floresgrancelli/EFG-Training"
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
    .hero-signature {font-size:.76rem;color:#BBA6D2;letter-spacing:.045em;margin-top:7px;font-weight:500}
    .hero-sub {font-size:1.07rem;color:#D8CAE9;margin:13px 0 0}
    /* Se conservan todos los fondos oscuros originales. Solo se destaca la tipografía. */
    [class*="st-key-efg_triserie_"] div[data-testid="stExpander"],
    [class*="st-key-efg_superserie_"] div[data-testid="stExpander"] {
      background:rgba(22,17,40,.73)!important;
      border:1px solid rgba(164,101,249,.27)!important;
      box-shadow:none!important;
    }
    [class*="st-key-efg_triserie_"] div[data-testid="stExpander"] summary p,
    [class*="st-key-efg_triserie_"] div[data-testid="stExpander"] summary span {
      color:#53EFFF!important;font-weight:850!important;
      text-shadow:0 0 13px rgba(34,211,238,.28);
    }
    [class*="st-key-efg_superserie_"] div[data-testid="stExpander"] summary p,
    [class*="st-key-efg_superserie_"] div[data-testid="stExpander"] summary span {
      color:#FF85F4!important;font-weight:850!important;
      text-shadow:0 0 13px rgba(236,72,227,.28);
    }
    .efg-legend {display:flex;flex-wrap:wrap;gap:9px;margin:2px 0 17px;}
    .efg-legend-item {padding:7px 11px;border:1px solid rgba(190,169,218,.22);
       border-radius:100px;font-size:.79rem;font-weight:850;background:rgba(22,17,40,.73)}
    .efg-legend-tri {color:#53EFFF;border-color:rgba(34,211,238,.48)}
    .efg-legend-ss {color:#FF85F4;border-color:rgba(217,70,239,.48)}
    .efg-legend-uni {color:#F2E9FF}
    /* Vista compacta de rutina, optimizada para consultar en el gimnasio */
    .quick-group {margin:0 0 13px;padding:11px 12px 9px;border-radius:16px;
        border:1px solid rgba(192,165,231,.22);background:rgba(22,17,40,.76)}
    .quick-group.triserie, .quick-group.superserie {
        background:rgba(22,17,40,.76);border-color:rgba(192,165,231,.22)}
    .quick-group-title {font-size:.80rem;font-weight:900;letter-spacing:.11em;
        text-transform:uppercase;color:#F4E6FF;padding:0 8px 7px}
    .quick-group.triserie .quick-group-title {color:#53EFFF;
        text-shadow:0 0 12px rgba(34,211,238,.30)}
    .quick-group.superserie .quick-group-title {color:#FF85F4;
        text-shadow:0 0 12px rgba(236,72,227,.30)}
    .quick-group.triserie .quick-ex {color:#53EFFF;font-weight:900}
    .quick-group.superserie .quick-ex {color:#FF85F4;font-weight:900}
    .quick-group.triserie .quick-num {color:#53EFFF}
    .quick-group.superserie .quick-num {color:#FF85F4}
    .quick-cols {display:grid;grid-template-columns:minmax(0,2.3fr) minmax(70px,.65fr) minmax(95px,1fr);
        gap:10px;align-items:center;padding:5px 9px;color:#B4A8C6;
        font-size:.72rem;font-weight:700;letter-spacing:.04em}
    .quick-row {display:grid;grid-template-columns:minmax(0,2.3fr) minmax(70px,.65fr) minmax(95px,1fr);
        align-items:center;gap:10px;padding:10px 9px;border-radius:9px;
        background:rgba(11,10,27,.32);margin-bottom:4px}
    .quick-ex {min-width:0;font-size:.93rem;line-height:1.23;font-weight:800;color:#FCF8FF;overflow-wrap:anywhere}
    .quick-num {color:#BDA0DD;padding-right:6px;font-size:.77rem}
    .quick-note {font-size:.73rem;font-weight:500;color:#BAACCD;margin-top:4px;line-height:1.35}
    .quick-count {font-size:.99rem;font-weight:850;color:#F5E7FF;white-space:nowrap}
    .quick-load {font-size:.87rem;font-weight:800;color:#B4FAEB;overflow-wrap:anywhere}
    .quick-muted {color:#B6A6CA;font-weight:600}
    .quick-loading-note {color:#BAACCD;font-size:.71rem;line-height:1.35;font-weight:500;margin-top:4px}
    @media(max-width:640px) {
      .quick-row {grid-template-columns:minmax(62px,.68fr) minmax(110px,1fr);gap:5px 8px}
      .quick-ex {grid-column:1/-1;font-size:.93rem}
      .quick-cols {grid-template-columns:1fr 1fr}
      .quick-cols span:first-child {display:none}
      .quick-count {font-size:.95rem}
      .quick-load {font-size:.85rem}
      .quick-group {padding:9px 8px}
    }
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


@st.cache_data(ttl=45, show_spinner=False)
def public_apple_watch() -> dict:
    try:
        data, _ = fetch_remote("data/apple_watch.json")
        return data if isinstance(data.get("workouts"), list) else {"workouts": [], "_offline": True}
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return {"workouts": [], "_offline": True}


@st.cache_data(ttl=45, show_spinner=False)
def public_weight() -> dict:
    try:
        data, _ = fetch_remote("data/weight.json")
        if isinstance(data.get("measurements"), list):
            return data
        return {"measurements": [], "_offline": True}
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return {"measurements": [], "_offline": True}


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


def weekly_report_weight(exercise: dict, unit: str = "lb") -> tuple[str, str] | None:
    """Carga declarada en el seguimiento de ESA semana, sin heredar otra semana."""
    report = exercise.get("weekly_report")
    if not isinstance(report, dict):
        return None
    factor = 1.0 if unit == "lb" else 0.45359237
    sequence = report.get("series_lb")
    try:
        if isinstance(sequence, list) and sequence:
            values = [float(v) for v in sequence]
        elif report.get("lb") is not None:
            values = [float(report["lb"])]
        else:
            return None
        if not values or any(not math.isfinite(v) or v < 0 for v in values):
            return None
    except (TypeError, ValueError):
        return None
    amounts = " / ".join(fmt(v * factor, 1).removesuffix(",0") for v in values)
    scope = str(report.get("scope", "")).strip()
    label = f"{amounts} {unit}" + (f" · {scope}" if scope else "")
    raw_date = str(report.get("date", ""))
    try:
        shown_date = date.fromisoformat(raw_date).strftime("%d/%m/%Y")
    except ValueError:
        shown_date = "fecha no indicada"
    context = f"Seguimiento registrado · {shown_date}"
    if len(values) > 1:
        context += f" · máximo {fmt(max(values) * factor, 1).removesuffix(',0')} {unit}"
    return label, context


def load_scope_kind(scope: str) -> str:
    """Normaliza el significado de una carga; no mezcla 'por lado' con peso total."""
    value = str(scope or "").casefold()
    if "por lado" in value:
        return "por_lado_y_barra"
    if "mancuerna" in value:
        return "mancuernas_sin_desglosar"
    if "peso corporal" in value:
        return "peso_corporal"
    if "disco" in value:
        return "disco"
    if "polea" in value:
        return "polea"
    if "máquina" in value or "maquina" in value:
        return "maquina"
    return "carga_externa"


def monthly_maximum_weights(
    plan: list[dict], sessions: list[dict], as_of: date | None = None
) -> dict[str, dict]:
    """Máximo móvil con cargas comparables, incluyendo reportes parciales.

    '180 lb por lado + barra' se conserva como 180 lb/lado: nunca se
    convierte en la carga total ni se suma una barra de peso desconocido.
    Una serie con carga ausente no aporta kg ficticios.
    """
    current = as_of or date.today()
    window_start = current - timedelta(days=29)
    recent: dict[str, list[dict]] = {}
    historical: dict[str, list[dict]] = {}

    def add(target, exercise, raw_kg, scope, source, when):
        name = " ".join(str(exercise).strip().casefold().split())
        try:
            amount = float(raw_kg)
        except (TypeError, ValueError):
            return
        if not name or not math.isfinite(amount) or amount < 0 or amount > 1500:
            return
        target.setdefault(name, []).append({
            "kg": amount, "scope": load_scope_kind(scope),
            "source": source, "date": when,
        })

    for ex in plan:
        name = ex.get("exercise", "")
        if int(ex.get("week", 0)) == 1:
            # Referencia sin fecha: solo se utilizará si no hay carga fechada reciente.
            initial_series = ex.get("reference_series_kg")
            if isinstance(initial_series, list) and initial_series:
                for value in initial_series:
                    add(historical, name, value, "", "excel_inicial", None)
            elif ex.get("reference_weight_kg") is not None:
                add(historical, name, ex.get("reference_weight_kg"), "", "excel_inicial", None)
        report = ex.get("weekly_report")
        if not isinstance(report, dict):
            continue
        try:
            reported_day = date.fromisoformat(str(report.get("date", "")))
        except (TypeError, ValueError):
            continue
        if not window_start <= reported_day <= current:
            continue
        pounds = report.get("series_lb")
        if not isinstance(pounds, list) or not pounds:
            pounds = [report.get("lb")]
        for value in pounds:
            try:
                converted = float(value) * 0.45359237
            except (TypeError, ValueError):
                continue
            add(recent, name, converted, report.get("scope"), "seguimiento", reported_day)

    for session in sessions:
        if not isinstance(session, dict):
            continue
        try:
            recorded_day = date.fromisoformat(str(session.get("date", "")))
        except (TypeError, ValueError):
            continue
        if not window_start <= recorded_day <= current:
            continue
        name = session.get("exercise", "")
        reported_lb = session.get("reported_load_lb")
        if reported_lb is not None:
            try:
                kg = float(reported_lb) * 0.45359237
            except (TypeError, ValueError):
                continue
            add(recent, name, kg, session.get("load_scope"), "app", recorded_day)
        else:
            for series in session.get("sets", []):
                if isinstance(series, dict):
                    add(recent, name, series.get("kg"), series.get("load_scope"),
                        "app", recorded_day)

    result: dict[str, dict] = {}
    for name in set(historical) | set(recent):
        if recent.get(name):
            records = recent[name]
            # Si cambia la modalidad registrada, no comparar kg por lado con
            # kilogramos totales: elegimos la modalidad más reciente.
            newest = max(
                enumerate(records),
                key=lambda item: (item[1]["date"], item[1]["source"] == "app", item[0]),
            )[1]
            comparable = [item for item in records if item["scope"] == newest["scope"]]
            result[name] = max(comparable, key=lambda item: item["kg"])
        elif historical.get(name):
            result[name] = max(historical[name], key=lambda item: item["kg"])
    return result

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
        f'<h1>{title}</h1><div class="hero-signature">by EFG</div>'
        f'<div class="hero-sub">{sub}</div>'
        f'<div style="margin-top:18px"><span class="pill">5 DÍAS</span>'
        f'<span class="pill">12 SEMANAS</span>'
        f'<span class="pill">FUERZA + DATOS</span></div></div>',
        unsafe_allow_html=True,
    )


PLAN = load_plan_local()
PLAN_WEEKS = sorted({int(row['week']) for row in PLAN})
HISTORY = public_history()
WEIGHT = public_weight()
WATCH = public_apple_watch()
WATCH_WORKOUTS = WATCH.get("workouts", [])
MEASUREMENTS = WEIGHT.get("measurements", [])
SESSIONS = HISTORY.get("sessions", [])
MONTHLY_MAX = monthly_maximum_weights(PLAN, SESSIONS)
DF = series_rows(SESSIONS)
TOKEN = secret("GITHUB_TOKEN")
ADMIN_PIN = secret("ADMIN_PIN")

announce(
    "EFG TRAINING  /  PERFORMANCE LAB  ·  V1.0",
    "LA CIENCIA<br>TAMBIÉN ENTRENA.",
    "Fuerza, método y datos para medir cada avance.",
)

tabs = st.tabs(["⚡ MI RUTINA", "📋 RUTINA RESUMEN", "⏱️ TEMPORIZADOR", "📊 PROGRESO", "⌚ APPLE WATCH", "📚 HISTORIAL", "⚖️ PESO", "🔐 ADMIN"])

with tabs[0]:
    st.markdown("### ⚡ Plan de entrenamiento")
    a, b = st.columns(2)
    a.metric("Días de entrenamiento", "05")
    b.metric("Semanas planificadas", f"{len(PLAN_WEEKS):02d}")
    st.markdown("")
    left, right = st.columns([1, 1])
    with left:
        week = st.selectbox("SEMANA", PLAN_WEEKS, format_func=lambda x: f"Semana {x}")
    with right:
        day = st.selectbox("DÍA", [1, 2, 3, 4, 5],
                          format_func=lambda x: f"Día {x} · {DAY_NAMES[x-1]}")
    chosen = [r for r in PLAN if int(r["week"]) == week and int(r["day"]) == day]
    st.markdown(
        f'<div class="finish"><div class="mini-title">TU SESIÓN</div>'
        f'<h3 style="margin:3px 0 4px">SEMANA {week} · {DAY_NAMES[day-1].upper()}</h3>'
        f'<div class="muted">{len(chosen)} ejercicios · desplegá cualquiera para ver sus indicaciones</div></div>',
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(
        '<div class="efg-legend" aria-label="Código visual de los bloques">'
        '<span class="efg-legend-item efg-legend-tri">AZUL · Triserie</span>'
        '<span class="efg-legend-item efg-legend-ss">VIOLETA · Superserie</span>'
        '<span class="efg-legend-item efg-legend-uni">OSCURO · Individual</span>'
        '</div>', unsafe_allow_html=True,
    )
    if day == 3 and ((week - 1) % 4) + 1 in (2, 3, 4):
        st.caption(
            "Nota del Excel: en esta semana, el circuito abdominal del miércoles "
            "solo tiene dos ejercicios; no figura el tercero."
        )
    for index, ex in enumerate(chosen, 1):
        kind = ex.get("set_type", "individual")
        if kind not in ("individual", "superserie", "triserie"):
            kind = "individual"
        group = ex.get("set_group", "")
        type_label = "TRISERIE" if kind == "triserie" else "SUPERSERIE"
        group_tag = f"  ·  {type_label} {group}" if kind != "individual" else ""
        display_label = f"{index:02}. {ex['exercise']}  ·  {ex['series']} × {ex['repetitions']}{group_tag}"
        with st.container(key=f"efg_{kind}_{ex['id']}"):
            with st.expander(display_label):
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
                report_load = weekly_report_weight(ex, "lb")
                if report_load:
                    load_text, load_context = report_load
                    st.info(f"**Carga de semana {week}:** {load_text}. {load_context}.")
                elif week == 1 and ex.get("reference_series_kg"):
                    string = " · ".join(f"{fmt(w, 1)} kg" for w in ex["reference_series_kg"])
                    st.info(f"Referencia inicial del Excel (semana 1): {string}.")
                elif week == 1 and ex.get("reference_weight_lb") is not None:
                    st.info(
                        f"Referencia inicial del Excel (semana 1): "
                        f"{fmt(ex.get('reference_weight_lb'), 1)} lb "
                        f"≈ {fmt(ex.get('reference_weight_kg'), 1)} kg."
                    )
                else:
                    st.caption("Carga de esta semana: todavía no confirmada en el seguimiento.")
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
        "Plan ampliado a 12 semanas con tres ciclos de cuatro semanas. "
        "Las cargas reportadas en el seguimiento se conservan en su semana original "
        "y el resumen muestra un máximo móvil de 30 días, no una meta impuesta. "
        "Las futuras semanas no tienen progresiones de peso inventadas."
    )

with tabs[1]:
    st.markdown("### 📋 Rutina resumen")
    st.caption("Modo gimnasio: todos los ejercicios de un vistazo y el mayor peso disponible del último mes.")
    qw, qd, qu = st.columns([1, 1.3, .8])
    with qw:
        summary_week = st.selectbox(
            "SEMANA", PLAN_WEEKS, format_func=lambda v: f"Semana {v}",
            key="quick_week",
        )
    with qd:
        summary_day = st.selectbox(
            "DÍA", [1, 2, 3, 4, 5],
            format_func=lambda v: DAY_NAMES[v - 1], key="quick_day",
        )
    with qu:
        summary_unit = st.selectbox("PESO EN", ["lb", "kg"], key="quick_unit")
    day_exercises = [
        x for x in PLAN
        if int(x["week"]) == summary_week and int(x["day"]) == summary_day
    ]
    def quick_weight_text(exercise):
        name = " ".join(str(exercise.get("exercise", "")).strip().casefold().split())
        peak = MONTHLY_MAX.get(name)
        if not peak:
            return "—"
        factor = 1.0 if summary_unit == "kg" else 1.0 / 0.45359237
        if peak.get("scope") == "peso_corporal":
            return "Peso corporal"
        value = fmt(peak["kg"] * factor, 1).removesuffix(",0")
        if peak.get("scope") == "por_lado_y_barra":
            return f"{value} {summary_unit}/lado + barra"
        if peak.get("scope") == "mancuernas_sin_desglosar":
            return f"{value} {summary_unit} · mancuernas*"
        return f"{value} {summary_unit}"

    st.markdown(
        f'<div class="finish" style="margin:12px 0 15px;padding:16px 20px">'
        f'<div class="mini-title">VISTA RÁPIDA · ENTRENAMIENTO</div>'
        f'<h3 style="margin:3px 0 4px">SEMANA {summary_week} · {DAY_NAMES[summary_day - 1].upper()}</h3>'
        f'<div class="muted">{len(day_exercises)} ejercicios · máximos en {summary_unit}</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="efg-legend" aria-label="Referencia visual">'
        '<span class="efg-legend-item efg-legend-tri">AZUL · Triserie</span>'
        '<span class="efg-legend-item efg-legend-ss">VIOLETA · Superserie</span>'
        '<span class="efg-legend-item efg-legend-uni">OSCURO · Individual</span>'
        '</div>', unsafe_allow_html=True,
    )

    groups = []
    for position, item in enumerate(day_exercises, 1):
        kind = str(item.get("set_type", "individual"))
        if kind not in ("superserie", "triserie"):
            kind = "individual"
        letter = str(item.get("set_group", "")).strip() if kind != "individual" else ""
        group_key = (kind, letter) if kind != "individual" else ("individual", position)
        if not groups or groups[-1]["key"] != group_key:
            groups.append({"key": group_key, "kind": kind, "letter": letter, "items": []})
        groups[-1]["items"].append((position, item))

    html_parts = []
    for group in groups:
        kind = group["kind"]
        if kind == "triserie":
            heading = f"TRISERIE {html_escape(group['letter'])} · {len(group['items'])} ejercicios"
        elif kind == "superserie":
            heading = f"SUPERSERIE {html_escape(group['letter'])} · {len(group['items'])} ejercicios"
        else:
            heading = "EJERCICIO INDIVIDUAL"
        html_parts.append(
            f'<section class="quick-group {kind}">'
            f'<div class="quick-group-title">{heading}</div>'
            '<div class="quick-cols"><span>EJERCICIO</span><span>SERIES × REPS</span><span>PESO MÁX.</span></div>'
        )
        for position, exercise in group["items"]:
            ex_name = html_escape(str(exercise.get("exercise", "")))
            series = html_escape(str(exercise.get("series", "—") or "—"))
            reps = html_escape(str(exercise.get("repetitions", "—") or "—"))
            effort = str(exercise.get("intensity", "")).strip()
            notes = (" · " + html_escape(effort)) if effort else ""
            weight_value = quick_weight_text(exercise)
            html_parts.append(
                '<div class="quick-row">'
                f'<div class="quick-ex"><span class="quick-num">{position:02d}.</span> {ex_name}'
                f'<div class="quick-note">{html_escape(str(exercise.get("pattern", "")))}{notes}</div></div>'
                f'<div class="quick-count">{series} × {reps}</div>'
                f'<div class="quick-load">{html_escape(weight_value)}</div></div>'
            )
        html_parts.append("</section>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)
    if summary_day == 3 and ((summary_week - 1) % 4) + 1 in (2, 3, 4):
        st.caption("El Excel tiene solo dos ejercicios en el circuito abdominal del miércoles de esta semana.")
    if HISTORY.get("_offline"):
        st.warning("No se pudo actualizar el historial: pueden faltar los últimos pesos reales.")
    st.caption(
        "PESO MÁX.: mayor carga comparable registrada en los últimos 30 días, "
        "aunque en el último entrenamiento hayas usado menos. "
        "Los pesos por lado se muestran por lado + barra, sin inventar el peso de la barra. "
        "En mancuernas (*) no se presupone si la cifra es total o por mancuerna. "
        "Las cargas confirmadas sin repeticiones también cuentan como referencia de peso. "
        "Sin dato reciente se conserva la referencia inicial del Excel, sin fecha. "
        "«—» significa que no hay carga registrada."
    )


with tabs[2]:
    render_rest_timer()


with tabs[3]:
    st.markdown("### 📊 Tu evolución, en números")
    render_plan_charts(PLAN)
    st.divider()
    st.markdown("### 📈 Rendimiento registrado")
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
        confirmed_sets = sum(
            1 for session in SESSIONS if isinstance(session, dict)
            for item in session.get("sets", [])
            if isinstance(item, dict) and isinstance(item.get("reps"), int)
        )
        confirmed_exercises = len({
            str(session.get("exercise", "")).strip()
            for session in SESSIONS if isinstance(session, dict)
            and any(isinstance(item, dict) and isinstance(item.get("reps"), int)
                    for item in session.get("sets", []))
        })
        vol = DF["Volumen"].sum()
        a, b, c, d = st.columns(4)
        a.metric("Días entrenados", sessions_count)
        b.metric("Series confirmadas", confirmed_sets)
        c.metric("Volumen calculable", f"{fmt(vol, 0)} kg·rep")
        d.metric("Ejercicios con repeticiones", confirmed_exercises)
        st.caption(
            "El volumen es parcial: solo incluye series con carga total cuantificada y "
            "repeticiones confirmadas. El detalle completo, incluso cargas por lado "
            "y datos incompletos, está en HISTORIAL."
        )

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
        st.markdown("#### 🔁 Más repeticiones con el mismo peso")
        st.caption(
            "Compará tu mejor serie por fecha manteniendo la misma carga. "
            "Así se ve el progreso por repeticiones aunque los kilos no cambien."
        )
        available_loads = sorted(filtered["Carga (kg)"].unique().tolist(), reverse=True)
        load_frequency = filtered.groupby("Carga (kg)")["Fecha"].nunique()
        default_load = max(available_loads, key=lambda load: (int(load_frequency[load]), load))
        chosen_load = st.selectbox(
            "Carga para comparar",
            available_loads,
            index=available_loads.index(default_load),
            format_func=lambda load: f"{fmt(load, 2).removesuffix(',00')} kg",
            key="stats_repetition_load",
        )
        same_load_reps = (
            filtered[filtered["Carga (kg)"] == chosen_load]
            .groupby("Fecha", as_index=False)["Repeticiones"].max()
            .sort_values("Fecha")
        )
        first_reps = int(same_load_reps.iloc[0]["Repeticiones"])
        last_reps = int(same_load_reps.iloc[-1]["Repeticiones"])
        rep_a, rep_b = st.columns(2)
        rep_a.metric("Última mejor serie", f"{last_reps} rep")
        rep_b.metric(
            "Cambio desde el primer registro",
            f"{last_reps - first_reps:+d} rep" if len(same_load_reps) >= 2 else "—",
        )
        reps_fig = go.Figure(go.Scatter(
            x=same_load_reps["Fecha"], y=same_load_reps["Repeticiones"],
            mode="lines+markers+text",
            line=dict(color=CYAN, width=4),
            marker=dict(size=12, color=PURPLE, line=dict(color="#FFFFFF", width=2)),
            text=[str(int(n)) for n in same_load_reps["Repeticiones"]],
            textposition="top center",
            hovertemplate="%{x}<br>%{y:.0f} repeticiones<extra></extra>",
        ))
        reps_fig.update_layout(yaxis_title="Mejor serie (repeticiones)", xaxis_title="Fecha")
        st.plotly_chart(
            plot_layout(reps_fig), use_container_width=True,
            config={"displayModeBar": False},
        )
        st.caption(
            "Se toma la serie con más repeticiones de cada fecha a la carga elegida, "
            "no la suma de todas las series. Interpretá las mejoras junto con la técnica y el RIR."
        )
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
        render_calendar(SESSIONS)

with tabs[4]:
    render_watch_dashboard(
        WATCH_WORKOUTS, offline=bool(WATCH.get("_offline")),
        plot_layout=plot_layout,
    )


with tabs[5]:
    st.markdown("### 📚 Historial y evolución de fuerza")
    render_session_detail(SESSIONS)
    st.divider()
    st.caption(
        "Tres fuentes diferenciadas: planilla inicial (semana 1), seguimiento "
        "conversado por semana y sesiones guardadas desde EFG Training."
    )

    # Estos pesos son máximos históricos informados por Edu, no sesiones fechadas.
    historic = []
    for ex in PLAN:
        if int(ex.get("week", 0)) != 1:
            continue
        raw_sequence = ex.get("reference_series_kg")
        valid_sequence = []
        if isinstance(raw_sequence, list):
            for amount in raw_sequence:
                try:
                    number = float(amount)
                    if math.isfinite(number) and number >= 0:
                        valid_sequence.append(number)
                except (ValueError, TypeError):
                    continue
        if valid_sequence:
            historic_max = max(valid_sequence)
        else:
            try:
                raw_max = ex.get("reference_weight_kg")
                historic_max = float(raw_max) if raw_max is not None else None
                if historic_max is not None and (not math.isfinite(historic_max) or historic_max < 0):
                    historic_max = None
            except (ValueError, TypeError):
                historic_max = None
        if historic_max is None:
            continue
        historic.append({
            "exercise": str(ex.get("exercise", "")).strip(),
            "day": int(ex["day"]),
            "pattern": str(ex.get("pattern", "")),
            "set_type": str(ex.get("set_type", "individual")),
            "sets": str(ex.get("series", "")),
            "reps": str(ex.get("repetitions", "")),
            "max_kg": historic_max,
            "per_set": valid_sequence,
        })

    st.markdown("#### 📌 Referencias iniciales del Excel · Semana 1")
    st.caption(
        "Las cargas de la planilla original se muestran aquí como punto de partida. "
        "Los valores documentados de las semanas siguientes aparecen en el seguimiento "
        "semanal, sin sustituir ni inventar sesiones de la aplicación."
    )
    historical_by_exercise = {}
    for item in historic:
        normalized = item["exercise"].casefold()
        historical_by_exercise[normalized] = max(
            item["max_kg"], historical_by_exercise.get(normalized, 0.0)
        )
    a, b, c = st.columns(3)
    a.metric("Ejercicios con referencia", len(historic))
    b.metric("Sesiones guardadas", len([x for x in SESSIONS if isinstance(x, dict)]))
    c.metric("Ejercicios con sesiones", len({
        str(x.get("exercise", "")).strip().casefold()
        for x in SESSIONS if isinstance(x, dict) and x.get("exercise")
    }))

    ref_table = []
    for ex in historic:
        ref_table.append({
            "Día": DAY_NAMES[ex["day"] - 1],
            "Ejercicio": ex["exercise"],
            "Bloque": (
                "Triserie" if ex["set_type"] == "triserie"
                else "Superserie" if ex["set_type"] == "superserie"
                else "Individual"
            ),
            "Series": ex["sets"],
            "Repeticiones": ex["reps"],
            "Máximo (lb)": round(ex["max_kg"] / 0.45359237, 1),
            "Máximo (kg)": round(ex["max_kg"], 2),
            "Cargas por serie (lb)": (
                " · ".join(fmt(v / 0.45359237, 1) for v in ex["per_set"])
                if ex["per_set"] else "—"
            ),
        })
    if ref_table:
        st.dataframe(
            pd.DataFrame(ref_table), use_container_width=True,
            hide_index=True, height=340,
        )
        st.download_button(
            "⬇️ Descargar referencia original del Excel (CSV)",
            pd.DataFrame(ref_table).to_csv(index=False).encode("utf-8-sig"),
            "efg_training_maximos_mes_anterior.csv", "text/csv",
        )
        st.markdown("##### Comparación visual por día")
        historic_day = st.selectbox(
            "Día de entrenamiento", list(range(1, 6)),
            format_func=lambda d: DAY_NAMES[d - 1],
            key="history_reference_day",
        )
        chosen_refs = [ex for ex in historic if ex["day"] == historic_day]
        if chosen_refs:
            ref_chart = go.Figure(go.Bar(
                x=[r["max_kg"] for r in chosen_refs],
                y=[r["exercise"] for r in chosen_refs],
                orientation="h",
                marker=dict(
                    color=[
                        CYAN if r["set_type"] == "triserie"
                        else PINK if r["set_type"] == "superserie" else PURPLE
                        for r in chosen_refs
                    ],
                    line=dict(width=0),
                ),
                text=[fmt(r["max_kg"], 1) + " kg" for r in chosen_refs],
                textposition="outside",
                hovertemplate="%{y}: %{x:.2f} kg<extra>Mes anterior · Excel</extra>",
            ))
            ref_chart.update_layout(
                yaxis=dict(autorange="reversed"),
                xaxis_title="Carga externa máxima (kg)",
                margin=dict(l=10, r=35, t=20, b=35),
            )
            st.plotly_chart(
                plot_layout(ref_chart, max(310, 42 * len(chosen_refs))),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            st.caption(
                "Visualización descriptiva: las cargas de máquinas y ejercicios diferentes "
                "no son comparables como una medida de rendimiento general."
            )

    st.divider()
    st.markdown("#### 🗓️ Pesos reportados por semana")
    week_reports = []
    for item in PLAN:
        detail = item.get("weekly_report")
        if not isinstance(detail, dict):
            continue
        values = detail.get("series_lb")
        if not isinstance(values, list) or not values:
            values = [detail.get("lb")]
        try:
            values = [float(number) for number in values]
            if not values or any(not math.isfinite(v) or v < 0 for v in values):
                continue
        except (TypeError, ValueError):
            continue
        week_reports.append({
            "exercise": str(item.get("exercise", "")).strip(),
            "week": int(item["week"]),
            "date": str(detail.get("date", "")),
            "lb": max(values),
            "scope": str(detail.get("scope", "")),
            "series_lb": values,
        })
    st.caption(
        "Cargas comunicadas en «Evaluación y plan fitness», asociadas a su semana. "
        "Se respeta «por lado», «por mancuerna» o «máquina»: no son cargas totales "
        "ni necesariamente máximos de una repetición."
    )
    if week_reports:
        with st.expander(
            f"Consultar todos los registros recuperados ({len(week_reports)})",
            expanded=False,
        ):
            st.dataframe(
                pd.DataFrame([
                    {
                        "Semana": item["week"],
                        "Fecha": item["date"],
                        "Ejercicio": item["exercise"],
                        "Carga (lb)": round(item["lb"], 1),
                        "Referencia de carga": item["scope"],
                        "Por serie (lb)": (
                            " / ".join(fmt(v, 1) for v in item["series_lb"])
                            if len(item["series_lb"]) > 1 else "—"
                        ),
                    } for item in week_reports
                ]).sort_values(["Semana", "Fecha", "Ejercicio"]),
                use_container_width=True, hide_index=True, height=350,
            )

    st.divider()
    st.markdown("#### 📈 Gráfico de evolución por ejercicio")
    st.caption(
        "Elegí un ejercicio para ver su propio gráfico. La línea utiliza las fechas reales "
        "de cada sesión; la referencia del Excel nunca se coloca en una fecha inventada."
    )
    exercise_names = {
        str(x.get("exercise", "")).strip() for x in PLAN
        if str(x.get("exercise", "")).strip()
    }
    exercise_names.update(
        str(x.get("exercise", "")).strip() for x in SESSIONS
        if isinstance(x, dict) and str(x.get("exercise", "")).strip()
    )
    exercise_options = sorted(exercise_names, key=str.casefold)
    if exercise_options:
        default_ex = "Sit ups con disco"
        default_index = exercise_options.index(default_ex) if default_ex in exercise_options else 0
        chosen_name = st.selectbox(
            "Seleccioná el ejercicio", exercise_options,
            index=default_index, key="history_exercise_chart",
        )
        chosen_key = chosen_name.casefold()
        baseline = historical_by_exercise.get(chosen_key)
        weekly_points = sorted(
            [r for r in week_reports if r["exercise"].casefold() == chosen_key],
            key=lambda record: (record["week"], record["date"]),
        )

        # Resumir únicamente cargas reales, con fecha, para el movimiento elegido.
        dated = {}
        reps_by_load = {}
        for session in SESSIONS:
            if not isinstance(session, dict):
                continue
            if str(session.get("exercise", "")).strip().casefold() != chosen_key:
                continue
            try:
                real_date = date.fromisoformat(str(session.get("date", "")))
            except (ValueError, TypeError):
                continue
            valid_sets = []
            for series in session.get("sets", []):
                if not isinstance(series, dict):
                    continue
                try:
                    load = float(series.get("kg", 0))
                    reps = int(series.get("reps", 0))
                except (ValueError, TypeError):
                    continue
                if math.isfinite(load) and 0 <= load <= 1500 and 0 <= reps <= 10000:
                    valid_sets.append((load, reps))
            if not valid_sets:
                continue
            for load, reps in valid_sets:
                load_key = round(load, 3)
                date_reps = reps_by_load.setdefault(load_key, {})
                date_reps[real_date] = max(date_reps.get(real_date, 0), reps)
            if real_date not in dated:
                dated[real_date] = {"max_kg": 0.0, "volume": 0.0, "reps": 0, "sets": 0}
            dated[real_date]["max_kg"] = max(
                dated[real_date]["max_kg"], max(x[0] for x in valid_sets)
            )
            dated[real_date]["volume"] += sum(x[0] * x[1] for x in valid_sets)
            dated[real_date]["reps"] += sum(x[1] for x in valid_sets)
            dated[real_date]["sets"] += len(valid_sets)

        history_dates = sorted(dated)
        last_real = dated[history_dates[-1]]["max_kg"] if history_dates else None
        earliest = weekly_points[0] if weekly_points else None
        latest = weekly_points[-1] if weekly_points else None
        comparable = (
            len(weekly_points) >= 2
            and earliest["scope"] == latest["scope"]
        )
        m1, m2, m3 = st.columns(3)
        m1.metric(
            "Última carga reportada",
            f"{fmt(latest['lb'], 1)} lb" if latest is not None else "—",
        )
        m2.metric(
            "Última carga registrada en app",
            f"{fmt(last_real, 1)} kg" if last_real is not None else "—",
        )
        m3.metric(
            "Cambio entre reportes",
            f"{latest['lb'] - earliest['lb']:+.1f} lb"
            if comparable else "—",
        )

        if weekly_points:
            st.markdown("##### 📈 Evolución semanal reportada")
            weekly_values = {
                int(item["week"]): float(item["lb"]) for item in weekly_points
            }
            weekly_labels = {
                int(item["week"]): item["scope"] for item in weekly_points
            }
            x_axis = list(PLAN_WEEKS)
            y_axis = [weekly_values.get(i) for i in x_axis]
            weekly_chart = go.Figure()
            weekly_chart.add_trace(go.Scatter(
                x=x_axis, y=y_axis, mode="lines+markers+text",
                line=dict(color=CYAN, width=4),
                marker=dict(size=12, color=PINK, line=dict(color="#FFFFFF", width=1)),
                text=[
                    f"{fmt(v, 1)} lb" if v is not None else ""
                    for v in y_axis
                ],
                textposition="top center",
                connectgaps=False,
                hovertemplate="%{x}<br>%{y:.1f} lb<extra>Seguimiento conversado</extra>",
            ))
            weekly_chart.update_layout(
                yaxis_title="Carga reportada (lb, con su condición de uso)",
                xaxis=dict(
                    type="linear", tickmode="linear", dtick=1,
                    range=[0.7, max(PLAN_WEEKS) + 0.3],
                    title="Semana del plan",
                ),
                margin=dict(l=10, r=20, t=45, b=35),
            )
            st.plotly_chart(
                plot_layout(weekly_chart, 350), use_container_width=True,
                config={"displayModeBar": False},
            )
            qualifiers = sorted(set(weekly_labels.values()))
            st.caption(
                "Unidad según registro: " + ", ".join(qualifiers) + ". "
                "Los puntos son los pesos reportados para cada semana; los huecos "
                "significan que no hay carga confirmada. "
                "No se sumó el peso de una barra cuando solo se informó «por lado»."
            )
        elif baseline is not None:
            st.caption("Solo tenemos la referencia inicial del Excel para este ejercicio.")

        if history_dates:
            st.markdown("##### Entrenamientos registrados en EFG Training")
            selected_metric = st.radio(
                "Indicador del gráfico",
                ["Carga máxima", "Volumen", "Repeticiones", "Repeticiones a igual carga"],
                horizontal=True, key="history_chart_metric",
            )
            if selected_metric == "Repeticiones a igual carga":
                loads = sorted(reps_by_load, reverse=True)
                default_load = max(loads, key=lambda load: (len(reps_by_load[load]), load))
                fixed_load = st.selectbox(
                    "Comparar con carga fija",
                    loads,
                    index=loads.index(default_load),
                    format_func=lambda load: f"{fmt(load, 2).removesuffix(',00')} kg",
                    key="history_repetition_load",
                )
                x_dates = sorted(reps_by_load[fixed_load])
                y_values = [reps_by_load[fixed_load][d] for d in x_dates]
            else:
                metric_key = {
                    "Carga máxima": "max_kg",
                    "Volumen": "volume",
                    "Repeticiones": "reps",
                }[selected_metric]
                x_dates = history_dates
                y_values = [dated[d][metric_key] for d in x_dates]
            chart = go.Figure()
            if selected_metric == "Volumen":
                chart.add_trace(go.Bar(
                    x=x_dates, y=y_values, marker_color=PURPLE,
                    hovertemplate="%{x|%d/%m/%Y}<br>%{y:.1f} kg·rep<extra></extra>",
                ))
            else:
                chart.add_trace(go.Scatter(
                    x=x_dates, y=y_values, mode="lines+markers",
                    line=dict(color=PINK, width=3),
                    marker=dict(size=11, color=PURPLE, line=dict(color="#FFFFFF", width=1)),
                    hovertemplate=(
                        "%{x|%d/%m/%Y}<br>%{y:.2f} kg<extra></extra>"
                        if selected_metric == "Carga máxima" else
                        "%{x|%d/%m/%Y}<br>%{y:.0f} repeticiones<extra></extra>"
                    ),
                ))
            if selected_metric == "Carga máxima" and baseline is not None:
                chart.add_hline(
                    y=baseline, line_color=CYAN, line_width=2,
                    line_dash="dash", annotation_text="Base Excel S1 (sin fecha)",
                    annotation_position="top left",
                    annotation_font_color=CYAN,
                )
            chart.update_layout(
                yaxis_title={
                    "Carga máxima": "Carga máxima por sesión (kg)",
                    "Volumen": "kg × repeticiones",
                    "Repeticiones": "Repeticiones totales",
                    "Repeticiones a igual carga": "Mejor serie a carga fija (repeticiones)",
                }[selected_metric],
                xaxis=dict(type="date", tickformat="%d/%m/%y"),
                margin=dict(l=10, r=20, t=45, b=35),
            )
            st.plotly_chart(
                plot_layout(chart, 365), use_container_width=True,
                config={"displayModeBar": False},
            )
            if selected_metric == "Repeticiones a igual carga":
                st.caption(
                    f"Cada punto muestra la serie con más repeticiones realizada con "
                    f"{fmt(fixed_load, 2).removesuffix(',00')} kg en esa fecha. "
                    "No suma repeticiones de series diferentes."
                )
            detail_rows = [
                {
                    "Fecha": day_record,
                    "Máximo (kg)": round(dated[day_record]["max_kg"], 2),
                    "Series": dated[day_record]["sets"],
                    "Repeticiones": dated[day_record]["reps"],
                    "Volumen (kg·rep)": round(dated[day_record]["volume"], 1),
                }
                for day_record in reversed(history_dates)
            ]
            st.dataframe(
                pd.DataFrame(detail_rows), use_container_width=True, hide_index=True,
                column_config={"Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY")},
            )
            st.caption(
                "El máximo es la carga externa mayor de esa sesión, no una estimación de 1RM. "
                "Volumen = kg × repeticiones; compará el mismo movimiento y equipamiento."
            )
        elif weekly_points:
            st.info(
                "Este gráfico muestra los pesos conversados por semana. "
                "Las sesiones con fechas y estadísticas de volumen aparecerán cuando "
                "registres entrenamientos desde ADMIN."
            )
        elif baseline is not None:
            # El Excel trae referencias sin fechas; representamos una barra, no una tendencia falsa.
            figure = go.Figure(go.Bar(
                x=["Base Excel · semana 1 (sin fecha exacta)"], y=[baseline],
                marker_color=CYAN,
                text=[fmt(baseline, 1) + " kg"], textposition="outside",
                hovertemplate="Referencia histórica: %{y:.2f} kg<extra></extra>",
            ))
            figure.update_layout(yaxis_title="Carga máxima (kg)")
            st.plotly_chart(
                plot_layout(figure, 310), use_container_width=True,
                config={"displayModeBar": False},
            )
            st.info(
                "Para este ejercicio solo tenemos una referencia inicial del Excel. "
                "La evolución semanal aparecerá al sumar cargas reportadas o "
                "sesiones guardadas desde ADMIN."
            )
        else:
            st.info(
                "Este ejercicio está en el plan, pero no tiene una carga histórica conocida "
                "ni sesiones reales guardadas. Su gráfico aparecerá cuando registres datos."
            )

    st.divider()
    st.markdown("#### 🗂️ Sesiones realmente registradas")
    st.caption("Cada entrenamiento guardado desde el administrador aparece aquí para todos.")
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
                "intensity","notes","set_type","set_group","reference_weight_lb","reference_weight_kg",
                "reference_weight_lb_text","weekly_report","template_week"]
    st.download_button(
        "⬇️ Descargar plan completo (12 semanas) en CSV",
        plan_rows.reindex(columns=included, fill_value="").to_csv(index=False).encode("utf-8-sig"),
        "efg_training_plan_completo.csv", "text/csv",
        help="Incluye los ejercicios y pesos de referencia que existían en el Excel original."
    )

with tabs[6]:
    st.markdown("### ⚖️ Evolución del peso corporal")
    st.caption("Mediciones reales, registradas por fecha y visibles para todos.")
    if WEIGHT.get("_offline"):
        st.warning("No se pudieron actualizar las mediciones desde GitHub.")
    render_weight_chart(MEASUREMENTS)


with tabs[7]:
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

            edit_tabs = st.tabs(["🏋️ Cargar entrenamiento", "✏️ Editar rutina", "⚖️ Peso corporal"])
            with edit_tabs[0]:
                col1, col2, col3 = st.columns(3)
                with col1:
                    edit_week = st.selectbox("Semana del plan", PLAN_WEEKS,
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
                                value=round(weight,2), step=2.5, key=f"weight_{ex['id']}_{edit_date.isoformat()}_{units}_{i}",
                            )
                        with c:
                            rep = st.number_input(
                                f"Reps · S{i+1}", 0, 10000,
                                value=int(oldset.get("reps",0)) if oldset else reps_plan[i],
                                step=1, key=f"reps_{ex['id']}_{edit_date.isoformat()}_{i}",
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
                modify_week = st.selectbox("Semana", PLAN_WEEKS, key="modify_week")
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
                    kind_options = ["individual", "superserie", "triserie"]
                    initial_kind = target.get("set_type", "individual")
                    if initial_kind not in kind_options:
                        initial_kind = "individual"
                    e_kind = st.selectbox(
                        "Tipo de bloque", kind_options,
                        index=kind_options.index(initial_kind),
                        format_func=lambda x: {
                            "individual": "Ejercicio individual",
                            "superserie": "Superserie (violeta)",
                            "triserie": "Triserie (azul)",
                        }[x],
                    )
                    group_options = ["", "A", "B", "C", "D", "E", "F", "G", "H"]
                    initial_group = target.get("set_group", "")
                    if initial_group not in group_options:
                        initial_group = ""
                    e_group = st.selectbox(
                        "Grupo del bloque", group_options,
                        index=group_options.index(initial_group),
                        format_func=lambda x: x or "Sin grupo / ejercicio individual",
                        help="Usá la misma letra para los ejercicios que van juntos.",
                    )
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
                    elif e_kind != "individual" and not e_group:
                        st.error("Elegí la letra del grupo de la superserie o triserie.")
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
                                "set_type":e_kind,
                                "set_group":e_group if e_kind != "individual" else "",
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


            with edit_tabs[2]:
                st.markdown("#### ⚖️ Registrar peso corporal")
                st.caption(
                    "Una medición por fecha. Si volvés a guardar la misma fecha, "
                    "se actualiza el valor anterior. El registro es público."
                )
                with st.form("weight_form", clear_on_submit=False):
                    weight_date = st.date_input(
                        "Fecha del pesaje", value=date.today(),
                        format="DD/MM/YYYY", key="weight_date"
                    )
                    weight_value = st.number_input(
                        "Peso corporal (kg)", min_value=20.0, max_value=350.0,
                        value=80.0, step=0.1, format="%.2f", key="weight_value"
                    )
                    weight_notes = st.text_area(
                        "Observaciones opcionales",
                        placeholder="Ej.: pesaje matutino, antes de desayunar",
                        key="weight_notes"
                    )
                    weight_submit = st.form_submit_button(
                        "💾 GUARDAR PESO CORPORAL", type="primary",
                        use_container_width=True
                    )

                if weight_submit:
                    try:
                        current, _ = fetch_remote("data/weight.json", TOKEN)
                        existing = current.get("measurements", [])
                        if not isinstance(existing, list):
                            raise ValueError("La estructura de los pesajes no es válida.")
                        saved = [
                            row for row in existing
                            if str(row.get("date", "")) != weight_date.isoformat()
                        ]
                        saved.append({
                            "date": weight_date.isoformat(),
                            "kg": round(float(weight_value), 2),
                            "notes": weight_notes.strip()[:400],
                            "saved_at": datetime.now(timezone.utc).isoformat(),
                        })
                        saved.sort(key=lambda row: row.get("date", ""))
                        persist_remote(
                            "data/weight.json",
                            {"schema_version": 1, "measurements": saved},
                            TOKEN,
                            f"EFG Training: registrar peso corporal {weight_date.isoformat()}",
                        )
                        public_weight.clear()
                        st.success("Peso corporal guardado. Ya figura en la pestaña pública de Peso.")
                        st.rerun()
                    except (requests.RequestException, ValueError, KeyError, TypeError) as error:
                        st.error(f"No se pudo guardar el peso corporal: {error}")

                if MEASUREMENTS:
                    st.markdown("**Pesajes ya registrados**")
                    weight_rows = sorted(
                        [
                            {"Fecha": r.get("date", ""), "Peso (kg)": r.get("kg", "")}
                            for r in MEASUREMENTS
                        ],
                        key=lambda item: item["Fecha"], reverse=True
                    )
                    st.dataframe(weight_rows, hide_index=True, use_container_width=True)

st.divider()
st.markdown(
    '<div class="mini-title">EFG TRAINING / STRENGTH IN NUMBERS · by EFG</div>'
    '<p class="muted">Rutina pública · Modificaciones protegidas · Datos almacenados en GitHub. '
    'Los indicadores son de entrenamiento, no evaluaciones médicas.</p>',
    unsafe_allow_html=True,
)
