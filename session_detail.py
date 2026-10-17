"""EFG Training · detalle cronológico de sesiones reales y cargas parciales."""

from __future__ import annotations

from datetime import date
import streamlit as st
import pandas as pd

LB_TO_KG = 0.45359237


def _lb(value):
    if value is None:
        return "—"
    value = float(value)
    return f"{value:g} lb"


def _load_label(row: dict) -> str:
    load = row.get("reported_load_lb")
    scope = str(row.get("load_scope") or "").strip()
    if load is None:
        known = [x for x in row.get("sets", []) if isinstance(x, dict) and (x.get("load_lb") is not None or x.get("kg") is not None)]
        if not known:
            return "No informada"
        values = [float(x["load_lb"]) if x.get("load_lb") is not None else float(x["kg"]) / LB_TO_KG for x in known]
        load = max(values)
        scope = str(known[-1].get("load_scope") or scope)

    if scope == "peso corporal" or load == 0:
        return "Peso corporal"
    label = _lb(load)
    if scope:
        label += f" · {scope}"
    return label


def _sets_label(session: dict) -> str:
    sets = session.get("sets", [])
    if not sets:
        return "No confirmadas"
    return f"{len(sets)} series"


def _reps_label(session: dict) -> str:
    sets = session.get("sets", [])
    if not sets:
        return "No confirmadas"
    if any(s.get("reps") is None for s in sets):
        return "Parciales"
    per_side = all(s.get("reps_per_side") is not None for s in sets)
    reps = [int(s["reps_per_side"] if per_side else s["reps"]) for s in sets]
    suffix = " por lado" if per_side else (" segundos" if session.get("duration_unit") == "seconds" or session.get("exercise") == "Plancha común" else "")
    return ( " × ".join([str(len(reps)), str(reps[0])]) if len(set(reps)) == 1 else " / ".join(map(str, reps))) + suffix


def _status_label(session: dict) -> str:
    status = str(session.get("record_status", "confirmado"))
    return {
        "confirmado": "Cargas y repeticiones informadas",
        "repeticiones_confirmadas_carga_total_incompleta": "Falta peso total de la barra",
        "repeticiones_confirmadas_alcance_carga_incierto": "Falta especificar el alcance de la carga",
        "repeticiones_confirmadas_cargas_anteriores_pendientes": "Faltan cargas de series anteriores",
        "carga_confirmada_series_y_reps_no_confirmadas": "Solo carga confirmada",
    }.get(status, "Parcial")


def render_session_detail(sessions: list[dict]):
    st.markdown("#### 🏋️ Entrenamientos detallados por fecha")
    st.caption(
        "Datos cargados a partir de tus registros. Si el peso de la barra, las cargas "
        "intermedias o las repeticiones no se confirmaron, se muestran como pendientes."
    )
    valid=[]
    for s in sessions:
        if not isinstance(s,dict):
            continue
        try:
            day=date.fromisoformat(str(s.get("date","")))
        except ValueError:
            continue
        valid.append((day,s))
    if not valid:
        st.info("Todavía no hay sesiones confirmadas.")
        return
    dates=sorted(set(d for d,_ in valid), reverse=True)
    chosen=st.selectbox(
        "Fecha del entrenamiento",
        dates, format_func=lambda d:d.strftime("%d/%m/%Y"),
        key="efg_detail_date",
    )
    chosen_sessions=[s for d,s in valid if d==chosen]
    reps_confirmed=sum(
        int(x["reps"])
        for session in chosen_sessions
        for x in session.get("sets",[])
        if isinstance(x,dict) and x.get("reps") is not None
    )
    sets_confirmed=sum(
        1 for s in chosen_sessions for x in s.get("sets",[])
        if isinstance(x,dict) and x.get("reps") is not None
    )
    a,b,c=st.columns(3)
    a.metric("Ejercicios registrados",len(chosen_sessions))
    b.metric("Series con repeticiones confirmadas",sets_confirmed)
    c.metric("Repeticiones confirmadas",reps_confirmed)
    table=[]
    for s in chosen_sessions:
        table.append({
            "Ejercicio":str(s.get("exercise","")),
            "Series":_sets_label(s),
            "Repeticiones":_reps_label(s),
            "Carga reportada":_load_label(s),
            "Estado":_status_label(s),
        })
    st.dataframe(pd.DataFrame(table),hide_index=True,use_container_width=True)
    st.markdown("##### Observaciones y datos pendientes")
    for s in chosen_sessions:
        note=str(s.get("notes","")).strip()
        if not note:
            continue
        with st.expander(str(s.get("exercise","Ejercicio"))):
            st.write(note)
            seq=s.get("sets",[])
            if seq:
                set_rows=[]
                for n,one in enumerate(seq,1):
                    kg=one.get("kg")
                    scope=one.get("load_scope") or s.get("load_scope") or ""
                    raw_lb=one.get("load_lb")
                    if raw_lb is not None:
                        load=_lb(raw_lb)
                        if scope:
                            load+=f" · {scope}"
                    elif kg is not None and float(kg)==0 and scope=="peso corporal":
                        load="Peso corporal"
                    elif kg is not None:
                        load=f"{float(kg):.2f} kg"
                    else:
                        load=_load_label(s) if s.get("reported_load_lb") is not None else "Pendiente"
                    set_rows.append({
                        "Serie":n, "Repeticiones":one.get("reps"), "Carga":load
                    })
                st.dataframe(pd.DataFrame(set_rows),hide_index=True,use_container_width=True)
            prev=s.get("previous_reference")
            if isinstance(prev,dict):
                before=prev.get("load_lb_per_side",prev.get("load_lb"))
                after=s.get("reported_load_lb")
                if before is not None and after is not None:
                    st.caption(
                        f"Progresión reportada: {_lb(before)} → {_lb(after)} "
                        f"({'por lado' if prev.get('load_lb_per_side') else 'carga informada'}). "
                        "El valor previo no tiene fecha confirmada."
                    )
    st.caption(
        "El volumen total calculado con kg × repeticiones es parcial: "
        "se excluyen ejercicios sin carga total comparable y las series con cargas desconocidas. "
        "Las sentadillas con peso corporal se cuentan en repeticiones, no en kilogramos externos."
    )
