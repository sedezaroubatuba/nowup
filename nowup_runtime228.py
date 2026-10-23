"""Cart sync, deferred analytics and single-process leased billing worker."""
import json,os,threading,logging,fcntl
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime,timezone
from urllib.parse import urlsplit
from fastapi import APIRouter,HTTPException,Request
router=APIRouter();G={};stop=threading.Event();thread=None

def configure(g):G.update(g)
@contextmanager
def connection():
 c=G['db']()
 try:yield c;c.commit()
 except Exception:c.rollback();raise
 finally:c.close()

def customer(request):
 u=G['current_user'](request)
 if not u or u['role']!='customer':raise HTTPException(401,'Entre como cliente')
 return u

@router.get('/api/cart/{store}')
def read_cart(request:Request,store:int):
 u=customer(request)
 with connection() as c:row=c.execute('SELECT payload FROM saved_carts WHERE user_id=? AND store_id=?',(u['id'],store)).fetchone()
 return {'items':json.loads(row[0]) if row else []}

@router.put('/api/cart/{store}')
async def write_cart(request:Request,store:int):
 if urlsplit(request.headers.get('origin','')).netloc!=request.headers.get('host'):raise HTTPException(403,'Origem inválida')
 u=customer(request);raw=await request.body()
 if len(raw)>64000:raise HTTPException(413,'Carrinho acima do limite')
 try:
  items=json.loads(raw)['items']
  if not isinstance(items,list) or len(items)>100:raise ValueError()
 except (ValueError,KeyError,TypeError,AssertionError):raise HTTPException(422,'Carrinho inválido')
 with connection() as c:
  if not c.execute('SELECT 1 FROM professionals WHERE id=?',(store,)).fetchone():raise HTTPException(404)
  try:updated=datetime.fromtimestamp(float(json.loads(raw).get('updatedAt',0))/1000,timezone.utc)
  except (ValueError,TypeError,OverflowError):raise HTTPException(422,'Versão de carrinho inválida')
  if abs((datetime.now(timezone.utc)-updated).total_seconds())>300:raise HTTPException(409,'Atualize a página para sincronizar o carrinho')
  c.execute('INSERT INTO saved_carts VALUES(?,?,?,?) ON CONFLICT(user_id,store_id) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at WHERE excluded.updated_at>saved_carts.updated_at',(u['id'],store,json.dumps(items),updated.isoformat()))
 return {'ok':True}

def analytics(store,event):
 try:
  with connection() as c:
   if event not in ('profile_view','menu_click'):return
   column='views' if event=='profile_view' else 'menu_clicks'
   c.execute('UPDATE professionals SET '+column+'='+column+'+1 WHERE id=?',(store,));c.execute('INSERT INTO analytics_events(professional_id,event_type,created_at) VALUES(?,?,?)',(store,event,datetime.now(timezone.utc).isoformat()))
 except Exception:logging.getLogger(__name__).warning('Analytics indisponível; requisição principal preservada')

def run_once():
 # Host-level lock also protects multiple uvicorn workers sharing the same database.
 lock=Path(G['db_path']).parent/'billing228.lock'
 with lock.open('a') as handle:
  try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  try:G['billing'].tick()
  finally:fcntl.flock(handle,fcntl.LOCK_UN)

def start_worker():
 global thread
 if os.getenv('NOWUP_BILLING_WORKER','0')!='1' or thread and thread.is_alive():return
 stop.clear()
 def loop():
  while not stop.is_set():
   try:run_once()
   except Exception:logging.getLogger(__name__).exception('Falha no worker de cobrança')
   stop.wait(60)
 thread=threading.Thread(target=loop,name='nowup-billing228',daemon=True);thread.start()
def stop_worker():stop.set()
