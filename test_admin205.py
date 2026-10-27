import sys,ast,sqlite3,secrets,types
from pathlib import Path
from datetime import datetime,timezone,timedelta
ROOT=Path(__file__).resolve().parent
if not (ROOT/'app.py').exists():ROOT=ROOT/'adm205'
sys.path.insert(0,str(ROOT))
import pytest
from fastapi import FastAPI,HTTPException
from fastapi.testclient import TestClient
from fastapi.templating import Jinja2Templates
import nowup_admin205 as m
import nowup_admin97 as legacy

@pytest.fixture
def env(tmp_path):
 path=tmp_path/'db.sqlite'
 def db():
  c=sqlite3.connect(path);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
 ns={'db':db,'datetime':datetime,'timezone':timezone,'timedelta':timedelta,'SESSION_ABSOLUTE_DAYS238':90,'SESSION_DAYS':30}
 tree=ast.parse((ROOT/'app.py').read_text());ensure=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='ensure_column');exec(compile(ast.Module(body=[ensure],type_ignores=[]),'schema','exec'),ns)
 init=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='init_db');part=[]
 for node in init.body:
  if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('defaults','epoch238') for t in node.targets):break
  if 'nowup_included195' not in ast.unparse(node):part.append(node)
 part.extend(ast.parse('conn.commit()\nconn.close()').body)
 fn=ast.FunctionDef(name='schema',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=part,decorator_list=[])
 exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'schema','exec'),ns);ns['schema']()
 def auth(r,role=None):
  role_=r.headers.get('x-role');uid=int(r.headers.get('x-user','1'))
  if not role_:raise HTTPException(401)
  if role and role!=role_:raise HTTPException(403)
  with db() as c:
   user=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
   if not user or not user['is_active']:raise HTTPException(401)
   return dict(user)
 with db() as c:
  for uid,role,name in [(1,'admin','Samuel'),(2,'customer','Maria'),(3,'customer','Lucas'),(4,'professional','Loja A'),(5,'professional','Loja B')]:
   c.execute('INSERT INTO users(id,role,name,email,password_hash,created_at,city,state,neighborhood,address) VALUES(?,?,?,?,?,?,?,?,?,?)',(uid,role,name,str(uid)+'@example.com','hash','2026-10-18T12:00:00+00:00','Ubatuba','SP','Centro','Rua 1, 100'))
  for pid,uid,plan in [(1,4,'vitrine'),(2,5,'cardapio')]:c.execute('INSERT INTO professionals(id,user_id,slug,display_name,created_at,city,state,neighborhood,plan_active,billing_due_date) VALUES(?,?,?,?,?,?,?,?,?,?)',(pid,uid,'loja'+str(pid),'Loja '+str(pid),'2026-10-18T12:00:00+00:00','Ubatuba','SP','Centro',plan,'2026-10-01'))
  c.execute("INSERT INTO orders(professional_id,customer_id,customer_name,created_at,updated_at,status,total_cents,neighborhood,fulfillment_type) VALUES(1,2,'Maria','2026-10-18T12:00:00+00:00','2026-10-18T13:00:00+00:00','completed',2500,'Centro','delivery')")
  c.execute("INSERT INTO order_status_history(order_id,status,created_at) VALUES(1,'completed','2026-10-18T13:00:00+00:00')")
 templates=Jinja2Templates(directory=str(ROOT/'templates'))
 def context(r,**kw):return dict({'request':r,'user':auth(r),'settings':{},'categories':[],'banners':[],'business_slides':[]},**kw)
 m.configure(dict(nowup_alerts112=None,db=db,require_user=auth,templates=templates,context=context,normalize_email=lambda x:x.strip().lower() if '@' in x else '',verification_token=lambda:('token','2026-10-19T12:00:00+00:00'),send_verification=lambda *a:True,slugify=lambda s:s.lower().replace(' ','-')))
 legacy.configure(db,auth,templates,context);legacy.init_support();m.initialize();m.initialize()
 app=FastAPI();app.include_router(m.router)
 client=TestClient(app,headers={'x-role':'admin','x-user':'1'},follow_redirects=False)
 return client,db,ns,tree

def test_all_screens(env):
 client,db,_,_=env
 for sec in m.SECTIONS:
  r=client.get('/admin/central',params={'secao':sec});assert r.status_code==200,(sec,r.text[:500]);assert r.headers['cache-control']=='no-store'
 for sec,uid in [('clientes',2),('lojistas',4)]:
  r=client.get('/admin/central',params={'secao':sec,'conta':uid});assert r.status_code==200,r.text[:500];assert 'Salvar cadastro' in r.text

def test_filters(env):
 client,db,_,_=env
 with db() as c:
  assert m.people(c,{'pedidos':'com'})[1]==1
  assert m.people(c,{'pedidos':'sem'})[1]==1
  assert m.people(c,{'bairro':'Ausente'})[1]==0
  assert m.people(c,{'cidade':'Ubatuba','estado':'SP','inicio':'2026-10-18','fim':'2026-10-18'})[1]==2
  assert m.people(c,{'situacao':'inadimplentes'},True)[1]==2 # vitrine também é paga
  assert m.people(c,{'plano':'vitrine'},True)[1]==1
  assert m.people(c,{'q':"' OR 1=1 --"})[1]==0
  assert m.people(c,{'pagina':'999'})[2]==1

def test_inactivate_and_preserve(env):
 client,db,_,_=env
 r=client.post('/admin/central/contas/2/situacao',data={'active':0,'reason':'Solicitado pelo cliente'});assert r.status_code==303
 with db() as c:
  assert c.execute('SELECT is_active FROM users WHERE id=2').fetchone()[0]==0
  assert c.execute('SELECT count(*) FROM orders WHERE customer_id=2').fetchone()[0]==1
  assert c.execute('SELECT count(*) FROM admin_changes205').fetchone()[0]==1
 assert client.post('/admin/central/contas/1/situacao',data={'active':0,'reason':'teste'}).status_code==404
 assert client.post('/admin/central/contas/3/situacao',data={'active':0,'reason':''}).status_code in (400,422)

def test_edit_email(env):
 client,db,_,_=env
 values=dict(name='Maria Nova',email='novo@example.com',phone='',address='Rua 2, 20',neighborhood='Estufa II',city='Ubatuba',state='SP')
 assert client.post('/admin/central/contas/2/editar',data=values).status_code==303
 with db() as c:
  u=c.execute('SELECT * FROM users WHERE id=2').fetchone();assert u['email_verified']==0;assert u['neighborhood']=='Estufa II'
 values['email']='3@example.com';assert client.post('/admin/central/contas/2/editar',data=values).status_code==409

def test_support_isolation(env):
 client,db,_,_=env
 assert client.post('/admin/central/contas/2/mensagem',data={'subject':'Atendimento','body':'Olá Maria'}).status_code==303
 r=client.get('/admin/central?secao=suporte&chamado=1');assert r.status_code==200
 headers={'x-role':'customer','x-user':'2'}
 r=client.get('/suporte?chamado=1',headers=headers);assert r.status_code==200;assert 'Olá Maria' in r.text
 assert client.get('/suporte?chamado=1',headers={'x-role':'customer','x-user':'3'}).status_code==404
 assert client.post('/suporte/1',data={'body':'Olá'},headers={'x-role':'customer','x-user':'3'}).status_code==404
 assert client.post('/suporte/1',data={'body':'Respondido'},headers=headers).status_code==303
 assert client.post('/admin/central/suporte/1',data={'status':'resolved','body':'Tudo certo'}).status_code==303
 assert client.post('/suporte/1',data={'body':'Mais uma dúvida'},headers=headers).status_code==303
 with db() as c:
  assert c.execute('SELECT status FROM support205 WHERE id=1').fetchone()[0]=='open'
  assert c.execute('SELECT count(*) FROM notifications WHERE user_id=2').fetchone()[0]==2

def test_access(env):
 client,db,_,_=env
 for sec in m.SECTIONS:
  assert client.get('/admin/central?secao='+sec,headers={'x-role':'customer','x-user':'2'}).status_code==403
 assert client.post('/admin/central/categorias',data={'name':'X'},headers={'x-role':'customer','x-user':'2'}).status_code==403

def test_category_region(env):
 client,db,_,_=env
 assert client.post('/admin/central/categorias',data={'name':'Restaurantes','active':1,'sort_order':1}).status_code==303
 assert client.post('/admin/central/categorias',data={'name':'Restaurantes','active':1}).status_code==409
 with db() as c:
  r=m.regional(c,{'inicio':'2026-10-18','fim':'2026-10-18','cidade':'Ubatuba','estado':'SP','bairro':'Centro'});assert r['sales'][0]['amount']==2500;assert r['delivered'][0]['amount']==2500;assert r['registrations'][0][0]['count']==2
 assert client.get('/admin/central?secao=relatorios&inicio=2026-10-20&fim=2026-10-01').status_code==400

def test_registration_fields(env):
 client,db,ns,tree=env
 from fastapi import Form
 from fastapi.responses import RedirectResponse
 from typing import Optional
 sent=[]
 def verify(*args):sent.append(args);return True
 ns.update(Request=__import__('fastapi').Request,Form=Form,Optional=Optional,sqlite3=sqlite3,RedirectResponse=RedirectResponse,os=__import__('os'),normalize_email=lambda x:x.strip().lower(),normalize_phone=lambda x:x,hash_password=lambda p:'hash',email_service_configured=lambda:True,verification_token=lambda:('verifytoken','2026-10-19T12:00:00+00:00'),now_iso=lambda:'2026-10-18T12:00:00+00:00',send_verification=verify,nowup_admin205=m,active_cities=lambda:['Ubatuba'],unique_slug=lambda c,n:'novo-lojista')
 for name in ('signup_customer','signup_professional'):
  node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name);node.decorator_list=[];exec(compile(ast.Module(body=[node],type_ignores=[]),'signup','exec'),ns)
 common=dict(name='Cliente Novo',email='clientenovo@example.com',phone='12999999999',password='senha1234',password_confirm='senha1234',accept_terms='1')
 r=ns['signup_customer'](**common,address='',neighborhood='',city='',state='');assert 'erro=endereco' in r.headers['location']
 r=ns['signup_customer'](**common,address='Rua X, 100',neighborhood='Estufa II',city='Ubatuba',state='SP');assert r.status_code==303
 with db() as c:
  u=c.execute('SELECT * FROM users WHERE email=?',(common['email'],)).fetchone();assert u['address']=='Rua X, 100';assert u['state']=='SP';assert u['email_verified']==0;assert u['verification_token']=='verifytoken'
 pro=dict(common,email='novaloja@example.com',name='Nova loja',doc_type='CNPJ',document='123',business_type='store',offer_mode='services',plan='vitrine',city='Ubatuba',neighborhood='Centro',cep='',description='',services='',category_ids=[],address='Rua A, 10',state='SP')
 assert ns['signup_professional'](**pro).status_code==303
 with db() as c:
  p=c.execute("SELECT * FROM professionals WHERE slug='novo-lojista'").fetchone();assert p['address']=='Rua A, 10';assert p['state']=='SP';assert p['admission_status']=='pending'
 assert len(sent)==2

def test_billing_wrapper_and_csrf(env):
 client,db,ns,tree=env
 from fastapi import Form,Request
 from fastapi.responses import RedirectResponse
 auth=m.G['require_user'];ns.update(Request=Request,Form=Form,HTTPException=HTTPException,RedirectResponse=RedirectResponse,require_user=auth)
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='admin_save_billing');node.decorator_list=[];exec(compile(ast.Module(body=[node],type_ignores=[]),'billing','exec'),ns);m.G['admin_save_billing']=ns['admin_save_billing']
 assert client.post('/admin/central/lojas/1/financeiro',data={'due_date':'2026-11-01','last_paid':'2026-10-01'},headers={'origin':'http://testserver'}).status_code==303
 assert client.post('/admin/central/lojas/1/financeiro',data={'due_date':'2026-11-01','last_paid':'2026-10-01'},headers={'origin':'https://evil.invalid'}).status_code==403
 with db() as c:assert c.execute('SELECT billing_due_date FROM professionals WHERE id=1').fetchone()[0]=='2026-11-01'

def test_template_forms_and_account_deletion(env):
 client,db,ns,tree=env
 from jinja2 import Environment,FileSystemLoader
 e=Environment(loader=FileSystemLoader(str(ROOT/'templates')))
 for p in (ROOT/'templates').glob('*.html'):e.get_template(p.name)
 # Account deletions are redirects; no DELETE statements remain in these handlers.
 for name in ('admin_delete_client','admin_delete_professional','admin_delete_all_demo_profiles'):
  node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
  assert 'DELETE FROM' not in ast.unparse(node)
