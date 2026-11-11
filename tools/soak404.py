"""300 Pix checkouts across two hours, isolated ASGI + disposable SQLite.

No production credentials, outbound network, bank transfers or WhatsApp sends.
Usage: python tools/soak404.py --duration 7200 --count 300 --output DIR
An accelerated smoke run is a separate run, never reported as a two-hour test.
"""
import argparse
import base64
import io
import json
import os
from pathlib import Path
import statistics
import sys
import time
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--duration',type=float,default=7200)
    parser.add_argument('--count',type=int,default=300)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not 2<=args.count<=300 or not 0<=args.duration<=7200:
        parser.error('count 2..300 and duration 0..7200')
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'isolated.db').exists():
        parser.error('Use a fresh output directory')
    for key in list(os.environ):
        if key.startswith(('NOWUP_','BREVO_','SMTP_','ASAAS_','AWS_','R2_','REDIS_')) or key=='DATABASE_URL':
            os.environ.pop(key,None)
    os.environ.update(NOWUP_DB_ENGINE='sqlite',NOWUP_DB=str(out/'isolated.db'),
        NOWUP_UPLOAD_DIR=str(out/'uploads'),NOWUP_HTTPS='0',
        NOWUP_ADMIN_EMAIL='soak404@example.invalid',
        NOWUP_ADMIN_PASSWORD='isolated-soak404-admin')
    import mailing
    mailing.send_email=lambda *a,**k: True
    mailing.send_verification=lambda *a,**k: True
    import app as m
    from fastapi.testclient import TestClient
    from bs4 import BeautifulSoup
    from PIL import Image
    import zxingcpp
    # The harness cannot open sockets or start subprocesses, including future integrations.
    def guard(event,values):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system','os.posix_spawn'):
            raise PermissionError('Isolated soak404: external I/O blocked')
    sys.addaudithook(guard)
    for callback in m.app.router.on_startup:
        if callback.__name__!='start':callback()
    # The production start callbacks initialize these before starting their workers.
    # Here only their schemas are needed; background delivery remains stopped.
    m.nowup_push75.initialize()
    m.nowup_alerts112.initialize()
    password='isolated-customer404'
    password_hash=m.hash_password(password)
    key='123e4567-e12b-12d1-a456-426655440000'
    customers=[]
    with m.db() as c:
        shops=c.execute('SELECT * FROM professionals ORDER BY id LIMIT 2').fetchall()
        for channel,p in zip(('nowup','external'),shops):
            c.execute("UPDATE professionals SET display_name=?,plan_active='completo',is_premium=1,offer_mode='menu',admission_status='approved',blocked=0,business_status='open',business_hours='',allows_pickup=1,minimum_order_cents=0,pix_key=?,pix_key_type='random',pix_receiver_name='LOJA FICTICIA TESTE',pix_receiver_city='UBATUBA' WHERE id=?",('Sede Zero FICTICIA teste' if channel=='external' else 'NowUp FICTICIO teste',key,p['id']))
            c.execute("INSERT INTO store_menu257(professional_id,whatsapp,mode) VALUES(?,'5512999999999','whatsapp') ON CONFLICT(professional_id) DO UPDATE SET mode='whatsapp'",(p['id'],))
            product=c.execute("INSERT INTO products(professional_id,name,category,price_cents,available,extras_mode,created_at,updated_at) VALUES(?,'Produto fictício404','Bebidas',1250,1,'none',?,?)",(p['id'],m.now_iso(),m.now_iso())).lastrowid
            for n in range(50):
                email=f'{channel}-customer{n}@example.invalid'
                scope=p['id'] if channel=='external' else 0
                internal=f'internal-soak404-{n}@example.invalid' if scope else email
                uid=c.execute("INSERT INTO users(role,name,email,phone,password_hash,email_verified,is_active,created_at,customer_store345,customer_email345) VALUES('customer',?,?,?, ?,1,1,?,?,?)",(f'Cliente fictício {n}',internal,'12988888888',password_hash,m.now_iso(),scope,email if scope else '')).lastrowid
                customers.append(dict(channel=channel,uid=uid,email=email,slug=p['slug'],store=p['id'],product=product))
        c.commit()
    # Authenticate through actual login endpoints; no patched identity or fabricated cookies.
    for user in customers:
        client=TestClient(m.app,headers={'Origin':'http://testserver'},follow_redirects=False)
        login='/p/'+user['slug']+'/entrar' if user['channel']=='external' else '/entrar'
        r=client.post(login,data={'email':user['email'],'password':password,'tipo':'cliente'})
        if r.status_code!=303 or 'erro=' in r.headers.get('location',''):
            raise RuntimeError('Synthetic authentication failed: '+str(r.status_code))
        user['client']=client
    # Interleave evenly, 150 marketplace + 150 standalone checkouts.
    users=[x for pair in zip(customers[:50],customers[50:]) for x in pair]
    started=time.monotonic();rows=[]
    status=dict(status='running',requested=args.count,duration_seconds=args.duration,
        started_at=datetime.now(timezone.utc).isoformat(),environment='isolated ASGI / SQLite',
        external_network='blocked',real_payments=False,real_whatsapp_messages=False,
        source_version='security404',completed=0,passed=0)
    def save():
        status.update(completed=len(rows),passed=sum(r['ok'] for r in rows),
            elapsed_seconds=round(time.monotonic()-started,2),
            channels={ch:sum(r['channel']==ch for r in rows) for ch in ('nowup','external')},
            failures=[r for r in rows if not r['ok']])
        values=sorted(r['ms'] for r in rows)
        if values:status.update(p50_ms=statistics.median(values),p95_ms=values[max(0,int(len(values)*.95)-1)])
        temporary=out/'status.tmp';temporary.write_text(json.dumps(status,indent=2));temporary.replace(out/'status.json')
    save()
    try:
        for n in range(args.count):
            target=started+args.duration*n/(args.count-1)
            while time.monotonic()<target:time.sleep(min(1,target-time.monotonic()))
            u=users[n%100];client=u['client'];tick=time.perf_counter()
            data=dict(customer_name='Nome adulterado',customer_phone='12988888888',
                cart_json=json.dumps([{'id':u['product'],'quantity':2,'price':1}]),
                fulfillment_type='pickup',payment_method='pix',request_key=f'soak404-request-{n:04}')
            url='/p/'+u['slug']+'/menu/'+('whatsapp' if u['channel']=='external' else 'pedido')
            row=dict(number=n+1,channel=u['channel'],ok=False)
            try:
                r=client.post(url,data=data,headers={'Accept':'application/json'})
                row['status']=r.status_code
                assert r.status_code==200,('checkout',r.status_code,r.text[:100])
                result=r.json();page=client.get(result['redirect'])
                assert page.status_code==200,('tracking',page.status_code)
                script=BeautifulSoup(page.text,'html.parser').select_one('[data-pix-payment] script')
                assert script is not None,'Missing immediate Pix QR'
                pix=json.loads(script.string)
                decoded=zxingcpp.read_barcode(Image.open(io.BytesIO(base64.b64decode(pix['qr_image'].split(',')[1]))))
                assert decoded and decoded.text==pix['payload'],'QR payload mismatch'
                assert '540525.00' in decoded.text and key in decoded.text,'Wrong Pix amount or recipient'
                again=client.post(url,data=data,headers={'Accept':'application/json'})
                assert again.status_code==200 and again.json()['redirect']==result['redirect'],'Retry is not idempotent'
                with m.db() as c:
                    order=c.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 1').fetchone()
                    assert order['customer_id']==u['uid'] and order['order_origin']==u['channel']
                    assert order['total_cents']==2500 and order['status']=='new'
                    assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==n+1
                    assert not c.execute('SELECT 1 FROM order_payment_checks401').fetchone(),'Payment falsely confirmed'
                row['ok']=True
            except Exception as exc:
                row['error']=str(exc)[:400]
            row['ms']=round((time.perf_counter()-tick)*1000,2)
            rows.append(row)
            with (out/'requests.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
            save()
            print(json.dumps({k:status[k] for k in ('completed','passed','elapsed_seconds')}),flush=True)
        status['status']='completed';save()
    finally:
        for u in users:u['client'].close()
    return 0 if status['passed']==args.count else 1


if __name__=='__main__':
    raise SystemExit(main())
