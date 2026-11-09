import sqlite3
import pytest
from fastapi import FastAPI,HTTPException
from fastapi.testclient import TestClient
import nowup_banners207 as banners

@pytest.fixture
def client(tmp_path):
 path=tmp_path/'banners.db'
 def db():
  c=sqlite3.connect(path);c.row_factory=sqlite3.Row;return c
 with db() as c:
  c.executescript('''CREATE TABLE professionals(id INTEGER PRIMARY KEY,user_id INTEGER,slug TEXT,blocked INTEGER,admission_status TEXT,plan_active TEXT,is_premium INTEGER,offer_mode TEXT);
  INSERT INTO professionals VALUES(1,1,'loja',0,'approved','cardapio',1,'menu'),(2,2,'outra',0,'approved','cardapio',1,'menu');
  CREATE TABLE products(id INTEGER PRIMARY KEY,professional_id INTEGER,name TEXT);
  INSERT INTO products VALUES(1,1,'Cerveja'),(2,1,'Água'),(3,2,'Outra loja');
  CREATE TABLE store_banners207(id INTEGER PRIMARY KEY,professional_id INTEGER,title TEXT,image TEXT,mode TEXT,product_ids TEXT,active INTEGER DEFAULT 1);
  INSERT INTO store_banners207 VALUES(1,1,'Primeiro','um.jpg','info','[]',1),(2,1,'Segundo','dois.jpg','single','[1]',1),(3,2,'Outra loja','tres.jpg','info','[]',1);''')
 def ensure(c,table,name,definition):
  if name not in {r[1] for r in c.execute('PRAGMA table_info('+table+')')}:c.execute('ALTER TABLE '+table+' ADD COLUMN '+name+' '+definition)
 def user(request,role):
  if request.headers.get('x-owner')!='1':raise HTTPException(403)
  return {'id':1}
 banners.G.clear();banners.configure({'db':db,'ensure_column':ensure,'require_user':user})
 banners.initialize();banners.initialize()
 app=FastAPI();app.include_router(banners.router)
 with TestClient(app,follow_redirects=False) as client:yield client,db

def test_migrate_preserve_existing_and_save_link(client):
 cl,db=client
 assert [b['title'] for b in cl.get('/api/loja/loja/banners207').json()['items']]==['Primeiro','Segundo']
 r=cl.post('/painel/banners/salvar',headers={'x-owner':'1'},data={'id':'1','title':'Compartilhe','mode':'link','link':'https://example.com/menu?x=1','active':'1'})
 assert r.status_code==303,r.text
 items=cl.get('/api/loja/loja/banners207').json()['items']
 assert items[0]['link']=='https://example.com/menu?x=1' and items[0]['ids']==[]
 with db() as c:assert c.execute('SELECT image FROM store_banners207 WHERE id=1').fetchone()[0]=='um.jpg'

@pytest.mark.parametrize('link',['javascript:alert(1)','data:text/html,a','//evil.com','https://ok.com\\evil','https://user:pass@example.com','https://example.com/\nx','', 'https://example.com:bad'])
def test_invalid_links_never_saved(client,link):
 cl,db=client
 r=cl.post('/painel/banners/salvar',headers={'x-owner':'1'},data={'id':'1','title':'Link','mode':'link','link':link})
 assert r.status_code==400
 with db() as c:assert c.execute('SELECT mode FROM store_banners207 WHERE id=1').fetchone()[0]=='info'

def test_saved_order_public_and_owner_isolation(client):
 cl,db=client
 r=cl.post('/painel/banners/ordem',headers={'x-owner':'1'},data={'banner_ids':['2','1']})
 assert r.status_code==303,r.text
 assert [b['title'] for b in cl.get('/api/loja/loja/banners207').json()['items']]==['Segundo','Primeiro']
 for ids in [['3','1'],['1','1'],['1'],['1','2','3']]:
  assert cl.post('/painel/banners/ordem',headers={'x-owner':'1'},data={'banner_ids':ids}).status_code==400
 assert cl.post('/painel/banners/ordem',data={'banner_ids':['1','2']}).status_code==403
 assert cl.post('/painel/banners/salvar',headers={'x-owner':'1'},data={'id':'3','title':'Intruso','mode':'info'}).status_code==404
 assert cl.post('/painel/banners/salvar',headers={'x-owner':'1'},data={'id':'1','title':'Intruso','mode':'single','products':['3']}).status_code==400
 with db() as c:assert c.execute('SELECT sort_order FROM store_banners207 WHERE id=3').fetchone()[0]==0

def test_new_banner_appends_and_links_clear_for_product_mode(client):
 cl,db=client
 with db() as c:c.execute("UPDATE store_banners207 SET mode='link',link='https://example.com' WHERE id=1")
 assert cl.post('/painel/banners/salvar',headers={'x-owner':'1'},data={'id':'1','title':'Produto','mode':'single','products':['2'],'active':'1'}).status_code==303
 with db() as c:assert c.execute('SELECT link FROM store_banners207 WHERE id=1').fetchone()[0]==''
 banners.G['save_image']=lambda upload:'novo.webp'
 assert cl.post('/painel/banners/salvar',headers={'x-owner':'1'},data={'title':'Novo','mode':'link','link':'https://example.com','active':'1'},files={'image':('novo.webp',b'fake','image/webp')}).status_code==303
 assert cl.get('/api/loja/loja/banners207').json()['items'][-1]['title']=='Novo'
