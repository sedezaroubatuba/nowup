import json
import pytest
from test_checkout247 import checkout


def place(checkout):
    m,client,url,data,pid,customer=checkout
    r=client.post(url,data=data,follow_redirects=False);assert r.status_code==303,r.text
    with m.db() as c:return dict(c.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 1').fetchone())


def test_receipt_statuses_and_chat_enqueue_once_for_the_recipient(checkout,monkeypatch):
    m,client,url,data,pid,customer=checkout;o=place(checkout)
    assert client.post(url,data=data,follow_redirects=False).status_code==303
    with m.db() as c:
        owner=dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?',(o['professional_id'],)).fetchone())
        assert c.execute('SELECT COUNT(*) FROM customer_push112 WHERE user_id=?',(customer['id'],)).fetchone()[0]==1
        initial=json.loads(c.execute('SELECT payload FROM customer_push112 WHERE user_id=?',(customer['id'],)).fetchone()[0]);assert 'Aguardando aceite' in initial['body']
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    for status in ('confirmed','preparing','ready','out_for_delivery','completed'):
        r=client.post(f"/painel/pedidos/{o['id']}/status",data={'status':status},follow_redirects=False);assert r.status_code==303,r.text
    with m.db() as c:
        jobs=[dict(r) for r in c.execute('SELECT * FROM customer_push112 WHERE user_id=?',(customer['id'],))]
        assert len(jobs)==6
        assert len({json.loads(r['payload'])['tag'] for r in jobs})==6
        assert all(json.loads(r['payload'])['url'].endswith(o['tracking_token']) for r in jobs)
    # A second, active order verifies both chat directions independently.
    monkeypatch.setattr(m,'current_user',lambda request:customer)
    data['request_key']='push375-second-order';other=place(checkout)
    assert client.post(f"/pedidos/{other['id']}/conversa",data={'message':'Dúvida do cliente'}).status_code==200
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    assert client.post(f"/pedidos/{other['id']}/conversa",data={'message':'Resposta da loja'}).status_code==200
    with m.db() as c:
        chats=[(r['user_id'],json.loads(r['payload'])) for r in c.execute('SELECT * FROM customer_push112') if json.loads(r['payload'])['title']=='Nova mensagem no pedido']
        assert {r[0] for r in chats}=={owner['id'],customer['id']}


def test_retry_only_targets_the_device_that_failed(checkout,monkeypatch):
    m,client,_,_,_,customer=checkout;uid=customer['id'];sent=[];failing={'b':True}
    with m.db() as c:
        n=c.execute("INSERT INTO notifications(user_id,title,message,link,created_at) VALUES(?,'Aviso','Mensagem','/cliente',?)",(uid,m.now_iso())).lastrowid
        m.nowup_alerts112.enqueue(c,uid,n,{'title':'Aviso','body':'Mensagem','url':'/cliente'})
        for endpoint in ('a','b'):c.execute('INSERT INTO push_subscriptions VALUES(?,?,?,?)',(endpoint,uid,'test','{}'))
    def send(row,payload):
        sent.append(row['endpoint']);return not (row['endpoint']=='b' and failing['b'])
    monkeypatch.setattr(m.nowup_push75,'send',send)
    m.nowup_alerts112.process()
    with m.db() as c:c.execute('UPDATE customer_push112 SET next_try=0')
    failing['b']=False;m.nowup_alerts112.process()
    assert sent==['a','b','b']
    with m.db() as c:assert c.execute('SELECT COUNT(*) FROM customer_push112').fetchone()[0]==0


def test_support_reply_has_push_and_a_valid_support_destination(checkout,monkeypatch):
    m,client,_,_,_,customer=checkout
    monkeypatch.setattr(m.nowup_admin205,'G',dict(m.nowup_admin205.G))
    m.nowup_admin205.configure(vars(m));m.nowup_admin205.initialize()
    r=client.post('/suporte',data={'subject':'Ajuda','body':'Preciso de orientação'},follow_redirects=False);assert r.status_code==303,r.text
    tid=int(r.headers['location'].split('chamado=')[1])
    with m.db() as c:admin=dict(c.execute("SELECT * FROM users WHERE role='admin'").fetchone())
    monkeypatch.setattr(m,'current_user',lambda request:admin)
    r=client.post(f'/admin/central/suporte/{tid}',data={'status':'in_progress','body':'Vamos ajudar'},follow_redirects=False);assert r.status_code==303,r.text
    with m.db() as c:
        payload=json.loads(c.execute('SELECT payload FROM customer_push112 WHERE user_id=?',(customer['id'],)).fetchone()[0])
        assert payload['url']==f'/suporte?chamado={tid}' and payload['body']=='Vamos ajudar'


def test_old_closed_session_cannot_receive_push(checkout,monkeypatch):
    m,*_=checkout;called=[]
    monkeypatch.setattr(m.nowup_push75,'webpush',lambda *a,**kw:called.append(1))
    with m.db() as c:
        uid=c.execute("SELECT id FROM users WHERE role='customer'").fetchone()[0]
        c.execute("INSERT INTO push_subscriptions VALUES('old-device',?,'missing-session','{}')",(uid,))
        row=c.execute("SELECT * FROM push_subscriptions WHERE endpoint='old-device'").fetchone()
    assert m.nowup_push75.send(row,{'title':'Teste'}) is True
    assert called==[]
    with m.db() as c:assert not c.execute("SELECT 1 FROM push_subscriptions WHERE endpoint='old-device'").fetchone()


def test_private_logout_revokes_only_its_push_subscription(checkout):
    import hashlib
    from datetime import datetime,timedelta,timezone
    m,client,_,_,product,customer=checkout
    with m.db() as c:
        p=c.execute('SELECT p.* FROM professionals p JOIN products pr ON pr.professional_id=p.id WHERE pr.id=?',(product,)).fetchone()
        other=c.execute('SELECT id FROM professionals WHERE id<>? LIMIT 1',(p['id'],)).fetchone()[0]
        expiry=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
        for token,store in [('push375-private-token',p['id']),('push375-other-token',other)]:
            c.execute('INSERT INTO sessions(token,user_id,expires_at,store_id345) VALUES(?,?,?,?)',(token,customer['id'],expiry,store))
            c.execute('INSERT INTO push_subscriptions VALUES(?,?,?,?)',(token,customer['id'],hashlib.sha256(token.encode()).hexdigest(),'{}'))
    client.cookies.set('nowup_loja345_'+str(p['id']),'push375-private-token',path='/p/'+p['slug'])
    r=client.post('/p/'+p['slug']+'/sair',follow_redirects=False);assert r.status_code==303,r.text
    with m.db() as c:
        assert not c.execute("SELECT 1 FROM push_subscriptions WHERE endpoint='push375-private-token'").fetchone()
        assert c.execute("SELECT 1 FROM push_subscriptions WHERE endpoint='push375-other-token'").fetchone()


def test_existing_vapid_key_can_sign_without_rotating_subscriptions(checkout):
    import base64
    from py_vapid import Vapid
    m,*_=checkout
    private,public=m.nowup_push75.keys()
    parsed=Vapid.from_string(private)
    assert parsed.private_key is not None
    assert len(base64.urlsafe_b64decode(public+'='*(-len(public)%4)))==65
    assert parsed.sign({'sub':'https://nowup.test','aud':'https://fcm.googleapis.com'})
