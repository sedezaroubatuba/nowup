"""Relatórios por loja: vendas finalizadas, período local e origem futura."""
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException, Request
TZ=ZoneInfo('America/Sao_Paulo')
DAYS=['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']
PAYMENTS={'pix':'Pix','cash':'Dinheiro','credit':'Crédito','debit':'Débito','card':'Cartão','credit_card':'Crédito','debit_card':'Débito'}

def init(conn):
    for table,col,definition in [('orders','sales_channel',"TEXT NOT NULL DEFAULT 'online'"),('order_items','category_snapshot',"TEXT NOT NULL DEFAULT ''")]:
        if col not in {r[1] for r in conn.execute('PRAGMA table_info('+table+')')}:
            conn.execute('ALTER TABLE '+table+' ADD COLUMN '+col+' '+definition)
    conn.execute('CREATE INDEX IF NOT EXISTS idx_reports98_store_date ON orders(professional_id,created_at)')
    conn.commit()

def period(preset,start,end,today):
    try:
        if start and end: a,b=date.fromisoformat(start),date.fromisoformat(end)
        elif preset=='today':a=b=today
        elif preset=='7':a,b=today-timedelta(days=6),today
        elif preset=='month':a,b=today.replace(day=1),today
        else:a,b=today-timedelta(days=29),today
    except ValueError:raise HTTPException(400,'Datas inválidas')
    if a>b:raise HTTPException(400,'A data inicial deve vir antes da final')
    if (b-a).days>365:raise HTTPException(400,'Escolha até 366 dias')
    return a,b

def bounds(a,b):
    return (datetime.combine(a,time.min,TZ).astimezone(timezone.utc).isoformat(),datetime.combine(b+timedelta(days=1),time.min,TZ).astimezone(timezone.utc).isoformat())

def build(conn,pid,a,b,source='all',ranking='most'):
    if source not in ('all','online','table'):raise HTTPException(400,'Origem inválida')
    if ranking not in ('most','least','zero'):raise HTTPException(400,'Ordenação inválida')
    where='professional_id=? AND created_at>=? AND created_at<?';params=[pid,*bounds(a,b)]
    if source!='all':where+=' AND sales_channel=?';params.append(source)
    orders=[dict(r) for r in conn.execute('SELECT * FROM orders WHERE '+where,params)]
    done=[o for o in orders if o['status']=='completed'];cancelled=[o for o in orders if o['status'] in ('cancelled','rejected')]
    total=sum(o['total_cents'] for o in done)
    previous_a=a-timedelta(days=(b-a).days+1);previous_b=a-timedelta(days=1)
    oldparams=[pid,*bounds(previous_a,previous_b)]+([source] if source!='all' else [])
    old=conn.execute("SELECT COALESCE(SUM(total_cents),0) FROM orders WHERE "+where+" AND status='completed'",oldparams).fetchone()[0]
    daily=defaultdict(lambda:[0,0]);hours=defaultdict(lambda:[0,0]);weekly={i:[0,0] for i in range(7)};payments=defaultdict(lambda:[0,0]);channels=defaultdict(lambda:[0,0]);reasons=defaultdict(int)
    for o in done:
        dt=datetime.fromisoformat(o['created_at']);dt=(dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt).astimezone(TZ)
        for bucket,key in [(daily,dt.date().isoformat()),(hours,dt.hour),(weekly,dt.weekday()),(payments,o['payment_method']),(channels,o['sales_channel'])]:bucket[key][0]+=1;bucket[key][1]+=o['total_cents']
    for o in cancelled:reasons[o['cancellation_reason'] or 'Sem motivo registrado']+=1
    products={r['id']:{'name':r['name'],'category':r['category'] or 'Geral','available':r['available'],'qty':0,'cents':0,'deleted':False} for r in conn.execute('SELECT id,name,category,available FROM products WHERE professional_id=?',(pid,))}
    categories=defaultdict(lambda:[0,0]);legacy=False
    # JOIN com os pedidos filtra a loja e o período antes de carregar itens.
    itemwhere=where.replace('professional_id','o.professional_id').replace('created_at','o.created_at').replace('sales_channel','o.sales_channel')
    for r in conn.execute("SELECT oi.* FROM order_items oi JOIN orders o ON o.id=oi.order_id WHERE "+itemwhere+" AND o.status='completed'",params):
        key=r['product_id'] if r['product_id'] in products else ('removed',r['product_id'],r['product_name'])
        p=products.setdefault(key,{'name':r['product_name'],'category':'Categoria não registrada','available':0,'qty':0,'cents':0,'deleted':True})
        value=r['quantity']*r['unit_price_cents'];p['qty']+=r['quantity'];p['cents']+=value
        category=r['category_snapshot'] or (p['category'] if not p['deleted'] else 'Categoria não registrada')
        if not r['category_snapshot']:legacy=True
        categories[category][0]+=r['quantity'];categories[category][1]+=value
    rows=list(products.values())
    if ranking=='zero':rows=[p for p in rows if p['qty']==0 and not p['deleted']]
    rows.sort(key=lambda p:((-p['qty'] if ranking=='most' else p['qty']),p['name'].lower()))
    return dict(total=total,count=len(done),ticket=round(total/len(done)) if done else 0,previous=old,change=round((total-old)*100/old,1) if old else None,
        cancelled=len(cancelled),cancelled_value=sum(o['total_cents'] for o in cancelled),pending=len(orders)-len(done)-len(cancelled),products=rows,
        daily=sorted(daily.items()),hours=sorted(hours.items(),key=lambda r:(-r[1][0],r[0])),weekly=[(DAYS[k],v) for k,v in weekly.items()],
        payments=[(PAYMENTS.get(k,k or 'Não informado'),v) for k,v in payments.items()],channels=[({'online':'Online','table':'Mesas'}.get(k,k),v) for k,v in channels.items()],
        categories=sorted(categories.items(),key=lambda r:-r[1][1]),reasons=sorted(reasons.items(),key=lambda r:-r[1]),legacy=legacy)

def install(app,db,require_user,templates,context):
    router=APIRouter()
    @app.on_event('startup')
    def setup():
        conn=db()
        try:init(conn)
        finally:conn.close()
    @router.get('/painel/relatorios')
    def report(request:Request,preset:str='30',inicio:str='',fim:str='',origem:str='all',ranking:str='most'):
        user=require_user(request,'professional');a,b=period(preset,inicio,fim,datetime.now(TZ).date());conn=db()
        try:
            pro=conn.execute('SELECT * FROM professionals WHERE user_id=?',(user['id'],)).fetchone()
            if not pro:raise HTTPException(404,'Loja não encontrada')
            data=build(conn,pro['id'],a,b,origem,ranking)
        finally:conn.close()
        return templates.TemplateResponse('reports98.html',context(request,report=data,start=a.isoformat(),end=b.isoformat(),origin=origem,ranking=ranking,pro=pro))
    app.include_router(router)
