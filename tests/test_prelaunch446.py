"""Regression checks for the audited package, isolated SQLite and captured notifications."""
import json
from datetime import datetime,timedelta,timezone
import pytest
from fastapi.testclient import TestClient
from test_merchant228 import env

@pytest.fixture
def adm(env):
 m,_,ids,pid,other=env
 m.nowup_alerts112.initialize()
 with m.db() as c:
  uid=c.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()[0]
  c.execute('INSERT OR REPLACE INTO sessions(token,user_id,expires_at) VALUES(?,?,?)',('regression446-admin',uid,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
 client=TestClient(m.app,headers={'Origin':'http://testserver'},follow_redirects=False);client.cookies.set('nowup_session','regression446-admin')
 return m,client,ids,pid,other

def change(client,kind,oid,value):
 state=client.get('/admin/super/api/state').json()
 return client.post('/admin/super/api/change',headers={'X-Nowup-Admin':'227'},json={'revision':state['_meta']['revision'],'reason':'Regressão isolada pacote 446','changes':[{'kind':kind,'id':oid,'value':value}]})

def test_store_form_hours_really_persist_and_invalid_schedule_rolls_back(adm):
 m,c,ids,pid,other=adm
 with m.db() as db:before=dict(db.execute('SELECT * FROM professionals WHERE id=?',(other,)).fetchone())
 fields={'name':'Loja de auditoria','owner':'Lojista','phone':'12999999999','document':'','city':'Ubatuba','neighborhood':'Centro','address':'Rua teste','radius':5,'prep':30,'hoursByDay':['18:00-02:00','fechado','','','','','']}
 r=change(c,'stores',pid,fields);assert r.status_code==200,r.text
 with m.db() as db:
  stored=dict(db.execute('SELECT * FROM professionals WHERE id=?',(pid,)).fetchone());schedule=json.loads(stored['business_hours']);assert schedule[m.DAYS[0]]=={'enabled':True,'start':'18:00','end':'02:00'}
  assert not schedule[m.DAYS[1]]['enabled']
  assert dict(db.execute('SELECT * FROM professionals WHERE id=?',(other,)).fetchone())==before
 assert change(c,'stores',pid,{'name':'Não persistir','hoursByDay':['25:00-26:00']*7}).status_code==400
 with m.db() as db:assert db.execute('SELECT display_name FROM professionals WHERE id=?',(pid,)).fetchone()[0]=='Loja de auditoria'


def test_contract_without_gateway_coupon_saves(adm):
 m,c,ids,pid,other=adm
 # Existing review rules remain active. Use a fixture-approved contract without changing its plan.
 r=change(c,'stores',pid,{'due':'2026-12-15','trialUntil':'','method':'Pix'})
 assert r.status_code==200,r.text
 assert next(s for s in r.json()['stores'] if s['id']==pid)['due']=='2026-12-15'
 assert change(c,'stores',pid,{'billingCoupon':'fabricado'}).status_code==400


def test_real_support_and_complaints_visible_and_response_reaches_user(adm):
 m,c,ids,pid,other=adm
 with m.db() as db:
  owner=db.execute('SELECT user_id FROM professionals WHERE id=?',(pid,)).fetchone()[0];stamp=m.now_iso()
  tid=db.execute("INSERT INTO support205(user_id,subject,created_at,updated_at) VALUES(?,'Atendimento real 446',?,?)",(owner,stamp,stamp)).lastrowid
  rid=db.execute("INSERT INTO reports(customer_id,professional_id,reason,created_at) VALUES(?,?,'Denúncia 446',?)",(owner,pid,stamp)).lastrowid
 data=c.get('/admin/super/api/support').json();assert any(x['id']==tid for x in data['rows']);assert data['counts']['tickets']>=1
 assert any(x['id']==rid for x in c.get('/admin/super/api/support?kind=reports').json()['rows'])
 assert c.post('/admin/super/api/support/'+str(tid),json={'status':'in_progress','body':'Resposta real 446'},headers={'X-Nowup-Admin':'227'}).status_code==200
 with m.db() as db:
  assert any(x['body']=='Resposta real 446' for x in m.nowup_admin205.ticket(db,tid)['messages'])
  assert db.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND title='Mensagem da equipe NowUp'",(owner,)).fetchone()[0]>=1
 assert c.post('/admin/super/api/reports/'+str(rid),json={'status':'resolved','reason':'Revisão concluída'},headers={'X-Nowup-Admin':'227'}).status_code==200
 with m.db() as db:assert db.execute('SELECT status FROM reports WHERE id=?',(rid,)).fetchone()[0]=='resolved'
 assert c.post('/admin/super/api/support/'+str(tid),json={'status':'resolved'},headers={'Origin':'https://evil.invalid','X-Nowup-Admin':'227'}).status_code==403


def test_private_order_details_and_monitoring_require_permissions(adm,monkeypatch):
 m,c,ids,pid,other=adm;oid=next(iter(ids.values()))
 detail=c.get('/admin/super/api/order/'+str(oid));assert detail.status_code==200,detail.text
 data=detail.json();assert data['order']['payment_method'] and data['items'] and 'payment_confirmed' in data['order']
 assert c.get('/admin/super/api/order/999999999').status_code==404
 import nowup_backup
 monkeypatch.setattr(nowup_backup,'state',lambda:{'error':'postgres://private-secret','external_key':'secret-file','last_external':m.now_iso()})
 monitor=c.get('/admin/super/api/operations');assert monitor.status_code==200,monitor.text
 assert monitor.json()['database']['engine']=='sqlite' and monitor.json()['backup']['failed']
 assert 'private-secret' not in monitor.text and 'secret-file' not in monitor.text
 for token in ('','merchant-test','other-test'):
  guest=TestClient(m.app,headers={'Origin':'http://testserver'})
  if token:guest.cookies.set('nowup_session',token)
  for path in ['/admin/super/api/support','/admin/super/api/operations','/admin/super/api/order/'+str(oid),'/admin/super/api/order/'+str(oid)+'/receipt/1']:
   assert guest.get(path).status_code in (401,403)


def test_staff_support_has_real_author_without_elevating_to_system(adm):
 m,c,ids,pid,other=adm
 with m.db() as db:
  owner=db.execute('SELECT user_id FROM professionals WHERE id=?',(pid,)).fetchone()[0];at=m.now_iso()
  tid=db.execute("INSERT INTO support205(user_id,subject,created_at,updated_at) VALUES(?,'Equipe 446',?,?)",(owner,at,at)).lastrowid
  from nowup_admin227 import put,tokenhash
  put(db,'staff',446,{'id':446,'name':'Suporte real','email':'staff@example.invalid','enabled':True,'permissions':['support']})
  db.execute('INSERT INTO adm227_team_sessions VALUES(?,?,?)',(tokenhash('staff446-token'),446,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
 staff=TestClient(m.app,headers={'Origin':'http://testserver'});staff.cookies.set('nowup_team227','staff446-token')
 assert staff.post('/admin/super/api/support/'+str(tid),json={'status':'resolved','body':'Resposta por funcionário'},headers={'X-Nowup-Admin':'227'}).status_code==200
 with m.db() as db:
  message=next(x for x in m.nowup_admin205.ticket(db,tid)['messages'] if x['body']=='Resposta por funcionário');assert message['name']=='Suporte real' and message['sender_id'] is None
 assert staff.get('/admin/super/api/operations').status_code==403
 assert staff.get('/admin/super/api/order/'+str(next(iter(ids.values())))).status_code==403


def test_operational_errors_store_route_template_without_client_data(adm):
 m,c,*_=adm
 @m.app.get('/audit446/failure/{tracking_token}')
 def fail_for_audit(tracking_token:str):raise RuntimeError('private-message-446')
 probe=TestClient(m.app,raise_server_exceptions=False)
 assert probe.get('/audit446/failure/private-tracking-446').status_code==500
 result=c.get('/admin/super/api/operations');assert result.status_code==200
 assert 'private-tracking-446' not in result.text and 'private-message-446' not in result.text
 assert any(i['route']=='/audit446/failure/{tracking_token}' and i['error_class']=='RuntimeError' for i in result.json()['incidents'])
 assert c.post('/admin/super/api/support/1',content='invalid-json',headers={'Origin':'http://testserver','X-Nowup-Admin':'227','Content-Type':'application/json'}).status_code==400
