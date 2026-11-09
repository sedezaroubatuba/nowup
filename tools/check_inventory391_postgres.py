"""Real PostgreSQL contention test, exclusively in a disposable random schema."""
import os,sys,uuid,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from fastapi import HTTPException
from nowup_database239 import PostgresConnection,row_factory
from nowup_inventory391 import initialize,lock_store,configure,replace,order_status,snapshot,ensure
url=os.environ['NOWUP_TEST_PG_URL391'];schema='inventory391_'+uuid.uuid4().hex
admin=psycopg.connect(url,autocommit=True)
admin.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
def db():
 raw=psycopg.connect(url,autocommit=True,row_factory=row_factory)
 raw.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(schema)))
 return PostgresConnection(raw)
try:
 with db() as c:
  c.execute('CREATE TABLE professionals(id INTEGER PRIMARY KEY,business_type TEXT)')
  c.execute('CREATE TABLE products(id INTEGER PRIMARY KEY,professional_id INTEGER,fashion_details387 TEXT)')
  c.execute('CREATE TABLE orders(id INTEGER PRIMARY KEY,professional_id INTEGER,customer_id INTEGER)')
  c.execute('CREATE TABLE order_items(id INTEGER PRIMARY KEY,order_id INTEGER,product_id INTEGER,quantity INTEGER)')
  initialize(c)
  c.execute("INSERT INTO professionals VALUES(1,'fashion')")
  stock={'mode':'variants','variants':[{'size':'M','color':'Preto','quantity':10},{'size':'M','color':'Branco','quantity':2}]}
  c.execute('INSERT INTO products VALUES(1,1,?)',(json.dumps({'stock':stock}),));configure(c,1,stock)
 def reserve(n):
  c=db()
  try:
   c.execute('BEGIN');lock_store(c,1)
   replace(c,'buyer-'+str(n),n+1,1,{(1,'M','Preto'):2})
   c.commit();return 200
  except HTTPException as e:c.rollback();return e.status_code
  finally:c.close()
 with ThreadPoolExecutor(max_workers=30) as pool:codes=list(pool.map(reserve,range(30)))
 assert codes.count(200)==5 and codes.count(409)==25,codes
 with db() as c:
  assert c.execute("SELECT SUM(quantity) FROM fashion_holds391 WHERE state='held'").fetchone()[0]==10
  c.execute('BEGIN');lock_store(c,1)
  c.execute('UPDATE fashion_holds391 SET expires_at=0')
  c.execute('INSERT INTO orders VALUES(1,1,100)')
  c.execute('INSERT INTO order_items VALUES(1,1,1,2)')
  c.execute("INSERT INTO fashion_order_items391 VALUES(1,'M','Preto')")
  replace(c,'order:1',100,1,{(1,'M','Preto'):2},1)
  order_status(c,1,'confirmed');order_status(c,1,'confirmed')
  assert c.execute("SELECT on_hand FROM fashion_inventory391 WHERE color='Preto'").fetchone()[0]==8
  order_status(c,1,'cancelled');order_status(c,1,'cancelled')
  assert c.execute("SELECT on_hand FROM fashion_inventory391 WHERE color='Preto'").fetchone()[0]==10
 print('PASS PostgreSQL: 30 competing transactions; 5 accepted, 25 rejected; expiry, idempotent sale and restock verified.')
finally:
 admin.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)));admin.close()
