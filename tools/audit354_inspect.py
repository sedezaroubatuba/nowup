"""Reproducible catalogue audit; loopback server and disposable SQLite only.
Never import this module into production. Outbound email is captured locally.
"""
import asyncio,io,json,os,sqlite3,statistics,subprocess,sys,tempfile,threading,time,traceback
from pathlib import Path
from datetime import datetime,timedelta,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));os.chdir(ROOT)
RUN=Path(os.environ.get('NOWUP_AUDIT_DIR',tempfile.mkdtemp(prefix='nowup354-'))).resolve();RUN.mkdir(exist_ok=True,parents=True)
os.environ.update(NOWUP_DB_ENGINE='sqlite',NOWUP_DB=str(RUN/'audit.db'),NOWUP_UPLOAD_DIR=str(RUN/'uploads'),NOWUP_ADMIN_EMAIL='audit354@example.com',NOWUP_ADMIN_PASSWORD='Isolated-audit354-password',NOWUP_HTTPS='0')
for name in ['DATABASE_URL','NOWUP_PUBLIC_ORIGIN','BREVO_API_KEY','SMTP_PASSWORD','SMTP_HOST','NOWUP_TEST_SANDBOX333']:os.environ.pop(name,None)
import app as m
from email_validator import validate_email,EmailNotValidError
from fastapi import Request
import uvicorn,httpx
from PIL import Image
RESULT={'run_dir':str(RUN),'engine':'sqlite','outbound_email':'stubbed; DNS deliverability disabled only in harness','checks':[],'loads':[]}
def check(name,ok,detail=''):
 RESULT['checks'].append({'name':name,'ok':bool(ok),'detail':detail});print(name,ok,str(detail)[:180],flush=True)
def email(value):
 try:return validate_email(value,check_deliverability=False).normalized.lower()
 except EmailNotValidError:return None
m.normalize_email=email;m.email_service_configured=lambda:True
mail_lock=threading.Lock()
def sent(*args,**kw):
 with mail_lock:
  with (RUN/'emails.jsonl').open('a') as f:f.write(json.dumps({'args':args,'kwargs':kw})+'\n')
 return True
m.send_email=sent;m.send_verification=lambda *args:sent(*args)
for callback in m.app.router.on_startup:
 if callback.__name__!='start':callback()
import socket
sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
BASE=f'http://127.0.0.1:{port}';os.environ['NOWUP_BASE_URL']=BASE
server=uvicorn.Server(uvicorn.Config(m.app,host='127.0.0.1',port=port,log_level='error',lifespan='off',access_log=False))
thread=threading.Thread(target=server.run,daemon=True);thread.start()
for _ in range(200):
 if server.started:break
 time.sleep(.05)
client=httpx.Client(trust_env=False,base_url=BASE,headers={'Origin':BASE},timeout=40,follow_redirects=False)

with m.db() as c:c.execute('DELETE FROM auth_limits247');c.commit()
previous=json.loads((RUN/'manifest.json').read_text());previous['base']=BASE;(RUN/'manifest.json').write_text(json.dumps(previous))
try:
 with (RUN/'inspect-browser.log').open('w') as out:subprocess.run(['node',str(ROOT/'tools/audit354_browser.cjs'),str(RUN/'manifest.json')],stdout=out,stderr=subprocess.STDOUT,timeout=180,env={**os.environ,'NOWUP_AUDIT_ONE':os.getenv('NOWUP_AUDIT_ONE',''),'AUDIT_PYTHON':sys.executable})
finally:server.should_exit=True;thread.join(timeout=10)
