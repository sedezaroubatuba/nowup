"""Bounded admin reads, SQL aggregation and tenant-safe filters (amounts in cents)."""
import json
import threading
import time
from datetime import date,datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import JSONResponse
router=APIRouter();G={};TZ=ZoneInfo('America/Sao_Paulo');_cache={};_lock=threading.Lock()
def configure(g):G.update(g)
def invalidate():
    with _lock:_cache.clear()
def allowed(a,module):return a.get('super') or module in a['permissions'] or module+':read' in a['permissions']
def authorize(request,c,module):
    a=G['admin'].auth(request,c)
    if not allowed(a,module):raise HTTPException(403,'Sem permissão para '+module)
    return a

def initialize(c):
    columns={r[1] for r in c.execute('PRAGMA table_info(orders)')}
    if 'delivery_neighborhood' not in columns:
        c.execute("ALTER TABLE orders ADD COLUMN delivery_neighborhood TEXT NOT NULL DEFAULT ''")
        c.execute("UPDATE orders SET delivery_neighborhood=COALESCE(neighborhood,'')")
    c.executescript('''CREATE INDEX IF NOT EXISTS idx_orders_store_created ON orders(professional_id,created_at);
    CREATE INDEX IF NOT EXISTS idx_orders_status_created ON orders(status,created_at);
    CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at,id);
    CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
    CREATE INDEX IF NOT EXISTS idx_visits_store_day ON analytics_events(professional_id,created_at);
    CREATE TABLE IF NOT EXISTS idempotency_keys(store_id INTEGER NOT NULL,key TEXT NOT NULL,order_id INTEGER NOT NULL REFERENCES orders(id),response_json TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(store_id,key));
    CREATE TABLE IF NOT EXISTS saved_carts(user_id INTEGER NOT NULL,store_id INTEGER NOT NULL,payload TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(user_id,store_id));''')

def bounds(q):
    try:
        first=date.fromisoformat(q.get('from') or datetime.now(TZ).date().isoformat())
        last=date.fromisoformat(q.get('to') or first.isoformat())
        if last<first:raise ValueError()
        h1=q.get('hour_from','');h2=q.get('hour_to','')
        start=datetime.combine(first,datetime.min.time(),TZ)
        end=datetime.combine(last+timedelta(days=1),datetime.min.time(),TZ)
        hours=None
        if h1!='' and h2!='':
            a,b=int(h1),int(h2)
            if not(0<=a<=23 and 0<=b<=23) or a==b:raise ValueError()
            start+=timedelta(hours=a);end=datetime.combine(last,datetime.min.time(),TZ)+timedelta(hours=b,days=int(b<a));hours=(a*60,b*60)
        elif h1!='' or h2!='':raise ValueError()
        return start.astimezone(timezone.utc).isoformat(),end.astimezone(timezone.utc).isoformat(),hours
    except ValueError:raise HTTPException(422,'Datas ou turno inválidos. Use início e fim do turno juntos.')

def where(q,completed=False):
    lower,upper,hours=bounds(q);clauses=['o.created_at>=?','o.created_at<?','p.is_demo=0'];params=[lower,upper]
    if completed:clauses.append("o.status='completed'")
    if q.get('city'):clauses.append('p.city=?');params.append(q['city'])
    if q.get('store'):
        try:store=int(q['store'])
        except ValueError:raise HTTPException(422,'Loja inválida')
        clauses.append('o.professional_id=?');params.append(store)
    if q.get('neighborhood'):clauses.append('o.delivery_neighborhood=?');params.append(q['neighborhood'])
    if q.get('status') and not completed:clauses.append('o.status=?');params.append(q['status'])
    if q.get('q'):clauses.append('(o.order_code LIKE ? OR o.customer_name LIKE ?)');params.extend(['%'+q['q'][:120]+'%']*2)
    if hours:
        a,b=hours;minute="(CAST(strftime('%H',o.created_at,'-3 hours') AS INTEGER)*60+CAST(strftime('%M',o.created_at,'-3 hours') AS INTEGER))"
        clauses.append('('+minute+'>=? '+('AND' if a<b else 'OR')+' '+minute+'<?)');params.extend([a,b])
    return ' AND '.join(clauses),params

def order_record(r,items=None):
    dt=datetime.fromisoformat(r['created_at'].replace('Z','+00:00'));dt=dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt;dt=dt.astimezone(TZ)
    keys=r.keys()
    return dict(id=r['id'],store=r['professional_id'],customer=r['customer_id'],date=dt.date().isoformat(),hour=dt.hour,minute=dt.minute,total=r['total_cents'],delivery=r['delivery_fee_cents'],status=r['status'],live=r['status'] not in ('completed','cancelled','rejected'),createdAt=r['created_at'],items=items or [],courier=None,coupon='',neighborhood=r['delivery_neighborhood'],city=r['city'] if 'city' in keys else '',storeName=r['store_name'] if 'store_name' in keys else '',customerName=r['customer_name'])

@router.get('/admin/super/api/metrics')
def metrics(request:Request):
    with connection() as c:
        actor=authorize(request,c,'dashboard');clause,params=where(request.query_params,True)
        revision=c.execute('SELECT revision FROM adm227_state WHERE id=1').fetchone()[0]
        key=(str(G['db_path']),actor['actor_id'],tuple(sorted(actor['permissions'])),revision,clause,tuple(params))
        with _lock:cached=_cache.get(key)
        if cached and cached[0]>time.monotonic():return JSONResponse(cached[1],headers={'Cache-Control':'private, no-store'})
        r=c.execute('SELECT COUNT(*) count,COALESCE(SUM(o.total_cents),0) gmv FROM orders o JOIN professionals p ON p.id=o.professional_id WHERE '+clause,params).fetchone()
        result={'count':r['count'],'gmv':r['gmv'],'ticket':round(r['gmv']/r['count'],2) if r['count'] else 0,'currency':'BRL','unit':'cents','cache_ttl':30}
        with _lock:
            if len(_cache)>256:_cache.clear()
            _cache[key]=(time.monotonic()+30,result)
        return JSONResponse(result,headers={'Cache-Control':'private, no-store'})

@router.get('/admin/super/api/orders')
def orders(request:Request,page:int=1,limit:int=50):
    if page<1 or not 1<=limit<=50:raise HTTPException(422,'Página ou limite inválido (1–50).')
    with connection() as c:
        authorize(request,c,'orders');clause,params=where(request.query_params)
        total=c.execute('SELECT COUNT(*) FROM orders o JOIN professionals p ON p.id=o.professional_id WHERE '+clause,params).fetchone()[0]
        rows=c.execute('SELECT o.*,p.city,p.display_name store_name FROM orders o JOIN professionals p ON p.id=o.professional_id WHERE '+clause+' ORDER BY o.created_at DESC,o.id DESC LIMIT ? OFFSET ?',(*params,limit,(page-1)*limit)).fetchall()
        items={}
        if rows:
            ids=[r['id'] for r in rows]
            for i in c.execute('SELECT * FROM order_items WHERE order_id IN ('+','.join('?'*len(ids))+')',ids):items.setdefault(i['order_id'],[]).append({'name':i['product_name'],'qty':i['quantity'],'price':i['unit_price_cents']})
        return JSONResponse({'items':[order_record(r,items.get(r['id'])) for r in rows],'page':page,'limit':limit,'total':total},headers={'Cache-Control':'private, no-store'})

@router.get('/admin/super/api/analytics/hourly')
def hourly(request:Request):
    with connection() as c:
        authorize(request,c,'dashboard');clause,params=where(request.query_params,True)
        rows=c.execute("SELECT CAST(strftime('%H',o.created_at,'-3 hours') AS INTEGER) hour,COUNT(*) count,SUM(o.total_cents) gmv FROM orders o JOIN professionals p ON p.id=o.professional_id WHERE "+clause+' GROUP BY hour ORDER BY hour',params).fetchall()
        return JSONResponse({'items':[dict(r) for r in rows],'timezone':'America/Sao_Paulo'},headers={'Cache-Control':'private, no-store'})

@router.get('/admin/super/api/customers')
def customers(request:Request,page:int=1,limit:int=50):
    if page<1 or not 1<=limit<=50:raise HTTPException(422,'Página ou limite inválido')
    with connection() as c:
        authorize(request,c,'customers');q=request.query_params;clauses=["role='customer'"];params=[]
        for key in ('city','neighborhood'):
            if q.get(key):clauses.append(key+'=?');params.append(q[key])
        if q.get('q'):clauses.append('(name LIKE ? OR email LIKE ?)');params.extend(['%'+q['q'][:120]+'%']*2)
        sql=' FROM users WHERE '+' AND '.join(clauses);total=c.execute('SELECT COUNT(*)'+sql,params).fetchone()[0]
        rows=c.execute('SELECT id,name,email,phone,city,neighborhood,is_active'+sql+' ORDER BY id DESC LIMIT ? OFFSET ?',(*params,limit,(page-1)*limit)).fetchall()
        return JSONResponse({'items':[dict(r) for r in rows],'total':total,'page':page,'limit':limit},headers={'Cache-Control':'private, no-store'})

from contextlib import contextmanager
@contextmanager
def connection():
    c=G['db']()
    try:
        yield c;c.commit()
    except Exception:c.rollback();raise
    finally:c.close()

@router.get('/admin/super/api/products')
def products(request:Request,page:int=1,limit:int=50):
    if page<1 or not 1<=limit<=50:raise HTTPException(422,'Página ou limite inválido')
    with connection() as c:
        authorize(request,c,'products');q=request.query_params;clauses=['p.is_demo=0'];params=[]
        for key,column in [('city','p.city'),('store','pr.professional_id')]:
            if q.get(key):clauses.append(column+'=?');params.append(q[key])
        if q.get('q'):clauses.append('pr.name LIKE ?');params.append('%'+q['q'][:120]+'%')
        sql=' FROM products pr JOIN professionals p ON p.id=pr.professional_id WHERE '+' AND '.join(clauses)
        total=c.execute('SELECT COUNT(*)'+sql,params).fetchone()[0]
        rows=c.execute('SELECT pr.id,pr.name,pr.category,pr.price_cents,pr.available,pr.professional_id,p.display_name store_name'+sql+' ORDER BY pr.id DESC LIMIT ? OFFSET ?',(*params,limit,(page-1)*limit)).fetchall()
        return JSONResponse({'items':[dict(r) for r in rows],'total':total,'page':page,'limit':limit},headers={'Cache-Control':'private, no-store'})
