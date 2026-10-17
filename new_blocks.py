"""Bloques de entrenamiento e identidad de movimientos, sin migrar registros reales."""
from __future__ import annotations
import math
import re
import unicodedata
from datetime import date

ACTIVE_BLOCK_ID = 'hipertrofia-2026-10'
LEGACY_BLOCK_ID = 'rutina-anterior'
ACTIVE_TITLE = 'Hipertrofia · 3 series · RIR 2'
DAY_FOCUS = {1:'Pecho · laterales · tríceps',2:'Piernas A · cuádriceps',3:'Espalda · posteriores · bíceps',4:'Piernas B · femorales y glúteos',5:'Torso complementario'}
DAY_TIME = {1:'50–60 min',2:'45–55 min',3:'50–60 min',4:'55–60 min',5:'55–65 min · ajustar al tiempo real'}

def normalized(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',str(value)) if not unicodedata.combining(c)).casefold().split())

# Equivalencias explícitas de nombres. Nunca se unen variantes por similitud textual.
_GROUPS = {
 'Abdominales cortitos con disco':['Abdominales cortitos c/disco','Abdominales cortitoscon disco'],
 'Buenos días con disco':['Buenos dias con disco'],
 'Extensión de cuádriceps':['Extension de cuadriceps'],
 'Press inclinado con mancuernas':['Press inclinado con mancuernas a 20–30°'],
 'Jalón al pecho con agarre neutro':['Dorsalera toma neutra en polea','Jalón dorsal agarre neutro'],
 'Extensión de tríceps con cuerda':['Tríceps con soga'],
 'Prensa a 45°':['Prensa 45°'],
}
ALIASES={normalized(alias):canonical for canonical,aliases in _GROUPS.items() for alias in [canonical,*aliases]}

def canonical_name(value):
    return ALIASES.get(normalized(value),str(value).strip())

def block_of(session):
    explicit=session.get('block_id')
    if explicit:return str(explicit)
    return ACTIVE_BLOCK_ID if str(session.get('exercise_id','')).startswith('hp261017-') else LEGACY_BLOCK_ID

def view_sessions(sessions):
    return [dict(s, exercise=canonical_name(s.get('exercise','')),block_id=block_of(s)) for s in sessions if isinstance(s,dict)]

def scope_key(value):
    s=normalized(value)
    if 'no confirmado' in s or 'sin aclarar' in s or 'alcance' in s or 'sin desglosar' in s:return 'Alcance sin confirmar'
    if 'por lado' in s or s=='por_lado_y_barra':return 'Por lado · barra o plataforma aparte'
    if 'por mancuerna' in s or s=='por_mancuerna':return 'Por mancuerna'
    if 'mancuerna' in s:return 'Alcance sin confirmar'
    if 'peso corporal' in s or s=='bodyweight':return 'Peso corporal'
    if 'disco' in s:return 'Disco'
    if 'lastre' in s:return 'Lastre externo'
    if 'maquina' in s or 'polea' in s:return 'Máquina o polea'
    return 'Carga total externa'

def valid_number(value):
    try:n=float(value)
    except (TypeError,ValueError):return None
    return n if math.isfinite(n) and 0<=n<=1500 else None

def load_records(sessions,exercise=None):
    """Una fila por serie conocida o una referencia por sesión parcial. No suma kg ficticios."""
    rows=[]
    for s in sessions:
        if not isinstance(s,dict):continue
        name=canonical_name(s.get('exercise',''))
        if exercise is not None and normalized(name)!=normalized(canonical_name(exercise)):continue
        try:day=date.fromisoformat(str(s.get('date','')))
        except ValueError:continue
        made=[]
        for i,item in enumerate(s.get('sets',[]),1):
            if not isinstance(item,dict):continue
            raw_lb=valid_number(item.get('load_lb'))
            raw_kg=valid_number(item.get('kg'))
            if raw_lb is None and raw_kg is None:continue
            scope=scope_key(item.get('load_scope') or s.get('load_scope',''))
            amount=raw_lb*.45359237 if raw_lb is not None else raw_kg
            reps=item.get('reps')
            reps=reps if isinstance(reps,int) and not isinstance(reps,bool) and 0<=reps<=10000 else None
            made.append(dict(date=day,kg=amount,scope=scope,reps=reps,exercise=name,block=block_of(s),series=i,source='Sesión registrada',seconds=bool(s.get('duration_unit')=='seconds' or name=='Plancha común')))
        rows.extend(made)
        reported=valid_number(s.get('reported_load_lb'))
        if reported is not None and not made:
            rows.append(dict(date=day,kg=reported*.45359237,scope=scope_key(s.get('load_scope','')),reps=None,exercise=name,block=block_of(s),series=None,source='Carga reportada sin series completas',seconds=name=='Plancha común'))
    return rows

def format_load(record,unit='lb'):
    if not record:return 'Sin registro'
    if record['scope']=='Peso corporal':return 'Peso corporal'
    n=record['kg'] if unit=='kg' else record['kg']/.45359237
    label=f'{n:.2f}'.rstrip('0').rstrip('.')+' '+unit
    return label+' · '+record['scope'].lower()

def last_and_best(sessions,exercise):
    rows=load_records(sessions,exercise)
    if not rows:return None,None
    # Última sesión, y dentro de ella su mayor carga; no se inventa un orden de series faltante.
    last=max(enumerate(rows),key=lambda x:(x[1]['date'],x[0]))[1]
    same_day=[r for r in rows if r['date']==last['date'] and r['scope']==last['scope']]
    last=max(same_day,key=lambda r:r['kg'])
    best=max((r for r in rows if r['scope']==last['scope']),key=lambda r:r['kg'])
    return last,best


def plan_reference(plan,exercise,unit='lb'):
    """Referencias históricas solo si coinciden movimiento y nombre explícito."""
    candidates=[]
    key=normalized(canonical_name(exercise))
    for e in plan:
        if normalized(canonical_name(e.get('exercise','')))!=key:continue
        report=e.get('weekly_report')
        if isinstance(report,dict):
            vals=report.get('series_lb') or [report.get('lb')]
            nums=[n for n in (valid_number(v) for v in vals) if n is not None]
            if nums:candidates.append((str(report.get('date','')),dict(kg=max(nums)*.45359237,scope=scope_key(report.get('scope',''))),'Seguimiento '+str(report.get('date',''))))
        ref=e.get('planned_load')
        if isinstance(ref,dict):
            if ref.get('kind')=='bodyweight':candidates.append(('',dict(kg=0,scope='Peso corporal'),'Referencia del plan anterior'))
            elif valid_number(ref.get('lb')) is not None:candidates.append(('',dict(kg=float(ref['lb'])*.45359237,scope=scope_key(ref.get('scope',''))),'Referencia del plan anterior'))
        raw=valid_number(e.get('reference_weight_lb'))
        if raw is not None:candidates.append(('',dict(kg=raw*.45359237,scope='Alcance sin confirmar'),'Referencia inicial sin fecha'))
    if not candidates:return 'Sin referencia comparable'
    _,row,source=max(candidates,key=lambda r:(r[0],r[1]['kg']))
    return format_load(row,unit)+' · '+source
