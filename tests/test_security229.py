"""Regression tests for session revocation and atomic checkout replay handling."""
import hashlib
import sqlite3
from datetime import datetime,timedelta,timezone
import pytest
from fastapi import HTTPException
from nowup_security import session_user,revoke_session
from nowup_checkout229 import begin_checkout,remember_checkout

@pytest.fixture
def connection(tmp_path):
 c=sqlite3.connect(tmp_path/'test.db');c.row_factory=sqlite3.Row
 c.executescript('''CREATE TABLE users(id INTEGER PRIMARY KEY,is_active INTEGER);CREATE TABLE sessions(token TEXT,user_id INTEGER,expires_at TEXT);CREATE TABLE adm227_access(session_hash TEXT,end TEXT);CREATE TABLE adm227_team_sessions(token_hash TEXT);CREATE TABLE orders(id INTEGER PRIMARY KEY,tracking_token TEXT);CREATE TABLE checkout_requests229(customer_id INTEGER,professional_id INTEGER,request_key TEXT,payload_hash TEXT,order_id INTEGER,created_at TEXT,PRIMARY KEY(customer_id,professional_id,request_key));''')
 yield c
 c.close()

def test_revocation_blocks_all_shared_session_readers(connection):
 c=connection;token='opaque-session';digest=hashlib.sha256(token.encode()).hexdigest()
 c.execute('INSERT INTO users VALUES(1,1)');c.execute('INSERT INTO sessions VALUES(?,?,?)',(token,1,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
 assert session_user(c,token)['id']==1
 c.execute('INSERT INTO adm227_access VALUES(?,?)',(digest,'revoked'))
 assert session_user(c,token) is None
 revoke_session(c,digest)
 assert not c.execute('SELECT * FROM sessions').fetchall()

def test_checkout_retry_reuses_order_and_changed_payload_conflicts(connection):
 c=connection;payload={'cart':'[{"id":1,"quantity":1}]','name':'Cliente'};key='test-request-123456'
 _,key,digest=begin_checkout(c,1,2,key,payload)
 c.execute("INSERT INTO orders VALUES(1,'tracking')")
 remember_checkout(c,1,2,key,digest,1,datetime.now(timezone.utc).isoformat());c.commit()
 assert begin_checkout(c,1,2,key,payload)[0]=='tracking'
 c.rollback()
 with pytest.raises(HTTPException) as exc:begin_checkout(c,1,2,key,{**payload,'name':'Changed'})
 assert exc.value.status_code==409

def test_legacy_checkout_retry_reuses_order(connection):
 c=connection;payload={'cart':'[]'}
 _,key,digest=begin_checkout(c,1,2,'',payload)
 c.execute("INSERT INTO orders VALUES(1,'tracking')")
 remember_checkout(c,1,2,key,digest,1,datetime.now(timezone.utc).isoformat());c.commit()
 assert begin_checkout(c,1,2,'',payload)[0]=='tracking'
 c.rollback()
