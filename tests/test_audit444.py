"""Synthetic audit only: isolated SQLite, no production orders or WhatsApp sends."""
import json,time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
from fastapi.testclient import TestClient
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from test_order_link377 import setup_order


def test_cardapio_burst_150_orders_and_30_registrations(channel,monkeypatch):
    m,client,slug,pid,data,product,buyer=channel
    with m.db() as c:
        m.nowup_receipts206.initialize();m.nowup_notinha401.initialize(c)
        store=dict(c.execute('SELECT * FROM professionals WHERE id=?',(pid,)).fetchone())
        users=[c.execute("INSERT INTO users(role,name,email,password_hash,created_at) VALUES('customer',?,?,?,?)",('Auditoria '+str(i),f'audit444-{i}@example.invalid','unused',m.now_iso())).lastrowid for i in range(150)]
    monkeypatch.setattr(m,'current_user',lambda r:dict(buyer,id=int(r.headers['x-audit-buyer']),name='Auditoria',phone='12999999999') if r.headers.get('x-audit-buyer') else {'id':store['user_id'],'role':'professional'})
    def submit(i):
        c=TestClient(m.app,headers={'Origin':'http://testserver','X-Audit-Buyer':str(users[i])})
        payload={**data,'request_key':'audit444-order-'+str(i).zfill(8),'payment_method':'pix' if i%2==0 else 'cash','cart_json':json.dumps([{'id':product,'quantity':1+i%3}]),'notes':'Auditoria isolada '+str(i)}
        start=time.perf_counter();r=c.post('/p/'+slug+'/menu/whatsapp',data=payload);assert r.status_code==200,r.text
        result=r.json();assert result['total_cents']==300*(1+i%3) and 'pix' not in result
        if i%10==0:assert c.post('/p/'+slug+'/menu/whatsapp',data=payload).json()['order_code']==result['order_code']
        page=c.get(result['redirect']);assert page.status_code==200 and 'data-pix-payment' not in page.text
        oid=int(result['order_code'].split('-')[-1]);paper=c.get('/p/'+slug+'/pedidos/'+str(oid)+'/notinha');assert paper.status_code==200 and 'Auditoria' in paper.text
        return time.perf_counter()-start
    start=time.perf_counter()
    with ThreadPoolExecutor(max_workers=20) as pool:times=list(pool.map(submit,range(150)))
    with m.db() as c:
        assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==150
        assert c.execute('SELECT COUNT(*) FROM order_items').fetchone()[0]==150
        assert c.execute("SELECT COUNT(*) FROM orders WHERE order_origin='external' AND status='new'").fetchone()[0]==150
        assert c.execute('SELECT SUM(total_cents) FROM orders').fetchone()[0]==90000
    for i in range(15):
        r=client.post('/painel/cardapio/ingredientes320',data={'name':'Extra auditoria '+str(i),'price':'2,50','inline_paid442':'1'});assert r.status_code==200,r.text
        r=client.post('/painel/cardapio/produtos',data={'name':'Produto auditoria '+str(i),'category':'Auditoria','price':'10,00','available':'1','extras_mode':'none'},follow_redirects=False);assert r.status_code==303,r.text
    with m.db() as c:assert c.execute("SELECT COUNT(*) FROM products WHERE name LIKE 'Produto auditoria %'").fetchone()[0]==15
    print('\nAUDIT444 '+json.dumps({'orders':150,'workers':20,'retries':15,'receipts':150,'registrations':30,'total_cents':90000,'seconds':round(time.perf_counter()-start,2),'p95_seconds':round(sorted(times)[142],3)}))


def test_whatsapp_handoff_chat_read_only(channel,monkeypatch):
    m,client,result,o,item,owner,buyer=setup_order(channel)
    with m.db() as c:c.execute('UPDATE orders SET created_at=? WHERE id=?',((datetime.now(timezone.utc)-timedelta(seconds=61)).isoformat(),o['id']))
    assert client.post(result['redirect']+'/espera434').status_code==200
    assert client.get(result['redirect']).status_code==200
    paper=client.get('/p/'+channel[2]+'/pedidos/'+str(o['id'])+'/notinha')
    assert paper.status_code==200 and 'pagamento manuais pelo WhatsApp' in paper.text
    for user in [buyer,owner]:
        monkeypatch.setattr(m,'current_user',lambda r,u=user:u)
        assert client.get('/pedidos/'+str(o['id'])+'/conversa').json()['closed']
        assert client.post('/pedidos/'+str(o['id'])+'/conversa',data={'message':'Não enviar no canal antigo'}).status_code==409
    monkeypatch.setattr(m,'current_user',lambda r:buyer)
    assert client.post('/pedidos/'+str(o['id'])+'/comprovante206',files={'file':('qa.pdf',b'test','application/pdf')}).status_code==409


def test_cardapio_burst_antispam(channel):
    m,client,slug,pid,data,product,buyer=channel
    codes=[]
    for i in range(6):
        codes.append(client.post('/p/'+slug+'/menu/whatsapp',data={**data,'request_key':'audit444-spam-'+str(i).zfill(8)}).status_code)
    assert codes==[200]*5+[429]
    with m.db() as c:assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==5
