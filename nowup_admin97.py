"""Central administrativa V97: pedidos internos, acesso exclusivo ao administrador."""
from collections import defaultdict
from datetime import datetime, date, timedelta, timezone
from calendar import monthrange
from zoneinfo import ZoneInfo
import sqlite3
import inspect
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from nowup_sales107 import admin_delivery_rows, admin_delivery_items

router = APIRouter()
TZ = ZoneInfo('America/Sao_Paulo')
_db = _auth = _templates = _context = None
STATUS = {'new':'A confirmar','confirmed':'Aceito','preparing':'Preparando','ready':'Pronto','out_for_delivery':'Em entrega','completed':'Concluído','cancelled':'Cancelado','rejected':'Recusado'}

def configure(db, auth, templates, context):
    global _db, _auth, _templates, _context
    _db, _auth, _templates, _context = db, auth, templates, context

def render(request, name, data):
    kwargs = dict(name=name, context=_context(request, **data))
    if 'request' in inspect.signature(_templates.TemplateResponse).parameters:
        kwargs['request'] = request
    return _templates.TemplateResponse(**kwargs)

def init_support():
    with _db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS admin_support97(
          id INTEGER PRIMARY KEY, order_id INTEGER REFERENCES orders(id),
          requester TEXT NOT NULL, subject TEXT NOT NULL, details TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'open', responsible TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS admin_support_history97(
          id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL REFERENCES admin_support97(id),
          admin_id INTEGER NOT NULL REFERENCES users(id), note TEXT NOT NULL, created_at TEXT NOT NULL);''')
    c.close()

def local_day(raw):
    dt = datetime.fromisoformat(raw.replace('Z','+00:00'))
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ).date()

def bounds(start, end):
    return (datetime.combine(start, datetime.min.time(), TZ).astimezone(timezone.utc).isoformat(),
            datetime.combine(end + timedelta(days=1), datetime.min.time(), TZ).astimezone(timezone.utc).isoformat())

def percent(current, previous):
    return round((current-previous)*100/previous, 1) if previous else None

def bucket(): return {'count':0,'cents':0}

def increment(groups, key, cents, quantity=1):
    groups[key]['count'] += quantity
    groups[key]['cents'] += cents

def ranked(groups):
    return [dict(label=k, **v) for k,v in sorted(groups.items(), key=lambda kv:(-kv[1]['cents'],-kv[1]['count'],str(kv[0])))]

def report(c, params, today=None):
    today = today or datetime.now(TZ).date()
    try:
        start=date.fromisoformat(params.get('inicio') or today.replace(day=1).isoformat())
        end=date.fromisoformat(params.get('fim') or today.isoformat())
    except ValueError: raise HTTPException(400, 'Datas inválidas.')
    if start>end or (end-start).days>366: raise HTTPException(400,'Escolha um período de até 367 dias, com início anterior ao fim.')
    filters = {k:str(params.get(k,'')).strip() for k in ('loja','cidade','bairro','pagamento','status','categoria')}
    if filters['status'] and filters['status'] not in STATUS: raise HTTPException(400,'Status inválido.')
    clauses=[]; args=[]
    for key,col in [('loja','p.id'),('cidade','p.city'),('bairro','p.neighborhood'),('pagamento','o.payment_method'),('status','o.status')]:
        if filters[key]: clauses.append(col+'=?'); args.append(filters[key])
    if filters['categoria']:
        clauses.append('EXISTS(SELECT 1 FROM professional_categories pc WHERE pc.professional_id=p.id AND pc.category_id=?)'); args.append(filters['categoria'])
    extra=(' AND '+' AND '.join(clauses)) if clauses else ''
    def orders_between(a,b):
        lower,upper=bounds(a,b)
        online=[dict(x) for x in c.execute('''SELECT o.*,p.display_name,p.city,p.neighborhood store_neighborhood
          FROM orders o JOIN professionals p ON p.id=o.professional_id
          WHERE p.is_demo=0 AND julianday(o.created_at)>=julianday(?) AND julianday(o.created_at)<julianday(?)'''+extra+' ORDER BY o.created_at DESC,o.id DESC', [lower,upper]+args)]
        return sorted(online+admin_delivery_rows(c,a,b,filters),key=lambda r:r['created_at'],reverse=True)
    orders=orders_between(start,end)
    origin_rows = {}
    for o in orders:
        origin = o.get('order_origin','legacy')
        label = {'external':'Link externo da loja','nowup':'Vitrine NowUp','manual_delivery':'Delivery lançado pelo lojista'}.get(origin,'Anterior à identificação de origem')
        key = (o['display_name'], label)
        entry = origin_rows.setdefault(key, dict(store=o['display_name'],channel=label,count=0,completed=0,cents=0))
        entry['count'] += 1
        if o['status']=='completed': entry['completed'] += 1; entry['cents'] += o['total_cents']
    completed=[o for o in orders if o['status']=='completed']
    cancelled=[o for o in orders if o['status'] in ('cancelled','rejected')]
    revenue=sum(o['total_cents'] for o in completed)
    daily=defaultdict(bucket); payments=defaultdict(bucket); stores=defaultdict(bucket); hours=defaultdict(bucket); cats=defaultdict(bucket)
    for o in completed:
        increment(daily,local_day(o['created_at']).isoformat(),o['total_cents'])
        if o.get('manual_payments'):
            for pay in o['manual_payments']:
                if not filters['pagamento'] or pay['method']==filters['pagamento']: increment(payments,pay['method'],pay['cents'])
        else: increment(payments,o['payment_method'],o['total_cents'])
        increment(stores,f"{o['display_name']} (#{o['professional_id']})",o['total_cents'])
        hour=datetime.fromisoformat(o['created_at'].replace('Z','+00:00'))
        if hour.tzinfo is None: hour=hour.replace(tzinfo=timezone.utc)
        increment(hours,hour.astimezone(TZ).strftime('%Hh'),o['total_cents'])
    by_id={o['id']:o for o in completed}
    lower,upper=bounds(start,end)
    # Consultas usam os mesmos filtros; produtos apagados mantêm o nome salvo no pedido.
    items=c.execute('''SELECT i.*,pr.category current_category FROM order_items i
      JOIN orders o ON o.id=i.order_id JOIN professionals p ON p.id=o.professional_id
      LEFT JOIN products pr ON pr.id=i.product_id AND pr.professional_id=o.professional_id
      WHERE p.is_demo=0 AND o.status='completed' AND julianday(o.created_at)>=julianday(?)
      AND julianday(o.created_at)<julianday(?)'''+extra,[lower,upper]+args).fetchall()
    items=list(items)+admin_delivery_items(c,completed)
    products=defaultdict(bucket)
    for i in items:
        o=by_id.get(i['order_id'])
        if not o: continue
        value=i['quantity']*i['unit_price_cents']
        label=f"{i['product_name']} — {o['display_name']} (#{o['professional_id']}, produto {i['product_id'] or 'removido'})"
        increment(products,label,value,i['quantity'])
        increment(cats,i['current_category'] or 'Sem categoria / produto removido',value,i['quantity'])
    monthly=[]
    month=today.replace(day=1)
    for _ in range(12):
        last=month.replace(day=monthrange(month.year,month.month)[1])
        stop=min(last,today)
        rows=orders_between(month,stop)
        done=[o for o in rows if o['status']=='completed']
        previous_end=month-timedelta(days=1)
        previous_start=previous_end.replace(day=1)
        # Mês aberto compara o mesmo número de dias, limitado ao mês anterior.
        compare_end=previous_end if stop==last else previous_start.replace(day=min(stop.day,previous_end.day))
        previous=[o for o in orders_between(previous_start,compare_end) if o['status']=='completed']
        cents=sum(o['total_cents'] for o in done); prev=sum(o['total_cents'] for o in previous)
        monthly.append({'month':month.strftime('%Y-%m'),'cents':cents,'count':len(done),'ticket':round(cents/len(done)) if done else 0,'growth':percent(cents,prev),'basis':f'{previous_start:%d/%m} a {compare_end:%d/%m}','partial':stop!=last})
        month=previous_start
    elapsed=today.day
    current=monthly[0]
    projection=round(current['cents']/elapsed*monthrange(today.year,today.month)[1]) if elapsed>=7 and current['count']>=10 else None
    pros=[dict(r) for r in c.execute('SELECT id,display_name,city,neighborhood,blocked,admission_status,plan_active FROM professionals WHERE is_demo=0 ORDER BY display_name')]
    selected_pros=[p for p in pros if (not filters['loja'] or str(p['id'])==filters['loja']) and (not filters['cidade'] or p['city']==filters['cidade']) and (not filters['bairro'] or p['neighborhood']==filters['bairro'])]
    if filters['categoria']:
        ids={str(r[0]) for r in c.execute('SELECT professional_id FROM professional_categories WHERE category_id=?',(filters['categoria'],))}
        selected_pros=[p for p in selected_pros if str(p['id']) in ids]
    locations=defaultdict(lambda:{'stores':0,'active':0})
    for p in selected_pros:
        key=(p['city'] or 'Não informada')+' / '+(p['neighborhood'] or 'Não informado')
        locations[key]['stores']+=1
        locations[key]['active']+=int(not p['blocked'] and p['admission_status']=='approved' and p['plan_active'] in ('vitrine','cardapio','ambos'))
    customers=[dict(r) for r in c.execute("SELECT id,name,phone,email,neighborhood,created_at FROM users WHERE role='customer' ORDER BY id DESC")]
    customer_regions=defaultdict(int)
    for u in customers: customer_regions[u['neighborhood'] or 'Não informado']+=1
    history=defaultdict(list)
    for o in completed:
        if o['customer_id']: history[o['customer_id']].append(o)
    active_customers=[]
    for u in customers:
        rows=history[u['id']]
        if rows:
            active_customers.append(dict(u,count=len(rows),cents=sum(o['total_cents'] for o in rows),stores=', '.join(sorted({o['display_name'] for o in rows})),last=rows[0]['created_at']))
    daily_rows=[]; day=start
    while day<=end:
        daily_rows.append(dict(label=day.isoformat(),**daily[day.isoformat()])); day+=timedelta(days=1)
    return dict(origin_rows=sorted(origin_rows.values(),key=lambda x:(x["store"],x["channel"])),start=start.isoformat(),end=end.isoformat(),filters=filters,orders=orders[:100],cancelled=cancelled[:100],
      total_orders=len(orders),completed_count=len(completed),cancelled_count=len(cancelled),cents=revenue,
      ticket=round(revenue/len(completed)) if completed else 0,cancel_rate=round(100*len(cancelled)/len(orders),1) if orders else 0,
      daily=daily_rows,payments=ranked(payments),stores=ranked(stores),products=ranked(products),product_categories=ranked(cats),hours=ranked(hours),
      monthly=list(reversed(monthly)),projection=projection,pros=pros,locations=[dict(label=k,**v) for k,v in sorted(locations.items())],
      customer_count=len(customers),new_customers=sum(start<=local_day(u['created_at'])<=end for u in customers),
      customer_regions=[dict(label=k,count=v) for k,v in sorted(customer_regions.items(),key=lambda x:-x[1])],
      active_customers=sorted(active_customers,key=lambda u:-u['cents'])[:100],
      categories=[dict(r) for r in c.execute('SELECT id,name FROM categories ORDER BY name')],
      statuses=STATUS,cities=sorted({p['city'] for p in pros if p['city']}),neighborhoods=sorted({p['neighborhood'] for p in pros if p['neighborhood']}),
      payment_choices=[r[0] for r in c.execute("SELECT DISTINCT payment_method FROM orders ORDER BY payment_method")])

@router.get('/admin/gestao')
def dashboard(request:Request):
    _auth(request,'admin')
    c=_db()
    try:
        data=report(c,request.query_params)
        data['tickets']=[dict(r) for r in c.execute('SELECT * FROM admin_support97 ORDER BY id DESC LIMIT 100')]
        data['ticket_history']=[dict(r) for r in c.execute('SELECT h.*,u.name admin_name FROM admin_support_history97 h JOIN users u ON u.id=h.admin_id ORDER BY h.id DESC LIMIT 300')]
    finally: c.close()
    response=render(request, 'admin_gestao97.html', data)
    response.headers['Cache-Control']='no-store'
    return response

@router.get('/admin/gestao/cliente/{uid}')
def customer(request:Request,uid:int):
    _auth(request,'admin'); c=_db()
    try:
        user=c.execute("SELECT id,name,neighborhood FROM users WHERE id=? AND role='customer'",(uid,)).fetchone()
        if not user: raise HTTPException(404,'Cliente não encontrado.')
        orders=[dict(r) for r in c.execute('SELECT o.*,p.display_name FROM orders o JOIN professionals p ON p.id=o.professional_id WHERE o.customer_id=? AND p.is_demo=0 ORDER BY o.id DESC LIMIT 100',(uid,))]
        items=[dict(r) for r in c.execute('SELECT i.* FROM order_items i WHERE i.order_id IN (SELECT o.id FROM orders o JOIN professionals p ON p.id=o.professional_id WHERE o.customer_id=? AND p.is_demo=0 ORDER BY o.id DESC LIMIT 100)',(uid,))]
    finally:c.close()
    response=render(request, 'admin_cliente97.html', dict(client=dict(user), orders=orders, items=items, statuses=STATUS))
    response.headers['Cache-Control']='no-store'
    return response

@router.post('/admin/gestao/suporte')
def new_ticket(request:Request,requester:str=Form(...),subject:str=Form(...),details:str=Form(...),order_id:str=Form('')):
    user=_auth(request,'admin')
    if not requester.strip() or not subject.strip() or not details.strip(): raise HTTPException(400,'Preencha o chamado.')
    try: oid=int(order_id) if order_id.strip() else None
    except ValueError: raise HTTPException(400,'Número do pedido inválido.')
    c=_db(); stamp=datetime.now(timezone.utc).isoformat()
    try:
        if oid and not c.execute('SELECT 1 FROM orders WHERE id=?',(oid,)).fetchone(): raise HTTPException(400,'Pedido não encontrado.')
        cur=c.execute('INSERT INTO admin_support97(order_id,requester,subject,details,created_at,updated_at) VALUES(?,?,?,?,?,?)',(oid,requester.strip()[:120],subject.strip()[:160],details.strip()[:4000],stamp,stamp))
        c.execute('INSERT INTO admin_support_history97(ticket_id,admin_id,note,created_at) VALUES(?,?,?,?)',(cur.lastrowid,user['id'],'Chamado criado',stamp));c.commit()
    finally:c.close()
    return RedirectResponse('/admin/gestao#suporte',303)

@router.post('/admin/gestao/suporte/{tid}')
def update_ticket(request:Request,tid:int,status:str=Form(...),responsible:str=Form(''),note:str=Form('')):
    user=_auth(request,'admin')
    if status not in ('open','in_progress','resolved'):raise HTTPException(400,'Status inválido.')
    c=_db();stamp=datetime.now(timezone.utc).isoformat()
    try:
        if not c.execute('SELECT 1 FROM admin_support97 WHERE id=?',(tid,)).fetchone():raise HTTPException(404,'Chamado não encontrado.')
        c.execute('UPDATE admin_support97 SET status=?,responsible=?,updated_at=? WHERE id=?',(status,responsible.strip()[:120],stamp,tid))
        c.execute('INSERT INTO admin_support_history97(ticket_id,admin_id,note,created_at) VALUES(?,?,?,?)',(tid,user['id'],f'Status: {status}; responsável: {responsible.strip()[:120]}. {note.strip()[:2000]}',stamp));c.commit()
    finally:c.close()
    return RedirectResponse('/admin/gestao#suporte',303)
