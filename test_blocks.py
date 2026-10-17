import ast,base64,json,math,unittest
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch
from new_blocks import *

class BlockTests(unittest.TestCase):
 def test_identity_and_variants(self):
  self.assertEqual(canonical_name('Tríceps con soga'),canonical_name('Extensión de tríceps con cuerda'))
  self.assertEqual(canonical_name('Abdominales cortitoscon disco'),canonical_name('Abdominales cortitos con disco'))
  self.assertNotEqual(canonical_name('Vuelos laterales'),canonical_name('Vuelos laterales en máquina'))
  self.assertNotEqual(canonical_name('Peso muerto rumano'),canonical_name('Peso muerto rumano en Smith'))
  self.assertNotEqual(canonical_name('Curl martillo'),canonical_name('Curl con mancuernas'))
 def test_plan_and_archive_integrity(self):
  old=json.loads(Path('data/plan.json').read_text());new=json.loads(Path('data/active_plan.json').read_text())
  self.assertEqual(len(old['entries']),565)
  self.assertEqual(len(new['entries']),480)
  self.assertFalse({e['id'] for e in old['entries']} & {e['id'] for e in new['entries']})
  for w in range(1,13):
   for day,count in [(1,8),(2,7),(3,8),(4,8),(5,9)]:
    rows=[e for e in new['entries'] if e['week']==w and e['day']==day]
    self.assertEqual(len(rows),count)
    self.assertTrue(all(e['series']=='2' for e in rows[:3]))
    self.assertTrue(all(e['series']=='3' and e['repetitions']=='8–12' and e['intensity']=='RIR 2' for e in rows[3:]))
    self.assertTrue(all(e.get('rest') and not e.get('weekly_report') and not e.get('planned_load') for e in rows))
 def test_partial_scopes_and_blocks(self):
  sessions=[{'exercise':'Tríceps con soga','exercise_id':'s4-d3-f1','date':'2026-10-14','sets':[{'kg':30,'reps':10,'load_scope':'polea'}]}, {'exercise':'Extensión de tríceps con cuerda','exercise_id':'hp261017-w1-d1-e5','date':'2026-10-19','sets':[{'kg':35,'reps':9,'load_scope':'Máquina o polea'}]}, {'exercise':'Tríceps con soga','date':'2026-10-20','sets':[{'kg':None,'load_lb':50,'reps':8,'load_scope':'por lado'}]}]
  rows=load_records(sessions,'Extensión de tríceps con cuerda')
  self.assertEqual(len(rows),3);self.assertEqual(rows[1]['block'],ACTIVE_BLOCK_ID)
  self.assertNotEqual(rows[0]['scope'],rows[2]['scope'])
  last,best=last_and_best(sessions,'Extensión de tríceps con cuerda')
  self.assertEqual(last['scope'],best['scope'])
  self.assertEqual(len(sessions[0]['sets']),1)
 def test_none_is_not_zero(self):
  rows=load_records([{'exercise':'X','date':'2026-10-13','sets':[{'kg':None,'reps':10}]}])
  self.assertEqual(rows,[])
 def test_existing_maximum_function(self):
  mod=ast.parse(Path('app.py').read_text());target=next(n for n in mod.body if isinstance(n,ast.FunctionDef) and n.name=='monthly_maximum_weights')
  ns={'date':date,'timedelta':timedelta,'math':math}
  exec(compile(ast.Module(body=[target],type_ignores=[]),'<test>','exec'),ns)
  old=json.loads(Path('data/plan.json').read_text())['entries']
  m=ns['monthly_maximum_weights'](old,[],date(2026,10,12))
  self.assertAlmostEqual(m['extension de cuadriceps']['kg']/.45359237,235)

if __name__=='__main__':unittest.main()
