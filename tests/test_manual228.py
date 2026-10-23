"""Manual deployment without Asaas: safe migration and audited receipts."""
import json,os,secrets,sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from test_release228 import release
from test_merchant228 import env

def test_runtime_secrets_are_generated_once_and_persist(tmp_path,monkeypatch):
 from nowup_security import require_secrets
 monkeypatch.setenv('NOWUP_DB',str(tmp_path/'db.sqlite'))
 for key in ('NOWUP_ADMIN_SECRET','NOWUP_JWT_SECRET'):monkeypatch.delenv(key,raising=False)
 require_secrets();original={key:os.environ[key] for key in ('NOWUP_ADMIN_SECRET','NOWUP_JWT_SECRET')}
 path=tmp_path/'.runtime-secrets228.json'
 assert path.stat().st_mode&0o777==0o600
 assert len(original['NOWUP_ADMIN_SECRET'])>=32 and original['NOWUP_ADMIN_SECRET']!=original['NOWUP_JWT_SECRET']
 for key in original:monkeypatch.delenv(key)
 require_secrets();assert all(os.environ[key]==value for key,value in original.items())

def test_upgrade_preserves_existing_access_without_inventing_payment(monkeypatch):
 import nowup_billing228 as b
 monkeypatch.delenv('NOWUP_BILLING_MODE',raising=False);monkeypatch.delenv('NOWUP_KYC_ENFORCE',raising=False)
 c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
 c.executescript("CREATE TABLE professionals(id INTEGER PRIMARY KEY,admission_status TEXT,plan_active TEXT,blocked INTEGER,business_status TEXT);INSERT INTO professionals VALUES(1,'approved','ambos',0,'open');INSERT INTO professionals VALUES(2,'approved','ambos',1,'open');INSERT INTO professionals VALUES(3,'pending','ambos',0,'open');")
 b.initialize(c)
 rows={r['id']:r for r in c.execute('SELECT * FROM professionals')}
 assert b.effective_status(rows[1])['online'] and rows[1]['subscription_status']=='pending' and rows[1]['subscription_paid']==0
 assert not b.effective_status(rows[2])['online'] and not b.effective_status(rows[3])['online']
 c.execute("INSERT INTO professionals(id,admission_status,plan_active,blocked,business_status) VALUES(4,'approved','ambos',0,'open')")
 b.initialize(c);new=c.execute('SELECT * FROM professionals WHERE id=4').fetchone()
 assert new['billing_mode']=='manual' and not b.effective_status(new)['online'];c.close()

def test_manual_approval_and_receipt_need_no_asaas(release,monkeypatch):
 m,admin,_,pid,_,_,_,_=release
 import nowup_billing228 as b
 monkeypatch.delenv('NOWUP_BILLING_MODE',raising=False)
 monkeypatch.delenv('ASAAS_API_KEY',raising=False);monkeypatch.delenv('ASAAS_WEBHOOK_TOKEN',raising=False)
 def forbidden(*args,**kwargs):raise AssertionError('Manual mode must never call Asaas')
 monkeypatch.setattr(b,'api',forbidden)
 with m.db() as c:
  c.execute("UPDATE professionals SET billing_mode='manual',admission_status='pending',kyc_status='pending',subscription_status='pending',subscription_paid=0,document='' WHERE id=?",(pid,))
  m.nowup_admin227.put(c,'storemeta',pid,{'id':pid,'plan':'start','price':7900});c.commit()
 state=admin.get('/admin/super/api/state').json()
 result=admin.post('/admin/super/api/change',json={'revision':state['_meta']['revision'],'reason':'Cadastro conferido para confirmação manual de mensalidade','changes':[{'kind':'stores','id':pid,'value':{'approval':'approved'}}]})
 assert result.status_code==200,result.text
 with m.db() as c:assert not b.effective_status(c.execute('SELECT * FROM professionals WHERE id=?',(pid,)).fetchone())['online']
 payload={'requestKey':secrets.token_hex(24),'amount':7900,'paidOn':b.today().isoformat(),'nextDue':(b.today()+timedelta(days=30)).isoformat(),'reference':'pix-test-'+secrets.token_hex(6),'reason':'Pix conferido no extrato pelo administrador'}
 def send(_):return admin.post('/admin/super/api/billing/'+str(pid)+'/manual-payment',json=payload)
 with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(send,range(2)))
 assert all(r.status_code==200 for r in responses),[r.text for r in responses]
 with m.db() as c:
  row=c.execute('SELECT * FROM professionals WHERE id=?',(pid,)).fetchone()
  assert row['subscription_status']=='active' and b.effective_status(row)['online']
  assert c.execute('SELECT COUNT(*) FROM manual_payments228 WHERE request_key=?',(payload['requestKey'],)).fetchone()[0]==1
  assert c.execute("SELECT COUNT(*) FROM billing_audit WHERE store_id=? AND action LIKE 'Recebimento manual%'",(pid,)).fetchone()[0]==1
  assert c.execute('SELECT COUNT(*) FROM billing_jobs WHERE store_id=?',(pid,)).fetchone()[0]==0
 assert admin.post('/admin/super/api/billing/'+str(pid)+'/manual-payment',json={**payload,'amount':14900}).status_code==409
 with m.db() as c:c.execute('UPDATE professionals SET blocked=1 WHERE id=?',(pid,));c.commit()
 newer={**payload,'requestKey':secrets.token_hex(24),'reference':'another-pix-reference'}
 assert admin.post('/admin/super/api/billing/'+str(pid)+'/manual-payment',json=newer).status_code==200
 with m.db() as c:assert not b.effective_status(c.execute('SELECT * FROM professionals WHERE id=?',(pid,)).fetchone())['online']
 b.tick()

def test_manual_endpoint_denies_non_finance_and_does_not_fake_payment(release,monkeypatch):
 m,admin,buyer,pid,_,_,_,_=release
 import nowup_billing228 as b
 monkeypatch.setenv('NOWUP_BILLING_MODE','manual')
 with m.db() as c:
  c.execute("UPDATE professionals SET billing_mode='manual',subscription_status='pending',subscription_paid=0 WHERE id=?",(pid,));m.nowup_admin227.put(c,'storemeta',pid,{'id':pid,'plan':'start','price':7900});c.commit()
 payload={'requestKey':secrets.token_hex(24),'amount':1,'paidOn':b.today().isoformat(),'nextDue':(b.today()+timedelta(days=30)).isoformat(),'reference':'invalid-amount-ref','reason':'Tentativa com valor diferente do contrato'}
 assert admin.post('/admin/super/api/billing/'+str(pid)+'/manual-payment',json=payload).status_code==422
 assert buyer.post('/admin/super/api/billing/'+str(pid)+'/manual-payment',json={**payload,'amount':7900},headers={'X-Nowup-Admin':'227'}).status_code==401
 with m.db() as c:assert c.execute('SELECT subscription_paid FROM professionals WHERE id=?',(pid,)).fetchone()[0]==0
 assert admin.post('/admin/super/api/billing/'+str(pid)+'/provision',json={'reason':'Tentativa sem gateway'}).status_code==409

def test_full_boot_without_asaas_or_new_secret_environment(tmp_path):
 import os,subprocess,sys
 from pathlib import Path
 env_vars=dict(os.environ)
 for key in ('NOWUP_ADMIN_SECRET','NOWUP_JWT_SECRET','ASAAS_API_KEY','ASAAS_WEBHOOK_TOKEN','NOWUP_BILLING_MODE','NOWUP_KYC_ENFORCE'):env_vars.pop(key,None)
 env_vars.update(NOWUP_DB=str(tmp_path/'nowup.db'),NOWUP_UPLOAD_DIR=str(tmp_path/'uploads'),NOWUP_ADMIN_EMAIL='isolated-boot@test.invalid',NOWUP_ADMIN_PASSWORD='isolated-boot-password-228',NOWUP_BILLING_WORKER='0')
 script='''import app
from fastapi.testclient import TestClient
for callback in app.app.router.on_startup:
 if callback.__name__!='start':callback()
assert TestClient(app.app).get('/health').status_code==200
assert (app.DB_PATH.parent/'.runtime-secrets228.json').exists()
assert app.nowup_billing228.billing_mode()=='manual'
'''
 result=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).resolve().parents[1],env=env_vars,capture_output=True,text=True,timeout=45)
 assert result.returncode==0,result.stderr[-3000:]
