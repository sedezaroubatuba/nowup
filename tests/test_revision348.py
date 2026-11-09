"""Independent regressions for the external audit; synthetic data only."""
import json,sqlite3,zipfile,hashlib
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from test_checkout247 import checkout

@pytest.mark.parametrize('promo,expected',[(750,0),(300,300)])
def test_admin_price_change_revalidates_promotion_and_checkout(checkout,monkeypatch,promo,expected):
    import nowup_admin227 as admin
    m,client,url,data,pid,_=checkout
    monkeypatch.setattr(admin,'G',dict(admin.G))
    admin.configure(vars(m));admin.initialize()
    with m.db() as c:
        c.execute('UPDATE products SET price_cents=1000,promo_price_cents=? WHERE id=?',(promo,pid))
        admin.update_product(c,{},pid,{'price':500},'Independent price regression')
        assert c.execute('SELECT promo_price_cents FROM products WHERE id=?',(pid,)).fetchone()[0]==expected
    assert client.post(url,data=data,follow_redirects=False).status_code==303
    with m.db() as c:assert c.execute('SELECT total_cents FROM orders').fetchone()[0]==(expected or 500)


def test_legacy_invalid_promo_is_never_charged(checkout):
    m,client,url,data,pid,_=checkout
    with m.db() as c:c.execute('UPDATE products SET price_cents=500,promo_price_cents=750 WHERE id=?',(pid,))
    assert client.post(url,data=data,follow_redirects=False).status_code==303
    with m.db() as c:assert c.execute('SELECT total_cents FROM orders').fetchone()[0]==500


def test_rate_limit_does_not_block_idempotent_retry(checkout):
    m,client,url,data,*_=checkout
    first=None
    for i in range(5):
        data['request_key']=f'revision348-order-{i:04}'
        r=client.post(url,data=data,follow_redirects=False)
        assert r.status_code==303,r.text
        if i==0:first=r.headers['location']
    data['request_key']='revision348-order-0005'
    assert client.post(url,data=data,follow_redirects=False).status_code==429
    data['request_key']='revision348-order-0000'
    assert client.post(url,data=data,follow_redirects=False).headers['location']==first
    with m.db() as c:assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==5


def test_native_contact_matches_authenticated_account(checkout):
    m,client,url,data,_,customer=checkout
    customer.update(name='Titular autenticado',phone='12988888888')
    data.update(customer_name='Nome adulterado',customer_phone='12977777777')
    assert client.post(url,data=data,follow_redirects=False).status_code==303
    with m.db() as c:
        order=c.execute('SELECT * FROM orders').fetchone()
        assert order['customer_name']==customer['name'] and order['customer_phone']==m.normalize_phone(customer['phone'])


def test_link_alone_and_other_customer_never_receive_private_order(checkout,monkeypatch):
    m,client,url,data,_,buyer=checkout
    data.update(address='Endereco privado348',notes='Segredo348')
    target=client.post(url,data=data,follow_redirects=False).headers['location']
    own=client.get(target);assert 'Endereco privado348' in own.text
    for viewer in (None,{'id':buyer['id']+1000,'role':'customer'}):
        monkeypatch.setattr(m,'current_user',lambda request:viewer)
        r=client.get(target)
        assert r.status_code==200
        for secret in ('Endereco privado348','Segredo348',data['customer_phone'],'Auditoria'):
            assert secret not in r.text
        assert r.headers['referrer-policy']=='no-referrer'


def test_verification_cooldown_reuses_valid_token_and_generic_response(checkout,monkeypatch):
    import email_verification as ev
    m,client,*_=checkout;sent=[]
    monkeypatch.setattr(ev,'db',m.db);monkeypatch.setattr(ev,'configured',lambda:True)
    monkeypatch.setattr(ev,'send_verification',lambda *args:sent.append(args))
    email='verification348@example.com'
    with m.db() as c:c.execute("INSERT INTO users(role,name,email,password_hash,created_at,email_verified) VALUES('customer','Verify',?,'unused',?,0)",(email,m.now_iso()))
    url='/reenviar-verificacao'
    first=client.post(url,data={'email':email},follow_redirects=False)
    assert first.status_code==303 and len(sent)==1
    assert client.post(url,data={'email':' '+email.upper()+' '},follow_redirects=False).status_code==429
    token=sent[0][2]
    with m.db() as c:c.execute('UPDATE auth_cooldowns348 SET sent_at=sent_at-61')
    assert client.post(url,data={'email':email},follow_redirects=False).status_code==303
    assert len(sent)==2 and sent[1][2]==token
    missing=client.post(url,data={'email':'missing348@example.com'},follow_redirects=False)
    assert missing.headers['location']==first.headers['location'] and len(sent)==2


def test_health_fails_without_database_or_capacity(checkout,monkeypatch):
    import shutil
    m,client,*_=checkout
    assert client.get('/health').status_code==200
    monkeypatch.setattr(shutil,'disk_usage',lambda _:SimpleNamespace(free=0))
    assert client.get('/health').status_code==503
    def fail():raise RuntimeError('Private credentials must not be exposed')
    monkeypatch.setattr(m,'db',fail)
    r=client.get('/health');assert r.status_code==503 and 'credentials' not in r.text


def test_encrypted_backup_restores_database_and_photo(tmp_path,monkeypatch):
    import nowup_backup as b
    monkeypatch.setenv('NOWUP_DB_ENGINE','sqlite')
    database=tmp_path/'source.db';uploads=tmp_path/'uploads';uploads.mkdir()
    (uploads/'photo.jpg').write_bytes(b'synthetic image')
    with sqlite3.connect(database) as c:
        c.executescript("CREATE TABLE products(id INTEGER PRIMARY KEY,image_filename TEXT);INSERT INTO products VALUES(1,'photo.jpg');CREATE TABLE order_receipts206(id INTEGER,content BLOB);INSERT INTO order_receipts206 VALUES(1,X'1234');")
    monkeypatch.setattr(b,'_db',database);monkeypatch.setattr(b,'_uploads',uploads)
    folder=tmp_path/'copy';folder.mkdir();archive=b.create_archive(folder)
    encrypted=tmp_path/'backup.enc';decrypted=tmp_path/'restored.zip';key=b'K'*32
    b.encrypt_archive(archive,encrypted,key);b.decrypt_archive(encrypted,decrypted,key)
    dest=tmp_path/'new-installation';dest.mkdir()
    with zipfile.ZipFile(decrypted) as z:
        manifest=json.loads(z.read('manifest.json'))
        for filename,digest in manifest['files'].items():assert hashlib.sha256(z.read(filename)).hexdigest()==digest
        z.extractall(dest)
    with sqlite3.connect(dest/'database/nowup.db') as c:
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert c.execute('SELECT image_filename FROM products').fetchone()[0]=='photo.jpg'
        assert c.execute('SELECT content FROM order_receipts206').fetchone()[0]==b'\x12\x34'
    assert (dest/'uploads/photo.jpg').read_bytes()==b'synthetic image'


def test_expired_public_link_keeps_buyer_access(checkout,monkeypatch):
    m,client,url,data,*_=checkout
    target=client.post(url,data=data,follow_redirects=False).headers['location']
    with m.db() as c:c.execute('UPDATE orders SET created_at=?',((datetime.now(timezone.utc)-timedelta(days=8)).isoformat(),))
    assert client.get(target).status_code==200
    monkeypatch.setattr(m,'current_user',lambda request:None)
    assert client.get(target).status_code==404
    assert client.get(target+'/status').status_code==404


def test_chat_is_limited_and_does_not_create_extra_notifications(checkout):
    m,client,url,data,*_=checkout
    client.post(url,data=data,follow_redirects=False)
    with m.db() as c:oid=c.execute('SELECT id FROM orders').fetchone()[0]
    for i in range(20):assert client.post(f'/pedidos/{oid}/conversa',data={'message':f'Mensagem {i}'}).status_code==200
    assert client.post(f'/pedidos/{oid}/conversa',data={'message':'Rajada'}).status_code==429
    with m.db() as c:assert c.execute('SELECT COUNT(*) FROM order_messages WHERE order_id=?',(oid,)).fetchone()[0]==20


def test_receipt_limit_preserves_replay_and_private_access(checkout,monkeypatch):
    m,client,url,data,*_=checkout
    import nowup_receipts206 as receipts
    monkeypatch.setattr(receipts,'G',dict(receipts.G))
    receipts.configure(vars(m));receipts.initialize()
    client.post(url,data=data,follow_redirects=False)
    with m.db() as c:oid=c.execute('SELECT id FROM orders').fetchone()[0]
    def send(i):return client.post(f'/pedidos/{oid}/comprovante206',data={'request_id':f'audit348-receipt-{i}'},files={'file':('receipt.pdf',b'%PDF-1.4\nsynthetic\n%%EOF','application/pdf')})
    for i in range(3):assert send(i).status_code==200
    assert send(3).status_code==429
    assert send(0).json()['duplicate'] is True
    monkeypatch.setattr(m,'current_user',lambda request:{'id':999999,'role':'customer'})
    assert client.get(f'/pedidos/{oid}/comprovantes206/1').status_code in (403,404)


def test_private_tokens_are_redacted_from_access_logs():
    import logging
    from nowup_hardening308 import PrivateAccessLog348
    record=logging.LogRecord('uvicorn.access',logging.INFO,'',0,'%s %s %s %s %s',('local','GET','/p/store/pedido/secret-token348?token=other-secret348','1.1',200),None)
    assert PrivateAccessLog348().filter(record)
    assert 'secret-token348' not in record.getMessage() and 'other-secret348' not in record.getMessage()
    assert '/pedido/[private]' in record.getMessage()
