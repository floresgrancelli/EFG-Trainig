"""Vistas de bloques y gráficos que mantienen variantes y condiciones de carga separadas."""
from datetime import date
from html import escape
import json
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from new_blocks import (ACTIVE_BLOCK_ID,LEGACY_BLOCK_ID,DAY_FOCUS,DAY_TIME,canonical_name,normalized,block_of,load_records,last_and_best,format_load,plan_reference)
DAYS=['Lunes','Martes','Miércoles','Jueves','Viernes']


def render_summary(plan,sessions,legacy_plan,*,prefix,archive=False):
    weeks=sorted({int(e['week']) for e in plan})
    if not weeks:
        st.info('No hay ejercicios disponibles para este bloque.');return
    a,b,c=st.columns([1,1.3,.8])
    with a:week=st.selectbox('SEMANA',weeks,index=weeks.index(4) if archive and 4 in weeks else 0,format_func=lambda w:f'Semana {w}',key=prefix+'_week')
    with b:day=st.selectbox('DÍA',range(1,6),format_func=lambda n:DAYS[n-1],key=prefix+'_day')
    with c:unit=st.selectbox('PESO EN',['lb','kg'],key=prefix+'_unit')
    chosen=[e for e in plan if int(e['week'])==week and int(e['day'])==day]
    relevant=[s for s in sessions if block_of(s)==LEGACY_BLOCK_ID] if archive else sessions
    st.markdown(f'<div class="finish"><div class="mini-title">{"RUTINA ANTERIOR · CONSULTA" if archive else "BLOQUE NUEVO · "+DAY_FOCUS[day]}</div><h3>SEMANA {week} · {DAYS[day-1].upper()}</h3><div class="muted">{len(chosen)} ejercicios'+('' if archive else ' · '+DAY_TIME[day])+'</div></div>',unsafe_allow_html=True)
    if archive:st.caption('Plan anterior conservado. Las referencias del plan se distinguen de las sesiones realizadas. Esta solapa es de consulta.')
    else:st.caption('Core y movilidad: dos vueltas, 10–15 s entre ejercicios y 30 s entre vueltas. Después, aproximaciones. Principal: 3 × 8–12 a RIR 2. Las cargas previas son referencias, no una carga asignada.')
    for i,e in enumerate(chosen,1):
        name=e['exercise'];last,best=last_and_best(relevant,name)
        exact=[s for s in relevant if s.get('exercise_id')==e['id']]
        done=max(exact,key=lambda s:str(s.get('date',''))) if exact else None
        core=e.get('set_type')=='triserie'
        colour='triserie' if core else ('superserie' if e.get('set_type')=='superserie' else 'individual')
        last_text=format_load(last,unit)
        if last:last_text+=' · '+last['date'].strftime('%d/%m/%Y')
        best_text=format_load(best,unit)
        if not last:reference=plan_reference(legacy_plan,name,unit)
        else:reference=''
        performed=''
        if done and done.get('sets'):
            reps=['?' if s.get('reps') is None else str(s.get('reps_per_side',s['reps'])) for s in done['sets']]
            suffix=' segundos' if e.get('duration_unit')=='seconds' else (' por lado' if e.get('repetitions_per_side') else '')
            performed='HECHO: '+str(len(reps))+' × '+('/'.join(reps))+suffix+' · '+str(done.get('date',''))
        rest=e.get('rest','Descanso no indicado en el plan anterior')
        html=(f'<section class="quick-group {colour}"><div class="quick-row"><div class="quick-ex">{i:02d}. {escape(name)}<div class="quick-note">{escape(e.get("pattern",""))} · {escape(e.get("intensity","") or "Esfuerzo no indicado")}</div></div>'
          f'<div class="quick-count"><div class="quick-plan">PLAN: {escape(str(e["series"]))} × {escape(str(e["repetitions"]))}</div><div class="quick-actual">{escape(performed)}</div></div>'
          f'<div class="quick-load">Última sesión: {escape(last_text)}<div class="quick-note">Mejor carga comparable: {escape(best_text)}</div></div></div>'
          f'<div class="quick-note">DESCANSO: {escape(rest)}</div>'
          +(f'<div class="quick-note">{escape(reference)}</div>' if reference else '')+'</section>')
        st.markdown(html,unsafe_allow_html=True)
    st.caption('Última sesión = mayor carga conocida de la sesión más reciente. Mejor carga = máximo histórico en esa misma condición de carga. No se mezclan pesos por lado, por mancuerna o totales. Cambiar de máquina o gimnasio puede cambiar la escala de carga.')


def render_archive(plan,sessions):
    st.markdown('### 🗃️ Rutinas antiguas')
    st.caption('Rutina anterior · 12 semanas conservadas con sus pesos, reportes y registros. La rutina nueva se consulta en Mi rutina y Rutina resumen.')
    render_summary(plan,sessions,plan,prefix='archive',archive=True)
    with st.expander('Resumen de las cinco sesiones de esta semana'):
        week=st.session_state.get('archive_week',4)
        rows=[]
        unit=st.session_state.get('archive_unit','lb')
        legacy_sessions=[s for s in sessions if block_of(s)==LEGACY_BLOCK_ID]
        for e in plan:
            if e['week']!=week:continue
            last,best=last_and_best(legacy_sessions,e['exercise'])
            rows.append({'Día':DAYS[e['day']-1],'Ejercicio':e['exercise'],'Series':e['series'],'Reps':e['repetitions'],'Última carga':format_load(last,unit),'Mejor carga comparable':format_load(best,unit),'Referencia anterior':plan_reference(plan,e['exercise'],unit)})
        st.dataframe(rows,hide_index=True,use_container_width=True)
    st.download_button('Descargar rutina anterior completa',json.dumps({'entries':plan},ensure_ascii=False,indent=2),'efg_rutina_anterior_12_semanas.json','application/json',key='archive_download')


def render_exercise_progress(sessions,plan,plot_layout,*,prefix):
    rows=load_records(sessions)
    a,b=st.columns(2)
    with a:block=st.selectbox('Bloque',['Todos los bloques','Rutina nueva','Rutina anterior'],key=prefix+'_block')
    with b:unit=st.selectbox('Unidad del gráfico',['lb','kg'],key=prefix+'_unit')
    if block!='Todos los bloques':
        wanted=ACTIVE_BLOCK_ID if block=='Rutina nueva' else LEGACY_BLOCK_ID
        rows=[r for r in rows if r['block']==wanted]
    names=sorted({r['exercise'] for r in rows},key=str.casefold)
    if not names:
        st.info('Todavía no hay cargas conocidas en este bloque. Los registros anteriores se conservan en Todos los bloques y Rutinas antiguas.');return
    name=st.selectbox('Ejercicio',names,key=prefix+'_exercise')
    chosen=[r for r in rows if r['exercise']==name]
    scopes=sorted({r['scope'] for r in chosen})
    scope=st.selectbox('Condición de carga',scopes,key=prefix+'_scope')
    chosen=[r for r in chosen if r['scope']==scope]
    if scope=='Alcance sin confirmar':st.info('Se conservan estos valores, pero su alcance no está confirmado. No se comparan con cargas totales ni por mancuerna.')
    factor=1/.45359237 if unit=='lb' else 1
    frame=pd.DataFrame(chosen)
    frame['Carga']=frame['kg']*factor
    by_date=frame.groupby('date',as_index=False)['Carga'].max().sort_values('date')
    st.caption('Solo registros con fecha. Se mantienen juntos nombres equivalentes verificados; las variantes nuevas tienen curvas propias. En máquinas distintas, la cifra de la pila no asegura un esfuerzo equivalente.')
    fig=go.Figure(go.Scatter(x=by_date['date'],y=by_date['Carga'],mode='lines+markers',line=dict(color='#F472B6',width=3),marker=dict(size=10),hovertemplate='%{x}<br>%{y:.2f} '+unit+'<extra></extra>'))
    fig.update_layout(yaxis_title=f'Carga mayor de cada sesión ({unit}) · {scope}')
    active=[r['date'] for r in chosen if r['block']==ACTIVE_BLOCK_ID]
    if active and block=='Todos los bloques':
        start=min(active).isoformat()
        fig.add_shape(type='line',x0=start,x1=start,y0=0,y1=1,yref='paper',line=dict(color='#22D3EE',dash='dash'))
        fig.add_annotation(x=start,y=1,yref='paper',text='Primera sesión del nuevo bloque',showarrow=False)
    st.plotly_chart(plot_layout(fig),use_container_width=True,key=prefix+'_load_chart',config={'displayModeBar':False})
    last=max(chosen,key=lambda r:(r['date'],r['kg']));best=max(chosen,key=lambda r:r['kg'])
    x,y=st.columns(2);x.metric('Última sesión',format_load(last,unit));y.metric('Mejor carga comparable',format_load(best,unit))
    rep_rows=[r for r in chosen if r['reps'] is not None]
    if rep_rows:
        loads=sorted({round(r['kg'],3) for r in rep_rows},reverse=True)
        fixed=st.selectbox('Carga fija para comparar repeticiones',loads,format_func=lambda v:f'{v*factor:.2f} {unit}',key=prefix+'_fixed')
        fixed_rows=[r for r in rep_rows if round(r['kg'],3)==fixed]
        rep_frame=pd.DataFrame(fixed_rows).groupby('date',as_index=False)['reps'].max().sort_values('date')
        seconds=any(r.get('seconds') for r in fixed_rows)
        label='Segundos' if seconds else 'Repeticiones'
        st.markdown('#### '+label+' a igual carga')
        rep_fig=go.Figure(go.Scatter(x=rep_frame['date'],y=rep_frame['reps'],mode='lines+markers',line=dict(color='#22D3EE',width=3)))
        rep_fig.update_layout(yaxis_title='Mejor serie · '+label.lower())
        st.plotly_chart(plot_layout(rep_fig),use_container_width=True,key=prefix+'_rep_chart',config={'displayModeBar':False})
        st.caption('Se compara la mejor serie de cada fecha a la misma carga y condición. No se suman repeticiones de series diferentes; interpretá junto con técnica y RIR.')
    detail=frame[['date','exercise','Carga','scope','reps','block','source']].rename(columns={'date':'Fecha','exercise':'Ejercicio','scope':'Condición','reps':'Reps o segundos','block':'Bloque','source':'Fuente'})
    st.dataframe(detail.sort_values('Fecha',ascending=False),hide_index=True,use_container_width=True)


def render_legacy_reports(plan,plot_layout):
    st.markdown('#### Evolución de los pesos reportados del plan anterior')
    names=sorted({e['exercise'] for e in plan if e.get('weekly_report')},key=str.casefold)
    if not names:return
    name=st.selectbox('Ejercicio del seguimiento anterior',names,key='legacy_report_exercise')
    points=[]
    for e in plan:
        r=e.get('weekly_report')
        if e['exercise']!=name or not isinstance(r,dict):continue
        vals=r.get('series_lb') or [r.get('lb')]
        nums=[]
        for v in vals:
            try:n=float(v)
            except (TypeError,ValueError):continue
            if 0<=n<=3300:nums.append(n)
        if not nums:continue
        try:day=date.fromisoformat(str(r.get('date','')))
        except ValueError:continue
        points.append({'Fecha':day,'Semana anterior':e['week'],'Carga lb':max(nums),'Condición':str(r.get('scope','Sin especificar'))})
    if not points:return
    conditions=sorted({p['Condición'] for p in points})
    condition=st.selectbox('Condición del reporte anterior',conditions,key='legacy_report_scope')
    frame=pd.DataFrame([p for p in points if p['Condición']==condition]).sort_values('Fecha')
    frame=frame.drop_duplicates(['Fecha','Carga lb','Condición'])
    fig=go.Figure(go.Scatter(x=frame['Fecha'],y=frame['Carga lb'],mode='lines+markers',line=dict(color='#22D3EE',width=3)))
    fig.update_layout(yaxis_title='Carga reportada en lb · '+condition)
    st.plotly_chart(plot_layout(fig),use_container_width=True,key='legacy_report_chart',config={'displayModeBar':False})
    st.caption('Seguimiento con fecha del plan anterior, separado de las sesiones realizadas. Las referencias sin fecha se conservan en el resumen y no se colocan en una fecha inventada.')
    st.dataframe(frame,hide_index=True,use_container_width=True)
