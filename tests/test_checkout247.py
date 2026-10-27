import importlib,json
from datetime import datetime,timezone
from fastapi.testclient import TestClient
import pytest

@pytest.fixture
def checkout(tmp_path,monkeypatch):
    monkeypatch.setenv('NOWUP_DB_ENGINE','sqlite')
    monkeypatch.setenv('NOWUP_ADMIN_EMAIL','admin-release247@example.invalid')
    monkeypatch.setenv('NOWUP_ADMIN_PASSWORD','isolated-release247-password')
    m=importlib.import_module('app');monkeypatch.setattr(m,'DB_PATH',tmp_path/'db')
    uploads=tmp_path/'uploads';uploads.mkdir();monkeypatch.setattr(m,'UPLOAD_DIR',uploads)
    m.init_db();m.nowup_push75.initialize();m.nowup_alerts112.initialize()
    with m.db() as c:
        pro=c.execute('SELECT * FROM professionals ORDER BY id LIMIT 1').fetchone()
        c.execute("UPDATE professionals SET plan_active='ambos',is_premium=1,offer_mode='menu',business_status='open',business_hours='',allows_pickup=1,minimum_order_cents=0,admission_status='approved' WHERE id=?",(pro['id'],))
        stamp=datetime.now(timezone.utc).isoformat()
        product=c.execute("INSERT INTO products(professional_id,name,price_cents,extras_mode,created_at,updated_at) VALUES(?,'Auditoria',300,'none',?,?)",(pro['id'],stamp,stamp)).lastrowid
        uid=c.execute("INSERT INTO users(role,name,email,password_hash,created_at) VALUES('customer','Audit','audit247@example.invalid','unused',?)",(stamp,)).lastrowid
    customer={'id':uid,'role':'customer'}
    monkeypatch.setattr(m,'current_user',lambda request:customer)
    client=TestClient(m.app,headers={'Origin':'http://testserver'})
    payload={'customer_name':'Audit','customer_phone':'12999999999','fulfillment_type':'pickup','cart_json':json.dumps([{'id':product,'quantity':1}]),'request_key':'release247-request-0001'}
    return m,client,'/p/'+pro['slug']+'/menu/pedido',payload,product,customer

@pytest.mark.parametrize('bad',[{'id':'bad','quantity':1},{'id':1,'quantity':True},{'id':1,'quantity':1.5},{'id':1,'quantity':0}])
def test_invalid_item_rejects_entire_order(checkout,bad):
    m,client,url,data,pid,_=checkout
    data['cart_json']=json.dumps([{'id':pid,'quantity':1},bad])
    assert client.post(url,data=data,follow_redirects=False).status_code==400
    with m.db() as c:assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==0

def test_more_than_50_lines_rejected_not_truncated(checkout):
    m,client,url,data,pid,_=checkout;data['cart_json']=json.dumps([{'id':pid,'quantity':1}]*51)
    assert client.post(url,data=data,follow_redirects=False).status_code==400
    with m.db() as c:assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==0

def test_completion_is_authenticated_scoped_and_retry_is_idempotent(checkout):
    m,client,url,data,_,customer=checkout
    result=client.post(url,data=data,follow_redirects=False);assert result.status_code==303,result.text
    again=client.post(url,data=data,follow_redirects=False);assert again.headers['location']==result.headers['location']
    response=client.get('/api/cart-completion247',params={'request_key':data['request_key']});assert response.json()['confirmed'] is True
    assert 'no-store' in response.headers['cache-control']
    with m.db() as c:assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==1
    customer['id']+=10000
    assert client.get('/api/cart-completion247',params={'request_key':data['request_key']}).json()['confirmed'] is False
    customer['role']='professional'
    assert client.get('/api/cart-completion247',params={'request_key':data['request_key']}).status_code==403
